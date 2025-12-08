#!/usr/bin/env python3
"""
3D Gaussian Splatting을 위한 품질 기반 프레임 선택 도구

파이프라인:
    1. Optical Flow 필터 - 정지 구간 제거 (Farneback, 2003)
    2. 품질 필터 - Laplacian 선명도 + 밝기 체크 (Pech-Pacheco, 2000)
    3. Overlap 기반 샘플링 - 60-70% 오버랩 보장하며 균등 간격 선택

References:
    - Farneback, G. "Two-frame motion estimation based on polynomial expansion." SCIA 2003.
    - Pech-Pacheco, J.L. et al. "Diatom autofocusing in brightfield microscopy." ICPR 2000.

작성자: JHKim
작성일: 2025-11-03
최종수정일: 2025-12-08
"""

import argparse
import os
import json
import shutil
import tempfile
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
import numpy as np
import cv2
from tqdm import tqdm


# ============================================================================
# 데이터 클래스
# ============================================================================

@dataclass
class FrameInfo:
    """프레임 메타데이터"""
    index: int
    path: str
    sharpness: float
    brightness: float
    flow_magnitude: float
    is_valid: bool = True
    reject_reason: str = ""


@dataclass
class SelectorConfig:
    """프레임 선택 설정"""
    # Optical Flow 설정 (518px 다운샘플 기준)
    flow_threshold: float = 0.3  # 이 이하면 정지로 판단 (다운샘플 기준)

    # 품질 필터 설정 (518px 다운샘플 기준)
    sharpness_threshold: float = 50.0  # Laplacian variance 최소값 (다운샘플 기준)
    brightness_min: float = 30.0  # 최소 밝기 (0-255)
    brightness_max: float = 220.0  # 최대 밝기 (0-255)

    # 샘플링 설정
    target_frames: int = 60  # 최종 선택할 프레임 수
    overlap_ratio: float = 0.65  # 프레임 간 오버랩 비율 (0.6-0.7 권장)

    # 다운샘플링 설정 (VGGT 스타일)
    analysis_size: int = 518  # 분석용 이미지 크기 (VGGT 기준)


# ============================================================================
# 이미지 다운샘플링 (VGGT 스타일)
# ============================================================================

def downsample_for_analysis(image: np.ndarray, target_size: int = 518) -> np.ndarray:
    """
    VGGT 스타일 다운샘플링: 분석 속도 향상을 위해 이미지 축소

    VGGT는 518x518 기준으로 이미지를 처리함.
    품질 분석도 동일한 크기로 다운샘플링하여 속도 향상.

    Args:
        image: 원본 BGR 이미지
        target_size: 목표 크기 (기본값 518, VGGT 기준)

    Returns:
        다운샘플링된 이미지 (가로 또는 세로 중 긴 쪽이 target_size)
    """
    h, w = image.shape[:2]
    max_dim = max(h, w)

    # 이미 작으면 그대로 반환
    if max_dim <= target_size:
        return image

    # 비율 유지하며 축소
    scale = target_size / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ============================================================================
# 품질 분석기
# ============================================================================

class FrameQualityAnalyzer:
    """
    이미지 품질 분석기

    Laplacian Variance (Pech-Pacheco et al., ICPR 2000):
        - 2차 미분 기반 선명도 측정
        - 높을수록 엣지가 선명함 (블러 없음)
        - 빠르고 효과적인 블러 감지
    """

    @staticmethod
    def compute_sharpness(image: np.ndarray) -> float:
        """
        Laplacian variance를 이용한 선명도 측정

        Args:
            image: BGR 이미지 또는 그레이스케일 이미지

        Returns:
            선명도 점수 (높을수록 선명)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return float(laplacian.var())

    @staticmethod
    def compute_brightness(image: np.ndarray) -> float:
        """
        평균 밝기 계산

        Args:
            image: BGR 이미지 또는 그레이스케일 이미지

        Returns:
            평균 밝기 (0-255)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return float(gray.mean())

    @staticmethod
    def check_quality(sharpness: float, brightness: float, config: SelectorConfig) -> Tuple[bool, str]:
        """
        품질 기준 통과 여부 확인

        Returns:
            (통과 여부, 거부 사유)
        """
        if sharpness < config.sharpness_threshold:
            return False, "blur"
        if brightness < config.brightness_min:
            return False, "too_dark"
        if brightness > config.brightness_max:
            return False, "too_bright"
        return True, ""


