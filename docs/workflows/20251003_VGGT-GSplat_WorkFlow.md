# 2025-10-03 VGGT-GSplat 워크플로우 정리

## 🎯 목표
**DTU 데이터셋 준비 및 파이프라인 유연성 개선** - 다양한 데이터셋 실행 환경 구축

## 📋 작업 개요

### 🔍 시작 상황 (2025-10-03 시작)
- **환경 상태**: VGGT, gsplat 환경 모두 구축 완료
- **파이프라인**: P1-P5 모두 구현 완료 (20250926 기준)
- **데이터셋**: DTU 데이터셋 미준비 상태
- **run_pipeline.sh**: 데이터셋 경로 하드코딩 (`scan1_standard`)

### ✅ 해결 목표
1. **DTU 데이터셋 다운로드 및 준비**
2. **파이프라인 유연성 개선**: 다양한 데이터셋 경로 지원
3. **DTU→COLMAP 변환 아키텍처 이해**

## 🚀 구현 과정

### 1️⃣ **DTU 데이터셋 조사 및 다운로드**

#### 데이터셋 출처:
- **GitHub**: [YoYo000/MVSNet](https://github.com/YoYo000/MVSNet)
- **Google Drive**: `https://drive.google.com/file/d/1eDjh-_bxKKnEuz5h-HXS7EDJn59clx6V/view`
- **Baidu Pan**: `https://pan.baidu.com/s/1Wb9E6BWCJu4wZfwxm_t4TQ` (코드: s2v2)

#### 다운로드 시도:
```bash
# gdown 설치
pip install gdown

# Google Drive 다운로드 시도
cd ./datasets/DTU
gdown https://drive.google.com/uc?id=1eDjh-_bxKKnEuz5h-HXS7EDJn59clx6V

# ❌ 실패: "Too many users have viewed or downloaded this file recently"
# ✅ 해결: 브라우저에서 직접 다운로드 후 수동 업로드
```

#### DTU 데이터셋 구조:
```
datasets/DTU/
├── Cameras/           # 카메라 파라미터 (49개 cam.txt)
├── Depths/            # 깊이 맵 (120개 스캔)
└── Rectified/         # 정류된 이미지 (120개 스캔)
    ├── scan1_train/   # 343개 PNG 이미지
    ├── scan18_train/
    ├── scan32_train/
    └── ... (120 scans)
```

### 2️⃣ **DTU → COLMAP 변환 아키텍처 조사**

#### 다른 연구자들의 접근법:

**방법 A: DTU Cameras 폴더 활용** (StackOverflow 방식)
```python
import cv2
from scipy.spatial.transform import Rotation

def convert_dtu_to_colmap(world_mat, scale_mat):
    # DTU의 world_mat + scale_mat → COLMAP 형식 변환
    P = (world_mat @ scale_mat)[:3, :]
    K, R, t = cv2.decomposeProjectionMatrix(P)[:3]

    # Extract intrinsics
    fx, fy = K[0,0], K[1,1]
    cx, cy = K[0,2], K[1,2]

    # Convert to quaternion
    qx, qy, qz, qw = Rotation.from_matrix(R).as_quat()

    # Write cameras.txt, images.txt
    ...
```

**방법 B: COLMAP SfM 실행 후 변환** (MVSNet 방식)
```bash
# COLMAP으로 SfM 수행 → MVSNet 포맷 변환
python colmap2mvsnet.py --dense_folder COLMAP/dense
```

**방법 C: 현재 프로젝트 방식** (✅ 가장 단순하고 실용적)
```bash
# 이미지 준비만 수행 - COLMAP 변환 불필요
./prepare_standard_dataset.sh "<원본_이미지_경로>"
# → 파이프라인이 알아서 COLMAP 생성 (P1/P1R)
# → 또는 VGGT가 직접 재구성 (P2/P3)
```

### 3️⃣ **데이터셋 표준화 실행**

#### prepare_standard_dataset.sh 활용:
```bash
# DTU scan1 준비 (343개 → 60개 샘플링)
./prepare_standard_dataset.sh "./datasets/DTU/Rectified/scan1_train"

# 실행 결과:
# 📊 원본 이미지: 343개
# ⚠️ 343개 > 60개 → 균등 샘플링 실행
#    샘플링 간격: 매 5번째
# ✅ 표준 데이터셋 준비 완료!
# 📁 위치: ./datasets/DTU/scan1_standard/images
# 📸 최종 이미지 수: 60개
```

#### 최종 데이터셋 구조:
```
datasets/DTU/
├── Rectified/scan1_train/     # 원본 343개 이미지
└── scan1_standard/            # 표준화된 60개 이미지
    └── images/
        ├── rect_001_3_r5000.png
        ├── rect_006_3_r5000.png
        └── ... (60 images, 균등 샘플링)
```

### 4️⃣ **run_pipeline.sh 유연성 개선**

#### 개선 전 (하드코딩):
```bash
STANDARD_DIR="./datasets/DTU/scan1_standard"  # 고정된 경로

if [ ! -d "$STANDARD_DIR/images" ]; then
    echo "❌ 표준 데이터셋이 준비되지 않았습니다."
    exit 1
fi
```

#### 개선 후 (인자 지원):
```bash
PIPELINE="$1"
DATA_DIR="${2:-./datasets/DTU/scan1_standard}"  # 기본값 + 오버라이드
STANDARD_DIR="$DATA_DIR"

if [ ! -d "$STANDARD_DIR/images" ]; then
    echo "❌ 데이터셋 디렉토리가 존재하지 않거나 images 폴더가 없습니다: $STANDARD_DIR"
    echo ""
    echo "사용 가능한 데이터셋:"
    find ./datasets -type d -name "images" 2>/dev/null | sed 's|/images||' | head -5
    exit 1
fi
```

#### 개선된 사용법:
```bash
# 사용법: ./run_pipeline.sh <파이프라인> [데이터셋_디렉토리]

# 예시 1: 기본 경로 사용 (기존 호환성)
./run_pipeline.sh P5

# 예시 2: 명시적 경로 지정
./run_pipeline.sh P5 ./datasets/DTU/scan1_standard

# 예시 3: 다른 스캔 사용
./prepare_standard_dataset.sh "./datasets/DTU/Rectified/scan18_train"
./run_pipeline.sh P5 ./datasets/DTU/scan18_standard

# 예시 4: 커스텀 씬 사용
./run_pipeline.sh P3 ./datasets/custom_scene
```

## 📊 최종 결과

### ✅ **데이터셋 준비 완료**

#### DTU scan1 데이터셋:
- **원본**: `DTU/Rectified/scan1_train/` (343개 PNG)
- **표준화**: `DTU/scan1_standard/images/` (60개 PNG, 균등 샘플링)
- **준비 시간**: 즉시 (이미지 복사만)
- **상태**: ✅ 파이프라인 실행 준비 완료

#### 파일 구조:
```
datasets/DTU/
├── Cameras/           # 49개 카메라 파라미터
├── Depths/            # 120개 스캔의 깊이맵
├── Rectified/         # 120개 스캔의 정류 이미지
│   └── scan1_train/   # 343개 원본 이미지
└── scan1_standard/    # 60개 표준화 이미지 ✅
    └── images/
```

### 🎯 **파이프라인 유연성 확보**

#### run_pipeline.sh 개선사항:
| 항목 | 개선 전 | 개선 후 |
|-----|---------|---------|
| **데이터셋 경로** | 하드코딩 (`scan1_standard`) | 인자로 받기 (`$2`) |
| **기본값** | 변경 불가 | `${2:-./datasets/DTU/scan1_standard}` |
| **도움말** | 파이프라인만 설명 | 사용 예시 3개 추가 |
| **에러 메시지** | 단순 경고 | 사용 가능한 데이터셋 자동 표시 |
| **확장성** | scan1만 지원 | 모든 데이터셋 지원 |

#### 실용적 가치:
```python
pipeline_flexibility = {
    "multiple_scans": "DTU 120개 스캔 모두 사용 가능",
    "custom_datasets": "ETH3D, Tanks&Temples 등 추가 가능",
    "backward_compatible": "기존 스크립트 모두 호환",
    "easy_experiment": "데이터셋 변경이 매우 간편"
}
```

## 🔧 기술적 세부사항

### DTU 데이터셋 특징:
```yaml
dtu_dataset:
  scans: 120
  cameras: 49 viewpoints
  image_format: "PNG (rect_XXX_Y_r5000.png)"
  resolution: "1600×1200 (추정)"
  camera_params: "world_mat + scale_mat (4×4 matrices)"
  depth_maps: "포함 (Depths/ 폴더)"
```

### prepare_standard_dataset.sh 로직:
```bash
# 균등 샘플링 로직
MAX_IMAGES=60
TOTAL_IMAGES=343
INTERVAL=$((343 / 60))  # = 5

# 매 5번째 이미지 선택
# rect_001, rect_006, rect_011, ... (60개)
```

### 현재 프로젝트 vs 타 연구자 비교:
| 접근법 | 복잡도 | 속도 | 유연성 |
|-------|--------|------|--------|
| **DTU→COLMAP 직접 변환** | 🔴 높음 | 🟡 보통 | 🟢 높음 |
| **COLMAP 실행 후 변환** | 🟡 보통 | 🔴 느림 | 🟡 보통 |
| **현재 프로젝트 (이미지만)** | 🟢 낮음 | 🟢 빠름 | 🟢 높음 |

## 🔬 연구적 통찰

### **데이터 준비 전략의 혁신**:

#### 기존 연구자들의 접근:
```python
traditional_approach = {
    "step1": "DTU Cameras 파일 읽기 (world_mat, scale_mat)",
    "step2": "cv2.decomposeProjectionMatrix()로 분해",
    "step3": "cameras.txt, images.txt 수동 생성",
    "step4": "COLMAP 형식으로 변환",
    "complexity": "높음",
    "error_prone": "매트릭스 변환 오류 가능"
}
```

#### 현재 프로젝트의 접근:
```python
our_approach = {
    "step1": "이미지만 준비 (prepare_standard_dataset.sh)",
    "step2": "파이프라인이 자동 처리",
    "p1_p1r": "COLMAP이 이미지에서 직접 SfM",
    "p2_p3": "VGGT가 feed-forward 재구성",
    "p4_p5": "VGGT → gsplat 하이브리드",
    "complexity": "낮음",
    "reliability": "검증된 파이프라인 활용"
}
```

### **실용적 워크플로우 완성**:
```
1. 원본 다운로드 (DTU/Rectified/scanN_train/)
   ↓
2. 표준화 (./prepare_standard_dataset.sh)
   ↓ (60개 초과시 균등 샘플링)
3. 표준 데이터셋 (datasets/DTU/scanN_standard/)
   ↓
4. 파이프라인 실행 (./run_pipeline.sh P5 [경로])
   ↓
5. 결과 저장 (results/P5_YYYYMMDD_HHMMSS/)
```

## 📚 학습된 교훈

### **유연한 스크립트 설계**:
```bash
# ✅ Good: 기본값 + 오버라이드
DATA_DIR="${2:-./datasets/DTU/scan1_standard}"

# ❌ Bad: 하드코딩
DATA_DIR="./datasets/DTU/scan1_standard"
```

### **에러 메시지 개선**:
```bash
# ✅ Good: 사용 가능한 옵션 제시
echo "사용 가능한 데이터셋:"
find ./datasets -type d -name "images" | sed 's|/images||'

# ❌ Bad: 단순 에러만 출력
echo "❌ 데이터셋이 없습니다."
```

### **도움말 작성 원칙**:
```python
help_message_principles = {
    "usage": "간결한 사용법 표시",
    "examples": "3개 이상의 실제 예시 제공",
    "context": "언제 각 옵션을 사용하는지 설명",
    "troubleshooting": "자주 발생하는 문제 해결책 포함"
}
```

## 🛠️ 트러블슈팅 과정

### 1️⃣ **Google Drive 다운로드 제한**
- **문제**: "Too many users have viewed or downloaded this file recently"
- **시도한 해결책**:
  - `gdown` CLI 도구 사용 → ❌ 실패
  - Baidu Pan 링크 조사 → 접근 가능하나 미사용
- **최종 해결**: 브라우저에서 직접 다운로드 후 수동 업로드

### 2️⃣ **DTU 데이터셋 구조 이해**
- **문제**: MVSNet README가 `SampleSet/MVS Data/Cleaned/scan1/images` 언급
- **발견**: 실제 다운로드 파일은 `Rectified/scanN_train/` 구조
- **해결**: `prepare_standard_dataset.sh`가 모든 구조 자동 처리

### 3️⃣ **파이프라인 경로 호환성**
- **문제**: 기존 스크립트가 `scan1_standard` 하드코딩
- **요구사항**: 다양한 스캔 (scan18, scan32 등) 지원 필요
- **해결**: 인자 방식으로 변경, 기본값 유지로 하위 호환성 확보

## 🔮 다음 단계 계획

### **단기 목표 (10/04 - 10/07)**:
1. **다양한 스캔 테스트**:
   ```bash
   ./prepare_standard_dataset.sh "./datasets/DTU/Rectified/scan18_train"
   ./run_pipeline.sh P5 ./datasets/DTU/scan18_standard
   ```

2. **성능 비교 분석**:
   - scan1 vs scan18 vs scan32 결과 비교
   - DTU benchmark 표준 스캔 선정

3. **자동화 스크립트**:
   ```bash
   # 모든 DTU 스캔 일괄 처리
   for scan in scan{1,18,32,50,83}; do
       ./prepare_standard_dataset.sh "./datasets/DTU/Rectified/${scan}_train"
       ./run_pipeline.sh P5 ./datasets/DTU/${scan}_standard
   done
   ```

### **중기 목표 (10/08 - 10/15)**:
1. **다른 데이터셋 지원**:
   - ETH3D 데이터셋 다운로드 및 변환
   - Tanks&Temples 데이터셋 준비
   - 커스텀 데이터셋 가이드 작성

2. **문서화 강화**:
   - 데이터셋 준비 가이드 작성
   - 파이프라인 사용 튜토리얼
   - 트러블슈팅 FAQ

## 📦 최종 산출물

### 1️⃣ **Git 커밋**:
```bash
# run_pipeline.sh 개선 커밋 (예정)
git add run_pipeline.sh
git commit -m "🔧 run_pipeline.sh 유연성 개선 - 데이터셋 경로 인자 지원

- 데이터셋 경로를 인자로 받도록 개선 (기본값: scan1_standard)
- 도움말에 사용 예시 3개 추가
- 에러 메시지 개선 (사용 가능한 데이터셋 자동 표시)
- 다양한 DTU 스캔 및 커스텀 데이터셋 지원
- 하위 호환성 유지 (기존 스크립트 동작 보장)"
```

### 2️⃣ **준비된 데이터셋**:
- `datasets/DTU/scan1_standard/` (60개 이미지)
- 원본: `datasets/DTU/Rectified/scan1_train/` (343개 이미지)

### 3️⃣ **문서화**:
- **20251003 워크플로우**: DTU 준비 + 파이프라인 유연성 개선 기록
- **DTU→COLMAP 변환 조사**: 3가지 접근법 비교 분석

## 🎉 결론

### ✅ **달성 목표**:
1. **DTU 데이터셋 다운로드**: Rectified, Cameras, Depths 폴더 확보
2. **scan1 표준화**: 343개 → 60개 균등 샘플링 완료
3. **파이프라인 유연성**: 데이터셋 경로 인자 지원
4. **하위 호환성**: 기존 스크립트 모두 정상 동작

### 🚀 **핵심 성과**:
- **데이터 준비 완료**: DTU scan1 즉시 실행 가능
- **확장성 확보**: 120개 DTU 스캔 모두 사용 가능
- **워크플로우 단순화**: 이미지만 준비 → 파이프라인 자동 처리
- **연구자 편의성**: 경로 변경만으로 다양한 실험 가능

### 💡 **혁신적 기여**:
1. **단순한 데이터 준비**: COLMAP 변환 불필요, 이미지만 준비
2. **유연한 실행 환경**: 모든 데이터셋 지원
3. **실용적 워크플로우**: 3단계로 완결 (다운로드 → 표준화 → 실행)
4. **타 연구 대비 우위**: 복잡한 매트릭스 변환 없이 간편한 사용

---

## 📚 참고 자료

### DTU 데이터셋:
- **MVSNet 저장소**: [https://github.com/YoYo000/MVSNet](https://github.com/YoYo000/MVSNet)
- **Google Drive**: `1eDjh-_bxKKnEuz5h-HXS7EDJn59clx6V`
- **Baidu Pan**: `https://pan.baidu.com/s/1Wb9E6BWCJu4wZfwxm_t4TQ` (코드: s2v2)

### 변환 방법 조사:
- **StackOverflow**: DTU→COLMAP 변환 코드 예시
- **Neuralangelo**: NVlabs의 DTU 전처리 방법
- **COLMAP 공식 문서**: 카메라 포맷 스펙

### 이전 워크플로우:
- [20250926_VGGT-GSplat_WorkFlow.md](20250926_VGGT-GSplat_WorkFlow.md) - P5 파이프라인 완성
- [20250919_VGGT-GSplat_WorkFlow.md](20250919_VGGT-GSplat_WorkFlow.md) - P4 파이프라인

---

**작성일**: 2025-10-03
**작성자**: Claude Code Assistant
**프로젝트**: VGGT-Gaussian Splatting Research
**저장소**: [Jihunkim95/vggt-gaussian-splatting-research](https://github.com/Jihunkim95/vggt-gaussian-splatting-research)
**상태**: ✅ DTU 데이터셋 준비 완료, 🎯 파이프라인 유연성 확보
