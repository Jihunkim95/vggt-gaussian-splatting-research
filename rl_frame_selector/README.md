# 🎯 RL Frame Selector for 3D Gaussian Splatting

강화학습을 활용한 적응형 프레임 선택 시스템

## 📋 프로젝트 개요

비디오 또는 이미지 시퀀스에서 3D Gaussian Splatting (3DGS) 품질을 최대화하는 프레임을 자동으로 선택하는 RL 시스템입니다.

### 문제 정의

- **입력**: 비디오 (300프레임)
- **출력**: 최적의 60개 프레임 선택
- **목표**: 3DGS 결과 품질(PSNR, SSIM, LPIPS) 최대화

### 기존 방법의 한계

`quality_sampler.py`는 고정된 휴리스틱을 사용:
- Stratified sampling (10개 구간)
- BRISQUE + Sharpness 고정 가중치 (0.5, 0.5)
- 장면별 특성 미반영

### RL 접근법의 장점

- **적응적 선택**: 장면 특성에 맞춰 프레임 선택
- **End-to-end 최적화**: 3DGS 품질 직접 최대화
- **학습 가능**: 새로운 데이터로 지속 개선

---

## 🏗️ 시스템 아키텍처

### Phase 1: Surrogate Reward (빠른 학습)

**학습 시간**: ~5-10분

```python
# Surrogate Reward Components:
1. Temporal Coverage Uniformity (시간적 균등성)
2. Average Quality Score (평균 품질)
3. Quality Diversity (품질 다양성)
```

**Why Surrogate?**
- 실제 3DGS 훈련은 10분 소요 → 학습 불가능
- Surrogate는 0.1초 이내 → 빠른 iteration

### Phase 2: Fine-tuning (실제 3DGS)

**학습 시간**: ~1-3시간 (50 episodes)

```python
# Real 3DGS Reward:
reward = 0.5 * PSNR_normalized + 0.3 * SSIM + 0.2 * (1 - LPIPS)
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# vggt_env 활성화
source ./env/vggt_env/bin/activate

# RL 패키지 설치
cd rl_frame_selector
pip install -r requirements_rl.txt
```

### 2. Phase 1 학습 (Surrogate Reward)

```bash
cd phase1_surrogate

# 단일 비디오로 학습
python train.py --videos ../datasets/custom/cChair.mp4

# 여러 비디오로 학습 (권장)
python train.py \
    --videos ../datasets/custom/cChair.mp4 ../datasets/custom/cTable.mp4 \
    --total-timesteps 100000 \
    --output-dir ./trained_models
```

**예상 소요 시간**: 5-10분

**Tensorboard 모니터링**:
```bash
tensorboard --logdir ./logs
# http://localhost:6006 접속
```

### 3. Phase 2 Fine-tuning (실제 3DGS)

⚠️ **주의**: Phase 2는 `run_pipeline.sh` 통합이 필요합니다.

```bash
cd phase2_finetune

python finetune.py \
    --model-path ../phase1_surrogate/trained_models/final_model.zip \
    --video ../datasets/custom/cLectern.mp4 \
    --pipeline P4 \
    --num-episodes 10
```

---

## 📊 학습 결과 분석

### Tensorboard 메트릭

Phase 1 학습 중 모니터링 가능:
- `ep_rew_mean`: Episode 평균 reward
- `ep_len_mean`: Episode 길이
- `loss/policy_loss`: Policy loss
- `loss/value_loss`: Value loss

### 예상 결과

**Phase 1 (Surrogate)**:
- Episode reward: 0.5 → 0.8+ (수렴)
- Temporal uniformity 개선
- Quality selection 개선

**Phase 2 (Real 3DGS)**:
- Baseline (stratified): PSNR ~18.0
- RL Agent: PSNR ~18.5+ (목표: +0.5dB)

---

## 🔬 실험 설계

### Baseline 비교

1. **Random**: 무작위 60개 선택
2. **Uniform**: 균등 간격 60개
3. **Quality-only**: 품질 점수 Top-60
4. **Stratified** (현재): 구간별 품질 샘플링
5. **RL Agent** (우리): 학습된 정책

### 평가 데이터셋

- DTU: scan1, scan14, scan24
- Videos: cChair, cTable, cLectern, cSpace
- **총 7개 장면 × 5 baselines = 35 experiments**

