#!/bin/bash

# 파이프라인 실행 및 결과 저장 스크립트
# 사용법: ./run_pipeline.sh <파이프라인> [데이터셋_디렉토리]

# PyTorch CUDA 메모리 단편화 방지
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# H100 GPU 지원 (compute capability 9.0)
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
export TMPDIR=/data/tmp

PIPELINE="$1"
DATA_DIR="${2:-./datasets/DTU/scan1_standard}"  # 기본값: scan1_standard
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_BASE="./results"

# 데이터셋 경로에서 스캔 이름 추출 (예: scan24_standard → scan24)
SCAN_NAME=$(basename "$DATA_DIR" | sed 's/_standard$//')

if [ -z "$PIPELINE" ]; then
    echo "사용법: $0 <P1|P1R|P2|P3|P4|P5> [데이터셋_디렉토리]"
    echo ""
    echo "파이프라인 설명:"
    echo "  P1: Original COLMAP SfM + gsplat (Images only)"
    echo "  P2: VGGT Feed-Forward Only"
    echo "  P3: VGGT + Bundle Adjustment"
    echo "  P4: VGGT → COLMAP → gsplat"
    echo "  P5: Advanced Hybrid Pipeline"
    echo ""
    echo "예시:"
    echo "  $0 P5                                    # 기본 경로 사용"
    echo "  $0 P5 ./datasets/DTU/scan1_standard      # 명시적 경로 지정"
    echo "  $0 P5 ./datasets/DTU/custom_scene        # 커스텀 씬 사용"
    exit 1
fi

# 데이터셋 디렉토리 검증
STANDARD_DIR="$DATA_DIR"
if [ ! -d "$STANDARD_DIR/images" ]; then
    echo "❌ 데이터셋 디렉토리가 존재하지 않거나 images 폴더가 없습니다: $STANDARD_DIR"
    echo "🔧 먼저 실행하세요: ./prepare_standard_dataset.sh '<원본_이미지_경로>'"
    echo ""
    echo "사용 가능한 데이터셋:"
    find ./datasets -type d -name "images" 2>/dev/null | sed 's|/images||' | head -5
    exit 1
fi

# 결과 디렉토리 생성 (스캔 이름 포함)
RESULT_DIR="${RESULTS_BASE}/${PIPELINE}_${SCAN_NAME}_${TIMESTAMP}"
mkdir -p "$RESULT_DIR"

# 임시 작업 디렉토리 생성 (충돌 방지)
TEMP_WORK_DIR="./temp_work_${PIPELINE}_${TIMESTAMP}"
cp -r "$STANDARD_DIR" "$TEMP_WORK_DIR"
echo "🔧 임시 작업 디렉토리: $TEMP_WORK_DIR"

echo "🚀 파이프라인 $PIPELINE 실행 시작"
echo "📁 결과 저장: $RESULT_DIR"
echo "⏰ 시작 시간: $(date)"

# 시작 시간 기록
START_TIME=$(date +%s)

case "$PIPELINE" in
    "P1")
        echo "📋 P1: Original COLMAP SfM + gsplat (Images Only) 실행"
        echo "🔧 gsplat 환경 활성화 중..."
        source ./env/gsplat_env/bin/activate

        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        # 기존 sparse 재구성 제거하여 이미지만으로 시작 (진짜 COLMAP SfM)
        if [ -d "$TEMP_WORK_DIR/sparse" ]; then
            echo "🧹 기존 sparse 재구성 제거 (이미지만으로 시작)"
            rm -rf "$TEMP_WORK_DIR/sparse"
        fi
        python p1_baseline.py \
            --data-dir "$TEMP_WORK_DIR" \
            --output-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000
        ;;

    "P2")
        echo "📋 P2: VGGT Feed-Forward Only 실행"
        source ./env/vggt_env/bin/activate
        PYTHONPATH=./libs/vggt:$PYTHONPATH python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --conf_thres_value 5.0

        # 결과 복사
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/"
        ;;

    "P3")
        echo "📋 P3: VGGT + Bundle Adjustment 실행"
        source ./env/vggt_env/bin/activate
        PYTHONPATH=./libs/vggt:$PYTHONPATH python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --use_ba \
            --conf_thres_value 5.0 \
            --max_reproj_error 8.0 \
            --max_query_pts 4096

        # 결과 복사
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/"
        ;;

    "P4")
        echo "📋 P4: VGGT Feed-Forward → gsplat 실행"

        # Step 1: VGGT Feed-Forward (vggt_env)
        echo "🔴 Step 1: VGGT Feed-Forward"
        source ./env/vggt_env/bin/activate
        PYTHONPATH=./libs/vggt:$PYTHONPATH python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --conf_thres_value 5.0

        # Verify VGGT output
        if [ ! -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
            echo "❌ VGGT feed-forward failed - no sparse reconstruction"
            exit 1
        fi
        echo "✅ VGGT sparse reconstruction completed"

        # Step 2: gsplat Training (gsplat_env)
        echo "🔵 Step 2: gsplat Training"
        source ./env/gsplat_env/bin/activate

        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        python ./libs/gsplat/examples/simple_trainer.py default \
            --data-dir "$TEMP_WORK_DIR" \
            --result-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000

        # 결과 복사 (VGGT sparse도 함께)
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/vggt_sparse"
        ;;

    "P5")
        echo "📋 P5: VGGT + Bundle Adjustment → gsplat 실행"

        # Step 1: VGGT + Bundle Adjustment (vggt_env)
        echo "🟢 Step 1: VGGT + Bundle Adjustment"
        source ./env/vggt_env/bin/activate
        PYTHONPATH=./libs/vggt:$PYTHONPATH python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --use_ba \
            --conf_thres_value 5.0 \
            --max_reproj_error 8.0 \
            --max_query_pts 4096

        # Verify VGGT+BA output
        if [ ! -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
            echo "❌ VGGT + Bundle Adjustment failed - no sparse reconstruction"
            exit 1
        fi
        echo "✅ VGGT + Bundle Adjustment reconstruction completed"

        # Step 2: gsplat Training (gsplat_env)
        echo "🔵 Step 2: gsplat Training"
        source ./env/gsplat_env/bin/activate

        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        python ./libs/gsplat/examples/simple_trainer.py default \
            --data-dir "$TEMP_WORK_DIR" \
            --result-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000

        # 결과 복사 (VGGT+BA sparse도 함께)
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/vggt_ba_sparse"
        ;;

    *)
        echo "❌ 알 수 없는 파이프라인: $PIPELINE"
        exit 1
        ;;
