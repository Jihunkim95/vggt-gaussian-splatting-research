#!/bin/bash
# ============================================================================
# VGGT-Gaussian Splatting Research Environment Setup
# H100 GPU 환경 자동 설정 스크립트
# ============================================================================

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 프로젝트 루트 확인
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

log_info "VGGT-Gaussian Splatting 환경 설정 시작"
log_info "프로젝트 루트: $PROJECT_ROOT"

# ============================================================================
# 1. 시스템 요구사항 확인
# ============================================================================
log_info "시스템 요구사항 확인 중..."

# GPU 확인
if ! command -v nvidia-smi &> /dev/null; then
    log_error "NVIDIA GPU 드라이버가 설치되지 않았습니다."
    exit 1
fi

GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
log_success "GPU: $GPU_NAME"

# CUDA 확인
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | sed 's/,//')
    log_success "CUDA: $CUDA_VERSION"
else
    log_warning "nvcc를 찾을 수 없습니다. CUDA Toolkit을 설치합니다..."
fi

# Python 확인
if ! command -v python3 &> /dev/null; then
    log_error "Python 3가 설치되지 않았습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log_success "$PYTHON_VERSION"

# ============================================================================
# 2. 시스템 패키지 설치 (COLMAP, 빌드 도구)
# ============================================================================
log_info "시스템 패키지 설치 중..."

# COLMAP 설치
if ! command -v colmap &> /dev/null; then
    log_info "COLMAP 설치 중... (약 166MB, 시간이 걸릴 수 있습니다)"
    sudo apt-get update -qq
    sudo apt-get install -y -qq colmap > /dev/null 2>&1
    log_success "COLMAP 3.7 설치 완료"
else
    COLMAP_VERSION=$(colmap -h 2>&1 | grep "COLMAP" | head -1 || echo "알 수 없음")
    log_success "COLMAP 이미 설치됨: $COLMAP_VERSION"
fi

# 빌드 필수 도구
log_info "빌드 도구 설치 중..."
sudo apt-get install -y -qq build-essential git wget > /dev/null 2>&1
log_success "빌드 도구 설치 완료"

# ============================================================================
# 3. CUDA Toolkit 12.1 설치 (fused-ssim 컴파일용)
# ============================================================================
CUDA_HOME="/opt/cuda-12.1"

if [ ! -d "$CUDA_HOME" ]; then
    log_info "CUDA Toolkit 12.1 설치 중... (약 3GB, 10분 소요)"

    CUDA_INSTALLER="cuda_12.1.0_530.30.02_linux.run"

    if [ ! -f "$CUDA_INSTALLER" ]; then
        log_info "CUDA Toolkit 다운로드 중..."
        wget -q --show-progress \
            https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/$CUDA_INSTALLER
    fi

    log_info "CUDA Toolkit 설치 중... (sudo 권한 필요)"
    sudo sh $CUDA_INSTALLER --silent --toolkit --toolkitpath=$CUDA_HOME

    rm -f $CUDA_INSTALLER
    log_success "CUDA Toolkit 12.1 설치 완료: $CUDA_HOME"
else
    log_success "CUDA Toolkit 12.1 이미 설치됨: $CUDA_HOME"
fi

# CUDA 환경변수 설정
export CUDA_HOME=$CUDA_HOME
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# ============================================================================
# 4. VGGT 환경 구축
# ============================================================================
VGGT_ENV="$PROJECT_ROOT/env/vggt_env"

log_info "VGGT 환경 구축 중: $VGGT_ENV"

if [ ! -d "$VGGT_ENV" ]; then
    log_info "vggt_env 가상환경 생성 중..."
    python3 -m venv "$VGGT_ENV"
    log_success "vggt_env 생성 완료"
else
    log_success "vggt_env 이미 존재"
fi

# VGGT 환경 활성화 및 패키지 설치
source "$VGGT_ENV/bin/activate"

log_info "VGGT 패키지 설치 중... (약 5분 소요)"

# PyTorch 생태계
pip install -q torch==2.8.0 torchvision==0.23.0
pip install -q transformers==4.56.1 accelerate==1.10.1

# VGGT 핵심 라이브러리
pip install -q pycolmap==3.10.0  # CRITICAL: API 호환성
pip install -q einops==0.8.1 kornia==0.8.1 trimesh==4.8.1

# 설정 관리
pip install -q hydra-core==1.3.2 omegaconf==2.3.0

# 이미지 처리
pip install -q opencv-python==4.12.0.88 pillow==11.3.0

# Hugging Face
pip install -q huggingface-hub==0.35.0 safetensors==0.6.2 tokenizers==0.22.0

# LightGlue
pip install -q git+https://github.com/cvg/LightGlue.git

# 유틸리티
pip install -q matplotlib==3.10.6 tqdm==4.67.1 requests==2.32.5 PyYAML==6.0.2

log_success "VGGT 환경 설치 완료"

deactivate

