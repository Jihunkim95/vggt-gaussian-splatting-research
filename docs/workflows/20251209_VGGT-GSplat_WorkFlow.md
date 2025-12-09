# VGGT-GSplat Workflow - 2025-12-09

**날짜**: 2025년 12월 9일
**작업자**: JHKim
**작업 위치**: `/data/users/jhkim/vggt-gaussian-splatting-research`

---

## 1. 오늘 한 작업

### 1.1 AUTO_RETRY 로직 개선 (run_pipeline.sh)

**문제**:
- MipNeRF360/bicycle_60 데이터셋에서 P4 실행 시 자동 재시도가 작동하지 않음
- 기존 감지 로직: 경로에 "custom" 또는 "quality_" 포함 여부로 판단
- MipNeRF360 등 벤치마크 데이터셋은 감지되지 않음

**해결**:
- DTU 감지 방식으로 변경: DTU 데이터셋만 재시도 비활성화, 나머지는 모두 활성화

```bash
# 변경 전: 특정 키워드 포함 여부로 AUTO_RETRY 활성화
if [[ "$DATA_DIR" == *"custom"* ]] || [[ "$DATA_DIR" == *"quality_"* ]]; then
    AUTO_RETRY=true
fi

# 변경 후: DTU만 비활성화, 나머지는 모두 활성화
if [[ "$DATA_DIR" == *"DTU"* ]] && [[ "$DATA_DIR" == *"scan"* ]]; then
    CONF_THRES=5.0
    CONF_THRES_BA=5.0
    AUTO_RETRY=false
    echo "🔧 DTU 데이터셋 감지 → conf_thres=5.0 (재시도 없음)"
else
    CONF_THRES=5.0
    CONF_THRES_BA=5.0
    AUTO_RETRY=true
    echo "🔧 일반 데이터셋 감지 → conf_thres=5.0 (자동 재시도 활성화)"
fi
```

**변경 이유**:
- DTU는 깔끔한 스튜디오 환경 데이터셋으로 conf_thres=5.0에서 안정적
- Custom 동영상, MipNeRF360 등은 야외/복잡한 환경으로 낮은 conf_thres 필요할 수 있음
- "positive list" 방식에서 "negative list" 방식으로 전환

### 1.2 3D 포인트 수 검증 추가 (run_pipeline.sh)

**문제**:
- P4 실행 시 `points3D.bin` 파일이 존재해도 포인트가 0개인 경우 발생
- gsplat 학습 시 "No points to train on" 오류 발생

**해결**:
- 최소 포인트 수 검증 추가 (MIN_POINTS=1000)

```bash
MIN_POINTS=1000  # gsplat 학습에 필요한 최소 포인트 수

if [ -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
    # 실제 포인트 수 확인
    POINT_COUNT=$(./env/vggt_env/bin/python -c "
import pycolmap
r = pycolmap.Reconstruction('$TEMP_WORK_DIR/sparse')
print(len(r.points3D))
" 2>/dev/null || echo "0")

    if [ "$POINT_COUNT" -ge "$MIN_POINTS" ]; then
        echo "✅ VGGT 성공: $POINT_COUNT개 3D 포인트 생성"
        VGGT_SUCCESS=true
        break
    else
        echo "⚠️ 포인트 부족: $POINT_COUNT개 (최소 $MIN_POINTS개 필요)"
        # conf_thres_value 낮춰서 재시도
    fi
fi
```

### 1.3 quality_sampler.py 이미지 디렉토리 처리 개선

**문제**:
- 이미지 디렉토리 입력 시에도 Optical Flow 체크 수행
- 이미 정제된 이미지에 불필요한 정지 프레임 필터 적용

**해결**:
- `analyze_images()` 메서드에서 Optical Flow 체크 스킵

```python
def analyze_images(self, image_paths: List[str]) -> List[FrameInfo]:
    """
    이미지 리스트 분석 (다운샘플링 적용)

    이미지는 이미 정제된 데이터일 가능성이 높으므로:
    - Optical Flow 체크 스킵 (정지 프레임 필터 비활성화)
    - Sharpness + Brightness만 체크
    """
    print(f"📷 이미지 모드: Optical Flow 체크 스킵 (sharpness + brightness만 사용)")

    for idx, img_path in enumerate(image_paths):
        # ... sharpness, brightness 계산 ...

        # 이미지는 flow 체크 스킵 (이미 정제된 데이터)
        frame_info = FrameInfo(
            # ...
            flow_magnitude=0.0,  # 이미지는 flow 미사용
        )
```

**적용 범위**:
- 비디오 입력: Optical Flow + Sharpness + Brightness 모두 적용
- 이미지 디렉토리 입력: Sharpness + Brightness만 적용

### 1.4 Mip-NeRF360 데이터셋 다운로드 및 정제

**다운로드**:
```bash
# 다운로드 (약 4GB)
wget http://storage.googleapis.com/gresearch/refraw360/360_v2.zip
unzip 360_v2.zip -d datasets/MipNeRF360/
```

