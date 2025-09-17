#!/bin/bash

# 파이프라인 실행 및 결과 저장 스크립트
# 사용법: ./run_pipeline.sh <파이프라인> [옵션]

PIPELINE="$1"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_BASE="./results"

if [ -z "$PIPELINE" ]; then
    echo "사용법: $0 <P1|P2|P3|P4|P5> [옵션]"
    echo ""
    echo "파이프라인 설명:"
    echo "  P1: COLMAP + gsplat Baseline"
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
        echo "📋 P1: COLMAP + gsplat Baseline 실행"
        source scripts/utils/switch_env.sh gsplat
        python create_simple_colmap_scan1.py  # COLMAP 파일 생성
        python p1_baseline.py \
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

    "P4"|"P5")
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

# 임시 디렉토리 정리
rm -rf "$TEMP_WORK_DIR"
echo "🧹 임시 작업 디렉토리 정리 완료"

echo "✅ $PIPELINE 파이프라인 실행 완료!"
echo "⏱️ 총 소요시간: ${DURATION}초"
echo "📁 결과 위치: $RESULT_DIR"
echo "📊 분석 파일: $RESULT_DIR/metadata.json, $RESULT_DIR/analysis.json"