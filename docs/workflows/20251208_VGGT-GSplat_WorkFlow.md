# VGGT-GSplat Workflow - 2025-12-08

**날짜**: 2025년 12월 8일
**작업자**: JHKim
**작업 위치**: `/data/users/jhkim/vggt-gaussian-splatting-research`

---

## 1. 오늘 한 작업

### 1.1 quality_sampler.py VGGT 스타일 다운샘플링 적용

**문제**:
- 1분 동영상 (2800 프레임) 분석에 ~1시간 40분 소요
- 원본 해상도(4K)로 품질 분석 시 매우 느림

**해결**:
- VGGT와 동일한 518px 다운샘플링 적용
- 분석만 518px로 빠르게, 저장은 원본 그대로

```python
def downsample_for_analysis(image: np.ndarray, target_size: int = 518) -> np.ndarray:
    """VGGT 스타일 다운샘플링: 분석 속도 향상을 위해 이미지 축소"""
    h, w = image.shape[:2]
    max_dim = max(h, w)
    if max_dim <= target_size:
        return image
    scale = target_size / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
```

**품질 분석 정확도**:
- Laplacian (선명도): 다운샘플링하면 절대값 달라지지만 **상대적 순위는 유지** → 블러 vs 선명 구분 가능
- Optical Flow (움직임): magnitude가 비례 축소되지만 **상대적 움직임 감지는 동일**
- 결론: 순위 비교에 영향 없음, 임계값만 조정 필요

**임계값 조정**:
```python
flow_threshold: 1.0 → 0.3  # 다운샘플 기준
sharpness_threshold: 100.0 → 50.0  # 다운샘플 기준
```

### 1.2 Overlap 기반 샘플링으로 변경

**기존 방식 (Stratified Sampling)**:
- 구간별로 나눠서 각 구간에서 최고 품질 선택
- 문제: 구간 경계에서 오버랩 부족 가능

**새로운 방식 (Overlap 기반 Sampling)**:
- 60-70% 오버랩 보장하는 균등 간격 선택
- 각 위치에서 품질 기반 미세 조정

```python
def overlap_based_select(self, frame_infos: List[FrameInfo]) -> List[int]:
    """Overlap 기반 샘플링: 연속 프레임 간 60-70% 오버랩 보장"""
    target_k = self.config.target_frames  # 60
    overlap_ratio = self.config.overlap_ratio  # 0.65

    # 균등 간격 계산
    interval = len(valid_frames) / target_k

    # 각 위치 주변 윈도우에서 최고 품질 프레임 선택
    ...
```

**레거시 코드 제거**:
- `stratified_select()` 메서드 삭제
- `select_frames()` 메서드 삭제
- `--num-strata`, `--sampling-mode` 옵션 삭제

### 1.3 run_pipeline.sh conf_thres_value 자동 조정

**문제**:
- P5 Bundle Adjustment 실패: "Not enough inliers per frame, skip BA"
- Custom 데이터셋에서 높은 conf_thres_value로 인해 포인트 부족

**원인 분석**:
- `libs/vggt/vggt/dependency/np_to_pycolmap.py:71`에서 `min_inlier_per_frame=64` 체크
- 각 프레임마다 최소 64개의 inlier 포인트 필요
- conf_thres_value가 높으면 포인트가 적게 생성됨

**해결 (자동 재시도 로직)**:

```bash
# P4: 5.0 → 4.5 → 4.0 → ... → 0.5
# P5: 5.0 → 4.5 → 4.0 → ... → 0.5 → 0.01

# Custom 데이터셋: 실패 시 conf_thres_value를 점진적으로 낮춤
if [[ "$DATA_DIR" == *"custom"* ]] || [[ "$DATA_DIR" == *"quality_"* ]]; then
    CURRENT_CONF=5.0
    while (( $(echo "$CURRENT_CONF >= $MIN_CONF" | bc -l) )); do
        echo "🔄 VGGT 시도: conf_thres_value=$CURRENT_CONF"
        # 실행 후 성공 여부 확인
        if [ -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
            break
        fi
        CURRENT_CONF=$(echo "$CURRENT_CONF - 0.5" | bc -l)
    done
fi
```

**Custom 데이터셋 감지 기준**:
- 경로에 "custom" 또는 "quality_" 포함 여부
- 기존: `DTU` 또는 `scan` 포함 여부 (문제 있음)

### 1.4 timing_results.json 체크포인트별 시간 추가

**기존**:
```json
{
  "pipeline_total_seconds": 1008,
  "training_seconds": 954,
  "setup_seconds": 54
}
```

**개선**:
```json
{
  "pipeline_total_seconds": 1008,
  "setup_seconds": 54,
  "training_seconds": 954,
  "checkpoint_times": {
    "step_7000": 159.2,
    "step_15000": 390.2,
    "step_30000": 929.9
  }
}
```

**구현**:
- gsplat이 이미 `stats/train_step*_rank0.json`에 `ellipse_time` 저장
- `run_pipeline.sh`에서 이 정보를 파싱하여 `timing_results.json`에 통합

### 1.5 gsplat 환경 오류 해결