**데이터셋 구성** (7개 씬):
| 씬 | 이미지 수 | 해상도 |
|-----|----------|--------|
| bicycle | 194 | 1558x1039 |
| bonsai | 292 | 1558x1039 |
| counter | 240 | 1558x1039 |
| garden | 185 | 1558x1039 |
| kitchen | 279 | 1558x1039 |
| room | 311 | 1558x1039 |
| stump | 125 | 1558x1039 |

**bicycle 정제 (194 → 60)**:
```bash
./env/vggt_env/bin/python quality_sampler.py \
    ./datasets/MipNeRF360/bicycle/images \
    --output-dir ./datasets/MipNeRF360/bicycle_60 \
    --target-count 60 \
    --overlap-ratio 0.65
```

**결과**: `datasets/MipNeRF360/bicycle_60/images/` (60개 이미지)

---

## 2. 기술 상세

### 2.1 Overlap 기반 샘플링 설명

**오해 가능한 부분**:
- "Overlap"은 **장면의 시각적 오버랩**이 아닌 **프레임 인덱스 간격**을 의미
- 실제 장면 오버랩 계산에는 카메라 pose 정보 필요 (COLMAP 이후에만 가능)

**현재 구현**:
```python
# 1800 프레임에서 60개 선택 시
interval = 1800 / 60 = 30  # 30프레임마다 1개 선택

# overlap_ratio=0.65 → 실제로는 품질 윈도우 크기에만 영향
# 각 위치 ±15 프레임 범위에서 최고 품질 선택
```

**결과**:
- 균등 간격으로 프레임 선택 → COLMAP 매칭에 유리
- 각 위치에서 품질(sharpness) 기반 미세 조정

### 2.2 AUTO_RETRY 동작 흐름

```
[시작]
    ↓
[데이터셋 경로 확인]
    ├── DTU + scan 포함? → AUTO_RETRY=false, conf=5.0 고정
    └── 그 외 → AUTO_RETRY=true
    ↓
[VGGT 실행 (conf=5.0)]
    ↓
[points3D.bin 확인]
    ├── 없음 또는 <1000개 → conf -= 0.5, 재시도
    └── ≥1000개 → 성공, gsplat 학습 진행
    ↓
[재시도 반복]
    └── conf=0.5까지 (P4) 또는 0.01까지 (P5)
```

---

## 3. 실험 상태

### 3.1 현재 실행 중인 파이프라인

| 파이프라인 | 데이터셋 | 상태 |
|------------|----------|------|
| P5 | custom/cMugcup_quality_20251208 | 실행 중 |
| P4 | MipNeRF360/bicycle_60 | 실행 중 (AUTO_RETRY 테스트) |

### 3.2 MipNeRF360/bicycle_60 P4 실험 결과

**목적**: AUTO_RETRY 로직 검증

**결과** (성공):
| conf_thres | 3D 포인트 수 | 결과 |
|------------|-------------|------|
| 5.0 | 0 | 실패 |
| 4.5 | 0 | 실패 |
| 4.0 | 5 | 실패 (<1000) |
| 3.5 | 43 | 실패 (<1000) |
| **3.0** | **16,643** | **성공** |

**분석**:
- MipNeRF360 야외 씬은 DTU 스튜디오 씬보다 낮은 conf_thres 필요
- AUTO_RETRY 로직이 정상 작동하여 자동으로 최적값 탐색
- VGGT 처리 시간: ~320초 (5회 재시도 포함)

---

## 4. 내일 할 일

### 4.1 실험 결과 확인
- MipNeRF360/bicycle P4 결과 확인
- cMugcup P5 결과 확인 및 분석

### 4.2 다른 MipNeRF360 씬 테스트
- garden, kitchen 등 다른 씬에서 AUTO_RETRY 동작 확인
- 최적 conf_thres_value 패턴 파악

### 4.3 발표자료 업데이트
- AUTO_RETRY 로직 설명 추가
- MipNeRF360 벤치마크 결과 포함

---

## 5. 변경된 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `run_pipeline.sh` | 수정 | AUTO_RETRY 로직 개선 (DTU만 비활성화), MIN_POINTS 검증 추가 |
| `quality_sampler.py` | 수정 | 이미지 디렉토리 입력 시 Optical Flow 스킵 |

---

## 6. 참고 명령어

```bash
# MipNeRF360 데이터셋 정제
./env/vggt_env/bin/python quality_sampler.py \
    ./datasets/MipNeRF360/garden/images \
    --output-dir ./datasets/MipNeRF360/garden_60 \
    --target-count 60

# P4 실행 (AUTO_RETRY 활성화됨)
./run_pipeline.sh P4 ./datasets/MipNeRF360/garden_60

# 결과 확인
cat ./results/P4_garden_60_*/stats/val_step29999.json

# 실행 중인 파이프라인 확인
ps aux | grep run_pipeline

# GPU 상태
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

---

## 7. 참고 자료

- **Mip-NeRF360**: Barron et al. "Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields" CVPR 2022
- **데이터셋 URL**: http://storage.googleapis.com/gresearch/refraw360/360_v2.zip
- **이전 워크플로우**: `docs/workflows/20251208_VGGT-GSplat_WorkFlow.md`
