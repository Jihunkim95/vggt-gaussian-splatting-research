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

# 캐시를 사용자 홈으로 리다이렉트
export TORCH_HOME=/data/users/jhkim/.cache/torch
export PIP_CACHE_DIR=/data/users/jhkim/.cache/pip
export TRANSFORMERS_CACHE=/data/users/jhkim/.cache/huggingface
export HF_HOME=/data/users/jhkim/.cache/huggingface
export TORCH_EXTENSIONS_DIR=/data/users/jhkim/.cache/torch_extensions

# gsplat JIT 컴파일용 ninja 경로 추가
export PATH=/data/users/jhkim/vggt-gaussian-splatting-research/env/gsplat_env/bin:$PATH

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

# conf_thres_value 자동 결정
# - Custom 폴더: 낮은 임계값 (P4: 2.0, P5: 0.05)
# - 그 외 (DTU 등): 높은 임계값 (5.0)
# 감지 기준: 경로에 "custom" 또는 "quality_" 포함 여부
if [[ "$DATA_DIR" == *"custom"* ]] || [[ "$DATA_DIR" == *"quality_"* ]]; then
    CONF_THRES=5.0      # P2, P3, P4용
    CONF_THRES_BA=5.0   # P5용 (BA에 더 많은 포인트 필요)
    echo "🔧 Custom 데이터셋 감지 → P4: conf_thres=5.0, P5: conf_thres=5.0"
else
    CONF_THRES=5.0
    CONF_THRES_BA=5.0
    echo "🔧 표준 데이터셋 감지 (DTU 등) → conf_thres_value=5.0"
fi

