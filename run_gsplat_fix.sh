#!/bin/bash
# gsplat 환경 수정 스크립트

echo "🔧 Activating gsplat environment and fixing dependencies..."

# gsplat 환경 활성화
source /workspace/envs/gsplat_env/bin/activate

# 환경 수정 스크립트 실행
python /workspace/fix_gsplat_env.py

echo "✅ Environment fix completed!"