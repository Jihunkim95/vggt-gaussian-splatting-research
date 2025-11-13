#!/usr/bin/env python3
"""
Phase 1: Surrogate Reward로 RL Agent 학습 (Multi-video Training)

대규모 데이터셋 학습으로 zero-shot generalization 달성
"""
import argparse
from pathlib import Path
import sys
sys.path.append('..')

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env, SubprocVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from env import FrameSelectionEnv
from utils.dataset_loader import load_dataset, create_train_val_split


def main():
    parser = argparse.ArgumentParser(description='RL Frame Selector - Phase 1 Training (Multi-video)')

    # Dataset selection
    parser.add_argument('--dataset', type=str, required=True,
                       choices=['co3d', 'dtu', 'custom'],
                       help='학습 데이터셋: co3d (CO3Dv2), dtu (DTU scans), custom (사용자 비디오)')
    parser.add_argument('--num-train-videos', type=int, default=100,
                       help='학습에 사용할 비디오 수 (default: 100)')
    parser.add_argument('--num-eval-videos', type=int, default=10,
                       help='평가에 사용할 비디오 수 (default: 10)')
    parser.add_argument('--dataset-root', type=str, default=None,
                       help='데이터셋 루트 디렉토리 (None = 기본 경로 사용)')

    # Frame selection parameters
    parser.add_argument('--num-source-frames', type=int, default=300,
                       help='비디오에서 추출할 프레임 수 (default: 300)')
    parser.add_argument('--target-frames', type=int, default=60,
                       help='최종 선택할 프레임 수 (default: 60)')
    parser.add_argument('--max-gap', type=int, default=10,
                       help='연속 선택 프레임 간 최대 gap (overlap 보장, default: 10)')

    # Training parameters
    parser.add_argument('--total-timesteps', type=int, default=500000,
                       help='총 학습 timesteps (default: 500000)')
    parser.add_argument('--n-envs', type=int, default=4,
                       help='병렬 환경 수 (default: 4)')
    parser.add_argument('--output-dir', type=str, default='./trained_models',
                       help='모델 저장 디렉토리 (default: ./trained_models)')
    parser.add_argument('--tensorboard-log', type=str, default='./logs',
                       help='Tensorboard 로그 디렉토리 (default: ./logs)')

    args = parser.parse_args()

    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🎯 RL Frame Selector - Phase 1: Multi-Video Training")
    print("=" * 70)
    print(f"📦 Dataset: {args.dataset}")
    print(f"📹 Train videos: {args.num_train_videos}")
    print(f"📹 Eval videos: {args.num_eval_videos}")
    print(f"🎯 Source frames: {args.num_source_frames}")
    print(f"🎯 Target frames: {args.target_frames}")
    print(f"📊 Total timesteps: {args.total_timesteps}")
    print(f"🔄 Parallel envs: {args.n_envs}")
    print("=" * 70)
    print()

    # Load videos from dataset
    print(f"📥 Loading {args.dataset} dataset...")
    kwargs = {}
    if args.dataset_root:
        kwargs['root'] = args.dataset_root

    all_videos = load_dataset(
        args.dataset,
        num_videos=args.num_train_videos + args.num_eval_videos,
        **kwargs
    )

    # Split into train/val
    split_data = create_train_val_split(
        all_videos,
        val_ratio=args.num_eval_videos / len(all_videos)
    )

    train_videos = split_data['train'][:args.num_train_videos]
    eval_videos = split_data['val'][:args.num_eval_videos]

    print(f"✅ Loaded: {len(train_videos)} train, {len(eval_videos)} eval videos")
    print(f"📁 Sample train video: {train_videos[0]}")
    print()

    # Create multi-video training environment
    # 각 episode마다 랜덤하게 비디오 선택
    import random
    import numpy as np

    def make_env(video_list, rank, seed=0):
        """
        환경 생성 함수 (각 프로세스마다 호출)
        episode마다 랜덤하게 다른 비디오 선택
        """
        def _init():
            # 랜덤하게 비디오 선택
            video_path = random.choice(video_list)
            env = FrameSelectionEnv(
                video_path=video_path,
                num_source_frames=args.num_source_frames,
                target_frames=args.target_frames,
                max_gap=args.max_gap
            )
            env.reset(seed=seed + rank)
            return env
        return _init

    # Training 환경 (병렬 환경)
    print(f"🔧 Creating {args.n_envs} parallel training environments...")
    env = SubprocVecEnv([make_env(train_videos, i) for i in range(args.n_envs)])

    # Evaluation 환경 (단일)
    print(f"🔧 Creating evaluation environment...")
    eval_env = FrameSelectionEnv(
        video_path=eval_videos[0],
        num_source_frames=args.num_source_frames,
        target_frames=args.target_frames,
        max_gap=args.max_gap
    )
    print()

    # PPO Agent 생성
    print("🤖 PPO Agent 초기화 중...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=args.tensorboard_log,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01
    )

    print("✅ Agent 생성 완료")
    print()

    # Callbacks
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(output_dir / 'best_model'),
        log_path=str(output_dir / 'eval_logs'),
        eval_freq=5000,
        deterministic=True,
        render=False
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=str(output_dir / 'checkpoints'),
        name_prefix='rl_frame_selector'
    )

    # 학습 시작
    print("🚀 학습 시작!")
    print(f"   Tensorboard: tensorboard --logdir {args.tensorboard_log}")
    print()

    model.learn(
        total_timesteps=args.total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True
    )

    # 최종 모델 저장
    final_model_path = output_dir / 'final_model.zip'
    model.save(final_model_path)

    print()
    print("=" * 70)
    print("✅ Phase 1 Multi-Video Training 완료!")
    print("=" * 70)
    print(f"📁 모델 저장: {final_model_path}")
    print(f"📁 Best 모델: {output_dir / 'best_model'}")
    print()
    print("📊 학습 통계:")
    print(f"   - 총 학습 비디오: {len(train_videos)}개")
    print(f"   - 총 timesteps: {args.total_timesteps}")
    print(f"   - 병렬 환경: {args.n_envs}")
    print()
    print("📊 다음 단계:")
    print(f"   1. Tensorboard 확인: tensorboard --logdir {args.tensorboard_log}")
    print(f"   2. Zero-shot 테스트: python ../evaluate.py --model {final_model_path} --video <new_video>")
    print(f"   3. Phase 2 Fine-tuning 진행 (실제 3DGS 평가)")
    print()


if __name__ == '__main__':
    main()
