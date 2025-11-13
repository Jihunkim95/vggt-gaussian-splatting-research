#!/usr/bin/env python3
"""
Frame Selection Gym Environment (with Overlap Constraints)
"""
import gymnasium as gym
import numpy as np
from typing import List, Dict, Tuple
import sys
sys.path.append('..')
from utils.video_utils import extract_frames_uniformly
from utils.quality_metrics import compute_all_metrics
from utils.overlap_utils import compute_pairwise_overlap


class FrameSelectionEnv(gym.Env):
    """
    강화학습 환경: 비디오에서 최적의 프레임 선택 (Overlap 제약 포함)

    State: 현재 프레임의 품질 정보 + 선택 상태
    Action: 0 (SKIP) or 1 (SELECT)
    Reward: Surrogate reward (빠른 평가)

    **중요**: COLMAP/3DGS 성공을 위해 overlap 제약 적용
    """

    def __init__(self, video_path: str, num_source_frames: int = 300,
                 target_frames: int = 60, max_gap: int = 10):
        """
        Args:
            video_path: 비디오 파일 경로
            num_source_frames: 비디오에서 추출할 프레임 수
            target_frames: 최종 선택할 프레임 수
            max_gap: 연속 선택 프레임 간 최대 gap (overlap 보장)
                    - max_gap=10: 10프레임 이내에 다음 프레임 선택 필수
                    - 값이 작을수록 overlap 강화, 크면 자유도 증가
        """
        super().__init__()

        self.video_path = video_path
        self.num_source_frames = num_source_frames
        self.target_frames = target_frames
        self.max_gap = max_gap

        # Action space: 0 (SKIP), 1 (SELECT)
        self.action_space = gym.spaces.Discrete(2)

        # State space: [sharpness, brisque, brightness, temporal_pos, selected_count]
        self.observation_space = gym.spaces.Box(
            low=0.0, high=1.0, shape=(5,), dtype=np.float32
        )

        # 초기화
        self.frames = []
        self.quality_metrics = []
        self.reset()

    def reset(self, seed=None, options=None):
        """환경 리셋"""
        super().reset(seed=seed)

        # 비디오에서 프레임 추출
        print(f"🎬 비디오 로딩: {self.video_path}")
        self.frames = extract_frames_uniformly(
            self.video_path, self.num_source_frames
        )

        # 실제 추출된 프레임 수에 맞춰 num_source_frames 업데이트
        # (DTU는 60개만 있을 수 있음)
        actual_frames = len(self.frames)
        if actual_frames < self.num_source_frames:
            print(f"ℹ️  프레임 수 조정: {self.num_source_frames} → {actual_frames}")
            self.num_source_frames = actual_frames

        # 품질 메트릭 미리 계산
        print(f"📊 품질 메트릭 계산 중...")
        self.quality_metrics = []
        for frame in self.frames:
            metrics = compute_all_metrics(frame)
            self.quality_metrics.append(metrics)

        print(f"✅ 준비 완료: {len(self.frames)}개 프레임")

        # 상태 초기화
        self.current_step = 0
        self.selected_indices = []

        # 초기 observation
        obs = self._get_observation()
        info = {}

        return obs, info

    def _get_observation(self) -> np.ndarray:
        """현재 상태 observation 생성"""
        if self.current_step >= len(self.frames):
            # Episode 종료
            return np.zeros(5, dtype=np.float32)

        metrics = self.quality_metrics[self.current_step]

        obs = np.array([
            metrics['sharpness'],
            metrics['brisque'],
            metrics['brightness'],
            self.current_step / self.num_source_frames,  # Temporal position
            len(self.selected_indices) / self.target_frames  # Selection progress
        ], dtype=np.float32)

        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        환경 step 실행 (Overlap 제약 포함)

        Args:
            action: 0 (SKIP) or 1 (SELECT)

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        reward = 0.0

        # ===== Overlap 제약 체크 =====
        if action == 1:  # SELECT
            if len(self.selected_indices) > 0:
                last_selected = self.selected_indices[-1]
                gap = self.current_step - last_selected

                # Gap이 너무 크면 큰 페널티 + 강제 SKIP
                if gap > self.max_gap:
                    reward = -5.0  # 큰 페널티!
                    print(f"⚠️  Gap too large: {gap} > {self.max_gap}, forced SKIP")

                    # 다음 프레임으로 이동 (SELECT 무시)
                    self.current_step += 1

                    obs = self._get_observation()
                    info = {
                        'selected_count': len(self.selected_indices),
                        'current_step': self.current_step,
                        'gap_violation': True
                    }

                    return obs, reward, False, False, info

            # Gap 제약 통과 → 선택 허용
            if len(self.selected_indices) < self.target_frames:
                self.selected_indices.append(self.current_step)

        # 다음 프레임으로 이동
        self.current_step += 1

        # Episode 종료 조건
        terminated = False
        truncated = False

        if len(self.selected_indices) == self.target_frames:
            # 목표 개수 달성
            terminated = True
            reward = self._compute_final_reward_with_overlap()
            print(f"✅ Target reached! Final reward: {reward:.4f}")

        elif self.current_step >= self.num_source_frames:
            # 모든 프레임 확인 완료
            if len(self.selected_indices) < self.target_frames:
                # 목표 미달 (패널티)
                truncated = True
                reward = -10.0
                print(f"❌ Target not reached: {len(self.selected_indices)}/{self.target_frames}")
            else:
                terminated = True
                reward = self._compute_final_reward_with_overlap()

        obs = self._get_observation()
        info = {
            'selected_count': len(self.selected_indices),
            'current_step': self.current_step,
            'gap_violation': False
        }

        return obs, reward, terminated, truncated, info

    def _compute_final_reward_with_overlap(self) -> float:
        """
        Episode 종료 시 최종 reward 계산 (Overlap 포함)

        Surrogate reward 구성:
        1. Temporal coverage uniformity (20%)
        2. Average quality (30%)
        3. Quality diversity (10%)
        4. Overlap score (40%) ← **가장 중요!**
        """
        if len(self.selected_indices) == 0:
            return -10.0

        # 1. Temporal coverage uniformity
        selected_sorted = sorted(self.selected_indices)
        gaps = np.diff(selected_sorted)
        temporal_uniformity = 1.0 / (1.0 + np.std(gaps))

        # 2. Average quality (sharpness + brisque)
        selected_qualities = [
            self.quality_metrics[i]['sharpness'] +
            self.quality_metrics[i]['brisque']
            for i in self.selected_indices
        ]
        avg_quality = np.mean(selected_qualities)

        # 3. Diversity (avoid selecting too similar frames)
        quality_diversity = np.std(selected_qualities) if len(selected_qualities) > 1 else 0.0

        # 4. Overlap score (SIFT feature matching)
        print(f"🔍 Overlap 계산 중... (SIFT matching)")
        overlap_score = compute_pairwise_overlap(self.frames, self.selected_indices)
        print(f"   Overlap score: {overlap_score:.4f}")

        # Weighted combination (Overlap 가장 중요!)
        reward = (
            0.2 * temporal_uniformity +
            0.3 * avg_quality +
            0.1 * quality_diversity +
            0.4 * overlap_score  # ← COLMAP 성공에 가장 중요
        )

        # 디버깅 정보
        print(f"   Temporal uniformity: {temporal_uniformity:.4f}")
        print(f"   Avg quality: {avg_quality:.4f}")
        print(f"   Diversity: {quality_diversity:.4f}")
        print(f"   Overlap: {overlap_score:.4f}")
        print(f"   → Final reward: {reward:.4f}")

        return float(reward)

    def render(self):
        """렌더링 (선택사항)"""
        pass
