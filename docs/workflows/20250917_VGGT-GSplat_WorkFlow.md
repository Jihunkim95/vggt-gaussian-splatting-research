# 2025-09-17 VGGT-GSplat 워크플로우 정리

## 🎯 목표
P1 파이프라인을 Ground Truth 기반에서 **이미지만으로 시작하는 공정한 비교**로 변경하여 P1/P2/P3 간의 공정한 성능 비교 환경 구축

## 📋 작업 개요

### 🔍 문제 발견
- **P1**: DTU Ground Truth 카메라 포즈 사용 (부정행위!)
- **P2/P3**: 이미지만으로 VGGT가 포즈 추정
- → **불공정한 비교 조건**

### ✅ 해결 방안
P1을 **이미지 → COLMAP SfM → gsplat** 파이프라인으로 변경

## 🚀 구현 과정

### 1️⃣ **환경 분석 및 준비**
```bash
# 기존 P1 결과 확인
ls -la results/P1_20250917_054101/
# PLY: 99.3MB, 6999/7000 steps 완료 확인
```

**기존 P1 성능:**
- 훈련 시간: 3.7분
- 최종 단계: 6999/7000 (99.99%)
- PLY 크기: 99.3MB
- 초기 GS: 100,000 → 최종: ~128,000

### 2️⃣ **P1 파이프라인 재설계**

#### 핵심 수정 파일:
- `p1_baseline.py`: COLMAP SfM + gsplat 통합 구현
- `run_pipeline.sh`: P1/P1R 옵션 추가
- `create_simple_colmap_scan1.py`: 명령행 인자 지원
- `scripts/utils/switch_env.sh`: 경로 수정

#### 새로운 P1 구조:
```python
def run_p1_baseline(data_dir, output_dir, max_steps=30000):
    # Step 1: COLMAP SfM 실행
    success = run_colmap_sfm(data_path, sparse_dir)

    # Step 2: gsplat 훈련
    result = run_training_with_monitoring(training_cmd, max_steps)
```

### 3️⃣ **COLMAP SfM 구현**

#### COLMAP 설치:
```bash
apt update && apt install -y colmap
```

#### COLMAP SfM 파이프라인:
```python
def run_colmap_sfm(data_path, sparse_dir):
    # Step 1: Feature extraction (CPU 모드)
    colmap feature_extractor --SiftExtraction.use_gpu false

    # Step 2: Feature matching
    colmap exhaustive_matcher --SiftMatching.use_gpu false

    # Step 3: Sparse reconstruction
    colmap mapper --Mapper.ba_refine_focal_length true
```

#### Headless 환경 설정:
```python
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'
os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '330'
os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
```

### 4️⃣ **터미널 진행률 모니터링 구현**

```python
def run_training_with_monitoring(cmd, max_steps, description=""):
    # 실시간 stdout 파싱
    step_match = re.search(r'step\s+(\d+)', output.lower())

    # 진행률 바 표시
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"📊 [{bar}] {current_step:,}/{max_steps:,} ({progress:.1f}%)")
```

### 5️⃣ **파이프라인 실행 및 최적화**

#### 실행 명령어:
```bash
./run_pipeline.sh P1
```

#### 성능 최적화:
- CPU 기반 SIFT 특징점 추출
- GPU 없이도 안정적 실행
- 메모리 효율적 처리

## 📊 최종 결과

### ✅ **P1 COLMAP SfM + gsplat 성공!**

#### COLMAP SfM 결과:
- **Feature Extraction**: 21.5초 (60개 이미지)
- **Feature Matching**: 31.6분 (1,284개 매치)
- **Sparse Reconstruction**: 24.6분
- **총 COLMAP 시간**: 56.6분

#### COLMAP 출력 파일:
```
📷 cameras.bin: 3,368 bytes
📸 images.bin: 17,533,688 bytes
🔺 points3D.bin: 5,587,447 bytes
```

#### gsplat 훈련 결과:
- **훈련 단계**: 6999/7000 (99.99%)
- **PLY 파일**: 205MB (point_cloud_6999.ply)
- **체크포인트**: 205MB (ckpt_6999_rank0.pt)
- **훈련 시간**: 2.8분

#### 총 파이프라인 시간: **약 60분**

### 🎯 **공정한 비교 환경 구축 완료**

| 파이프라인 | 입력 조건 | 방법론 | 비교 상태 |
|-----------|----------|--------|----------|
| **P1** | 이미지만 | COLMAP SfM → gsplat | ✅ 공정 |
| **P2** | 이미지만 | VGGT Feed-Forward | ✅ 공정 |
| **P3** | 이미지만 | VGGT + Bundle Adjustment | ✅ 공정 |