### 실험 스크립트

```bash
# Baseline 실행
./evaluate_baselines.sh cChair.mp4

# RL Agent 평가
./evaluate_rl_agent.sh cChair.mp4 --model trained_models/final_model.zip
```

---

## 📁 프로젝트 구조

```
rl_frame_selector/
├── phase1_surrogate/           # Phase 1: Surrogate Reward
│   ├── env.py                  # Gym Environment
│   ├── train.py                # Training script
│   ├── trained_models/         # 학습된 모델
│   └── logs/                   # Tensorboard 로그
│
├── phase2_finetune/            # Phase 2: Real 3DGS Fine-tuning
│   ├── finetune.py             # Fine-tuning script
│   └── finetuned_models/       # Fine-tuned 모델
│
├── utils/                      # 공통 유틸리티
│   ├── video_utils.py          # 비디오 처리
│   └── quality_metrics.py      # 품질 평가
│
├── requirements_rl.txt         # 추가 패키지
└── README.md                   # 프로젝트 문서 (이 파일)
```

---

## 🎓 교육적 가치

### 학습 주제

1. **강화학습 기초**
   - MDP (Markov Decision Process)
   - Policy Gradient (PPO)
   - Reward Engineering

2. **실용적 RL**
   - Surrogate Reward 설계
   - Sample Efficiency
   - Sim-to-Real Transfer

3. **컴퓨터 비전**
   - 이미지 품질 평가
   - Feature Extraction
   - 3D Reconstruction

### 확장 아이디어

1. **Multi-objective RL**: PSNR + SSIM + Speed 동시 최적화
2. **Meta-learning**: Few-shot adaptation
3. **Curriculum Learning**: 쉬운 장면 → 어려운 장면
4. **Offline RL**: 기존 실험 데이터 활용 (CQL, IQL)

---

## ⚠️ 주의사항

### Phase 2 구현 필요사항

Phase 2 fine-tuning은 다음 통합 작업이 필요합니다:

1. **프레임 저장**: 선택된 프레임을 임시 디렉토리에 저장
2. **Pipeline 실행**: `run_pipeline.sh` 호출
3. **결과 파싱**: `val_step29999.json` 읽기
4. **Reward 계산**: PSNR/SSIM/LPIPS → reward

```python
# finetune.py의 run_3dgs_pipeline() 함수 구현 필요
def run_3dgs_pipeline(selected_frames, video_path, pipeline='P4'):
    # 1. 프레임 저장
    temp_dir = save_selected_frames(selected_frames, video_path)

    # 2. Pipeline 실행
    subprocess.run([
        './run_pipeline.sh', pipeline, temp_dir
    ])

    # 3. 결과 읽기
    result = json.load(open(f'./results/.../val_step29999.json'))

    return result
```

### 계산 리소스

- **Phase 1**: CPU 가능, GPU 권장 (속도)
- **Phase 2**: H100 GPU 필수 (3DGS 훈련)

---

## 📚 참고 자료

### 강화학습
- [Stable-Baselines3 Documentation](https://stable-baselines3.readthedocs.io/)
- [PPO Paper](https://arxiv.org/abs/1707.06347)

### 3D Reconstruction
- [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [COLMAP](https://colmap.github.io/)

---

## 🤝 기여

이 프로젝트는 대학원 실습용 스타터 코드입니다.

### TODO

- [ ] Phase 2 `run_3dgs_pipeline()` 구현
- [ ] Baseline 비교 스크립트
- [ ] Ablation study (reward components)
- [ ] Visualization tools (선택된 프레임 분포)

---

## 📧 문의

- 프로젝트: VGGT Gaussian Splatting Research
- 환경: H100 GPU (80GB)
- 목표: WACV 2026 submission

---

## 🎉 시작하기

```bash
# 1. 환경 활성화
source ../env/vggt_env/bin/activate
cd rl_frame_selector

# 2. 패키지 설치
pip install -r requirements_rl.txt

# 3. Phase 1 학습 시작!
cd phase1_surrogate
python train.py --videos ../../datasets/custom/cChair.mp4

# 4. Tensorboard 확인
tensorboard --logdir ./logs
```

Good luck! 🚀
