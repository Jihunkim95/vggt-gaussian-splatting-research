# VGGT-GSplat Workflow - 2025-12-07

**날짜**: 2025년 12월 7일
**작업자**: JHKim
**작업 위치**: `/data/users/jhkim/vggt-gaussian-splatting-research`

---

## 1. 오늘 한 작업

### 1.1 quality_sampler.py 프로세스 변경 ✅

**기존 파이프라인**:
```
[BRISQUE 50%] + [Laplacian Sharpness 50%] → Stratified Sampling
```

**새로운 파이프라인**:
```
[Optical Flow] → [Laplacian + 밝기] → [Stratified Sampling]
```

**변경 사유**:
- BRISQUE는 통계적 자연스러움 측정으로 COLMAP에 직접적 기여 부족
- Optical Flow (Farneback 2003)로 정지 프레임 자동 제거
- Laplacian Sharpness (Pech-Pacheco 2000)로 블러 프레임 제거
- 밝기 필터로 노출 이상 프레임 제거 (30-220 범위)

**주요 변경 내용**:
- `frame_selector.py` 기반으로 `quality_sampler.py` 완전 재작성
- 비디오/이미지 디렉토리 입력 모두 지원
- COLMAP 호환 출력 형식 (0001.jpg, 0002.jpg, ...)
- JSON 메타데이터 + 논문 레퍼런스 포함

**참고 논문**:
- Farneback, G. "Two-frame motion estimation based on polynomial expansion." SCIA 2003
- Pech-Pacheco, J.L. et al. "Diatom autofocusing in brightfield microscopy." ICPR 2000

### 1.2 run_full_pipeline.sh 테스트 ✅

**수정 사항**:
- 품질 평가 방법 설명 업데이트
- `--intermediate-count` 옵션 제거 (불필요)
- Python 경로 문제 수정 (`./env/vggt_env/bin/python` 명시)

**테스트 명령어**:
```bash
./run_full_pipeline.sh ./datasets/custom/cChair.mp4 P5
```

### 1.3 frame_selector.py 레거시 코드 제거 ✅

- `quality_sampler.py`가 `frame_selector.py` 기능을 완전히 대체
- `frame_selector.py`는 참조용으로 유지 (향후 삭제 예정)

### 1.4 cChair 실험 진행 중 🔄

**실험 설정**:
```bash
./run_full_pipeline.sh ./datasets/custom/cChair.mp4 P5
```

**파이프라인 단계**:
1. Step 1/2: 품질 기반 이미지 샘플링 (Optical Flow → Laplacian + Brightness → Stratified)
2. Step 2/2: 3D Gaussian Splatting (P5: VGGT+BA → gsplat)

---

## 2. 기술 상세

### 2.1 새로운 품질 평가 파이프라인

| 단계 | 기술 | 목적 | 임계값 |
|------|------|------|--------|
| 1 | Optical Flow (Farneback) | 정지 프레임 제거 | flow_threshold=1.0 |
| 2 | Laplacian Variance | 블러 프레임 제거 | sharpness_threshold=100.0 |
| 3 | Brightness Filter | 노출 이상 제거 | 30.0 ~ 220.0 |
| 4 | Stratified Sampling | 시간 구간별 최고 품질 선택 | num_strata=10 |

### 2.2 출력 구조

```
output_dir/
├── images/
│   ├── 0001.jpg
│   ├── 0002.jpg
│   └── ... (COLMAP 호환 형식)
└── frame_selection_metadata.json
```

### 2.3 메타데이터 예시

```json
{
  "pipeline": "Optical Flow → Laplacian + Brightness → Stratified Sampling",
  "references": {
    "optical_flow": "Farneback 2003",
    "sharpness": "Pech-Pacheco 2000"
  },
  "statistics": {
    "total_frames": 1000,
    "valid_frames": 800,
    "selected_frames": 60,
    "rejection_reasons": {
      "static": 100,
      "blur": 80,
      "too_dark": 15,
      "too_bright": 5
    }
  }
}
```

---

## 3. 내일 할 일

### 3.1 동영상 프레임 분석 속도 향상 🎯

**현재 문제**:
- 전체 프레임 순차 분석으로 긴 비디오에서 시간 소요

**개선 방안**:
1. 프레임 건너뛰기 (skip frames) 옵션 추가
2. 멀티스레딩/멀티프로세싱 적용
3. 다운샘플링 후 분석 → 원본에서 추출

### 3.2 발표자료 만들기 📊

**포함 내용**:
- VGGT + 3DGS 파이프라인 개요
- 품질 기반 프레임 선택 방법론
- 실험 결과 및 비교 분석

---

## 4. 참고 명령어

```bash
# 새로운 파이프라인 실행
./run_full_pipeline.sh ./datasets/custom/video.mp4 P5

# 품질 샘플러 단독 실행
./env/vggt_env/bin/python quality_sampler.py ./video.mp4 \
    --output-dir ./output \
    --target-count 60 \
    --num-strata 10

# 결과 확인
cat ./results/P5_*/stats/val_step29999.json
```

---

## 5. 변경된 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `quality_sampler.py` | 완전 재작성 | Optical Flow + Laplacian + Brightness 파이프라인 |
| `run_full_pipeline.sh` | 수정 | 품질 방법 설명 업데이트, 옵션 정리 |
| `frame_selector.py` | 유지 (레거시) | 참조용, 향후 삭제 예정 |
