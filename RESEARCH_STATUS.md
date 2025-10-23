# 🚀 VGGT-Gaussian Splatting Research Status

**H100 GPU 환경 기반 연구 진행 상황**

**Last Updated**: 2025-10-23
**Environment**: H100 80GB + CUDA 12.1 + Ubuntu 22.04

---

## 📊 현재 상태 (Current Status)

### ✅ 완료된 작업 (Completed)

#### 1. 환경 구축 (Environment Setup)
- ✅ **H100 GPU 최적화** (TORCH_CUDA_ARCH_LIST=9.0)
- ✅ **자동 환경 설치 스크립트** (setup_environment.sh)
- ✅ **COLMAP 3.7 통합** (apt-get 설치)
- ✅ **CUDA Toolkit 12.1** (/opt/cuda-12.1, fused-ssim 컴파일용)
- ✅ **가상환경 분리** (vggt_env + gsplat_env)
  - vggt_env: PyTorch 2.8.0, pycolmap 3.10.0
  - gsplat_env: PyTorch 2.3.1+cu121, gsplat 1.5.3

#### 2. 파이프라인 구현 (Pipeline Implementation)
- ✅ **P1 Baseline** (COLMAP SfM + gsplat)
  - p1_baseline.py 완성
  - H100 환경변수 자동 설정
  - COLMAP 3-step SfM: Feature extraction, Matching, Sparse reconstruction
  - CPU fallback 지원 (OpenGL 에러 대응)

- ✅ **P4 Balanced** (VGGT + gsplat, no BA)
  - run_pipeline.sh 통합
  - VGGT feed-forward 초기화 (빠른 처리)
  - Bundle Adjustment 없이 gsplat 직접 훈련
  - 처리 시간: ~8분 (P1보다 2-3배 빠름)

- ✅ **P5 Full** (VGGT + BA + gsplat)
  - run_pipeline.sh 통합
  - VGGT 초기화 (3.5분)
  - Bundle Adjustment 최적화
  - gsplat 훈련 (30K steps)

#### 3. 데이터셋 준비 (Dataset Preparation)
- ✅ **prepare_standard_dataset.sh 개선**
  - DTU 각도별 정렬 (0→1→2→3→4→5→6) for COLMAP 최적화
  - PNG/JPG 자동 감지 및 지원
  - 데이터셋별 출력 경로 (DTU/CO3Dv2/Generic)
  - 균등 샘플링 (343개 → 60개)

- ✅ **DTU 데이터셋 검증**
  - scan14: 60/60 images, 60/60 cameras registered (100%)
  - scan24: P5 완료, PSNR 16.06, SSIM 0.741

- ✅ **CO3Dv2 데이터셋 검증**
  - apple: 80/80 cameras registered (100%)
  - P1 완료: 13.8분, COLMAP 100% 성공

#### 4. 도구 개발 (Tools Development)
- ✅ **extract_frames.sh** (비디오 → 이미지 변환)
  - 동영상에서 60개 프레임 균등 추출
  - ffmpeg + bc 자동 설치
  - 지원 포맷: MP4, MOV, AVI 등 모든 ffmpeg 호환 비디오
  - 파이프라인 직접 호환 출력 (images/ 디렉토리)

#### 5. 문서화 (Documentation)
- ✅ **README.md** - H100 환경, P4 파이프라인, extract_frames.sh 반영
- ✅ **QUICK_START_GUIDE.md** - P4 파이프라인, 비디오 워크플로우 추가 (2025-10-23)
- ✅ **docs/ARCHITECTURE.md** - 전체 파이프라인 아키텍처 (P1-P5) 통합 문서
- ✅ **docs/ENVIRONMENT_SETUP.md** - H100 환경 설정 완전 가이드
- ✅ **docs/TOOLS_REFERENCE.md** - 모든 스크립트 사용법 레퍼런스
- ✅ **워크플로우 문서** (docs/workflows/)
  - 20251006_VGGT-GSplat_WorkFlow.md (H100 호환성 해결)
  - 20251007_VGGT-GSplat_WorkFlow.md (P1 구현 & DTU 각도 정렬)
  - 기타 연구 일지 (2025-09-08 ~ 2025-10-23)

---

## 📈 실험 결과 (Experimental Results)

### P1 Baseline (COLMAP + gsplat)

| Dataset | Frames | VRAM | Time | COLMAP Reg. | Status |
|---------|--------|------|------|-------------|--------|
| **CO3Dv2 apple** | 60 | ~2.5GB | 13.8min | 80/80 (100%) | ✅ |
| **DTU scan14** | 60 | ~2.5GB | 22.8min | 60/60 (100%) | ✅ |

**특징**:
- 전통적인 COLMAP SfM baseline
- DTU 각도 정렬로 100% 카메라 등록 성공
- CO3Dv2: 비디오 프레임 → COLMAP 완벽 호환

### P4 Balanced (VGGT + gsplat, no BA)

