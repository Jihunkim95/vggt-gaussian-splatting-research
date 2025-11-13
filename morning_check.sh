#!/bin/bash
# morning_check.sh - 아침 프로젝트 상태 확인
# 사용법: ./morning_check.sh

cd /data/vggt-gaussian-splatting-research

echo "=========================================="
echo "🌅 Morning Check - $(date +%Y-%m-%d)"
echo "=========================================="
echo ""

# 1. 실행 중인 실험 확인
echo "🔬 실행 중인 실험:"
RUNNING=$(ps aux | grep -E "(python|run_pipeline)" | grep -v grep | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo "   ✅ $RUNNING 개 프로세스 실행 중"
    ps aux | grep -E "(python|run_pipeline)" | grep -v grep | awk '{print "      PID "$2": "$11" "$12" "$13}' | head -5
else
    echo "   ⭕ 실행 중인 실험 없음"
fi
echo ""

# 2. 어제/오늘 생성된 결과
echo "📊 최근 결과 (어제~오늘):"
YESTERDAY=$(date -d yesterday +%Y%m%d)
TODAY=$(date +%Y%m%d)

RECENT_COUNT=$(find ./results -maxdepth 1 -type d -newermt "yesterday" | wc -l)
if [ $RECENT_COUNT -gt 1 ]; then
    echo "   ✅ ${RECENT_COUNT} 개 새 결과"
    find ./results -maxdepth 1 -type d -newermt "yesterday" | tail -5 | xargs -I {} basename {}
else
    echo "   ⭕ 어제 이후 새 결과 없음"
fi
echo ""

# 3. 최근 완료된 실험 성능 (top 3)
echo "🏆 최근 완료 실험 성능 (Top 3):"
for dir in $(ls -td ./results/P*_*/ 2>/dev/null | head -3); do
    if [ -f "$dir/stats/val_step29999.json" ]; then
        echo "   $(basename $dir)"
        cat "$dir/stats/val_step29999.json" | grep -E '"(psnr|ssim|lpips)"' | head -3 | sed 's/^/      /'
    elif [ -f "$dir/analysis.json" ]; then
        echo "   $(basename $dir)"
        echo "      (COLMAP only - no metrics)"
    fi
done
echo ""

# 4. GPU 상태
echo "🖥️  GPU 상태:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader | \
    awk -F, '{printf "   GPU 사용률: %s | 메모리: %s / %s\n", $1, $2, $3}'
echo ""

# 5. 디스크 용량
echo "💾 디스크 상태:"
df -h /data | tail -1 | awk '{printf "   사용: %s / %s (%s 사용 중)\n", $3, $2, $5}'
du -sh ./results 2>/dev/null | awk '{printf "   results/: %s\n", $1}'
echo ""

# 6. RL 프로젝트 상태
echo "🤖 RL Frame Selector 상태:"
if [ -d "./rl_frame_selector/phase1_surrogate/trained_models" ]; then
    MODEL_COUNT=$(find ./rl_frame_selector/phase1_surrogate/trained_models -name "*.zip" 2>/dev/null | wc -l)
    if [ $MODEL_COUNT -gt 0 ]; then
        echo "   ✅ 학습된 모델: $MODEL_COUNT 개"
        find ./rl_frame_selector/phase1_surrogate/trained_models -name "*.zip" 2>/dev/null | tail -3 | xargs -I {} echo "      $(basename {})"
    else
        echo "   ⭕ 학습된 모델 없음"
    fi
else
    echo "   ⚠️  trained_models/ 디렉토리 없음"
fi
echo ""

# 7. 오늘의 TODO
echo "📋 오늘의 할 일:"
TODAY_WORKFLOW="./docs/workflows/$(date +%Y%m%d)_VGGT-GSplat_WorkFlow.md"
TODAY_TODO="./TODO_$(date +%Y%m%d).md"

if [ -f "$TODAY_WORKFLOW" ]; then
    echo "   ✅ Workflow 문서 존재: $TODAY_WORKFLOW"
elif [ -f "$TODAY_TODO" ]; then
    echo "   📝 TODO 파일 존재: $TODAY_TODO"
    cat "$TODAY_TODO" | grep "\[ \]" | head -3 | sed 's/^/      /'
else
    echo "   ⚠️  오늘의 TODO 파일 없음"
    echo "      → 어제 workflow 확인: ./docs/workflows/$(date -d yesterday +%Y%m%d)_VGGT-GSplat_WorkFlow.md"
fi
echo ""

# 8. 다음 액션 추천
echo "🎯 추천 액션:"
if [ $RUNNING -gt 0 ]; then
    echo "   1. 실행 중인 실험 모니터링"
    echo "      → tail -f ./experiment_logs_$(date +%Y%m%d)_*/[실험명].log"
elif [ $RECENT_COUNT -gt 1 ]; then
    echo "   1. 어제 완료된 결과 분석"
    echo "      → ls -lt ./results/ | head -5"
else
    echo "   1. 새 실험 시작 or RL 학습 시작"
    echo "      → ./run_pipeline.sh P4 [dataset]"
    echo "      → cd rl_frame_selector/phase1_surrogate && python train.py ..."
fi

# RL 프로젝트 상태에 따른 추천
if [ ! -d "./rl_frame_selector/phase1_surrogate/trained_models" ] || [ $MODEL_COUNT -eq 0 ]; then
    echo "   2. RL 프로젝트 DTU Quick Test 시작 (30분)"
    echo "      → cd rl_frame_selector/ && cat ROADMAP.md"
fi

echo ""
echo "=========================================="
echo "✅ Morning Check 완료!"
echo "=========================================="
