#!/bin/bash

# 표준 데이터셋 준비 스크립트
# P1-P5 파이프라인 실행 전 반드시 실행해야 함

STANDARD_DIR="./datasets/DTU/scan1_standard"
STANDARD_IMAGES_DIR="$STANDARD_DIR/images"
MAX_IMAGES=60

echo "🔧 표준 데이터셋 준비 중..."

# 입력 검증
if [ $# -ne 1 ]; then
    echo "사용법: $0 <원본_이미지_디렉토리>"
    echo "예시: $0 './datasets/DTU/SampleSet/MVS Data/Cleaned/scan1/images'"
    exit 1
fi

SOURCE_DIR="$1"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ 원본 디렉토리가 존재하지 않습니다: $SOURCE_DIR"
    exit 1
fi

# 표준 디렉토리 생성
echo "📁 표준 디렉토리 생성: $STANDARD_DIR"
rm -rf "$STANDARD_DIR"  # 기존 제거
mkdir -p "$STANDARD_IMAGES_DIR"

# 원본 이미지 개수 확인
TOTAL_IMAGES=$(ls "$SOURCE_DIR"/*.png 2>/dev/null | wc -l)

if [ $TOTAL_IMAGES -eq 0 ]; then
    echo "❌ PNG 이미지가 없습니다: $SOURCE_DIR"
    exit 1
fi

echo "📊 원본 이미지: ${TOTAL_IMAGES}개"

# 이미지 개수에 따른 처리
if [ $TOTAL_IMAGES -le $MAX_IMAGES ]; then
    echo "✅ ${TOTAL_IMAGES}개 ≤ ${MAX_IMAGES}개 → 전체 복사"
    cp "$SOURCE_DIR"/*.png "$STANDARD_IMAGES_DIR/"
    FINAL_COUNT=$TOTAL_IMAGES
else
    echo "⚠️ ${TOTAL_IMAGES}개 > ${MAX_IMAGES}개 → 균등 샘플링 실행"

    # 균등 샘플링
    INTERVAL=$((TOTAL_IMAGES / MAX_IMAGES))
    if [ $INTERVAL -eq 0 ]; then
        INTERVAL=1
    fi

    echo "   샘플링 간격: 매 ${INTERVAL}번째"

    count=0
    selected=0

    for img in "$SOURCE_DIR"/*.png; do
        if [ $((count % INTERVAL)) -eq 0 ] && [ $selected -lt $MAX_IMAGES ]; then
            cp "$img" "$STANDARD_IMAGES_DIR/"
            selected=$((selected + 1))
        fi
        count=$((count + 1))
    done

    FINAL_COUNT=$selected
fi

echo "✅ 표준 데이터셋 준비 완료!"
echo "📁 위치: $STANDARD_IMAGES_DIR"
echo "📸 최종 이미지 수: ${FINAL_COUNT}개"
echo ""
echo "🚀 이제 P1-P5 파이프라인을 실행할 수 있습니다:"
echo "   P1: python p1_baseline.py --data-dir $STANDARD_DIR"
echo "   P2: python demo_colmap.py --scene_dir $STANDARD_DIR --conf_thres_value 5.0"
echo "   P3: python demo_colmap.py --scene_dir $STANDARD_DIR --use_ba --conf_thres_value 5.0"