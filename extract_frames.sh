#!/bin/bash

# extract_frames.sh - 동영상에서 60개의 프레임을 균등하게 추출하는 스크립트

set -e

# 사용법 출력
function show_usage() {
    echo "Usage: $0 <video_file> [output_directory]"
    echo ""
    echo "Examples:"
    echo "  $0 video.mp4"
    echo "  $0 video.mp4 ./datasets/my_scene"
    echo "  $0 /path/to/video.mov ./datasets/custom_scene"
    echo ""
    echo "Arguments:"
    echo "  video_file        : Path to input video file (mp4, mov, avi, etc.)"
    echo "  output_directory  : Output directory (default: ./datasets/video_frames)"
    echo ""
    echo "Output:"
    echo "  Extracts 60 frames evenly spaced throughout the video"
    echo "  Saves to <output_directory>/images/"
    echo "  Ready to use with run_pipeline.sh"
    exit 1
}

# 인자 확인
if [ $# -lt 1 ]; then
    echo "Error: Video file required"
    show_usage
fi

VIDEO_FILE="$1"
OUTPUT_DIR="${2:-./datasets/video_frames}"

# 동영상 파일 존재 확인
if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: Video file not found: $VIDEO_FILE"
    exit 1
fi

# ffmpeg 및 bc 설치 확인
if ! command -v ffmpeg &> /dev/null || ! command -v bc &> /dev/null; then
    echo "Installing required packages (ffmpeg, bc)..."
    apt-get update -qq && apt-get install -y ffmpeg bc
fi

# 출력 디렉토리 생성
IMAGES_DIR="$OUTPUT_DIR/images"
mkdir -p "$IMAGES_DIR"

echo "=================================================="
echo "🎬 Video Frame Extraction"
echo "=================================================="
echo "📹 Input video: $VIDEO_FILE"
echo "📁 Output directory: $IMAGES_DIR"
echo "🖼️  Target frames: 60"
echo ""

# 동영상 정보 가져오기
echo "📊 Analyzing video..."
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE")
TOTAL_FRAMES=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$VIDEO_FILE")
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" | bc -l)

echo "   Duration: ${DURATION}s"
echo "   Total frames: $TOTAL_FRAMES"
echo "   FPS: $FPS"
echo ""

# 60개의 프레임을 균등하게 추출
echo "🔄 Extracting frames..."
ffmpeg -i "$VIDEO_FILE" -vf "select='not(mod(n\,$(echo "$TOTAL_FRAMES/60" | bc)))'" -vsync vfr -q:v 2 "$IMAGES_DIR/frame_%04d.jpg" -loglevel warning

# 추출된 프레임 수 확인
EXTRACTED_COUNT=$(ls -1 "$IMAGES_DIR"/*.jpg 2>/dev/null | wc -l)
echo "✅ Extracted $EXTRACTED_COUNT frames"

# 파일명을 0001.jpg, 0002.jpg 형식으로 변경
echo "📝 Renaming files..."
counter=1
for file in "$IMAGES_DIR"/frame_*.jpg; do
    if [ -f "$file" ]; then
        new_name=$(printf "%04d.jpg" $counter)
        mv "$file" "$IMAGES_DIR/$new_name"
        counter=$((counter + 1))
    fi
done

# 60개로 제한 (더 많이 추출된 경우)
FINAL_COUNT=$(ls -1 "$IMAGES_DIR"/*.jpg 2>/dev/null | wc -l)
if [ $FINAL_COUNT -gt 60 ]; then
    echo "⚠️  $FINAL_COUNT frames extracted, keeping first 60..."
    counter=61
    while [ $counter -le $FINAL_COUNT ]; do
        rm -f "$IMAGES_DIR/$(printf "%04d.jpg" $counter)"
        counter=$((counter + 1))
    done
    FINAL_COUNT=60
fi

echo ""
echo "=================================================="
echo "✅ Frame extraction completed!"
echo "=================================================="
echo "📁 Output: $IMAGES_DIR"
echo "🖼️  Total frames: $FINAL_COUNT"
echo ""
echo "Next steps:"
echo "  1. Run COLMAP (if needed):"
echo "     colmap feature_extractor --image_path $IMAGES_DIR --database_path $OUTPUT_DIR/database.db"
echo ""
echo "  2. Or run pipeline directly:"
echo "     ./run_pipeline.sh P4 $OUTPUT_DIR"
echo "     ./run_pipeline.sh P5 $OUTPUT_DIR"
echo "=================================================="
