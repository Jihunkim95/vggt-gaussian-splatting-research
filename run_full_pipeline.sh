#!/bin/bash

##############################################################################
# run_full_pipeline.sh - End-to-End Pipeline with Quality Sampling
#
# 사용법:
#   ./run_full_pipeline.sh <input> <pipeline> [options]
#
# 예시:
#   ./run_full_pipeline.sh ./datasets/custom/video.mp4 P5
#   ./run_full_pipeline.sh ./datasets/custom/images/ P4 --target-count 80
#   ./run_full_pipeline.sh ./my_video.mp4 P5 --overlap-ratio 0.7
#
# 파이프라인:
#   P1: COLMAP → 3DGS
#   P4: VGGT → 3DGS
#   P5: VGGT+BA → 3DGS
#
# 품질 평가 방법 (Farneback 2003, Pech-Pacheco 2000):
#   - Optical Flow: 정지 프레임 제거 (Farneback Dense Flow)
#   - Laplacian Sharpness: 블러 프레임 제거
#   - Brightness: 노출 이상 프레임 제거
#   - Overlap 기반 샘플링: 60-70% 오버랩 보장 균등 간격 선택
##############################################################################

set -e  # Exit on error

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 함수
show_help() {
    echo "사용법: $0 <input> <pipeline> [options]"
    echo ""
    echo "필수 인자:"
    echo "  input              입력 경로 (비디오 파일 또는 이미지 디렉토리)"
    echo "  pipeline           파이프라인 타입 (P1, P4, P5)"
    echo ""
    echo "선택 옵션:"
    echo "  --target-count N       최종 이미지 수 (기본: 60)"
    echo "  --overlap-ratio N      프레임 간 오버랩 비율 (기본: 0.65, 즉 65%)"
    echo "  --flow-threshold N     Optical Flow 임계값 (기본: 0.3)"
    echo "  --sharpness-threshold N  선명도 임계값 (기본: 30.0)"
    echo "  --skip-sampling        품질 샘플링 건너뛰기 (이미지 디렉토리 직접 사용)"
    echo "  --keep-temp            임시 디렉토리 유지 (디버깅용)"
    echo "  -h, --help             도움말 표시"
    echo ""
    echo "품질 평가 방법 (Farneback 2003, Pech-Pacheco 2000):"
    echo "  - Optical Flow: 정지 프레임 제거"
    echo "  - Laplacian Sharpness: 블러 프레임 제거"
    echo "  - Brightness: 노출 이상 프레임 제거"
    echo "  - Overlap 기반 샘플링: 60-70% 오버랩 보장 균등 간격 선택"
    echo ""
    echo "예시:"
    echo "  # 비디오로 P5 파이프라인 실행 (기본 설정)"
    echo "  $0 ./my_video.mp4 P5"
    echo ""
    echo "  # 이미지 디렉토리로 P4 실행 (80개 샘플링)"
    echo "  $0 ./images/ P4 --target-count 80"
    echo ""
    echo "  # 70% 오버랩으로 샘플링"
    echo "  $0 ./video.mp4 P5 --overlap-ratio 0.7 --target-count 60"
    echo ""
}

# 에러 핸들러
error_exit() {
    echo -e "${RED}❌ 오류: $1${NC}" >&2
    if [ -n "$TEMP_DIR" ] && [ "$KEEP_TEMP" != "true" ]; then
        echo -e "${YELLOW}🧹 임시 디렉토리 정리 중...${NC}"
        rm -rf "$TEMP_DIR"
    fi
    exit 1
}

# 인자 파싱
if [ $# -lt 2 ]; then
    show_help
    exit 1
fi

INPUT_PATH="$1"
PIPELINE="$2"
shift 2

# 기본값 설정
TARGET_COUNT=60
OVERLAP_RATIO=0.65
FLOW_THRESHOLD=0.3
SHARPNESS_THRESHOLD=30.0
SKIP_SAMPLING=false
KEEP_TEMP=false

# 캐시를 사용자 홈으로 리다이렉트
export TORCH_HOME=/data/users/jhkim/.cache/torch
export PIP_CACHE_DIR=/data/users/jhkim/.cache/pip
export TRANSFORMERS_CACHE=/data/users/jhkim/.cache/huggingface
export HF_HOME=/data/users/jhkim/.cache/huggingface
export TORCH_EXTENSIONS_DIR=/data/users/jhkim/.cache/torch_extensions

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --target-count)
            TARGET_COUNT="$2"
            shift 2
            ;;
        --overlap-ratio)
            OVERLAP_RATIO="$2"
            shift 2
            ;;
        --flow-threshold)
            FLOW_THRESHOLD="$2"
            shift 2
            ;;
        --sharpness-threshold)
            SHARPNESS_THRESHOLD="$2"
            shift 2
            ;;
        --skip-sampling)
            SKIP_SAMPLING=true
            shift
            ;;
        --keep-temp)
            KEEP_TEMP=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error_exit "알 수 없는 옵션: $1"
            ;;
    esac
done

# 입력 검증
if [ ! -e "$INPUT_PATH" ]; then
    error_exit "입력 경로가 존재하지 않습니다: $INPUT_PATH"
fi

if [[ ! "$PIPELINE" =~ ^P[145]$ ]]; then
    error_exit "지원하지 않는 파이프라인: $PIPELINE (P1, P4, P5 중 선택)"
fi