| Dataset | Frames | VRAM | Time | PSNR | SSIM | LPIPS | Gaussians | Status |
|---------|--------|------|------|------|------|-------|-----------|--------|
| **DTU scan14** | 60 | ~2.6GB | 8.0min | 19.27 | 0.727 | - | 1,577,187 | ✅ |

**특징**:
- VGGT feed-forward + gsplat (Bundle Adjustment 제외)
- P1 대비 2-3배 빠른 처리 (8분 vs 23분)
- 메모리 효율적 (~2.6GB VRAM)
- 빠른 프로토타이핑에 최적

### P5 Full (VGGT + BA + gsplat)

| Dataset | Frames | VRAM | Time | PSNR | SSIM | LPIPS | Gaussians | Status |
|---------|--------|------|------|------|------|-------|-----------|--------|
| **DTU scan24** | 60 | ~20GB | 13.2min | 16.06 | 0.741 | 0.227 | 1,469,317 | ✅ |

**특징**:
- VGGT + Bundle Adjustment + gsplat 통합
- H100 메모리 효율적 (2.43GB/80GB, 3% utilization)
- 고품질 3D 재구성

---

## 🔍 주요 발견사항 (Key Findings)

### 1. H100 CUDA 아키텍처 호환성
- **문제**: `TORCH_CUDA_ARCH_LIST="8.9"` → H100에서 커널 실행 불가
- **해결**: `TORCH_CUDA_ARCH_LIST="9.0"` 설정
- **영향**: run_pipeline.sh, p1_baseline.py, setup_environment.sh 모두 반영

### 2. DTU 데이터셋 COLMAP 호환성
- **문제**: DTU 이미지 순서 무작위 → COLMAP incremental SfM 실패 (11/60 등록)
- **해결**: 각도별 정렬 (0→1→2→3→4→5→6) in prepare_standard_dataset.sh
- **결과**: 60/60 cameras registered (100%)

### 3. CO3Dv2 vs DTU
- **CO3Dv2**: 비디오 프레임 → 연속 카메라 움직임 → COLMAP 완벽 호환
- **DTU**: 7각도 × 다양한 조명 → 불연속 배치 → 각도 정렬 필요
- **권장**: CO3Dv2 (Seen), DTU (Unseen), Custom (사용자 촬영)

### 4. 시스템 의존성
- **COLMAP**: apt-get install 필수 (127 packages, 166MB)
- **CUDA Toolkit 12.1**: fused-ssim 컴파일 필수
- **opencv-python-headless**: libGL.so.1 문제 해결

### 5. 비디오 기반 워크플로우 (2025-10-23)
- **문제**: 동영상 파일을 직접 파이프라인 입력으로 사용 불가
- **해결**: extract_frames.sh로 60개 프레임 균등 추출
- **장점**:
  - 스마트폰 촬영 영상 직접 활용 가능
  - CO3Dv2와 유사한 연속 프레임 → COLMAP 호환성 우수
  - 데이터셋 준비 시간 단축 (1-2분)

---

## 🔄 진행 중 (In Progress)

### 데이터셋 확장
- [ ] DTU 추가 스캔 (scan18, scan37 등)
- [ ] CO3Dv2 다양한 카테고리 (hydrant, teddybear 등)
- [ ] 비디오 기반 커스텀 데이터셋 (extract_frames.sh 활용)

### 파이프라인 검증
- [ ] P2 (VGGT only) 재검증
- [ ] P3 (VGGT + BA) 재검증

### 정량적 비교
- [ ] P1 vs P5 Chamfer Distance
- [ ] 메모리 프로파일링
- [ ] 처리 시간 상세 분석

---

## 📁 프로젝트 구조 (Project Structure)

```
vggt-gaussian-splatting-research/
├── setup_environment.sh              # 자동 환경 설치 (H100 최적화)
├── run_pipeline.sh                   # 통합 파이프라인 실행기 (P1-P5)
├── prepare_standard_dataset.sh      # 데이터셋 표준화 (DTU 각도 정렬)
├── extract_frames.sh                 # ⭐ 비디오 → 60개 프레임 추출 (NEW)
├── p1_baseline.py                   # P1 파이프라인 (COLMAP + gsplat)
│
├── env/
│   ├── vggt_env/                    # VGGT 환경
│   ├── gsplat_env/                  # gsplat 환경
│   └── setup_h100.sh                # H100 환경변수
│
├── datasets/
│   ├── DTU/
│   │   ├── Rectified/scan*_train/  # 원본 (343 images)
│   │   └── scan*_standard/          # 표준화 (60 images, 각도 정렬)
│   └── CO3Dv2/
│       └── apple_*_standard/        # 표준화 (60 images)
│
├── results/
│   ├── P1_*/                        # COLMAP + gsplat 결과
│   ├── P4_*/                        # VGGT + gsplat 결과 (no BA)
│   └── P5_*/                        # VGGT + BA + gsplat 결과
│
└── docs/
    ├── ARCHITECTURE.md               # ⭐ 파이프라인 아키텍처 (P1-P5) (NEW)
    ├── ENVIRONMENT_SETUP.md          # ⭐ H100 환경 설정 가이드 (NEW)
    ├── TOOLS_REFERENCE.md            # ⭐ 모든 스크립트 사용법 (NEW)
    ├── workflows/                    # 연구 일지 (2025-09-08 ~ 2025-10-23)
    │   ├── 20251006_VGGT-GSplat_WorkFlow.md
    │   ├── 20251007_VGGT-GSplat_WorkFlow.md
    │   └── ...                       # 기타 워크플로우 문서
    ├── archive/                      # 구버전 문서
    ├── QUICK_START_GUIDE.md          # H100 Quick Start
    └── RESEARCH_STATUS.md            # 이 문서
```

