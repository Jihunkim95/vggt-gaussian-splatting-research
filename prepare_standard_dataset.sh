#!/bin/bash

# 표준 데이터셋 준비 스크립트
# P1-P5 파이프라인 실행 전 반드시 실행해야 함

MAX_IMAGES=60

echo "🔧 표준 데이터셋 준비 중..."

# 입력 검증
if [ $# -ne 1 ]; then
    echo "사용법: $0 <원본_이미지_디렉토리>"
    echo "예시: $0 './datasets/DTU/Rectified/scan1_train'"
    echo "예시: $0 './datasets/DTU/Rectified/scan24_train'"
    exit 1
fi

SOURCE_DIR="$1"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ 원본 디렉토리가 존재하지 않습니다: $SOURCE_DIR"
    exit 1
fi

# 스캔 이름 자동 추출
# DTU: scan1_train → scan1_standard
# CO3Dv2: apple/110_13051_23361/images → CO3Dv2_apple_110_13051_23361_standard
if [[ "$SOURCE_DIR" == *"/DTU/"* ]]; then
    SCAN_NAME=$(basename "$SOURCE_DIR" | sed 's/_train$//')
    STANDARD_DIR="./datasets/DTU/${SCAN_NAME}_standard"
elif [[ "$SOURCE_DIR" == *"/CO3Dv2/"* ]]; then
    # Extract: datasets/CO3Dv2/apple/110_13051_23361/images → apple_110_13051_23361
    DATASET_PATH=$(echo "$SOURCE_DIR" | sed 's|.*/CO3Dv2/||' | sed 's|/images$||' | tr '/' '_')
    STANDARD_DIR="./datasets/CO3Dv2/${DATASET_PATH}_standard"
else
    # Generic: use directory name
    SCAN_NAME=$(basename "$SOURCE_DIR")
    STANDARD_DIR="./datasets/${SCAN_NAME}_standard"
fi
STANDARD_IMAGES_DIR="$STANDARD_DIR/images"

echo "📂 입력: $SOURCE_DIR"
echo "📂 출력: $STANDARD_DIR"

# 표준 디렉토리 생성
echo "📁 표준 디렉토리 생성: $STANDARD_DIR"
rm -rf "$STANDARD_DIR"  # 기존 제거
mkdir -p "$STANDARD_IMAGES_DIR"

# 원본 이미지 개수 확인 (PNG 또는 JPG)
TOTAL_PNG=$(ls "$SOURCE_DIR"/*.png 2>/dev/null | wc -l)
TOTAL_JPG=$(ls "$SOURCE_DIR"/*.jpg 2>/dev/null | wc -l)
TOTAL_IMAGES=$((TOTAL_PNG + TOTAL_JPG))

if [ $TOTAL_IMAGES -eq 0 ]; then
    echo "❌ 이미지가 없습니다 (PNG/JPG): $SOURCE_DIR"
    exit 1
fi

# 이미지 확장자 결정
if [ $TOTAL_PNG -gt 0 ]; then
    IMG_EXT="png"
else
    IMG_EXT="jpg"
fi

echo "📸 이미지 형식: $IMG_EXT"

echo "📊 원본 이미지: ${TOTAL_IMAGES}개"

# DTU 데이터셋인지 확인 (rect_XXX_Y_r5000.png 패턴)
IS_DTU=$(ls "$SOURCE_DIR"/*.$IMG_EXT 2>/dev/null | head -1 | grep -q "rect_.*_[0-6]_r5000" && echo "yes" || echo "no")

# 이미지 개수에 따른 처리
if [ $TOTAL_IMAGES -le $MAX_IMAGES ]; then
    echo "✅ ${TOTAL_IMAGES}개 ≤ ${MAX_IMAGES}개 → 전체 복사"

    if [ "$IS_DTU" = "yes" ]; then
        echo "   📷 DTU 데이터셋 감지 → 각도별 정렬 (COLMAP 최적화)"

        # DTU: 각도별로 정렬 (0→1→2→3→4→5→6)
        counter=1
        for angle in 0 1 2 3 4 5 6; do
            for img in $(ls "$SOURCE_DIR"/rect_*_${angle}_r5000.$IMG_EXT 2>/dev/null | sort); do
                printf -v padded "%03d" $counter
                img_name=$(basename "$img")
                cp "$img" "$STANDARD_IMAGES_DIR/${padded}_${img_name}"
                counter=$((counter + 1))
            done
        done
        FINAL_COUNT=$((counter - 1))
    else
        cp "$SOURCE_DIR"/*.$IMG_EXT "$STANDARD_IMAGES_DIR/"
        FINAL_COUNT=$TOTAL_IMAGES
    fi
else
    echo "⚠️ ${TOTAL_IMAGES}개 > ${MAX_IMAGES}개 → 균등 샘플링 실행"

    # 균등 샘플링
    INTERVAL=$((TOTAL_IMAGES / MAX_IMAGES))
    if [ $INTERVAL -eq 0 ]; then
        INTERVAL=1
    fi

    echo "   샘플링 간격: 매 ${INTERVAL}번째"

    if [ "$IS_DTU" = "yes" ]; then
        echo "   📷 DTU 데이터셋 감지 → 각도별 정렬 후 샘플링"

        # 임시 디렉토리에 각도별로 정렬
        TEMP_SORTED="/tmp/dtu_sorted_$$"
        mkdir -p "$TEMP_SORTED"

        counter=1
        for angle in 0 1 2 3 4 5 6; do
            for img in $(ls "$SOURCE_DIR"/rect_*_${angle}_r5000.$IMG_EXT 2>/dev/null | sort); do
                printf -v padded "%05d" $counter
                ln -s "$(realpath "$img")" "$TEMP_SORTED/${padded}_$(basename "$img")"
                counter=$((counter + 1))
            done
        done

        # 정렬된 이미지에서 균등 샘플링
        count=0
        selected=0
        for img in "$TEMP_SORTED"/*.$IMG_EXT; do
            if [ $((count % INTERVAL)) -eq 0 ] && [ $selected -lt $MAX_IMAGES ]; then
                cp "$img" "$STANDARD_IMAGES_DIR/"
                selected=$((selected + 1))
            fi
            count=$((count + 1))
        done

        rm -rf "$TEMP_SORTED"
        FINAL_COUNT=$selected
    else
        count=0
        selected=0

        for img in "$SOURCE_DIR"/*.$IMG_EXT; do
            if [ $((count % INTERVAL)) -eq 0 ] && [ $selected -lt $MAX_IMAGES ]; then
                cp "$img" "$STANDARD_IMAGES_DIR/"
                selected=$((selected + 1))
            fi
            count=$((count + 1))
        done

        FINAL_COUNT=$selected
    fi
fi

echo "✅ 표준 데이터셋 준비 완료!"
echo "📁 위치: $STANDARD_IMAGES_DIR"
echo "📸 최종 이미지 수: ${FINAL_COUNT}개"
echo ""
echo "🚀 이제 P1-P5 파이프라인을 실행할 수 있습니다:"
echo "   P1: python p1_baseline.py --data-dir $STANDARD_DIR"
echo "   P2: python demo_colmap.py --scene_dir $STANDARD_DIR --conf_thres_value 5.0"
echo "   P3: python demo_colmap.py --scene_dir $STANDARD_DIR --use_ba --conf_thres_value 5.0"