# 입력 타입 감지
INPUT_PATH=$(realpath "$INPUT_PATH")
if [ -f "$INPUT_PATH" ]; then
    INPUT_TYPE="video"
    INPUT_NAME=$(basename "$INPUT_PATH" | sed 's/\.[^.]*$//')
elif [ -d "$INPUT_PATH" ]; then
    INPUT_TYPE="directory"
    INPUT_NAME=$(basename "$INPUT_PATH")
else
    error_exit "입력이 파일도 디렉토리도 아닙니다: $INPUT_PATH"
fi

echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 End-to-End 3DGS Pipeline with Quality Sampling${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📁 입력:${NC} $INPUT_PATH"
echo -e "${GREEN}📋 타입:${NC} $INPUT_TYPE"
echo -e "${GREEN}🔧 파이프라인:${NC} $PIPELINE"
echo -e "${GREEN}🎯 목표 이미지 수:${NC} $TARGET_COUNT"
echo -e "${GREEN}🔗 오버랩 비율:${NC} ${OVERLAP_RATIO}"
echo -e "${GREEN}🔬 품질 방법:${NC} Optical Flow → Laplacian + Brightness → Overlap Sampling"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo ""

# 타임스탬프 생성
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 품질 샘플링 단계
if [ "$SKIP_SAMPLING" = true ]; then
    echo -e "${YELLOW}⏭️  품질 샘플링 건너뛰기 (직접 입력 사용)${NC}"
    DATASET_DIR="$INPUT_PATH"
else
    echo -e "${GREEN}🔵 Step 1/2: 품질 기반 이미지 샘플링${NC}"

    # 출력 디렉토리 설정
    # 입력이 datasets/custom/ 안에 있으면 같은 위치에 출력
    INPUT_DIR=$(dirname "$INPUT_PATH")
    if [[ "$INPUT_DIR" == *"datasets/custom"* ]]; then
        OUTPUT_DIR="${INPUT_DIR}/${INPUT_NAME}_quality_${TIMESTAMP}"
    else
        OUTPUT_DIR="./datasets/custom/${INPUT_NAME}_quality_${TIMESTAMP}"
    fi

    # 출력 디렉토리 부모 생성
    mkdir -p "$(dirname "$OUTPUT_DIR")"

    # 환경 활성화 확인
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}⚠️  vggt_env 활성화 중...${NC}"
        source ./env/vggt_env/bin/activate || error_exit "vggt_env 활성화 실패"
    fi

    # quality_sampler.py 실행
    echo -e "${BLUE}📊 Quality Sampler 실행 중...${NC}"

    # Overlap 기반 프레임 샘플링
    ./env/vggt_env/bin/python quality_sampler.py "$INPUT_PATH" \
        --output-dir "$OUTPUT_DIR" \
        --target-count $TARGET_COUNT \
        --overlap-ratio $OVERLAP_RATIO \
        --flow-threshold $FLOW_THRESHOLD \
        --sharpness-threshold $SHARPNESS_THRESHOLD \
        || error_exit "Quality Sampler 실행 실패"

    echo -e "${GREEN}✅ 품질 샘플링 완료: $OUTPUT_DIR${NC}"
    echo ""

    DATASET_DIR="$OUTPUT_DIR"
fi

# 3DGS 파이프라인 실행
echo -e "${GREEN}🔵 Step 2/2: 3D Gaussian Splatting 파이프라인 실행${NC}"
echo -e "${BLUE}📋 파이프라인 $PIPELINE 실행 중...${NC}"

# 컴파일러 환경 설정
export CC=/usr/bin/gcc-12
export CXX=/usr/bin/g++-12
export CUDAHOSTCXX=/usr/bin/g++-12

# 파이프라인 실행
./run_pipeline.sh "$PIPELINE" "$DATASET_DIR" || error_exit "파이프라인 실행 실패"

# 결과 디렉토리 찾기
RESULT_DIR=$(ls -dt ./results/${PIPELINE}_${INPUT_NAME}_quality_* 2>/dev/null | head -1)

if [ -z "$RESULT_DIR" ]; then
    RESULT_DIR=$(ls -dt ./results/${PIPELINE}_* 2>/dev/null | head -1)
fi

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ End-to-End Pipeline 완료!${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📁 데이터셋:${NC} $DATASET_DIR"
if [ -n "$RESULT_DIR" ]; then
    echo -e "${GREEN}📊 결과:${NC} $RESULT_DIR"

    # 결과 요약 표시
    STATS_FILE="$RESULT_DIR/stats/val_step29999.json"
    if [ -f "$STATS_FILE" ]; then
        echo ""
        echo -e "${BLUE}📈 최종 성능 지표:${NC}"
        PSNR=$(jq -r '.psnr | tostring[0:6]' "$STATS_FILE" 2>/dev/null)
        SSIM=$(jq -r '.ssim | tostring[0:6]' "$STATS_FILE" 2>/dev/null)
        LPIPS=$(jq -r '.lpips | tostring[0:5]' "$STATS_FILE" 2>/dev/null)
        NUM_GS=$(jq -r '.num_GS' "$STATS_FILE" 2>/dev/null)

        if [ -n "$PSNR" ]; then
            echo -e "  ${GREEN}PSNR:${NC}  $PSNR dB"
            echo -e "  ${GREEN}SSIM:${NC}  $SSIM"
            echo -e "  ${GREEN}LPIPS:${NC} $LPIPS"
            echo -e "  ${GREEN}GS:${NC}    $NUM_GS"
        fi
    fi
fi
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