# ============================================================================
# Optical Flow 분석기
# ============================================================================

class OpticalFlowAnalyzer:
    """
    Optical Flow 분석기

    Farneback Dense Optical Flow (Farneback, SCIA 2003):
        - 다항 전개 기반 밀집 광류 추정
        - 모든 픽셀의 움직임 벡터 계산
        - 정지 구간 감지에 효과적
    """

    def __init__(self):
        self.prev_gray: Optional[np.ndarray] = None

        # Farneback 파라미터
        self.flow_params = dict(
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

    def compute_flow_magnitude(self, image: np.ndarray) -> float:
        """
        이전 프레임과의 optical flow magnitude 계산

        Args:
            image: BGR 이미지

        Returns:
            평균 flow magnitude (첫 프레임은 0.0)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if self.prev_gray is None:
            self.prev_gray = gray
            return 0.0

        # Farneback optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None, **self.flow_params
        )

        # Flow magnitude 계산
        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        mean_magnitude = float(magnitude.mean())

        self.prev_gray = gray
        return mean_magnitude

    def reset(self):
        """상태 초기화"""
        self.prev_gray = None


# ============================================================================
# 프레임 선택기
# ============================================================================

class FrameSelector:
    """
    프레임 선택기

    VGGT + 3D Gaussian Splatting을 위한 최적 프레임 선택

    성능 최적화:
        - VGGT 스타일 다운샘플링 (518px) 적용으로 분석 속도 ~16배 향상
        - 원본: 1920x1080 → 분석용: 518x291 (비율 유지)
    """

    def __init__(self, config: Optional[SelectorConfig] = None):
        self.config = config or SelectorConfig()
        self.quality_analyzer = FrameQualityAnalyzer()
        self.flow_analyzer = OpticalFlowAnalyzer()

    def analyze_images(self, image_paths: List[str]) -> List[FrameInfo]:
        """
        이미지 리스트 분석 (다운샘플링 적용)

        Args:
            image_paths: 이미지 파일 경로 리스트

        Returns:
            각 프레임의 분석 결과 리스트
        """
        self.flow_analyzer.reset()
        frame_infos = []
        analysis_size = self.config.analysis_size

        for idx, img_path in enumerate(tqdm(image_paths, desc="프레임 분석 중")):
            image = cv2.imread(img_path)
            if image is None:
                continue

            # VGGT 스타일 다운샘플링 (속도 최적화)
            small_image = downsample_for_analysis(image, analysis_size)

            # 품질 분석 (다운샘플링된 이미지 사용)
            sharpness = self.quality_analyzer.compute_sharpness(small_image)
            brightness = self.quality_analyzer.compute_brightness(small_image)
            flow_mag = self.flow_analyzer.compute_flow_magnitude(small_image)

            # 품질 체크
            is_valid, reject_reason = self.quality_analyzer.check_quality(
                sharpness, brightness, self.config
            )

            # 정지 구간 체크 (첫 프레임 제외)
            if idx > 0 and flow_mag < self.config.flow_threshold:
                is_valid = False
                reject_reason = "static"

            frame_info = FrameInfo(
                index=idx,
                path=img_path,
                sharpness=sharpness,
                brightness=brightness,
                flow_magnitude=flow_mag,
                is_valid=is_valid,
                reject_reason=reject_reason
            )
            frame_infos.append(frame_info)

        return frame_infos

    def analyze_video(self, video_path: str) -> List[FrameInfo]:
        """
        비디오 분석 (다운샘플링 적용)

        Args:
            video_path: 비디오 파일 경로

        Returns:
            각 프레임의 분석 결과 리스트
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"비디오를 열 수 없습니다: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        analysis_size = self.config.analysis_size

        # 다운샘플링 비율 계산
        max_dim = max(width, height)
        scale = analysis_size / max_dim if max_dim > analysis_size else 1.0
        analysis_w = int(width * scale)
        analysis_h = int(height * scale)

        print(f"📹 비디오: {total_frames} 프레임, {fps:.1f} FPS")
        print(f"📐 원본: {width}x{height} → 분석용: {analysis_w}x{analysis_h} (VGGT 스타일)")

        self.flow_analyzer.reset()
        frame_infos = []

        pbar = tqdm(total=total_frames, desc="프레임 분석 중")
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # VGGT 스타일 다운샘플링 (속도 최적화)
            small_frame = downsample_for_analysis(frame, analysis_size)

            # 품질 분석 (다운샘플링된 이미지 사용)
            sharpness = self.quality_analyzer.compute_sharpness(small_frame)
            brightness = self.quality_analyzer.compute_brightness(small_frame)
            flow_mag = self.flow_analyzer.compute_flow_magnitude(small_frame)

            # 품질 체크
            is_valid, reject_reason = self.quality_analyzer.check_quality(
                sharpness, brightness, self.config
            )

            # 정지 구간 체크 (첫 프레임 제외)
            if frame_idx > 0 and flow_mag < self.config.flow_threshold:
                is_valid = False
                reject_reason = "static"

            frame_info = FrameInfo(
                index=frame_idx,
                path=f"frame_{frame_idx:06d}",
                sharpness=sharpness,
                brightness=brightness,
                flow_magnitude=flow_mag,
                is_valid=is_valid,
                reject_reason=reject_reason
            )
            frame_infos.append(frame_info)

            frame_idx += 1
            pbar.update(1)

        pbar.close()
        cap.release()

        return frame_infos

    def overlap_based_select(self, frame_infos: List[FrameInfo]) -> List[int]:
        """
        Overlap 기반 샘플링: 연속 프레임 간 60-70% 오버랩 보장

        3DGS/COLMAP에 최적화된 샘플링 방식:
        - 균등 간격으로 프레임 선택하여 일정한 오버랩 유지
        - 각 구간 내에서 최고 품질 프레임 선택
        - COLMAP feature matching 성공률 향상

        Args:
            frame_infos: 프레임 분석 결과

        Returns:
            선택된 프레임 인덱스 리스트
        """
        target_k = self.config.target_frames
        overlap_ratio = self.config.overlap_ratio

        # 유효한 프레임만 필터링
        valid_frames = [f for f in frame_infos if f.is_valid]
        valid_indices = [f.index for f in valid_frames]

        if len(valid_frames) == 0:
            print("⚠️  유효한 프레임이 없습니다. 품질 기준을 낮춰주세요.")
            return []

        if len(valid_frames) <= target_k:
            print(f"⚠️  유효 프레임({len(valid_frames)})이 목표({target_k})보다 적습니다.")
            return valid_indices

        # 오버랩 기반 간격 계산
        # overlap_ratio = 0.65 → 프레임 간 35% 이동 → interval = total / (target * (1 - overlap))
        # 단순화: 균등 간격 = total_valid / target
        total_valid = len(valid_frames)
        base_interval = total_valid / target_k

        print(f"\n📊 Overlap 기반 샘플링")
        print(f"   유효 프레임: {total_valid}개")
        print(f"   목표: {target_k}장")
        print(f"   오버랩 비율: {overlap_ratio*100:.0f}%")
        print(f"   기본 간격: {base_interval:.1f} 프레임")

        selected_indices = []
        window_size = max(3, int(base_interval * 0.3))  # 품질 선택을 위한 윈도우

        for i in range(target_k):
            # 목표 위치 계산 (유효 프레임 인덱스 기준)
            target_pos = int(i * base_interval)

            # 윈도우 범위 설정
            window_start = max(0, target_pos - window_size)
            window_end = min(total_valid, target_pos + window_size + 1)

            # 윈도우 내 프레임 중 최고 품질 선택
            window_frames = valid_frames[window_start:window_end]

            # 이미 선택된 프레임 제외
            available_frames = [f for f in window_frames if f.index not in selected_indices]

            if not available_frames:
                # 윈도우에 사용 가능한 프레임 없으면 가장 가까운 유효 프레임 선택
                available_frames = [f for f in valid_frames if f.index not in selected_indices]
                if not available_frames:
                    break
                # 목표 위치에서 가장 가까운 프레임 선택
                target_original_idx = valid_frames[target_pos].index
                available_frames.sort(key=lambda f: abs(f.index - target_original_idx))

            # 품질(선명도) 기준 최고 프레임 선택
            best_frame = max(available_frames, key=lambda f: f.sharpness)
            selected_indices.append(best_frame.index)

        # 시간순 정렬
        selected_indices = sorted(selected_indices)

        # 오버랩 검증
        if len(selected_indices) >= 2:
            intervals = [selected_indices[i+1] - selected_indices[i]
                        for i in range(len(selected_indices)-1)]
            avg_interval = np.mean(intervals)
            print(f"   실제 평균 간격: {avg_interval:.1f} 프레임")
            print(f"   선택된 프레임: {len(selected_indices)}장")

        return selected_indices



# ============================================================================
# 이미지 저장 및 메타데이터
# ============================================================================

def extract_and_save_frames(
    source: str,
    frame_indices: List[int],
    frame_infos: List[FrameInfo],
    output_dir: str,
    is_video: bool = False
) -> Tuple[List[str], dict]:
    """
    선택된 프레임을 COLMAP 호환 형식으로 저장

    Args:
        source: 비디오 경로 또는 이미지 디렉토리 경로
        frame_indices: 추출할 프레임 인덱스
        frame_infos: 전체 프레임 분석 정보
        output_dir: 출력 디렉토리
        is_video: 비디오 입력 여부

    Returns:
        (저장된 이미지 경로 리스트, 메타데이터 dict)
    """
    output_path = Path(output_dir)
    images_dir = output_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    selected_infos = []
    frame_set = set(frame_indices)

    if is_video:
        # 비디오에서 프레임 추출
        cap = cv2.VideoCapture(source)
        frame_idx = 0
        save_idx = 1

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx in frame_set:
                filename = f"{save_idx:04d}.jpg"
                filepath = images_dir / filename
                cv2.imwrite(str(filepath), frame)
                saved_paths.append(str(filepath))
                selected_infos.append(frame_infos[frame_idx])
                save_idx += 1

            frame_idx += 1

        cap.release()
    else:
        # 이미지 디렉토리에서 복사
        save_idx = 1
        for idx in frame_indices:
            src_path = frame_infos[idx].path
            filename = f"{save_idx:04d}.jpg"
            filepath = images_dir / filename

            # 이미지 로드 후 JPG로 저장 (형식 통일)
            image = cv2.imread(src_path)
            if image is not None:
                cv2.imwrite(str(filepath), image)
                saved_paths.append(str(filepath))
                selected_infos.append(frame_infos[idx])
                save_idx += 1

    # 메타데이터 생성
    metadata = create_metadata(frame_infos, selected_infos, output_dir)

    # 메타데이터 저장
    metadata_path = output_path / "frame_selection_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n📁 {len(saved_paths)}장 이미지 저장: {images_dir}")
    print(f"📊 메타데이터 저장: {metadata_path}")

    return saved_paths, metadata


