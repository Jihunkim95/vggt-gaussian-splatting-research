#!/usr/bin/env python3
"""
3D Gaussian Splatting을 위한 품질 기반 이미지 샘플링 도구

계층화 품질 샘플링 (Stratified Quality Sampling):
- 이미지를 시간적 구간(계층)으로 분할
- 각 구간에서 최고 품질 이미지 선택
- COLMAP Sequential Matching을 위한 시간적 커버리지 보장
- 3DGS 재구성 성공률 최적화

사용 기술:
- BRISQUE: 통계적 자연스러움 기반 품질 평가
- Laplacian Sharpness: 선명도 기반 품질 평가
- Stratified Sampling: 시간적 커버리지 보장 샘플링

작성자: VGGT Research Team
작성일: 2025-11-03
"""

import argparse
import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
import numpy as np
from PIL import Image
from tqdm import tqdm


# ============================================================================
# 품질 측정 메트릭
# ============================================================================

def compute_brisque_score(img_path: str) -> float:
    """
    BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator) 점수 계산

    특징:
    - 참조 이미지 없이 품질 평가 가능
    - 통계적 자연스러움 기반
    - 낮은 점수 = 높은 품질 (내부적으로 반전하여 반환)

    Args:
        img_path: 이미지 파일 경로

    Returns:
        품질 점수 (0~1, 높을수록 좋음)
    """
    try:
        from skimage import io, color
        from skimage.filters import gaussian

        # 이미지 로드 및 그레이스케일 변환
        img = io.imread(img_path)
        if len(img.shape) == 3:
            img = color.rgb2gray(img)

        # 지역 평균 및 분산 특성 계산
        mu = gaussian(img, sigma=1.5, mode='nearest')
        sigma = np.sqrt(np.abs(gaussian(img**2, sigma=1.5, mode='nearest') - mu**2))

        # 정규화
        sigma_eps = sigma + 1e-10
        features = (img - mu) / sigma_eps

        # 간단한 품질 메트릭: 분산의 역수
        quality = 1.0 / (1.0 + np.std(features))

        return float(quality)

    except Exception as e:
        print(f"⚠️  BRISQUE 계산 실패 ({img_path}): {e}")
        return 0.5  # 중립 점수 반환


def compute_sharpness_score(img_path: str) -> float:
    """
    라플라시안 분산을 이용한 선명도 점수 계산

    원리:
    - 라플라시안 필터는 에지(경계)를 강조
    - 선명한 이미지는 높은 라플라시안 분산을 가짐
    - 흐릿한 이미지는 낮은 분산을 가짐

    Args:
        img_path: 이미지 파일 경로

    Returns:
        선명도 점수 (0~1, 높을수록 선명)
    """
    try:
        img = Image.open(img_path).convert('L')  # 그레이스케일 변환
        img_array = np.array(img, dtype=float)

        # 라플라시안 커널 (에지 검출용)
        laplacian = np.array([[0, -1, 0],
                             [-1, 4, -1],
                             [0, -1, 0]])

        # 컨볼루션 적용
        from scipy.ndimage import convolve
        response = convolve(img_array, laplacian)

        # 라플라시안 응답의 분산 계산
        sharpness = response.var()

        # 0-1 범위로 정규화 (휴리스틱)
        normalized = min(sharpness / 1000.0, 1.0)

        return float(normalized)

    except Exception as e:
        print(f"⚠️  선명도 계산 실패 ({img_path}): {e}")
        return 0.5


def compute_quality_score(img_path: str) -> float:
    """
    통합 품질 점수 계산 (BRISQUE 50% + Sharpness 50%)

    Args:
        img_path: 이미지 파일 경로

    Returns:
        통합 품질 점수 (높을수록 좋음)
    """
    brisque = compute_brisque_score(img_path)
    sharpness = compute_sharpness_score(img_path)

    # 50:50 가중 평균
    combined = 0.5 * brisque + 0.5 * sharpness
    return float(combined)


# ============================================================================
# 계층화 품질 샘플링 (핵심 알고리즘)
# ============================================================================

