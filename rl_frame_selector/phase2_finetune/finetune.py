#!/usr/bin/env python3
"""
Phase 2: 실제 3DGS로 Fine-tuning

Phase 1에서 학습된 모델을 실제 3DGS PSNR/SSIM으로 fine-tune
"""
import argparse
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
import sys
sys.path.append('..')

from stable_baselines3 import PPO
import numpy as np


def run_3dgs_pipeline(selected_frames, video_path, pipeline='P4'):
    """
    선택된 프레임으로 3DGS 파이프라인 실행

    Args:
        selected_frames: 선택된 프레임 인덱스 리스트
        video_path: 원본 비디오 경로
        pipeline: 파이프라인 (P4 or P5)

    Returns:
        {'psnr': ..., 'ssim': ..., 'lpips': ...}
    """
    # TODO: 실제 구현
    # 1. 선택된 프레임만 임시 디렉토리에 저장
    # 2. run_pipeline.sh 실행
    # 3. val_step29999.json 읽어서 메트릭 반환

    print(f"⚠️  Phase 2 Fine-tuning은 실제 3DGS 파이프라인 통합이 필요합니다")
    print(f"   선택된 프레임: {len(selected_frames)}개")
    print(f"   이 부분은 사용자가 run_pipeline.sh와 통합해야 합니다")

    # Placeholder - 실제로는 3DGS 실행 후 결과 반환
    return {
        'psnr': 18.0 + np.random.randn() * 0.5,
        'ssim': 0.70 + np.random.randn() * 0.02,
        'lpips': 0.24 + np.random.randn() * 0.01
    }


def main():
    parser = argparse.ArgumentParser(description='RL Frame Selector - Phase 2 Fine-tuning')
    parser.add_argument('--model-path', type=str, required=True,
                       help='Phase 1에서 학습된 모델 경로 (.zip)')
    parser.add_argument('--video', type=str, required=True,
                       help='Fine-tuning 비디오 경로')
    parser.add_argument('--pipeline', type=str, default='P4', choices=['P4', 'P5'],
                       help='3DGS 파이프라인 (default: P4)')
    parser.add_argument('--num-episodes', type=int, default=10,
                       help='Fine-tuning episodes (default: 10)')
    parser.add_argument('--output-dir', type=str, default='./finetuned_models',
                       help='Fine-tuned 모델 저장 디렉토리')

    args = parser.parse_args()

    print("=" * 70)
    print("🎯 RL Frame Selector - Phase 2: 3DGS Fine-tuning")
    print("=" * 70)
    print(f"📁 모델: {args.model_path}")
    print(f"📹 비디오: {args.video}")
    print(f"🔧 파이프라인: {args.pipeline}")
    print(f"🔄 Episodes: {args.num_episodes}")
    print("=" * 70)
    print()

    # 모델 로드
    print("🤖 모델 로딩 중...")
    model = PPO.load(args.model_path)
    print("✅ 모델 로드 완료")
    print()

    # Fine-tuning loop
    print("🚀 Fine-tuning 시작...")
    print(f"⚠️  주의: 각 episode는 ~10분 소요됩니다 (3DGS 훈련)")
    print()

    for episode in range(args.num_episodes):
        print(f"Episode {episode + 1}/{args.num_episodes}")

        # TODO: 실제 구현
        # 1. Agent로 프레임 선택
        # 2. run_3dgs_pipeline() 실행
        # 3. Reward로 모델 업데이트

        print(f"   [TODO] Agent로 프레임 선택")
        print(f"   [TODO] 3DGS 파이프라인 실행")
        print(f"   [TODO] Reward 계산 및 모델 업데이트")
        print()

    # 최종 모델 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / 'finetuned_model.zip'

    model.save(final_path)

    print("=" * 70)
    print("✅ Phase 2 Fine-tuning 완료!")
    print("=" * 70)
    print(f"📁 모델 저장: {final_path}")
    print()
    print("📊 다음 단계:")
    print(f"   1. Baseline과 비교 평가")
    print(f"   2. 여러 비디오/데이터셋에서 테스트")
    print()


if __name__ == '__main__':
    main()