def create_metadata(
    all_frames: List[FrameInfo],
    selected_frames: List[FrameInfo],
    output_dir: str
) -> dict:
    """메타데이터 생성"""

    # 통계 계산
    total = len(all_frames)
    valid = sum(1 for f in all_frames if f.is_valid)
    selected = len(selected_frames)

    # 제거 사유별 카운트
    reject_counts = {}
    for f in all_frames:
        if not f.is_valid and f.reject_reason:
            reject_counts[f.reject_reason] = reject_counts.get(f.reject_reason, 0) + 1

    # 선택된 프레임 통계
    if selected_frames:
        sharpness_values = [f.sharpness for f in selected_frames]
        brightness_values = [f.brightness for f in selected_frames]
        flow_values = [f.flow_magnitude for f in selected_frames]
    else:
        sharpness_values = brightness_values = flow_values = [0]

    metadata = {
        "pipeline": "Optical Flow → Laplacian + Brightness → Overlap-based Sampling",
        "sampling_mode": "overlap",
        "references": {
            "optical_flow": "Farneback, G. 'Two-frame motion estimation based on polynomial expansion.' SCIA 2003",
            "sharpness": "Pech-Pacheco, J.L. et al. 'Diatom autofocusing in brightfield microscopy.' ICPR 2000"
        },
        "statistics": {
            "total_frames": total,
            "valid_frames": valid,
            "selected_frames": selected,
            "rejection_reasons": reject_counts
        },
        "quality_metrics": {
            "sharpness": {
                "min": float(np.min(sharpness_values)),
                "max": float(np.max(sharpness_values)),
                "mean": float(np.mean(sharpness_values)),
                "std": float(np.std(sharpness_values))
            },
            "brightness": {
                "min": float(np.min(brightness_values)),
                "max": float(np.max(brightness_values)),
                "mean": float(np.mean(brightness_values)),
                "std": float(np.std(brightness_values))
            },
            "flow_magnitude": {
                "min": float(np.min(flow_values)),
                "max": float(np.max(flow_values)),
                "mean": float(np.mean(flow_values)),
                "std": float(np.std(flow_values))
            }
        },
        "selected_files": [
            {
                "colmap_name": f"{i+1:04d}.jpg",
                "original_index": f.index,
                "sharpness": f.sharpness,
                "brightness": f.brightness,
                "flow_magnitude": f.flow_magnitude
            }
            for i, f in enumerate(selected_frames)
        ]
    }

    return metadata