# ============================================================================
# 5. gsplat 환경 구축
# ============================================================================
GSPLAT_ENV="$PROJECT_ROOT/env/gsplat_env"

log_info "gsplat 환경 구축 중: $GSPLAT_ENV"

if [ ! -d "$GSPLAT_ENV" ]; then
    log_info "gsplat_env 가상환경 생성 중..."
    python3 -m venv "$GSPLAT_ENV"
    log_success "gsplat_env 생성 완료"
else
    log_success "gsplat_env 이미 존재"
fi

# gsplat 환경 활성화 및 패키지 설치
source "$GSPLAT_ENV/bin/activate"

log_info "gsplat 패키지 설치 중... (약 10분 소요)"

# H100 환경변수 설정 (중요!)
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH

# PyTorch (CUDA 12.1)
pip install -q torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121
pip install -q torchmetrics==1.8.2

# 핵심 Gaussian Splatting
pip install -q gsplat==1.5.3

# COLMAP (gsplat 최적화 버전)
pip install -q git+https://github.com/rmbrualla/pycolmap@cc7ea4b7301720ac29287dbe450952511b32125e

# 수치 계산
pip install -q numpy==1.26.4 scipy==1.15.3 scikit-learn==1.7.2

# 이미지 처리 (headless - libGL 문제 해결)
pip uninstall -y opencv-python > /dev/null 2>&1 || true
pip install -q opencv-python-headless==4.12.0.88
pip install -q pillow==11.3.0 imageio==2.37.0 scikit-image==0.25.2

# 3D 처리
pip install -q trimesh==4.8.1 manifold3d==3.2.1 shapely==2.1.1

# NeRF 뷰어
pip install -q git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787
pip install -q viser==1.0.10

# 신경 렌더링 메트릭
log_info "fused-ssim 설치 중... (CUDA 컴파일, 약 2분 소요)"
pip install -q --no-build-isolation "git+https://github.com/rahul-goel/fused-ssim@328dc9836f513d00c4b5bc38fe30478b4435cbb5"
pip install -q lpips==0.1.4

# CLI & 유틸리티
pip install -q tyro==0.9.31 rich==14.1.0 colorlog==6.9.0
pip install -q tensorboard==2.20.0 tqdm==4.67.1

# 필수 패키지 (run_pipeline.sh에서 사용)
pip install -q imageio tqdm tyro

log_success "gsplat 환경 설치 완료"

deactivate

# ============================================================================
# 6. 환경변수 설정 파일 생성
# ============================================================================
log_info "환경변수 설정 파일 생성 중..."

cat > "$PROJECT_ROOT/env/setup_h100.sh" << 'EOF'
#!/bin/bash
# H100 GPU 환경변수 설정

export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/opt/cuda-12.1/lib64:$LD_LIBRARY_PATH
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TMPDIR=/data/tmp

echo "✅ H100 GPU 환경변수 설정 완료"
echo "   TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCH_LIST"
echo "   CUDA_HOME=$CUDA_HOME"
EOF

chmod +x "$PROJECT_ROOT/env/setup_h100.sh"
log_success "환경변수 설정 파일 생성: env/setup_h100.sh"

# ============================================================================
# 7. 검증
# ============================================================================
log_info "환경 검증 중..."

# VGGT 환경 검증
source "$VGGT_ENV/bin/activate"
VGGT_TORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
VGGT_PYCOLMAP_VERSION=$(python -c "import pycolmap; print(pycolmap.__version__)")
deactivate

# gsplat 환경 검증
source "$GSPLAT_ENV/bin/activate"
GSPLAT_TORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
GSPLAT_VERSION=$(python -c "import gsplat; print(gsplat.__version__)")
deactivate

log_success "VGGT 환경: PyTorch $VGGT_TORCH_VERSION, pycolmap $VGGT_PYCOLMAP_VERSION"
log_success "gsplat 환경: PyTorch $GSPLAT_TORCH_VERSION, gsplat $GSPLAT_VERSION"

# ============================================================================
# 8. 완료
# ============================================================================
echo ""
echo "============================================================================"
log_success "환경 설정 완료!"
echo "============================================================================"
echo ""
echo "📋 설치된 환경:"
echo "   • VGGT 환경: $VGGT_ENV"
echo "   • gsplat 환경: $GSPLAT_ENV"
echo "   • COLMAP: $(which colmap)"
echo "   • CUDA Toolkit: $CUDA_HOME"
echo ""
echo "🚀 다음 단계:"
echo "   1. 데이터셋 준비:"
echo "      ./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan1_train"
echo ""
echo "   2. 파이프라인 실행:"
echo "      ./run_pipeline.sh P1 ./datasets/DTU/scan1_standard"
echo "      ./run_pipeline.sh P5 ./datasets/DTU/scan1_standard"
echo ""
echo "   3. H100 환경변수 활성화 (필요시):"
echo "      source env/setup_h100.sh"
echo ""
echo "============================================================================"
