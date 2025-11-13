# 강화학습 기반 적응형 프레임 선택 연구 기획서
**Reinforcement Learning for Adaptive Frame Selection in 3D Gaussian Splatting**

---

## 1. 연구 배경 및 동기

3D Gaussian Splatting (3DGS)는 Neural Radiance Fields (NeRF)의 대안으로 빠르게 주목받고 있으나, 입력 이미지 선택이 재구성 품질에 결정적 영향을 미친다. 기존 방법들은 균등 샘플링(uniform) 또는 품질 기반 휴리스틱(quality-based heuristic)에 의존하지만, 이는 장면별 특성을 반영하지 못하고 COLMAP의 feature matching 실패로 이어질 수 있다.

본 연구는 강화학습(Reinforcement Learning)을 활용하여 비디오 프레임에서 3DGS 재구성 품질을 최대화하는 최적의 이미지 부분집합을 자동으로 선택하는 시스템을 제안한다.

---

## 2. 연구 목표

**목표**: 비디오(300 프레임) → 최적의 60개 프레임 선택 → 3DGS 품질(PSNR/SSIM) 최대화

**핵심 과제**:
1. **Overlap 보장**: COLMAP feature matching 성공을 위한 프레임 간 충분한 겹침
2. **품질 최적화**: Sharpness, BRISQUE 등 이미지 품질 고려
3. **Sample Efficiency**: 실제 3DGS 훈련(10분/episode)의 계산 비용 문제 해결
4. **Zero-shot Generalization**: 대규모 공개 데이터셋으로 학습 → 새 비디오에 재학습 없이 적용

---

## 3. 강화학습 접근법

### 3.1 문제 정식화 (MDP)

- **State** (s): 현재 프레임의 품질 메트릭 (sharpness, BRISQUE, brightness) + 선택 상태 (temporal position, selected count)
- **Action** (a): {SKIP (0), SELECT (1)}
- **Reward** (r): Surrogate reward (Phase 1) / Real 3DGS metrics (Phase 2)

### 3.2 대규모 데이터셋 학습 (Generalization)

**학습 데이터셋: CO3Dv2 (Common Objects in 3D v2)**
- Meta AI Research의 공개 데이터셋 (19,000+ 물체, 50개 카테고리)
- 학습: 1,000개 비디오 (다양한 시점, 조명, 장면)
- 평가: DTU (정적 장면) + Custom 비디오 (동적 장면)
- **Zero-shot 적용**: 새 비디오에 재학습 없이 즉시 적용 가능

**왜 CO3Dv2인가?**
- 표준화된 벤치마크 (재현성 보장)
- 다양한 객체 카테고리 (일반화 능력 향상)
- 3D reconstruction 연구에 최적화

### 3.3 2단계 학습 전략 (Hybrid RL)

**Phase 1: Surrogate Reward on CO3Dv2 (1-2시간)**
- **Reward 구성** (SIFT 기반 빠른 평가):
  - Temporal uniformity (20%)
  - Average quality (30%)
  - Quality diversity (10%)
  - **Overlap score (40%)** ← SIFT feature matching

- **Hard Constraint**: max_gap = 10 (연속 프레임 간 최대 간격)
  - Gap violation → Penalty (-5.0) + 강제 SKIP
  - COLMAP 성공률 100% 보장

- **Multi-video Training**: 1,000개 비디오에서 병렬 학습

**Phase 2: Fine-tuning with Real 3DGS (3-5시간)**
- Reward: `0.5 * PSNR + 0.3 * SSIM + 0.2 * (1 - LPIPS)`
- CO3Dv2 부분집합 (50개 비디오)에서 실제 3DGS 평가
- H100 GPU 활용하여 병렬 파이프라인 실행

### 3.4 알고리즘: Proximal Policy Optimization (PPO)

PPO는 sample efficiency와 안정성이 검증된 on-policy 알고리즘으로, 제약 조건이 있는 sequential decision making에 적합하다.

---

## 4. 기대 효과

| Metric | Baseline (Stratified) | RL Agent (Target) |
|--------|----------------------|-------------------|
| COLMAP Success Rate | 90-95% | **100%** |
| PSNR | 18.0 dB | **18.5+ dB** (+0.5dB) |
| SSIM | 0.70 | **0.72+** |
| Overlap Score | 0.63 | **0.75+** (+19%) |

**실용적 기여**:
- 비디오 데이터 → 3DGS 자동화 파이프라인
- **Zero-shot Generalization**: 새 비디오에 재학습 불필요
- 표준 벤치마크 (CO3Dv2) 사용으로 재현성 보장
- H100 GPU 최적화 워크플로우

---

## 5. 참고 문헌

[1] Kerbl, B., et al. (2023). **3D Gaussian Splatting for Real-Time Radiance Field Rendering**. *ACM Transactions on Graphics (SIGGRAPH)*, 42(4).
→ 3DGS의 기초 이론 및 입력 데이터 요구사항

[2] Schönberger, J. L., & Frahm, J. M. (2016). **Structure-from-Motion Revisited**. *CVPR*.
→ COLMAP의 feature matching 및 overlap 요구사항

[3] Schulman, J., et al. (2017). **Proximal Policy Optimization Algorithms**. *arXiv:1707.06347*.
→ PPO 알고리즘의 이론적 배경

[4] Mildenhall, B., et al. (2020). **NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis**. *ECCV*.
→ View synthesis의 입력 이미지 선택 전략

[5] Reizenstein, J., et al. (2021). **Common Objects in 3D: Large-Scale Learning and Evaluation of Real-life 3D Category Reconstruction**. *ICCV*.
→ CO3Dv2 데이터셋 (19,000+ 물체, 50개 카테고리)

[6] Mittal, A., et al. (2012). **No-Reference Image Quality Assessment in the Spatial Domain**. *IEEE TIP*.
→ BRISQUE 품질 평가 메트릭

[7] Lowe, D. G. (2004). **Distinctive Image Features from Scale-Invariant Keypoints**. *IJCV*, 60(2), 91-110.
→ SIFT feature matching 이론

[8] Wang, T., et al. (2023). **VGGT: Visual Geometry Grounded Transformer for 3D Reconstruction**. *NeurIPS*.
→ Transformer 기반 3D reconstruction (본 연구의 baseline)

---

## 6. 연구 일정 (4주)

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Surrogate reward system 구축 | PPO agent (Phase 1) |
| 2 | Phase 1 학습 및 검증 | Trained model + 학습 곡선 |
| 3 | Phase 2 fine-tuning | Real 3DGS 통합 |
| 4 | Baseline 비교 및 보고서 | 실험 결과 + 논문 초안 |

---

**연구 환경**: NVIDIA H100 80GB, PyTorch 2.8.0, Stable-Baselines3
**목표 학회**: WACV 2026 (Workshop on Applications of Computer Vision)
**연구자**: 김지훈 (서강대학교 대학원)

---

**Keywords**: Reinforcement Learning, 3D Gaussian Splatting, Frame Selection, COLMAP, Proximal Policy Optimization, View Synthesis