esac

# 종료 시간 기록
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 결과 분석 및 저장
echo "📊 결과 분석 중..."

# GPU 정보 동적으로 가져오기
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 || echo "Unknown GPU")

# 메타데이터 생성
cat > "$RESULT_DIR/metadata.json" << EOF
{
    "pipeline": "$PIPELINE",
    "timestamp": "$TIMESTAMP",
    "start_time": "$(date -d @$START_TIME)",
    "end_time": "$(date -d @$END_TIME)",
    "duration_seconds": $DURATION,
    "standard_dataset": "$STANDARD_DIR",
    "temp_work_dir": "$TEMP_WORK_DIR",
    "isolation": "true",
    "git_commit": "$(git rev-parse HEAD)",
    "system": {
        "hostname": "$(hostname)",
        "gpu": "$GPU_NAME",
        "python_env": "vggt_env"
    }
}
EOF

# 결과 분석 (pycolmap이 필요한 경우)
# P2/P3 → sparse, P4 → vggt_sparse, P5 → vggt_ba_sparse 순서로 확인
SPARSE_DIR=""
if [ -f "$RESULT_DIR/sparse/points3D.bin" ]; then
    SPARSE_DIR="$RESULT_DIR/sparse"
elif [ -f "$RESULT_DIR/vggt_ba_sparse/points3D.bin" ]; then
    SPARSE_DIR="$RESULT_DIR/vggt_ba_sparse"
elif [ -f "$RESULT_DIR/vggt_sparse/points3D.bin" ]; then
    SPARSE_DIR="$RESULT_DIR/vggt_sparse"
fi

if [ -n "$SPARSE_DIR" ]; then
    source ./env/vggt_env/bin/activate
    python -c "
import pycolmap
import json
import os

sparse_dir = '$SPARSE_DIR'
result_dir = '$RESULT_DIR'
reconstruction = pycolmap.Reconstruction(sparse_dir)

# PLY 파일 경로 찾기
ply_path = os.path.join(sparse_dir, 'points.ply')
ply_size_mb = round(os.path.getsize(ply_path) / (1024*1024), 2) if os.path.exists(ply_path) else 0

results = {
    'images_count': len(reconstruction.images),
    'points3D_count': len(reconstruction.points3D),
    'cameras_count': len(reconstruction.cameras),
    'ply_file_size_mb': ply_size_mb,
    'sparse_reconstruction_dir': os.path.basename(sparse_dir)
}

with open(os.path.join(result_dir, 'analysis.json'), 'w') as f:
    json.dump(results, f, indent=2)

print(f'✅ {results[\"points3D_count\"]:,} 3D points generated')
print(f'📁 PLY file: {results[\"ply_file_size_mb\"]} MB')
print(f'📂 Sparse dir: {results[\"sparse_reconstruction_dir\"]}')
"
fi

# P1 결과에서 타이밍 정보 통합
if [ "$PIPELINE" = "P1" ] && [ -f "$RESULT_DIR/timing_results.json" ]; then
    echo "📊 P1 타이밍 결과 통합 중..."
    python -c "
import json
import os

result_dir = '$RESULT_DIR'
timing_file = os.path.join(result_dir, 'timing_results.json')
analysis_file = os.path.join(result_dir, 'analysis.json')

# 타이밍 데이터 로드
with open(timing_file, 'r') as f:
    timing_data = json.load(f)

# 기존 분석 데이터가 있으면 통합
if os.path.exists(analysis_file):
    with open(analysis_file, 'r') as f:
        analysis_data = json.load(f)
    analysis_data.update(timing_data)
else:
    analysis_data = timing_data

# 통합된 결과 저장
with open(analysis_file, 'w') as f:
    json.dump(analysis_data, f, indent=2)

print(f'✅ 타이밍 정보 통합 완료')
print(f'⏱️ 총 파이프라인 시간: {timing_data[\"pipeline_total_seconds\"]}초')
print(f'⏱️ 훈련 시간: {timing_data[\"training_seconds\"]}초')
"
fi

# 임시 디렉토리 정리
rm -rf "$TEMP_WORK_DIR"
echo "🧹 임시 작업 디렉토리 정리 완료"

echo "✅ $PIPELINE 파이프라인 실행 완료!"
echo "⏱️ 총 소요시간: ${DURATION}초"
echo "📁 결과 위치: $RESULT_DIR"
echo "📊 분석 파일: $RESULT_DIR/metadata.json, $RESULT_DIR/analysis.json"