## 🔧 기술적 세부사항

### gsplat_env 라이브러리 구성:
- **torch**: 2.3.1+cu121
- **gsplat**: 1.5.3
- **pycolmap**: cc7ea4b (특정 커밋)
- **nerfview**: 4538024 (GitHub)
- 총 100+ 라이브러리 (`/data/requirements_gsplat_env.txt` 참조)

### 핵심 gsplat 훈련 명령어:
```bash
python simple_trainer.py default \
    --data-dir temp_work_P1_20250917_064655 \
    --result-dir results/P1_20250917_064655 \
    --data-factor 1 \
    --max-steps 7000 \
    --save-ply \
    --disable-viewer
```

### 실행 환경:
- **GPU**: RTX 6000 Ada Generation (Compute Capability 8.9)
- **CUDA**: 12.1
- **메모리**: 48GB VRAM
- **디스크**: /data 마운트 (충분한 공간)

## 🚧 트러블슈팅 과정

### 1️⃣ **COLMAP GUI 문제**
- **문제**: `qt.qpa.xcb: could not connect to display`
- **해결**: `QT_QPA_PLATFORM=offscreen` 환경 변수 설정

### 2️⃣ **OpenGL 컨텍스트 오류**
- **문제**: `Check failed: context_.create()`
- **해결**: CPU 모드 폴백 (`--SiftExtraction.use_gpu false`)

### 3️⃣ **COLMAP 옵션 호환성**
- **문제**: `unrecognised option '--Mapper.triangulation_max_transitivity'`
- **해결**: COLMAP 3.7 지원 옵션으로 수정

### 4️⃣ **pycolmap API 차이**
- **문제**: `module 'pycolmap' has no attribute 'extract_features'`
- **해결**: COLMAP binary 직접 실행으로 우회

### 5️⃣ **미사용 코드 정리**
- **제거**: `p1_real_colmap.py`, `p1_pycolmap.py`
- **유지**: `p1_baseline.py` (통합 구현)

## 📈 성능 비교

### 이전 P1 (Ground Truth):
- **입력**: DTU 벤치마크 정확한 카메라 포즈
- **시간**: 3.7분 (훈련만)
- **결과**: 99.3MB PLY

### 새로운 P1 (COLMAP SfM):
- **입력**: 이미지만 (60개)
- **시간**: 60분 (56.6분 SfM + 2.8분 훈련)
- **결과**: 205MB PLY
- **품질**: 6999/7000 steps 완료

## 📦 최종 산출물

### 1️⃣ **코드 변경사항**
```
🚀 P1 진짜 COLMAP SfM + gsplat 파이프라인 구현
4 files changed, 409 insertions(+), 85 deletions(-)
```

### 2️⃣ **새로운 파일**
- `/data/requirements_gsplat_env.txt`: 환경 요구사항 정리

### 3️⃣ **실행 결과**
- `results/P1_20250917_064655/`: 205MB PLY + 체크포인트
- `temp_work_P1_20250917_064655/sparse/0/`: COLMAP SfM 결과

## 🎉 결론

### ✅ **달성 목표**
1. **공정한 비교 환경**: P1/P2/P3 모두 이미지만으로 시작
2. **완전한 파이프라인**: COLMAP SfM + gsplat 통합
3. **실용적 구현**: Headless 환경에서 안정적 실행
4. **성능 모니터링**: 터미널 기반 실시간 진행률

### 🚀 **향후 활용**
- **연구 목적**: 전통적 SfM vs 딥러닝 기반 방법 비교
- **벤치마크**: DTU 데이터셋 표준 평가
- **확장성**: 다른 데이터셋 적용 가능

### 💡 **핵심 학습**
1. **환경 격리**: 각 파이프라인별 독립 실행 환경
2. **의존성 관리**: 특정 커밋/버전 고정의 중요성
3. **모니터링**: 장시간 실행 작업의 진행률 추적
4. **트러블슈팅**: Headless 환경 GUI 도구 실행 기법

---

## 📚 참고 자료

- **COLMAP**: [https://colmap.github.io/](https://colmap.github.io/)
- **gsplat**: [http://www.gsplat.studio/](http://www.gsplat.studio/)
- **DTU Dataset**: Multi-View Stereo benchmark
- **pycolmap**: [https://github.com/rmbrualla/pycolmap](https://github.com/rmbrualla/pycolmap)

---

**작성일**: 2025-09-17
**작성자**: Claude Code Assistant
**프로젝트**: VGGT-Gaussian Splatting Research
**저장소**: [Jihunkim95/vggt-gaussian-splatting-research](https://github.com/Jihunkim95/vggt-gaussian-splatting-research)