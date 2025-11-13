# 🚀 Quick Start Guide

RL Frame Selector를 5분 안에 시작하는 가이드

## Step 1: 환경 설정 (1분)

```bash
# vggt_env 활성화
cd /data/vggt-gaussian-splatting-research
source ./env/vggt_env/bin/activate

# RL 패키지 설치
cd rl_frame_selector
pip install -r requirements_rl.txt
```

## Step 2: Phase 1 Multi-Video 학습 시작

### Option A: CO3Dv2 (권장 - Zero-shot Generalization)

```bash
cd phase1_surrogate

# CO3Dv2 1,000개 비디오로 학습 (1-2시간)
python train.py \
    --dataset co3d \
    --num-train-videos 1000 \
    --num-eval-videos 100 \
    --total-timesteps 500000 \
    --n-envs 8 \
    --output-dir ./trained_models/co3d_1k \
    --tensorboard-log ./logs/co3d_1k
```

### Option B: DTU (빠른 테스트, 30분-1시간)

```bash
# DTU 10개 스캔으로 학습
python train.py \
    --dataset dtu \
    --num-train-videos 10 \
    --num-eval-videos 2 \
    --total-timesteps 100000 \
    --n-envs 4 \
    --output-dir ./trained_models/dtu \
    --tensorboard-log ./logs/dtu
```

### Option C: Custom Videos

```bash
# 사용자 비디오로 학습
python train.py \
    --dataset custom \
    --num-train-videos 20 \
    --num-eval-videos 3 \
    --total-timesteps 200000 \
    --n-envs 4 \
    --output-dir ./trained_models/custom \
    --tensorboard-log ./logs/custom
```

## Step 3: 학습 모니터링

**새 터미널 열기**:
```bash
cd /data/vggt-gaussian-splatting-research/rl_frame_selector/phase1_surrogate
tensorboard --logdir ./logs
```

브라우저에서 확인 (포트포워딩 필요):
```
http://localhost:6006
```

### 주요 메트릭

- `rollout/ep_rew_mean`: Episode reward (0.5 → 0.8+ 목표)
- `train/policy_loss`: Policy gradient loss
- `train/value_loss`: Value function loss

## Step 4: 학습된 모델 테스트

```python
from stable_baselines3 import PPO
from env import FrameSelectionEnv

# 모델 로드
model = PPO.load("./trained_models/final_model.zip")

# 환경 생성
env = FrameSelectionEnv(
    video_path="../../datasets/custom/cLectern.mp4",
    num_source_frames=300,
    target_frames=60
)

# 프레임 선택
obs, _ = env.reset()
selected_frames = []

for _ in range(300):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)

    if action == 1:
        selected_frames.append(info['current_step'] - 1)

    if done or truncated:
        break

print(f"선택된 프레임: {len(selected_frames)}개")
print(f"최종 reward: {reward:.4f}")
print(f"프레임 인덱스: {sorted(selected_frames)}")
```

## 예상 결과

### Phase 1 학습 곡선

```
Episode 0-100:    Reward 0.3-0.5 (random exploration)
Episode 100-500:  Reward 0.5-0.7 (learning)
Episode 500+:     Reward 0.7-0.85 (convergence)
```

### Baseline 비교 (Surrogate Reward)

| Method | Temporal Uniformity | Avg Quality | Diversity | Total Reward |
|--------|---------------------|-------------|-----------|--------------|
| Random | 0.3 | 0.5 | 0.6 | 0.45 |
| Uniform | 0.9 | 0.4 | 0.3 | 0.52 |
| Quality-only | 0.2 | 0.9 | 0.4 | 0.50 |
| Stratified | 0.7 | 0.7 | 0.5 | 0.63 |
| **RL Agent** | **0.8** | **0.8** | **0.6** | **0.73** |

## 문제 해결

### GPU 메모리 부족
```bash
# CPU로 학습 (느리지만 가능)
python train.py --videos video.mp4 --total-timesteps 50000
```

### OpenCV 에러
```bash
pip install opencv-python-headless
```

### Tensorboard 포트 충돌
```bash
tensorboard --logdir ./logs --port 6007
```

## 다음 단계

1. ✅ Phase 1 완료 → Surrogate reward로 agent 학습
2. 🔧 Phase 2 구현 → `run_3dgs_pipeline()` 통합
3. 📊 Baseline 비교 → Random/Uniform/Stratified
4. 📝 보고서 작성 → 실험 결과 정리

## 참고

- 전체 문서: [README.md](README.md)
- Phase 2 구현: [phase2_finetune/finetune.py](phase2_finetune/finetune.py)
- 환경 구현: [phase1_surrogate/env.py](phase1_surrogate/env.py)