case "$PIPELINE" in
    "P1")
        echo "📋 P1: Original COLMAP SfM + gsplat (Images Only) 실행"

        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        ./env/gsplat_env/bin/pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        # 기존 sparse 재구성 제거하여 이미지만으로 시작 (진짜 COLMAP SfM)
        if [ -d "$TEMP_WORK_DIR/sparse" ]; then
            echo "🧹 기존 sparse 재구성 제거 (이미지만으로 시작)"
            rm -rf "$TEMP_WORK_DIR/sparse"
        fi
        ./env/gsplat_env/bin/python p1_baseline.py \
            --data-dir "$TEMP_WORK_DIR" \
            --output-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 7000 15000 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000
        ;;

    "P2")
        echo "📋 P2: VGGT Feed-Forward Only 실행"
        PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --conf_thres_value $CONF_THRES

        # 결과 복사
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/"
        ;;

    "P3")
        echo "📋 P3: VGGT + Bundle Adjustment 실행"
        PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
            --scene_dir "$TEMP_WORK_DIR" \
            --use_ba \
            --conf_thres_value $CONF_THRES \
            --max_reproj_error 8.0 \
            --max_query_pts 4096

        # 결과 복사
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/"
        ;;

    "P4")
        echo "📋 P4: VGGT Feed-Forward → gsplat 실행"

        # Step 1: VGGT Feed-Forward (vggt_env)
        echo "🔴 Step 1: VGGT Feed-Forward"
        SETUP_START=$(date +%s)

        # Custom 데이터셋: 실패 시 conf_thres_value를 점진적으로 낮춤
        if [[ "$DATA_DIR" == *"custom"* ]] || [[ "$DATA_DIR" == *"quality_"* ]]; then
            VGGT_SUCCESS=false
            CURRENT_CONF=4.0
            MIN_CONF=0.5

            while (( $(echo "$CURRENT_CONF >= $MIN_CONF" | bc -l) )); do
                echo "🔄 VGGT 시도: conf_thres_value=$CURRENT_CONF"

                # 이전 sparse 결과 삭제
                rm -rf "$TEMP_WORK_DIR/sparse"

                PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
                    --scene_dir "$TEMP_WORK_DIR" \
                    --conf_thres_value $CURRENT_CONF 2>&1 || true

                # points3D.bin 파일 존재 여부로 성공 판단
                if [ -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
                    echo "✅ VGGT 성공! conf_thres_value=$CURRENT_CONF"
                    VGGT_SUCCESS=true
                    break
                fi

                echo "⚠️ VGGT 실패 (conf_thres=$CURRENT_CONF), 임계값 낮추는 중..."
                CURRENT_CONF=$(echo "$CURRENT_CONF - 0.5" | bc -l)
            done

            if [ "$VGGT_SUCCESS" = false ]; then
                echo "❌ VGGT 실패: 모든 conf_thres_value 시도 실패"
                exit 1
            fi
        else
            # 표준 데이터셋: 단일 시도
            PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
                --scene_dir "$TEMP_WORK_DIR" \
                --conf_thres_value $CONF_THRES

            if [ ! -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
                echo "❌ VGGT feed-forward failed - no sparse reconstruction"
                exit 1
            fi
        fi

        SETUP_END=$(date +%s)
        SETUP_SECONDS=$((SETUP_END - SETUP_START))
        echo "✅ VGGT sparse reconstruction completed (${SETUP_SECONDS}s)"

        # Step 2: gsplat Training (gsplat_env)
        echo "🔵 Step 2: gsplat Training"
        TRAINING_START=$(date +%s)
        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        export TORCH_EXTENSIONS_DIR=/data/users/jhkim/.cache/torch_extensions
        export PATH=/data/users/jhkim/vggt-gaussian-splatting-research/env/gsplat_env/bin:$PATH
        ./env/gsplat_env/bin/pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        ./env/gsplat_env/bin/python ./libs/gsplat/examples/simple_trainer.py default \
            --data-dir "$TEMP_WORK_DIR" \
            --result-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 7000 15000 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000
        TRAINING_END=$(date +%s)
        TRAINING_SECONDS=$((TRAINING_END - TRAINING_START))
        echo "✅ gsplat training completed (${TRAINING_SECONDS}s)"

        # timing_results.json 생성 (체크포인트별 시간 포함)
        PIPELINE_TOTAL=$((SETUP_SECONDS + TRAINING_SECONDS))

        # 체크포인트별 시간 추출
        TIME_7K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step6999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")
        TIME_15K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step14999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")
        TIME_30K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step29999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")

        cat > "$RESULT_DIR/timing_results.json" << EOF
{
  "pipeline_total_seconds": $PIPELINE_TOTAL,
  "setup_seconds": $SETUP_SECONDS,
  "training_seconds": $TRAINING_SECONDS,
  "checkpoint_times": {
    "step_7000": $TIME_7K,
    "step_15000": $TIME_15K,
    "step_30000": $TIME_30K
  }
}
EOF

        # 결과 복사 (VGGT sparse도 함께)
        cp -r "$TEMP_WORK_DIR/sparse" "$RESULT_DIR/vggt_sparse"
        ;;

    "P5")
        echo "📋 P5: VGGT + Bundle Adjustment → gsplat 실행"

        # Step 1: VGGT + Bundle Adjustment (vggt_env)
        echo "🟢 Step 1: VGGT + Bundle Adjustment"
        SETUP_START=$(date +%s)

        # Custom 데이터셋: BA 실패 시 conf_thres_value를 점진적으로 낮춤
        if [[ "$DATA_DIR" == *"custom"* ]] || [[ "$DATA_DIR" == *"quality_"* ]]; then
            BA_SUCCESS=false
            CURRENT_CONF=5.0
            MIN_CONF=0.01

            while (( $(echo "$CURRENT_CONF >= $MIN_CONF" | bc -l) )); do
                echo "🔄 BA 시도: conf_thres_value=$CURRENT_CONF"

                # 이전 sparse 결과 삭제
                rm -rf "$TEMP_WORK_DIR/sparse"

                PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
                    --scene_dir "$TEMP_WORK_DIR" \
                    --use_ba \
                    --conf_thres_value $CURRENT_CONF \
                    --max_reproj_error 8.0 \
                    --max_query_pts 4096 2>&1 || true

                if [ -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
                    echo "✅ BA 성공! conf_thres_value=$CURRENT_CONF"
                    BA_SUCCESS=true
                    break
                fi

                echo "⚠️ BA 실패 (conf_thres=$CURRENT_CONF), 임계값 낮추는 중..."
                CURRENT_CONF=$(echo "$CURRENT_CONF - 0.5" | bc -l)

                # 0 이하로 내려가면 0.01로 마지막 시도
                if (( $(echo "$CURRENT_CONF < $MIN_CONF" | bc -l) )) && [ "$BA_SUCCESS" = false ]; then
                    CURRENT_CONF=$MIN_CONF
                fi
            done

            if [ "$BA_SUCCESS" = false ]; then
                echo "❌ BA 실패: 모든 conf_thres_value 시도 실패"
                echo "💡 P4 파이프라인(BA 없음)을 사용해보세요: ./run_pipeline.sh P4 $DATA_DIR"
                exit 1
            fi
        else
            # 표준 데이터셋: 단일 시도
            PYTHONPATH=./libs/vggt:$PYTHONPATH ./env/vggt_env/bin/python demo_colmap.py \
                --scene_dir "$TEMP_WORK_DIR" \
                --use_ba \
                --conf_thres_value $CONF_THRES_BA \
                --max_reproj_error 8.0 \
                --max_query_pts 4096

            if [ ! -f "$TEMP_WORK_DIR/sparse/points3D.bin" ]; then
                echo "❌ VGGT + Bundle Adjustment failed - no sparse reconstruction"
                exit 1
            fi
        fi

        SETUP_END=$(date +%s)
        SETUP_SECONDS=$((SETUP_END - SETUP_START))
        echo "✅ VGGT + Bundle Adjustment reconstruction completed (${SETUP_SECONDS}s)"

        # Step 2: gsplat Training (gsplat_env)
        echo "🔵 Step 2: gsplat Training"
        TRAINING_START=$(date +%s)
        # gsplat 환경에 필요한 추가 패키지 확인
        echo "📦 필요 패키지 설치 확인 중..."
        export TMPDIR=/data/tmp
        export TORCH_CUDA_ARCH_LIST="9.0"
        export TORCH_EXTENSIONS_DIR=/data/users/jhkim/.cache/torch_extensions
        export PATH=/data/users/jhkim/vggt-gaussian-splatting-research/env/gsplat_env/bin:$PATH
        ./env/gsplat_env/bin/pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true

        ./env/gsplat_env/bin/python ./libs/gsplat/examples/simple_trainer.py default \
            --data-dir "$TEMP_WORK_DIR" \
            --result-dir "$RESULT_DIR" \
            --data-factor 1 \
            --max-steps 30000 \
            --eval-steps 7000 15000 30000 \
            --save-steps 7000 15000 30000 \
            --ply-steps 7000 15000 30000 \
            --save-ply \
            --disable-viewer \
            --tb-every 1000
        TRAINING_END=$(date +%s)
        TRAINING_SECONDS=$((TRAINING_END - TRAINING_START))
        echo "✅ gsplat training completed (${TRAINING_SECONDS}s)"

        # timing_results.json 생성 (체크포인트별 시간 포함)
        PIPELINE_TOTAL=$((SETUP_SECONDS + TRAINING_SECONDS))

        # 체크포인트별 시간 추출
        TIME_7K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step6999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")
        TIME_15K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step14999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")
        TIME_30K=$(python3 -c "import json; f=open('$RESULT_DIR/stats/train_step29999_rank0.json'); d=json.load(f); print(round(d['ellipse_time'],1))" 2>/dev/null || echo "null")

        cat > "$RESULT_DIR/timing_results.json" << EOF
{
  "pipeline_total_seconds": $PIPELINE_TOTAL,
  "setup_seconds": $SETUP_SECONDS,
  "training_seconds": $TRAINING_SECONDS,
  "checkpoint_times": {
    "step_7000": $TIME_7K,
    "step_15000": $TIME_15K,
    "step_30000": $TIME_30K
  }
}
EOF

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
    ./env/vggt_env/bin/python -c "
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

# P1/P4/P5 결과에서 타이밍 정보 통합
if [[ "$PIPELINE" =~ ^(P1|P4|P5)$ ]] && [ -f "$RESULT_DIR/timing_results.json" ]; then
    echo "📊 $PIPELINE 타이밍 결과 통합 중..."
    ./env/vggt_env/bin/python -c "
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
print(f'⏱️ 셋업 시간: {timing_data[\"setup_seconds\"]}초')
"
fi

# 임시 디렉토리 정리
rm -rf "$TEMP_WORK_DIR"
echo "🧹 임시 작업 디렉토리 정리 완료"

echo "✅ $PIPELINE 파이프라인 실행 완료!"
echo "⏱️ 총 소요시간: ${DURATION}초"
echo "📁 결과 위치: $RESULT_DIR"
echo "📊 분석 파일: $RESULT_DIR/metadata.json, $RESULT_DIR/analysis.json"