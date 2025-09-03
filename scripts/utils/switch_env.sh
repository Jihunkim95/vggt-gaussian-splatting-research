#!/bin/bash

# VGGT + gsplat 환경 전환 스크립트
# 사용법: source switch_env.sh [vggt|gsplat|status]

VGGT_ENV="/workspace/vggt_env"
GSPLAT_ENV="/workspace/gsplat_env"

function show_status() {
    echo "📊 환경 상태 확인"
    echo "===================="
    
    if [[ "$VIRTUAL_ENV" == *"vggt_env"* ]]; then
        echo "🟢 현재 환경: VGGT"
        echo "📍 경로: $VIRTUAL_ENV"
        echo "🔧 주요 패키지:"
        pip list | grep -E "(torch|pycolmap|vggt)" 2>/dev/null || echo "  (패키지 정보 확인 불가)"
    elif [[ "$VIRTUAL_ENV" == *"gsplat_env"* ]]; then
        echo "🟢 현재 환경: gsplat"
        echo "📍 경로: $VIRTUAL_ENV"
        echo "🔧 주요 패키지:"
        pip list | grep -E "(torch|gsplat|pycolmap)" 2>/dev/null || echo "  (패키지 정보 확인 불가)"
    else
        echo "⚫ 현재 환경: 가상환경 미활성화"
    fi
    
    echo ""
    echo "📁 환경 경로:"
    echo "  - VGGT: $VGGT_ENV $([ -d "$VGGT_ENV" ] && echo "✅" || echo "❌")"
    echo "  - gsplat: $GSPLAT_ENV $([ -d "$GSPLAT_ENV" ] && echo "✅" || echo "❌")"
}

function switch_to_vggt() {
    if [ ! -d "$VGGT_ENV" ]; then
        echo "❌ VGGT 환경이 존재하지 않습니다: $VGGT_ENV"
        echo "💡 다음 명령으로 환경을 생성하세요:"
        echo "   python -m venv $VGGT_ENV"
        echo "   source $VGGT_ENV/bin/activate"
        echo "   pip install torch==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121"
        echo "   pip install numpy==1.26.1 pycolmap==0.6.1 ..."
        return 1
    fi
    
    echo "🔄 VGGT 환경으로 전환 중..."
    source "$VGGT_ENV/bin/activate"
    
    # 환경 검증
    if python -c "from vggt.models.vggt import VGGT; print('✅ VGGT 모듈 로드 성공')" 2>/dev/null; then
        echo "✅ VGGT 환경 활성화 완료"
    else
        echo "⚠️  VGGT 환경이 불완전합니다. 패키지 설치를 확인하세요."
    fi
    
    echo "📝 VGGT 사용법:"
    echo "   python /workspace/vggt/create_2m_colmap.py"
}

function switch_to_gsplat() {
    if [ ! -d "$GSPLAT_ENV" ]; then
        echo "❌ gsplat 환경이 존재하지 않습니다: $GSPLAT_ENV"
        echo "💡 다음 명령으로 환경을 생성하세요:"
        echo "   python -m venv $GSPLAT_ENV"
        echo "   source $GSPLAT_ENV/bin/activate"
        echo "   pip install torch==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121"
        echo "   pip install gsplat"
        echo "   cd /workspace/gsplat/examples && pip install -r requirements.txt"
        return 1
    fi
    
    echo "🔄 gsplat 환경으로 전환 중..."
    source "$GSPLAT_ENV/bin/activate"
    
    # 환경 검증
    if python -c "import gsplat; print('✅ gsplat 모듈 로드 성공')" 2>/dev/null; then
        echo "✅ gsplat 환경 활성화 완료"
    else
        echo "⚠️  gsplat 환경이 불완전합니다. 패키지 설치를 확인하세요."
    fi
    
    echo "📝 gsplat 사용법:"
    echo "   cd /workspace/gsplat/examples"
    echo "   python simple_trainer.py default --data-dir /workspace/labsRoom ..."
}

function show_help() {
    echo "🔧 VGGT + gsplat 환경 전환 도구"
    echo "================================"
    echo ""
    echo "사용법: source switch_env.sh [command]"
    echo ""
    echo "명령어:"
    echo "  vggt     - VGGT 환경으로 전환"
    echo "  gsplat   - gsplat 환경으로 전환"
    echo "  status   - 현재 환경 상태 확인"
    echo "  help     - 도움말 표시"
    echo ""
    echo "📋 워크플로우:"
    echo "  1. source switch_env.sh vggt"
    echo "  2. python /workspace/vggt/create_2m_colmap.py"
    echo "  3. source switch_env.sh gsplat"
    echo "  4. cd /workspace/gsplat/examples"
    echo "  5. python simple_trainer.py default --data-dir /workspace/labsRoom ..."
    echo ""
    echo "⚠️  주의: 이 스크립트는 반드시 'source' 명령으로 실행해야 합니다!"
}

# 메인 로직
case "${1:-help}" in
    "vggt")
        switch_to_vggt
        ;;
    "gsplat")
        switch_to_gsplat
        ;;
    "status")
        show_status
        ;;
    "help"|*)
        show_help
        ;;
esac