**오류**:
```
RuntimeError: Ninja is required to load C++ extensions
ImportError: cannot import name 'csrc' from 'gsplat'
```

**원인**:
- DTU 데이터셋은 정상 작동, Custom 데이터셋만 오류
- 경로 설정 문제로 ninja 찾지 못함

**해결**:
- `run_pipeline.sh`에 ninja 경로 추가
```bash
export PATH=/data/users/jhkim/vggt-gaussian-splatting-research/env/gsplat_env/bin:$PATH
```

---

## 2. 기술 상세

### 2.1 VGGT query frame 선택 방식

BA 실행 시 출력되는 query frame 순서:
```
Predicting tracks for query frame 0
Predicting tracks for query frame 11
Predicting tracks for query frame 1
Predicting tracks for query frame 17
...
```

**동작 원리**:
1. DINOv2 feature 추출 (모든 프레임)
2. "대표성(representativeness)" 기준으로 랭킹
3. 가장 다양하고 대표적인 8개 프레임 자동 선택
4. 항상 첫 번째 프레임(0)은 포함

```python
# libs/vggt/vggt/dependency/track_predict.py:59
query_frame_indexes = generate_rank_by_dino(images, query_frame_num=query_frame_num, device=device)
```

**조절 가능 파라미터**:
- `--query_frame_num`: 선택할 프레임 수 (기본 8)
- 프레임 선택 자체는 DINO 기반 자동, 수동 제어 불가

### 2.2 품질 평가 파이프라인 (업데이트)

| 단계 | 기술 | 목적 | 임계값 (518px 기준) |
|------|------|------|---------------------|
| 1 | Optical Flow (Farneback) | 정지 프레임 제거 | flow_threshold=0.3 |
| 2 | Laplacian Variance | 블러 프레임 제거 | sharpness_threshold=50.0 |
| 3 | Brightness Filter | 노출 이상 제거 | 30.0 ~ 220.0 |
| 4 | **Overlap Sampling** | 60-70% 오버랩 균등 선택 | overlap_ratio=0.65 |

### 2.3 conf_thres_value 재시도 전략

| 파이프라인 | 시작값 | 감소폭 | 최소값 | 성공 조건 |
|------------|--------|--------|--------|-----------|
| P4 (Feed-Forward) | 5.0 | -0.5 | 0.5 | points3D.bin 존재 |
| P5 (BA) | 5.0 | -0.5 | 0.01 | sparse reconstruction 완료 |

---

## 3. 촬영 가이드 (동영상 → 3D Object)

### 3.1 권장 촬영 방법

물체를 중심으로 세 번의 궤도 촬영:
1. **위에서 한 바퀴**: 물체 상단 커버리지
2. **중간에서 한 바퀴**: 측면 커버리지
3. **아래에서 한 바퀴**: 하단 커버리지

### 3.2 이미지 샘플링 고려사항

- **고해상도(4K) 문제**: gsplat 학습 매우 오래 걸림
- **작은 Object**: 1000px 해상도로도 충분
- **블러/과노출 제거 시 오버랩 걱정**: VGGT는 10장 이미지로도 pose estimation 가능 (정량적 수치는 미확인)

---

## 4. 내일 할 일

### 4.1 실험 결과 분석
- P4/P5 Custom 데이터셋 실험 결과 비교
- conf_thres_value 자동 조정 효과 검증

### 4.2 발표자료 업데이트
- 품질 기반 프레임 선택 방법론 설명 추가
- conf_thres_value 자동 조정 로직 설명

---

## 5. 변경된 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `quality_sampler.py` | 대폭 수정 | 518px 다운샘플링, Overlap 기반 샘플링, 레거시 제거 |
| `run_pipeline.sh` | 수정 | conf_thres_value 자동 재시도 로직, timing_results.json 개선 |
| `run_full_pipeline.sh` | 수정 | 옵션 정리, Custom 폴더 출력 경로 지원 |

---

## 6. 참고 명령어

```bash
# 동영상 → 3D (전체 파이프라인)
./run_full_pipeline.sh ./datasets/custom/video.mp4 P5

# 품질 샘플러 단독 실행
./env/vggt_env/bin/python quality_sampler.py ./video.mp4 \
    --output-dir ./output \
    --target-count 60 \
    --overlap-ratio 0.65

# P4 실행 (BA 없음)
./run_pipeline.sh P4 ./datasets/custom/my_scene_quality_20251208

# P5 실행 (BA 포함)
./run_pipeline.sh P5 ./datasets/custom/my_scene_quality_20251208

# 결과 확인
cat ./results/P5_*/stats/val_step29999.json
cat ./results/P5_*/timing_results.json
```

---

## 7. 참고 자료

- **Farneback, G.** "Two-frame motion estimation based on polynomial expansion." SCIA 2003
- **Pech-Pacheco, J.L. et al.** "Diatom autofocusing in brightfield microscopy." ICPR 2000
- **VGGT Paper**: Visual Geometry Grounded Transformer (Meta AI)
- **발표자료**: `C:\Research\ComputerVision\VGGTnArianRealEarth20251118.pptx`