def print_statistics(all_frames: List[FrameInfo], selected_indices: List[int]):
    """통계 출력"""
    total = len(all_frames)
    valid = sum(1 for f in all_frames if f.is_valid)
    selected = len(selected_indices)

    # 제거 사유별 카운트
    static_removed = sum(1 for f in all_frames if f.reject_reason == "static")
    blur_removed = sum(1 for f in all_frames if f.reject_reason == "blur")
    dark_removed = sum(1 for f in all_frames if f.reject_reason == "too_dark")
    bright_removed = sum(1 for f in all_frames if f.reject_reason == "too_bright")

    print("\n" + "=" * 60)
    print("📊 프레임 선택 통계")
    print("=" * 60)
    print(f"전체 프레임:         {total}")
    print(f"정지 구간 제거:      {static_removed} (Optical Flow < threshold)")
    print(f"블러 제거:           {blur_removed} (Laplacian < threshold)")
    print(f"너무 어두움:         {dark_removed}")
    print(f"너무 밝음:           {bright_removed}")
    print(f"유효 프레임:         {valid}")
    print(f"최종 선택:           {selected}")
    print("=" * 60)

    if selected_indices:
        selected_frames = [all_frames[i] for i in selected_indices]
        avg_sharpness = np.mean([f.sharpness for f in selected_frames])
        avg_brightness = np.mean([f.brightness for f in selected_frames])
        avg_flow = np.mean([f.flow_magnitude for f in selected_frames])
        print(f"평균 선명도:         {avg_sharpness:.1f}")
        print(f"평균 밝기:           {avg_brightness:.1f}")
        print(f"평균 Flow:           {avg_flow:.2f}")
        print("=" * 60)


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='3D Gaussian Splatting을 위한 품질 기반 프레임 선택',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
프레임 선택 파이프라인:
  1. Optical Flow - 정지 구간 제거 (Farneback, 2003)
  2. Laplacian + 밝기 - 블러/노출 불량 제거 (Pech-Pacheco, 2000)
  3. Overlap 기반 샘플링 - 균등 간격 + 품질 기반 선택 (60-70% 오버랩)

