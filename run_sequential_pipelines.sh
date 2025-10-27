#!/bin/bash

# 순차 파이프라인 실행 스크립트
# 각 파이프라인이 완료될 때까지 대기한 후 다음 파이프라인 실행

set -e  # 에러 발생 시 중단

# GCC-12 환경 변수 설정
export CC=/usr/bin/gcc-12
export CXX=/usr/bin/g++-12
export CUDAHOSTCXX=/usr/bin/g++-12

echo "=========================================="
echo "순차 파이프라인 실행 시작"
echo "=========================================="
echo ""

# 1. P1 on cGameController_v2
echo "▶ [1/4] P1 파이프라인 실행 중 (cGameController_v2)..."
./run_pipeline.sh P1 ./datasets/custom/cGameController_v2
echo "✅ [1/4] P1 완료 (cGameController_v2)"
echo ""

# 2. P1 on scan1_standard
echo "▶ [2/4] P1 파이프라인 실행 중 (DTU/scan1_standard)..."
./run_pipeline.sh P1 ./datasets/DTU/scan1_standard
echo "✅ [2/4] P1 완료 (DTU/scan1_standard)"
echo ""

# 3. P4 on scan1_standard
echo "▶ [3/4] P4 파이프라인 실행 중 (DTU/scan1_standard)..."
./run_pipeline.sh P4 ./datasets/DTU/scan1_standard
echo "✅ [3/4] P4 완료 (DTU/scan1_standard)"
echo ""

# 4. P5 on scan1_standard
echo "▶ [4/4] P5 파이프라인 실행 중 (DTU/scan1_standard)..."
./run_pipeline.sh P5 ./datasets/DTU/scan1_standard
echo "✅ [4/4] P5 완료 (DTU/scan1_standard)"
echo ""

echo "=========================================="
echo "모든 파이프라인 실행 완료!"
echo "=========================================="
echo ""
echo "실행된 파이프라인:"
echo "  1. P1 - cGameController_v2"
echo "  2. P1 - DTU/scan1_standard"
echo "  3. P4 - DTU/scan1_standard"
echo "  4. P5 - DTU/scan1_standard"
echo ""
echo "결과 확인:"
echo "  ls -la ./results/"