def sample_images_stratified(
    image_dir: str,
    output_dir: str,
    target_count: int = 60,
    num_strata: int = 10
) -> Tuple[List[str], List[float]]:
    """
    계층화 품질 기반 샘플링 (COLMAP 친화적)

    핵심 원리:
    - 시간적 커버리지 보장: 전체 시퀀스를 N개 구간으로 분할
    - 품질 최적화: 각 구간에서 최고 품질 이미지 선택
    - COLMAP Sequential Matching 성공률 극대화

    알고리즘:
    1. 이미지를 N개 계층(시간 구간)으로 분할
    2. 각 계층에서 품질 상위 K개 이미지 선택
    3. 결과: 시간적 균등 분포 + 품질 최적화

    Args:
        image_dir: 입력 이미지 디렉토리
        output_dir: 출력 디렉토리
        target_count: 최종 이미지 수 (기본값: 60)
        num_strata: 시간 구간 수 (기본값: 10)

    Returns:
        (선택된 이미지 경로 리스트, 품질 점수 리스트)
    """

    # 이미지 파일 탐지
    image_files = sorted([
        f for f in Path(image_dir).iterdir()
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
    ])

    total_images = len(image_files)
    images_per_stratum = target_count // num_strata

    print(f"\n📊 계층화 품질 샘플링 시작")
    print(f"   전체 이미지 수: {total_images}장")
    print(f"   계층 수: {num_strata}개 구간")
    print(f"   계층당 선택: {images_per_stratum}장")
    print(f"   목표 출력: {num_strata * images_per_stratum}장")
    print(f"   평가 방법: BRISQUE 50% + Sharpness 50%")

    # 이미지를 계층으로 분할
    stratum_size = total_images // num_strata
    selected_images = []

    print(f"\n🔍 품질 평가 및 선택 진행:")

    for stratum_idx in range(num_strata):
        # 현재 계층의 이미지 범위 계산
        start_idx = stratum_idx * stratum_size
        end_idx = (stratum_idx + 1) * stratum_size if stratum_idx < num_strata - 1 else total_images
        stratum_images = image_files[start_idx:end_idx]

        # 현재 계층의 품질 점수 계산
        quality_scores = []
        for img_path in tqdm(stratum_images,
                            desc=f"계층 {stratum_idx+1}/{num_strata}",
                            leave=False):
            score = compute_quality_score(str(img_path))
            quality_scores.append((img_path, score))

        # 현재 계층에서 상위 K개 선택
        quality_scores.sort(key=lambda x: x[1], reverse=True)
        selected = quality_scores[:images_per_stratum]
        selected_images.extend(selected)

        # 계층별 통계 출력
        if selected:
            print(f"   계층 {stratum_idx+1:2d}: {len(selected):2d}장 선택, "
                  f"품질={selected[0][1]:.4f}~{selected[-1][1]:.4f}, "
                  f"프레임 {start_idx}~{end_idx-1}")

    print(f"\n✅ 총 {len(selected_images)}장 선택 완료 (시간적 커버리지 보장됨)")

    # 시간 순서로 정렬 (COLMAP용)
    selected_temporal = sorted(selected_images, key=lambda x: x[0].name)

    # 선택된 이미지와 메타데이터 저장
    _save_images_with_metadata(
        selected_temporal,
        selected_images,
        output_dir,
        total_images,
        num_strata,
        images_per_stratum
    )

    # 최종 경로와 점수 추출
    selected_paths = [str(Path(output_dir) / 'images' / f"{i:04d}.jpg")
                     for i in range(1, len(selected_temporal) + 1)]
    final_scores = [score for _, score in selected_temporal]

    return selected_paths, final_scores