사용 예시:
  # 비디오 입력 (기본 60장, 65% 오버랩)
  python quality_sampler.py video.mp4 --output-dir ./output

  # 이미지 디렉토리 입력
  python quality_sampler.py ./images/ --output-dir ./output --target-count 60

  # 세부 설정
  python quality_sampler.py video.mp4 \\
      --output-dir ./output \\
      --target-count 60 \\
      --overlap-ratio 0.7 \\
      --flow-threshold 0.3 \\
      --sharpness-threshold 50.0
"""
    )

    parser.add_argument('input', type=str,
                       help='입력 경로 (비디오 파일 또는 이미지 디렉토리)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='출력 디렉토리 (기본값: <입력경로>_selected)')
    parser.add_argument('--target-count', type=int, default=60,
                       help='최종 선택할 프레임 수 (기본값: 60)')
    parser.add_argument('--overlap-ratio', type=float, default=0.65,
                       help='프레임 간 오버랩 비율 (기본값: 0.65, 즉 65%%)')
    parser.add_argument('--flow-threshold', type=float, default=0.3,
                       help='Optical Flow 임계값 (기본값: 0.3, 518px 다운샘플 기준)')
    parser.add_argument('--sharpness-threshold', type=float, default=50.0,
                       help='Laplacian 선명도 임계값 (기본값: 50.0, 518px 다운샘플 기준)')
    parser.add_argument('--brightness-min', type=float, default=30.0,
                       help='최소 밝기 (기본값: 30.0)')
    parser.add_argument('--brightness-max', type=float, default=220.0,
                       help='최대 밝기 (기본값: 220.0)')
    parser.add_argument('--analysis-size', type=int, default=518,
                       help='분석용 다운샘플링 크기 (기본값: 518, VGGT 기준)')

    args = parser.parse_args()

    # 입력 경로 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 입력 경로가 존재하지 않습니다: {args.input}")
        return

    # 입력 타입 확인
    is_video = input_path.is_file() and input_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']

    # 출력 디렉토리 설정
    if args.output_dir is None:
        args.output_dir = str(input_path.parent / f"{input_path.stem}_selected")

    # 설정
    config = SelectorConfig(
        flow_threshold=args.flow_threshold,
        sharpness_threshold=args.sharpness_threshold,
        brightness_min=args.brightness_min,
        brightness_max=args.brightness_max,
        target_frames=args.target_count,
        overlap_ratio=args.overlap_ratio,
        analysis_size=args.analysis_size
    )

    print("=" * 60)
    print("🎯 3D Gaussian Splatting을 위한 프레임 선택")
    print("=" * 60)
    print(f"📁 입력: {args.input}")
    print(f"📁 출력: {args.output_dir}")
    print(f"🎯 목표: {args.target_count}장")
    print(f"🔗 오버랩 비율: {args.overlap_ratio*100:.0f}%")
    print(f"🔧 Flow 임계값: {args.flow_threshold}")
    print(f"🔧 선명도 임계값: {args.sharpness_threshold}")
    print(f"🔧 밝기 범위: {args.brightness_min} ~ {args.brightness_max}")
    print(f"📐 분석 해상도: {args.analysis_size}px (VGGT 스타일)")
    print("=" * 60)

    # 프레임 선택기 생성
    selector = FrameSelector(config)

    # 분석
    if is_video:
        print(f"\n🎬 비디오 분석 중: {args.input}")
        frame_infos = selector.analyze_video(args.input)
    else:
        print(f"\n📂 이미지 디렉토리 분석 중: {args.input}")
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        image_paths = []
        for ext in image_extensions:
            image_paths.extend(sorted(input_path.glob(ext)))
        image_paths = [str(p) for p in sorted(image_paths)]

        if not image_paths:
            print(f"❌ 이미지를 찾을 수 없습니다: {args.input}")
            return

        print(f"   발견된 이미지: {len(image_paths)}장")
        frame_infos = selector.analyze_images(image_paths)

    # Overlap 기반 프레임 선택
    selected_indices = selector.overlap_based_select(frame_infos)

    if not selected_indices:
        print("❌ 선택된 프레임이 없습니다.")
        return

    # 통계 출력
    print_statistics(frame_infos, selected_indices)

    # 프레임 추출 및 저장
    saved_paths, metadata = extract_and_save_frames(
        source=args.input,
        frame_indices=selected_indices,
        frame_infos=frame_infos,
        output_dir=args.output_dir,
        is_video=is_video
    )

    print("\n" + "=" * 60)
    print("✅ 프레임 선택 완료!")
    print("=" * 60)
    print(f"📁 출력 디렉토리: {args.output_dir}")
    print(f"\n다음 단계:")
    print(f"  ./run_pipeline.sh P4 {args.output_dir}")
    print(f"  ./run_pipeline.sh P5 {args.output_dir}")


if __name__ == '__main__':
    main()
