# 🛠️ Tools Reference - 스크립트 빠른 참조

**프로젝트의 모든 실행 스크립트 사용법을 한눈에**

**Last Updated**: 2025-10-23

---

## 📋 목차

1. [run_pipeline.sh](#run_pipelinesh) - 파이프라인 실행
2. [extract_frames.sh](#extract_framessh) - 동영상 → 이미지
3. [prepare_standard_dataset.sh](#prepare_standard_datasetsh) - 데이터셋 준비
4. [setup_environment.sh](#setup_environmentsh) - 환경 설치

---

## 🚀 run_pipeline.sh

**역할**: P1-P5 파이프라인 통합 실행기

### 사용법
```bash
./run_pipeline.sh <PIPELINE> [DATASET_DIRECTORY]
```

### 파이프라인 옵션
```bash
P1   # COLMAP SfM + gsplat (전통적 방법)
P2   # VGGT Feed-Forward Only (가장 빠름)
P3   # VGGT + Bundle Adjustment
P4   # VGGT + gsplat (no BA)
P5   # VGGT + BA + gsplat (최고 품질)
```

### 예시

**기본 경로 사용**:
```bash
./run_pipeline.sh P5
# 기본값: ./datasets/DTU/scan1_standard
```

**명시적 경로 지정**:
```bash
# DTU 데이터셋
./run_pipeline.sh P5 ./datasets/DTU/scan14_standard

# 커스텀 데이터셋
./run_pipeline.sh P4 ./datasets/custom_scene

# CO3Dv2 데이터셋
./run_pipeline.sh P1 ./datasets/CO3Dv2/apple_110_13051_23361_standard
```

**병렬 실행** (H100 80GB):
```bash
# 여러 파이프라인 동시 실행
./run_pipeline.sh P1 ./datasets/DTU/scan14_standard &
./run_pipeline.sh P4 ./datasets/DTU/scan14_standard &
./run_pipeline.sh P5 ./datasets/DTU/scan14_standard &

# 진행 상황 모니터링
watch -n 1 'nvidia-smi; echo ""; ps aux | grep run_pipeline'
```

### 입력 요구사항
```
dataset_directory/
└── images/
    ├── 0001.jpg
    ├── 0002.jpg
    └── ...
```

### 출력 구조
```
results/P*_scanName_timestamp/
├── sparse/ (또는 vggt_sparse/ 또는 vggt_ba_sparse/)
├── ckpts/
├── ply/
├── renders/
├── stats/
├── metadata.json
└── analysis.json
```

### 파이프라인별 특징

| Pipeline | 시간 | VRAM | 품질 | 사용 사례 |
|----------|------|------|------|----------|
| **P1** | 15-25분 | 2.5GB | Baseline | 전통적 방법, 검증 |
| **P2** | 4분 | 3GB | 낮음 | 빠른 프로토타이핑 |
| **P3** | 4분 | 3GB | 중간 | VGGT 검증 |
| **P4** | 10분 | 2.6GB | 높음 | 균형잡힌 선택 |
| **P5** | 13분 | 20GB | 최고 | 최종 품질 |

---

## 🎬 extract_frames.sh

**역할**: 동영상에서 60개의 프레임을 균등하게 추출

### 사용법
```bash
./extract_frames.sh <VIDEO_FILE> [OUTPUT_DIRECTORY]
```

### 예시

**기본 출력 경로**:
```bash
./extract_frames.sh video.mp4
# 출력: ./datasets/video_frames/images/
```

**커스텀 출력 경로**:
```bash
./extract_frames.sh video.mp4 ./datasets/my_scene
# 출력: ./datasets/my_scene/images/

./extract_frames.sh /path/to/recording.mov ./datasets/room_scan
# 출력: ./datasets/room_scan/images/
```

**다양한 동영상 형식**:
```bash
./extract_frames.sh video.mp4 ./datasets/scene1
./extract_frames.sh video.mov ./datasets/scene2
./extract_frames.sh video.avi ./datasets/scene3
./extract_frames.sh video.mkv ./datasets/scene4
```

### 기능
- ✅ **60개 프레임 균등 추출** - 동영상 전체에서 균등하게 샘플링
- ✅ **자동 ffmpeg 설치** - 없으면 자동으로 설치
- ✅ **파일명 자동 정리** - 0001.jpg, 0002.jpg, ..., 0060.jpg
- ✅ **파이프라인 바로 사용** - 추출 후 즉시 run_pipeline.sh 실행 가능

### 출력 구조
```
output_directory/
└── images/
    ├── 0001.jpg
    ├── 0002.jpg
    ├── ...
    └── 0060.jpg
```

### 동영상 → 3D 재구성 워크플로우
```bash
# 1. 동영상에서 프레임 추출
./extract_frames.sh my_video.mp4 ./datasets/my_scene

# 2. 파이프라인 실행
./run_pipeline.sh P5 ./datasets/my_scene

# 3. 결과 확인
ls ./results/P5_my_scene_*/ply/
```

### 지원 동영상 형식
- MP4 (h264, h265)
- MOV (QuickTime)
- AVI
- MKV
- WebM

### 추출된 프레임 정보 확인
```bash
# 프레임 수 확인
ls ./datasets/my_scene/images/*.jpg | wc -l

# 파일 크기 확인
du -sh ./datasets/my_scene/images/
```

---

## 📦 prepare_standard_dataset.sh

**역할**: 데이터셋을 파이프라인 입력 형식으로 표준화

### 사용법
```bash
./prepare_standard_dataset.sh <SOURCE_PATH>
```

### 기능
- ✅ **60개로 균등 샘플링** (이미지가 60개 초과인 경우)
- ✅ **DTU 각도별 정렬** (COLMAP 최적화)
- ✅ **PNG/JPG 자동 감지**
- ✅ **데이터셋별 출력 경로** (DTU/CO3Dv2/Generic)

### 예시

**DTU 데이터셋**:
```bash
# scan1_train (343 images) → scan1_standard (60 images)
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan1_train

# scan14_train → scan14_standard
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan14_train

# scan24_train → scan24_standard
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan24_train
```

**CO3Dv2 데이터셋**:
```bash
./prepare_standard_dataset.sh ./datasets/CO3Dv2/apple/110_13051_23361/images
# 출력: ./datasets/CO3Dv2/apple_110_13051_23361_standard/
```

**커스텀 데이터셋**:
```bash
./prepare_standard_dataset.sh ./my_photos/
# 출력: ./datasets/my_photos_standard/
```

**extract_frames.sh 출력 사용**:
```bash
# 이미 60개라면 복사만 수행
./prepare_standard_dataset.sh ./datasets/video_frames/images
```

### 입력 형식
```
source_path/
├── image001.png  # 또는 .jpg
├── image002.png
└── ...
```

### 출력 구조
```
datasets/DATASET_NAME_standard/
└── images/
    ├── 0001.jpg
    ├── 0002.jpg
    └── ... (60개)
```

### DTU 각도 정렬

DTU 데이터셋은 7개 각도 × N장으로 구성되어 있습니다:
- 각도 0, 1, 2, 3, 4, 5, 6 순서로 정렬
- COLMAP incremental SfM에 최적화
- 100% 카메라 등록 보장

### 샘플링 로직
```bash
# 60개 이하: 모두 복사
ls source/*.png | wc -l  # 45 → 45개 모두 사용

# 60개 초과: 균등 샘플링
ls source/*.png | wc -l  # 343 → 60개 샘플링 (매 5번째)
```

---

## ⚙️ setup_environment.sh

**역할**: H100 환경 자동 설치 (최초 1회)

### 사용법
```bash
./setup_environment.sh
```

**소요 시간**: 15-20분 (인터넷 속도에 따라 다름)

### 자동 설치 항목

#### 1. 시스템 패키지
```bash
# COLMAP 3.7 (127 packages, 166MB)
sudo apt-get install -y colmap

# 기타 필수 패키지
sudo apt-get install -y wget git build-essential
```

#### 2. CUDA Toolkit 12.1
```bash
# /opt/cuda-12.1 설치
# fused-ssim 컴파일에 필요
```

#### 3. vggt_env (VGGT 환경)
```bash
# PyTorch 2.8.0
# pycolmap 3.10.0
# transformers, einops, kornia 등
```

#### 4. gsplat_env (Gaussian Splatting 환경)
```bash
# PyTorch 2.3.1+cu121
# gsplat 1.5.3
# lpips, fused-ssim 등
```

#### 5. H100 환경변수
```bash
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
```

### 설치 확인
```bash
# COLMAP 설치 확인
colmap -h | head -5

# 가상환경 확인
ls env/
# 출력: vggt_env/  gsplat_env/  setup_h100.sh

# CUDA Toolkit 확인
ls /opt/cuda-12.1/bin/nvcc
```

### 환경 활성화
```bash
# VGGT 환경
source ./env/vggt_env/bin/activate

# gsplat 환경
source ./env/gsplat_env/bin/activate

# H100 환경변수 (자동 활성화됨)
source ./env/setup_h100.sh
```

### 재설치가 필요한 경우
```bash
# 기존 환경 제거
rm -rf ./env/vggt_env ./env/gsplat_env

# 재설치
./setup_environment.sh
```

---

## 🔗 스크립트 조합 워크플로우

### 워크플로우 1: 동영상 → 3D 재구성
```bash
# 1. 동영상에서 60개 프레임 추출
./extract_frames.sh recording.mp4 ./datasets/my_room

# 2. 표준화 (이미 60개라면 생략 가능)
./prepare_standard_dataset.sh ./datasets/my_room

# 3. P5 파이프라인 실행
./run_pipeline.sh P5 ./datasets/my_room
```

### 워크플로우 2: DTU 데이터셋 처음 사용
```bash
# 1. 환경 설치 (최초 1회)
./setup_environment.sh

# 2. DTU 다운로드
# (Google Drive 또는 DTU 공식 사이트에서)

# 3. 표준화
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan14_train

# 4. 파이프라인 실행
./run_pipeline.sh P1 ./datasets/DTU/scan14_standard
./run_pipeline.sh P5 ./datasets/DTU/scan14_standard
```

### 워크플로우 3: 사진 폴더 → 3D 재구성
```bash
# 1. 사진 폴더 준비 (60-100장 권장)
ls ./my_photos/*.jpg | wc -l  # 이미지 수 확인

# 2. 표준화
./prepare_standard_dataset.sh ./my_photos

# 3. 파이프라인 실행
./run_pipeline.sh P4 ./datasets/my_photos_standard
```

### 워크플로우 4: 파이프라인 비교 실험
```bash
# 동일 데이터셋으로 P1, P4, P5 비교
DATASET="./datasets/DTU/scan14_standard"

./run_pipeline.sh P1 $DATASET &
./run_pipeline.sh P4 $DATASET &
./run_pipeline.sh P5 $DATASET &

wait  # 모든 파이프라인 완료 대기

# 결과 비교
cat ./results/P1_scan14_*/stats/val_step29999.json
cat ./results/P4_scan14_*/stats/val_step29999.json
cat ./results/P5_scan14_*/stats/val_step29999.json
```

---

## 🛠️ 트러블슈팅

### extract_frames.sh

**Q: "ffmpeg: not found" 에러**
```bash
# A: 자동 설치되지만, 수동 설치도 가능
sudo apt-get install -y ffmpeg
```

**Q: 추출된 프레임이 60개가 아님**
```bash
# A: 동영상이 너무 짧거나 프레임 수가 적음
# 동영상 정보 확인
ffprobe -v error -count_packets -show_entries stream=nb_read_packets -of csv=p=0 video.mp4
```

### prepare_standard_dataset.sh

**Q: "No such file or directory" 에러**
```bash
# A: 경로가 잘못되었거나 이미지가 없음
ls ./source_path/*.png  # 이미지 존재 확인
ls ./source_path/*.jpg
```

**Q: DTU 각도 정렬이 안됨**
```bash
# A: DTU 표준 파일명 형식이 아님
# 파일명 예: rect_001_3_r5000.png (각도 3)
ls ./datasets/DTU/*/rect_*.png | head -5
```

### run_pipeline.sh

**Q: "데이터셋 디렉토리가 존재하지 않음" 에러**
```bash
# A: images/ 폴더 확인
ls $DATASET_DIR/images/

# 사용 가능한 데이터셋 확인
find ./datasets -type d -name "images"
```

**Q: "H100 CUDA kernel 에러"**
```bash
# A: H100 환경변수 설정
source ./env/setup_h100.sh
export TORCH_CUDA_ARCH_LIST="9.0"
```

### setup_environment.sh

**Q: "sudo: command not found"**
```bash
# A: sudo 권한 필요 (COLMAP, CUDA Toolkit 설치)
# 관리자에게 문의하거나 수동 설치
```

**Q: 설치 중 인터넷 연결 끊김**
```bash
# A: 재실행하면 이어서 설치됨
./setup_environment.sh
```

---

## 📚 관련 문서

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 파이프라인 아키텍처 상세
- **[ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)** - 환경 설정 가이드
- **[QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)** - 빠른 시작 가이드

---

## 💡 팁과 모범 사례

### 데이터셋 준비
```bash
# 1. 이미지 품질 확인 (blur, 노출 등)
ls ./images/*.jpg | xargs -I{} identify -format "%f: %wx%h\n" {}

# 2. 60-80장이 적당 (너무 많으면 COLMAP 느려짐)
ls ./images/*.jpg | wc -l

# 3. 연속적인 카메라 움직임 권장 (비디오 프레임 이상적)
```

### 파이프라인 선택
```bash
# 빠른 테스트: P2
./run_pipeline.sh P2 ./datasets/test

# 품질 확인: P4
./run_pipeline.sh P4 ./datasets/test

# 최종 결과: P5
./run_pipeline.sh P5 ./datasets/production

# Baseline 비교: P1
./run_pipeline.sh P1 ./datasets/production
```

### 결과 분석
```bash
# PSNR, SSIM, LPIPS 확인
cat ./results/P5_*/stats/val_step29999.json | jq '.psnr, .ssim, .lpips'

# PLY 파일 크기
ls -lh ./results/P5_*/ply/point_cloud_29999.ply

# 처리 시간
cat ./results/P5_*/metadata.json | jq '.elapsed_time_seconds'
```

---

**Last Updated**: 2025-10-23
**Maintained by**: [@Jihunkim95](https://github.com/Jihunkim95)
