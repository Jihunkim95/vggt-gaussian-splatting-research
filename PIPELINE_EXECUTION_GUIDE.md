# 🚀 **VGGT-Gaussian Splatting Pipeline 실행 가이드**

**업데이트**: 2025-09-17
**환경**: RTX 6000 Ada (48GB VRAM)
**데이터셋**: DTU MVS SampleSet (scan1, scan6)

---

## 📋 **파이프라인 개요**

| 파이프라인 | 구성 | 환경 | 처리시간 | 출력 | 상태 |
|-----------|------|------|----------|------|------|
| **P1** | COLMAP + gsplat | `gsplat_env` | 47.2분 | 568,549 Gaussians | ✅ 완료 |
| **P2** | VGGT feed-forward | `vggt_env` | 12.5초 | 568,549 Points | ✅ 완료 |
| **P3** | VGGT + Bundle Adjustment | `vggt_env` | ~15분 | 40,469 Points | ⚠️ 이슈 |

---

## 🔧 **사전 준비**

### **1. 환경 설정**
```bash
# 프로젝트 루트로 이동
cd /workspace/vggt-gaussian-splatting-research

# 환경 상태 확인
source scripts/utils/switch_env.sh status

# DTU 데이터셋 확인
./scripts/utils/context_restore.sh
```

### **2. 데이터셋 준비**
```bash
# DTU SampleSet이 없는 경우 다운로드
cd ./datasets/DTU && wget -c "http://roboimagedata2.compute.dtu.dk/data/MVS/SampleSet.zip"
cd ./datasets/DTU && unzip SampleSet.zip

# scan1 이미지 확인 (392개 있어야 함)
ls ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1/ | wc -l
```

### **3. P1용 COLMAP 데이터 준비**
```bash
# P1 실행 전에 scan1을 COLMAP 형식으로 변환 (환경 무관)
python create_simple_colmap_scan1.py

# 변환 결과 확인
ls ./datasets/DTU/scan1_processed/sparse/0/
# 출력: cameras.bin images.bin points3D.bin
```

**⚠️ 환경별 사용 도구**:
- **P1 (gsplat)**: `gsplat_env` 환경 필수
- **P2/P3 (VGGT)**: `vggt_env` 환경 필수

---

## 🎯 **P1: COLMAP + gsplat Baseline** (`gsplat_env` 필요)

### **설명**: 기준선 파이프라인 (COLMAP 재구성 + Gaussian Splatting)

### **실행 방법**:
```bash
# 환경 설정
source scripts/utils/switch_env.sh gsplat

# P1 실행
python p1_baseline.py \
    --data-dir ./datasets/DTU/scan24 \
    --output-dir ./results/P1_baseline_scan24 \
    --max-steps 30000

# 또는 scan1 사용 (COLMAP 사전 처리 필요)
python create_simple_colmap_scan1.py  # COLMAP 파일 생성
python p1_baseline.py \
    --data-dir ./datasets/DTU/scan1_processed \
    --output-dir ./results/P1_baseline_scan1 \
    --max-steps 7000
```

### **출력**:
- `./results/P1_baseline_*/ckpts/ckpt_*.pt` - 체크포인트
- `./results/P1_baseline_*/ply/point_cloud_*.ply` - PLY 파일
- `./results/P1_baseline_*/stats/val_step*.json` - 평가 결과

### **예상 결과**:
- 처리 시간: ~47분
- 모델 개수: 568,549 Gaussians
- PSNR: ~23.48

---

## ⚡ **P2: VGGT Feed-Forward Only** (`vggt_env` 필요)

### **설명**: VGGT만 사용한 빠른 3D 재구성 (Bundle Adjustment 없음)

### **실행 방법**:
```bash
# 환경 설정
source scripts/utils/switch_env.sh vggt

# P2 실행 (Feed-Forward Only)
python demo_colmap.py \
    --scene_dir ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1 \
    --conf_thres_value 5.0

# 결과 정리
mkdir -p ./results/P2_VGGT_scan1_feedforward
cp ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1/sparse/points.ply \
   ./results/P2_VGGT_scan1_feedforward/vggt_scan1_feedforward.ply

# 결과 확인
echo "P2 결과 포인트 수: $(head -n 20 ./results/P2_VGGT_scan1_feedforward/vggt_scan1_feedforward.ply | grep 'element vertex' | cut -d ' ' -f 3)"
```

### **주의사항**:
- `max_points_for_colmap` 값을 568549로 설정해야 P1과 동일한 complexity
- 필요시 `demo_colmap.py` 라인 196 수정: `max_points_for_colmap = 568549`

### **출력**:
- `sparse/points.ply` - 3D 포인트 클라우드
- `sparse/cameras.bin` - 카메라 파라미터

### **예상 결과**:
- 처리 시간: ~12.5초
- 모델 개수: 568,549 Points
- Chamfer Distance: ~4.49 (vs P1)

---

## 🔄 **P3: VGGT + Bundle Adjustment** (`vggt_env` 필요)

### **설명**: VGGT + Bundle Adjustment로 품질 향상

