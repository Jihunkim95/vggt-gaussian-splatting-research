#!/bin/bash

# 파이프라인 실행 및 결과 저장 스크립트
# 사용법: ./run_pipeline.sh <파이프라인> [옵션]

PIPELINE="$1"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_BASE="./results"

if [ -z "$PIPELINE" ]; then
    echo "사용법: $0 <P1|P1R|P2|P3|P4|P5> [옵션]"
    echo ""
    echo "파이프라인 설명:"
    echo "  P1: Original COLMAP SfM + gsplat (Images only)"
    echo "  P1R: Real COLMAP SfM + gsplat (Images only)"
    echo "  P2: VGGT Feed-Forward Only"
    echo "  P3: VGGT + Bundle Adjustment"
    echo "  P4: VGGT → COLMAP → gsplat"
    echo "  P5: Advanced Hybrid Pipeline"
    exit 1
fi

# 표준 데이터셋 준비 확인
STANDARD_DIR="./datasets/DTU/scan1_standard"
if [ ! -d "$STANDARD_DIR/images" ]; then
    echo "❌ 표준 데이터셋이 준비되지 않았습니다."
    echo "🔧 먼저 실행하세요: ./prepare_standard_dataset.sh './datasets/DTU/SampleSet/MVS Data/Cleaned/scan1/images'"
    exit 1
fi

# 결과 디렉토리 생성
RESULT_DIR="${RESULTS_BASE}/${PIPELINE}_${TIMESTAMP}"
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
        export TORCH_CUDA_ARCH_LIST="8.9"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        # 기존 sparse 재구성 제거하여 이미지만으로 시작 (진짜 COLMAP SfM)
        if [ -d "$TEMP_WORK_DIR/sparse" ]; then
            echo "🧹 기존 sparse 재구성 제거 (이미지만으로 시작)"
            rm -rf "$TEMP_WORK_DIR/sparse"
        fi
        python p1_baseline.py \
            --data-dir "$TEMP_WORK_DIR" \
            --output-dir "$RESULT_DIR" \
            --max-steps 7000
        ;;

    "P1R")
        echo "📋 P1R: Real COLMAP SfM + gsplat (Images Only) 실행"
        echo "🔧 gsplat 환경 활성화 중..."
        source ./env/gsplat_env/bin/activate

        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="8.9"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        # 기존 sparse 재구성 제거하여 이미지만으로 시작
        if [ -d "$TEMP_WORK_DIR/sparse" ]; then
            echo "🧹 기존 sparse 재구성 제거 (이미지만으로 시작)"
            rm -rf "$TEMP_WORK_DIR/sparse"
        fi

        python p1_pycolmap.py \
            --data-dir "$TEMP_WORK_DIR" \
            --output-dir "$RESULT_DIR" \
            --max-steps 7000
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
            --max_reproj_error 8.0

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
        export TORCH_CUDA_ARCH_LIST="8.9"
        pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        python ./libs/gsplat/examples/simple_trainer.py default \
            --data-dir "$TEMP_WORK_DIR" \
            --result-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 7000 \
            --save-ply \
            --disable-viewer

        # 결과 복사 (VGGT sparse도 함께)
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/vggt_sparse"
        ;;

    "P5")
        echo "❌ $PIPELINE은 아직 구현되지 않았습니다."
        exit 1
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
        "gpu": "RTX 6000 Ada",
        "python_env": "vggt_env"
    }
}
EOF

# 결과 분석 (pycolmap이 필요한 경우)
if [ -f "$RESULT_DIR/sparse/points3D.bin" ]; then
    source ./env/vggt_env/bin/activate
    python -c "
import pycolmap
import json
import os

result_dir = '$RESULT_DIR'
reconstruction = pycolmap.Reconstruction(os.path.join(result_dir, 'sparse'))

results = {
    'images_count': len(reconstruction.images),
    'points3D_count': len(reconstruction.points3D),
    'cameras_count': len(reconstruction.cameras),
    'ply_file_size_mb': round(os.path.getsize(os.path.join(result_dir, 'sparse/points.ply')) / (1024*1024), 2)
}

with open(os.path.join(result_dir, 'analysis.json'), 'w') as f:
    json.dump(results, f, indent=2)

print(f'✅ {results[\"points3D_count\"]:,} 3D points generated')
print(f'📁 PLY file: {results[\"ply_file_size_mb\"]} MB')
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