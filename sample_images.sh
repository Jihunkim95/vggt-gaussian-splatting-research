#!/bin/bash

# 균등 샘플링으로 이미지 선택 스크립트
# 사용법: ./sample_images.sh <입력_디렉토리> <출력_디렉토리> <샘플_개수>

INPUT_DIR="$1"
OUTPUT_DIR="$2"
TARGET_COUNT="${3:-60}"  # 기본값 60개

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "사용법: $0 <입력_디렉토리> <출력_디렉토리> [샘플_개수]"
    echo "예시: $0 './datasets/DTU/SampleSet/MVS Data/Cleaned/scan1/images' './datasets/DTU/scan1_60frames/images' 60"
    exit 1
fi

# 입력 디렉토리 확인
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ 입력 디렉토리가 존재하지 않습니다: $INPUT_DIR"
    exit 1
fi

# 출력 디렉토리 생성
mkdir -p "$OUTPUT_DIR"

# 총 이미지 개수 계산
TOTAL_IMAGES=$(ls "$INPUT_DIR"/*.png 2>/dev/null | wc -l)

if [ $TOTAL_IMAGES -eq 0 ]; then
    echo "❌ PNG 이미지가 없습니다: $INPUT_DIR"
    exit 1
fi

# 샘플링 간격 계산
INTERVAL=$((TOTAL_IMAGES / TARGET_COUNT))

if [ $INTERVAL -eq 0 ]; then
    INTERVAL=1
fi

echo "📊 이미지 샘플링 정보:"
echo "   총 이미지: ${TOTAL_IMAGES}개"
echo "   목표 샘플: ${TARGET_COUNT}개"
echo "   샘플링 간격: 매 ${INTERVAL}번째"
echo "   실제 선택: $((TOTAL_IMAGES / INTERVAL))개"
echo "   입력: $INPUT_DIR"
echo "   출력: $OUTPUT_DIR"

# 균등 샘플링 실행
echo "🔄 샘플링 시작..."
count=0
selected=0

for img in "$INPUT_DIR"/*.png; do
    if [ $((count % INTERVAL)) -eq 0 ]; then
        cp "$img" "$OUTPUT_DIR/"
        selected=$((selected + 1))
        echo "   ✅ $(basename "$img") 복사됨 ($selected/$TARGET_COUNT)"
    fi
    count=$((count + 1))
done

echo "✅ 샘플링 완료: ${selected}개 이미지 선택"
echo "📁 결과 위치: $OUTPUT_DIR"