def _save_images_with_metadata(
    selected_temporal: List[Tuple[Path, float]],
    selected_by_quality: List[Tuple[Path, float]],
    output_dir: str,
    total_images: int,
    num_strata: int,
    images_per_stratum: int
):
    """
    선택된 이미지와 메타데이터를 저장

    저장 구조:
    - output_dir/images/: 선택된 이미지 (0001.jpg, 0002.jpg, ...)
    - output_dir/quality_sampling_metadata.json: 샘플링 정보

    Args:
        selected_temporal: 시간순 정렬된 (이미지경로, 점수) 리스트
        selected_by_quality: 품질순 정렬된 (이미지경로, 점수) 리스트
        output_dir: 출력 디렉토리
        total_images: 원본 전체 이미지 수
        num_strata: 계층 수
        images_per_stratum: 계층당 이미지 수
    """
    os.makedirs(output_dir, exist_ok=True)
    images_dir = Path(output_dir) / 'images'
    os.makedirs(images_dir, exist_ok=True)

    # 품질 순위 맵 생성 (전역 순위)
    quality_ranking = {}
    all_sorted = sorted(selected_by_quality, key=lambda x: x[1], reverse=True)
    for rank, (img_path, score) in enumerate(all_sorted, 1):
        quality_ranking[img_path] = (rank, score)

    # 시간 순서로 이미지 복사 (COLMAP 호환)
    for idx, (img_path, _) in enumerate(selected_temporal, 1):
        dst_name = f"{idx:04d}.jpg"
        dst_path = images_dir / dst_name
        shutil.copy2(img_path, dst_path)

    # 통계용 점수 추출
    final_scores = [score for _, score in selected_temporal]

    # 메타데이터 생성 및 저장
    metadata = {
        'total_images': total_images,
        'final_count': len(selected_temporal),
        'method': 'stratified_brisque_sharpness',
        'num_strata': num_strata,
        'images_per_stratum': images_per_stratum,
        'quality_scores': {
            'min': float(np.min(final_scores)),
            'max': float(np.max(final_scores)),
            'mean': float(np.mean(final_scores)),
            'std': float(np.std(final_scores))
        },
        'naming_convention': 'temporal_order',
        'description': '계층화 품질 샘플링: BRISQUE 50% + Sharpness 50%',
        'selected_files': [
            {
                'colmap_name': f"{idx:04d}.jpg",
                'original_path': str(img_path),
                'quality_score': score,
                'quality_rank': rank
            }
            for idx, (img_path, (rank, score)) in enumerate(
                [(p, quality_ranking[p]) for p, _ in selected_temporal], 1
            )
        ]
    }

    metadata_path = Path(output_dir) / 'quality_sampling_metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n📁 {len(selected_temporal)}장 이미지 저장 완료: {images_dir}")
    print(f"📊 메타데이터 저장 완료: {metadata_path}")
    print(f"✅ COLMAP 호환 구조 준비 완료!")


# ============================================================================
# 비디오 처리
# ============================================================================

def extract_frames_from_video(video_path: str, intermediate_count: int = 300) -> str:
    """
    비디오 파일에서 프레임 추출 (ffmpeg 사용)

    처리 과정:
    1. 비디오 총 프레임 수 확인
    2. 균등 간격으로 프레임 추출
    3. 임시 디렉토리에 JPG로 저장

    Args:
        video_path: 비디오 파일 경로
        intermediate_count: 추출할 프레임 수

    Returns:
        추출된 프레임이 저장된 임시 디렉토리 경로
    """
    temp_dir = tempfile.mkdtemp(prefix="video_frames_")

    print(f"\n🎬 비디오에서 {intermediate_count}개 프레임 추출 중...")
    print(f"   비디오: {video_path}")
    print(f"   임시 디렉토리: {temp_dir}")

    # 총 프레임 수 확인
    probe_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-count_packets', '-show_entries', 'stream=nb_read_packets',
        '-of', 'csv=p=0', video_path
    ]

    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        total_frames = int(result.stdout.strip())
        frame_interval = max(1, total_frames // intermediate_count)

        print(f"   비디오 총 프레임: {total_frames}")
        print(f"   {frame_interval}프레임마다 추출...")

        # 프레임 추출 실행
        extract_cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"select='not(mod(n\\,{frame_interval}))'",
            '-vsync', 'vfr', '-q:v', '2',
            f'{temp_dir}/frame_%04d.jpg'
        ]

        subprocess.run(extract_cmd, check=True, capture_output=True)

        frame_count = len(list(Path(temp_dir).glob('*.jpg')))
        print(f"   ✅ {frame_count}개 프레임 추출 완료")

        return temp_dir

    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"프레임 추출 실패: {e}")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='3D Gaussian Splatting을 위한 계층화 품질 샘플링',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
계층화 품질 샘플링 (Stratified Quality Sampling):
  시간적 커버리지를 보장하면서 고품질 이미지를 선택합니다.
  COLMAP Sequential Matching 성공률을 최적화합니다.

품질 평가 방법:
  - BRISQUE: 통계적 자연스러움 기반 (50%)
  - Laplacian Sharpness: 선명도 기반 (50%)