---

## 🎯 다음 단계 (Next Steps)

### 1. 정량적 벤치마크 (Quantitative Benchmark)
```bash
# P1 vs P5 비교
python scripts/compare_pipelines.py \
    --p1 ./results/P1_scan24_* \
    --p5 ./results/P5_scan24_* \
    --metrics chamfer psnr ssim lpips
```

### 2. 추가 데이터셋 실험
```bash
# DTU scan18
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan18_train
./run_pipeline.sh P4 ./datasets/DTU/scan18_standard
./run_pipeline.sh P5 ./datasets/DTU/scan18_standard

# 비디오 기반 커스텀 데이터셋
./extract_frames.sh recording.mp4 ./datasets/my_room
./run_pipeline.sh P4 ./datasets/my_room
./run_pipeline.sh P5 ./datasets/my_room

# CO3Dv2 hydrant
./prepare_standard_dataset.sh ./datasets/CO3Dv2/hydrant/*/images
./run_pipeline.sh P4 ./datasets/CO3Dv2/hydrant_*_standard
```

### 3. Ablation Studies
- [ ] BA iterations: 10 vs 50 vs 100
- [ ] gsplat steps: 7K vs 15K vs 30K
- [ ] 이미지 수: 30 vs 60 vs 80

### 4. 논문 작성 준비
- [ ] 실험 결과 테이블 정리
- [ ] Figure 생성 (Pareto frontier, 시각적 비교)
- [ ] 통계적 유의성 검증

---

## 💡 연구 방향 (Research Direction)

### 목표 학회
- **WACV 2026** - Workshop on Applications of Computer Vision
- **Focus**: Practical deployment + Thorough evaluation

### 핵심 기여 (Core Contributions)
1. **H100 환경 최적화** - CUDA arch 9.0 지원
2. **자동 환경 설치** - setup_environment.sh로 One-command setup
3. **DTU COLMAP 호환성** - 각도 정렬로 100% 등록 달성
4. **파이프라인 비교** - P1 (traditional) vs P4 (balanced) vs P5 (maximum quality)
5. **비디오 워크플로우** - extract_frames.sh로 동영상 직접 활용

### 데이터셋 전략
- **Seen Dataset**: CO3Dv2 (VGGT 학습 데이터)
- **Unseen Dataset**: DTU (VGGT 미학습 데이터)
- **Custom Dataset**: 사용자 직접 촬영

---

## 📚 참고 자료 (References)

### 워크플로우 문서
- [20251006 H100 호환성 해결](docs/workflows/20251006_VGGT-GSplat_WorkFlow.md)
- [20251007 P1 구현 및 DTU 각도 정렬](docs/workflows/20251007_VGGT-GSplat_WorkFlow.md)

### 가이드 문서
- [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) - H100 환경 Quick Start (P1-P5)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - 파이프라인 아키텍처 완전 가이드
- [docs/ENVIRONMENT_SETUP.md](./docs/ENVIRONMENT_SETUP.md) - H100 환경 설정 상세 가이드
- [docs/TOOLS_REFERENCE.md](./docs/TOOLS_REFERENCE.md) - 모든 스크립트 사용법 레퍼런스
- [README.md](./README.md) - 프로젝트 개요
- [RESEARCH_STATUS.md](./RESEARCH_STATUS.md) - 이 문서

### 핵심 스크립트
- [setup_environment.sh](./setup_environment.sh) - 자동 환경 설치
- [run_pipeline.sh](./run_pipeline.sh) - 파이프라인 실행기 (P1-P5)
- [prepare_standard_dataset.sh](./prepare_standard_dataset.sh) - 데이터셋 준비
- [extract_frames.sh](./extract_frames.sh) - 비디오 → 60개 프레임 추출
- [p1_baseline.py](./p1_baseline.py) - P1 파이프라인

---

## 🔗 관련 논문 (Related Papers)

### VGGT
- **Paper**: Visual Geometry Grounded Transformer (CVPR 2025, Best Paper)
- **GitHub**: https://github.com/facebookresearch/vggt

### 3D Gaussian Splatting
- **Paper**: 3D Gaussian Splatting for Real-Time Radiance Field Rendering (SIGGRAPH 2023)
- **gsplat**: https://github.com/nerfstudio-project/gsplat

---

**Last Updated**: 2025-10-23
**Maintainer**: [@Jihunkim95](https://github.com/Jihunkim95)
**Status**: ✅ H100 환경 검증 완료, P1/P4/P5 파이프라인 검증 완료, 비디오 워크플로우 추가