### **실행 방법**:
```bash
# 환경 설정
source scripts/utils/switch_env.sh vggt

# P3 실행 (Bundle Adjustment 포함)
python demo_colmap.py \
    --scene_dir ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1 \
    --use_ba \
    --conf_thres_value 5.0 \
    --max_reproj_error 8.0

# 더 많은 포인트를 원하는 경우 (실험적)
python demo_colmap.py \
    --scene_dir ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1 \
    --use_ba \
    --conf_thres_value 5.0 \
    --max_reproj_error 50.0

# 결과 정리
mkdir -p ./results/P3_VGGT_BA_scan1
cp ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1/sparse/points.ply \
   ./results/P3_VGGT_BA_scan1/vggt_ba_scan1.ply

# 결과 확인
echo "P3 결과 포인트 수: $(head -n 20 ./results/P3_VGGT_BA_scan1/vggt_ba_scan1.ply | grep 'element vertex' | cut -d ' ' -f 3)"
```

### **파라미터 설명**:
- `--max_reproj_error 8.0`: 엄격한 품질 필터링 (40,469 points)
- `--max_reproj_error 50.0`: 관대한 필터링 (더 많은 points)
- `--conf_thres_value 5.0`: 신뢰도 임계값

### **출력**:
- `sparse/points.ply` - Bundle Adjustment 적용된 3D 포인트
- Bundle Adjustment 로그

### **예상 결과**:
- 처리 시간: ~15분
- 모델 개수: 40,469 Points (고품질 필터링)
- 품질: 높은 정확도 (reprojection error < 8.0)

---

## 📊 **결과 비교 및 분석**

### **성능 비교**:
```bash
# Chamfer Distance 계산 (P1 vs P2)
python -c "
import numpy as np
from scipy.spatial.distance import cdist

# P1 결과 로드
p1_points = load_ply('./results/P1_baseline_*/ply/point_cloud_*.ply')
# P2 결과 로드
p2_points = load_ply('./results/P2_VGGT_*/vggt_*.ply')

# Chamfer Distance 계산
chamfer_dist = compute_chamfer_distance(p1_points, p2_points)
print(f'Chamfer Distance: {chamfer_dist:.6f}')
"
```

### **파일 크기 확인**:
```bash
# 결과 파일들 크기 비교
ls -lh ./results/*/ckpts/*.pt 2>/dev/null       # P1 체크포인트
ls -lh ./results/*/*.ply 2>/dev/null            # PLY 파일들
du -sh ./results/P* 2>/dev/null                 # 전체 결과 크기

# 포인트 수 빠른 비교
echo "=== 파이프라인 결과 비교 ==="
for f in ./results/*/*.ply; do
  if [[ -f "$f" ]]; then
    points=$(head -n 20 "$f" | grep 'element vertex' | cut -d ' ' -f 3)
    echo "$(basename $(dirname $f)): $points points"
  fi
done
```

---

## 🛠️ **문제 해결**

### **P1 관련**:
```bash
# CUDA 메모리 부족시
nvidia-smi  # VRAM 사용량 확인
# batch_size 줄이기 또는 max_steps 감소

# gsplat 환경 문제시
source scripts/utils/switch_env.sh gsplat
pip install gsplat
```

### **P2/P3 관련**:
```bash
# VGGT 환경 문제시
source scripts/utils/switch_env.sh vggt
# 필요시 libs/vggt의 demo_colmap.py 사용

# 포인트 수가 예상과 다를 때
# demo_colmap.py의 max_points_for_colmap 값 확인/수정
```

### **데이터셋 문제**:
```bash
# scan1 이미지가 없는 경우
ls ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1/

# 경로 문제시
./scripts/utils/context_restore.sh  # 현재 상태 확인
```

---

## 🚀 **빠른 실행 (Quick Start)**

### **전체 파이프라인 순차 실행**:
```bash
# 1. 환경 확인
./scripts/utils/context_restore.sh

# 2. P2 빠른 테스트 (12.5초)
source scripts/utils/switch_env.sh vggt
python demo_colmap.py --scene_dir ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1 --conf_thres_value 5.0

# 3. P3 품질 향상 (~15분)
python demo_colmap.py --scene_dir ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1 --use_ba --conf_thres_value 5.0

# 4. P1 기준선 (~47분, 선택사항)
source scripts/utils/switch_env.sh gsplat
python create_simple_colmap_scan1.py  # COLMAP 파일 생성
python p1_baseline.py --data-dir ./datasets/DTU/scan1_processed --max-steps 7000
```

---

## 📚 **추가 자료**

- **P1-P2 비교 분석**: `docs/analysis/P1_P2_Quantitative_Comparison.md`
- **워크플로우 상세**: `docs/workflows/20250912_VGGT-GSplat_WorkFlow.md`
- **실험 로그**: `docs/EXPERIMENT_LOG.md`
- **환경 설정**: `scripts/utils/switch_env.sh`

---

**📝 Last Updated**: 2025-09-17
**🎯 Target**: WACV 2026 submission
**💻 Environment**: RTX 6000 Ada (48GB VRAM)