사용 예시:
  # 기본 사용법 (10개 계층에서 60장 선택)
  python quality_sampler.py /data/tmp/frames

  # 상세 설정
  python quality_sampler.py /data/tmp/frames \\
      --output-dir ./datasets/my_scene \\
      --target-count 60 \\
      --num-strata 10

  # 비디오에서 직접 추출
  python quality_sampler.py video.mp4 \\
      --intermediate-count 300 \\
      --target-count 60
"""
    )

    parser.add_argument('input_dir', type=str,
                       help='입력 이미지 디렉토리 또는 비디오 파일 (.mp4, .avi, .mov)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='출력 디렉토리 (기본값: <입력경로>_quality)')
    parser.add_argument('--target-count', type=int, default=60,
                       help='목표 이미지 수 (기본값: 60)')
    parser.add_argument('--intermediate-count', type=int, default=300,
                       help='비디오에서 추출할 중간 프레임 수 (기본값: 300)')
    parser.add_argument('--num-strata', type=int, default=10,
                       help='시간 계층 수 (기본값: 10)')

    args = parser.parse_args()

    # 입력이 비디오인지 디렉토리인지 확인
    input_path = Path(args.input_dir)
    is_video = input_path.is_file() and input_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']
    temp_dir = None

    # 비디오인 경우 프레임 추출
    if is_video:
        temp_dir = extract_frames_from_video(str(input_path), args.intermediate_count)
        image_dir = temp_dir
    else:
        # 이미지 디렉토리 입력 - 2단계 샘플링 필요 여부 확인
        image_dir = str(input_path)

        # 디렉토리 내 이미지 수 확인
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        all_image_files = []
        for ext in image_extensions:
            all_image_files.extend(sorted(Path(image_dir).glob(ext)))

        image_count = len(all_image_files)

        # 대용량 디렉토리일 경우 2단계 샘플링 적용
        if image_count > args.intermediate_count:
            print(f"\n📊 대용량 이미지 디렉토리 감지: {image_count}장")
            print(f"   2단계 샘플링 적용: {image_count} → {args.intermediate_count} → {args.target_count}")

            # 1단계: 균등 샘플링으로 중간 개수로 축소
            interval = max(1, image_count // args.intermediate_count)
            sampled_files = [all_image_files[i] for i in range(0, image_count, interval)][:args.intermediate_count]

            # 샘플링된 이미지를 임시 디렉토리에 복사
            temp_dir = tempfile.mkdtemp(prefix="uniform_sample_")
            print(f"   임시 디렉토리 생성: {temp_dir}")

            for i, src in enumerate(sampled_files, start=1):
                dst = Path(temp_dir) / f"frame_{i:04d}{src.suffix}"
                shutil.copy2(src, dst)

            print(f"   ✅ {len(sampled_files)}장 균등 샘플링 완료")
            image_dir = temp_dir
        else:
            print(f"\n📊 이미지 디렉토리: {image_count}장 (직접 계층화 샘플링)")

    # 출력 디렉토리 결정
    if args.output_dir is None:
        args.output_dir = str(input_path.parent / f"{input_path.stem}_quality")

    print("=" * 70)
    print("🎯 3D Gaussian Splatting을 위한 계층화 품질 샘플링")
    print("=" * 70)
    print(f"📁 입력: {args.input_dir}")
    print(f"📁 출력: {args.output_dir}")
    print(f"🎯 목표: {args.target_count}장")
    print(f"📊 계층: {args.num_strata}개 시간 구간")
    print(f"🔧 방법: BRISQUE 50% + Sharpness 50%")

    try:
        # 계층화 품질 샘플링 실행
        selected_paths, scores = sample_images_stratified(
            image_dir,
            args.output_dir,
            args.target_count,
            args.num_strata
        )

    finally:
        # 임시 디렉토리 정리
        if temp_dir and Path(temp_dir).exists():
            print(f"\n🧹 임시 디렉토리 정리: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("✅ 계층화 품질 샘플링 완료!")
    print("   - 시간적 커버리지: 계층화 샘플링으로 보장")
    print("   - 품질 평가: BRISQUE 50% + Sharpness 50%")
    print("=" * 70)
    print(f"\n최종 출력: {args.output_dir}")
    print(f"\n다음 단계:")
    print(f"  1. 선택된 이미지 확인: ls {args.output_dir}/images")
    print(f"  2. 파이프라인 실행:")
    print(f"     ./run_pipeline.sh P4 {args.output_dir}")
    print(f"     ./run_pipeline.sh P5 {args.output_dir}")


if __name__ == '__main__':
    main()
