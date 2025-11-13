#!/bin/bash
# evening_wrap.sh - 저녁 작업 정리
# 사용법: ./evening_wrap.sh

cd /data/vggt-gaussian-splatting-research

echo "=========================================="
echo "🌙 Evening Wrap-up - $(date +%Y-%m-%d)"
echo "=========================================="
echo ""

TODAY=$(date +%Y%m%d)
TODAY_WORKFLOW="./docs/workflows/${TODAY}_VGGT-GSplat_WorkFlow.md"

# 1. 오늘 생성된 결과 확인
echo "📊 오늘 생성된 결과:"
TODAY_RESULTS=$(find ./results -maxdepth 1 -type d -newermt "today" | tail -n +2)
if [ -n "$TODAY_RESULTS" ]; then
    RESULT_COUNT=$(echo "$TODAY_RESULTS" | wc -l)
    echo "   ✅ $RESULT_COUNT 개 결과 생성됨"
    echo "$TODAY_RESULTS" | xargs -I {} basename {} | sed 's/^/      - /'
else
    echo "   ⭕ 오늘 생성된 결과 없음"
fi
echo ""

# 2. 오늘 수정된 코드 파일
echo "📝 오늘 수정된 파일 (코드/문서):"
MODIFIED_FILES=$(find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" \) -newermt "today" -not -path "*/.*" -not -path "*/results/*" -not -path "*/env/*" -not -path "*/libs/*" | head -10)
if [ -n "$MODIFIED_FILES" ]; then
    MODIFIED_COUNT=$(echo "$MODIFIED_FILES" | wc -l)
    echo "   ✅ $MODIFIED_COUNT 개 파일 수정"
    echo "$MODIFIED_FILES" | sed 's|^\./||' | sed 's/^/      - /'
else
    echo "   ⭕ 수정된 파일 없음"
fi
echo ""

# 3. RL 프로젝트 진행 상황
echo "🤖 RL Frame Selector 오늘 진행:"
RL_MODELS=$(find ./rl_frame_selector -name "*.zip" -newermt "today" 2>/dev/null)
RL_LOGS=$(find ./rl_frame_selector/phase1_surrogate/logs -type f -newermt "today" 2>/dev/null | wc -l)

if [ -n "$RL_MODELS" ] || [ $RL_LOGS -gt 0 ]; then
    echo "   ✅ 활동 있음"
    [ -n "$RL_MODELS" ] && echo "$RL_MODELS" | xargs -I {} echo "      - 모델: $(basename {})"
    [ $RL_LOGS -gt 0 ] && echo "      - 학습 로그: $RL_LOGS 개 파일"
else
    echo "   ⭕ 오늘 활동 없음"
fi
echo ""

# 4. 실행 중인 작업 확인
echo "🔬 현재 실행 중인 작업:"
RUNNING=$(ps aux | grep -E "(python|run_pipeline)" | grep -v grep | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo "   ⚠️  $RUNNING 개 프로세스 실행 중 (백그라운드)"
    ps aux | grep -E "(python|run_pipeline)" | grep -v grep | awk '{print "      PID "$2": "$11" "$12" "$13}' | head -5
    echo ""
    echo "   💡 내일 아침 결과 확인 필요!"
else
    echo "   ✅ 실행 중인 작업 없음"
fi
echo ""

# 5. 오늘의 Workflow 문서 확인
echo "📋 오늘의 Workflow 문서:"
if [ -f "$TODAY_WORKFLOW" ]; then
    echo "   ✅ Workflow 문서 이미 작성됨: $TODAY_WORKFLOW"
    COMPLETED_COUNT=$(grep -c "\[x\]" "$TODAY_WORKFLOW" 2>/dev/null || echo 0)
    PENDING_COUNT=$(grep -c "\[ \]" "$TODAY_WORKFLOW" 2>/dev/null || echo 0)
    echo "      완료: $COMPLETED_COUNT 개 | 미완료: $PENDING_COUNT 개"
else
    echo "   ⚠️  Workflow 문서 미작성"
    echo ""
    echo "   📝 Workflow 템플릿 생성 중..."

    # Workflow 템플릿 자동 생성
    cat > "$TODAY_WORKFLOW" <<'EOF'
# 📋 VGGT-GSplat Workflow - YYYY-MM-DD

**날짜**: YYYY년 MM월 DD일
**작업 시간**: X시간
**주제**: [오늘의 주요 작업]

---

## 📌 오늘의 작업 요약

### 1. [작업 1 제목]
- **목적**: [왜 이 작업을 했는가?]
- **수행 내용**:
  - [구체적으로 무엇을 했는가?]
- **결과**:
  - [결과물, 성능, 관찰 사항]
- **소요 시간**: X시간

---

## 📊 실험 결과

### 실험 1: [실험명]
**설정**:
- 파이프라인: P1/P4/P5
- 데이터셋: [데이터셋명]
- 파라미터: [주요 파라미터]

**결과**:
- PSNR: XX.XX
- SSIM: 0.XX
- LPIPS: 0.XX
- 소요 시간: XX분

**관찰**:
- [주요 발견사항]

---

## 🐛 문제 & 해결

### 문제 1: [문제 제목]
- **상황**: [언제/어떻게 발생했는가?]
- **원인**: [분석 결과]
- **해결**: [어떻게 해결했는가?]
- **파일**: [수정한 파일명:라인]

---

## ✅ 완료 항목
- [x] [완료한 작업 1]
- [x] [완료한 작업 2]

## ⏳ 진행 중
- [ ] [진행 중인 작업] (XX% 완료)

## 📋 내일 할 일
- [ ] [작업 1] (우선순위 1)
- [ ] [작업 2]
- [ ] [작업 3]

---

## 💡 아이디어 & 메모
- [떠오른 아이디어나 나중에 시도해볼 것]

---

**작업 시간 분석**:
- 실험 실행: Xh
- 코드 작성: Xh
- 디버깅: Xh
- 문서화: Xh
EOF

    # 날짜 치환
    sed -i "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" "$TODAY_WORKFLOW"
    sed -i "s/YYYY년 MM월 DD일/$(date +%Y년\ %m월\ %d일)/g" "$TODAY_WORKFLOW"

    echo "   ✅ 템플릿 생성 완료: $TODAY_WORKFLOW"
    echo "      → 에디터로 열어서 오늘 작업 내용 작성"
fi
echo ""

# 6. 내일 TODO 확인/생성
echo "📅 내일 준비:"
TOMORROW_TODO="./TODO_$(date -d tomorrow +%Y%m%d).md"
if [ -f "$TOMORROW_TODO" ]; then
    echo "   ✅ 내일 TODO 이미 작성됨: $TOMORROW_TODO"
else
    echo "   ⚠️  내일 TODO 미작성"
    echo ""
    echo "   📝 내일 TODO 템플릿 생성 중..."

    cat > "$TOMORROW_TODO" <<EOF
# TODO - $(date -d tomorrow +%Y-%m-%d)

## Priority 1 (Must Do)
- [ ] [작업 1] - 예상: Xh
- [ ] [작업 2]

## Priority 2 (Should Do)
- [ ] [작업 3]

## 실험 큐
- [ ] [실험 1] - 예상: Xh

## 메모
- [내일 참고할 사항]
EOF

    echo "   ✅ 템플릿 생성 완료: $TOMORROW_TODO"
fi
echo ""

# 7. 디스크 정리 필요 여부
echo "💾 디스크 관리:"
DISK_USAGE=$(df -h /data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "   ⚠️  디스크 사용률 높음: ${DISK_USAGE}%"
    echo "      → 임시 파일 정리 고려"
    echo "      → rm -rf ./temp_work_*  # (진행 중 작업 확인 후)"
elif [ $DISK_USAGE -gt 70 ]; then
    echo "   💡 디스크 사용률: ${DISK_USAGE}% (주의)"
else
    echo "   ✅ 디스크 여유 충분: ${DISK_USAGE}% 사용 중"
fi
echo ""

# 8. Git 상태
echo "📦 Git 상태:"
MODIFIED=$(git status --porcelain | grep "^ M" | wc -l)
UNTRACKED=$(git status --porcelain | grep "^??" | wc -l)
STAGED=$(git status --porcelain | grep "^M" | wc -l)

if [ $MODIFIED -gt 0 ] || [ $UNTRACKED -gt 0 ] || [ $STAGED -gt 0 ]; then
    echo "   💡 변경사항 있음:"
    [ $STAGED -gt 0 ] && echo "      Staged: $STAGED 개 파일"
    [ $MODIFIED -gt 0 ] && echo "      Modified: $MODIFIED 개 파일"
    [ $UNTRACKED -gt 0 ] && echo "      Untracked: $UNTRACKED 개 파일"
    echo ""
    echo "   → git status 로 확인 후 커밋 고려"
else
    echo "   ✅ 변경사항 없음 (깔끔함)"
fi
echo ""

# 9. 요약 및 추천
echo "=========================================="
echo "✅ Evening Wrap-up 완료!"
echo "=========================================="
echo ""
echo "🎯 마무리 체크리스트:"
if [ ! -f "$TODAY_WORKFLOW" ] || [ $(wc -l < "$TODAY_WORKFLOW") -lt 50 ]; then
    echo "   [ ] Workflow 문서 작성: $TODAY_WORKFLOW"
fi
if [ ! -f "$TOMORROW_TODO" ]; then
    echo "   [ ] 내일 TODO 작성: $TOMORROW_TODO"
fi
if [ $MODIFIED -gt 0 ] || [ $UNTRACKED -gt 0 ]; then
    echo "   [ ] Git 변경사항 커밋 고려"
fi
if [ $RUNNING -gt 0 ]; then
    echo "   [ ] 백그라운드 작업 내일 확인 필요"
fi
echo ""
echo "🌙 수고하셨습니다! 내일 ./morning_check.sh로 시작하세요."
echo ""
