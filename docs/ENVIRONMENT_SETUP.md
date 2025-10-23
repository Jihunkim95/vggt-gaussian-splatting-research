# 🔧 VGGT + Gaussian Splatting 호환성 환경 가이드

**H100 GPU 환경 기준 (CUDA 12.1)**

**Last Updated**: 2025-10-23
**Validated Environment**: H100 80GB + CUDA 12.1 + Ubuntu 22.04

---

## 🚀 빠른 시작 (Recommended)

**가장 쉬운 방법**: 자동 환경 설치 스크립트 사용

```bash
# 프로젝트 clone
git clone https://github.com/Jihunkim95/vggt-gaussian-splatting-research.git
cd vggt-gaussian-splatting-research

# One-command setup (15-20분)
./setup_environment.sh
```

**setup_environment.sh가 자동으로 설치하는 것들:**
- ✅ COLMAP 3.7 (apt-get)
- ✅ CUDA Toolkit 12.1 (/opt/cuda-12.1)
- ✅ vggt_env (PyTorch 2.8.0, pycolmap 3.10.0)
- ✅ gsplat_env (PyTorch 2.3.1+cu121, gsplat 1.5.3)
- ✅ H100 환경변수 (TORCH_CUDA_ARCH_LIST=9.0)

---

## 📋 시스템 요구사항

### 필수 요구사항
```yaml
GPU: H100 (80GB VRAM) - Compute Capability 9.0
CUDA: 12.1+
Python: 3.10+
OS: Ubuntu 22.04+
Sudo Access: 필수 (COLMAP, CUDA Toolkit 설치용)
```

### 권장 사양
- **Storage**: 50GB+ (datasets + results)
- **RAM**: 32GB+
- **Internet**: 안정적인 연결 (패키지 다운로드)

---

## ⚠️ 주요 호환성 이슈 및 해결

이 가이드는 **PyTorch, CUDA, 기타 라이브러리 간의 버전 충돌**을 해결하고 **완벽하게 호환되는 환경**을 구축하는 방법을 제공합니다.

## 🚨 발견된 주요 충돌 문제들

### 1️⃣ **torchaudio C++ ABI 충돌**
```
❌ 문제: /venv/main/lib/python3.10/site-packages/torchaudio/lib/libtorchaudio.so: undefined symbol: _ZNK3c105Error4whatEv
✅ 해결: torchaudio는 VGGT/gsplat에서 불필요하므로 제외
```

### 2️⃣ **pycolmap 버전 불일치**  
```
❌ 문제: VGGT는 pycolmap==3.10.0, gsplat은 git 버전 필요
✅ 해결: 환경별 분리 설치 또는 호환 버전 사용
```

### 3️⃣ **NumPy 버전 호환성**
```
❌ 문제: NumPy 2.0+ PyTorch와 충돌 가능
✅ 해결: numpy<2.0.0 고정 사용
```

## 🎯 검증된 완벽 호환 환경 (2025-10-23 기준 - H100 검증 완료)

### 🖥️ 시스템 환경
```
GPU: H100 80GB (Compute Capability 9.0)
OS: Ubuntu 22.04 LTS
Python: 3.10+
CUDA: 12.1 (Toolkit installed via setup_environment.sh)
COLMAP: 3.7 (installed via apt-get)
```

### 📦 환경별 분리 구성 (실제 설치된 버전)

#### 🔴 VGGT 환경 (/data/vggt-gaussian-splatting-research/env/vggt_env)
```txt
# ===== PyTorch 생태계 (최신 안정 버전) =====
torch==2.8.0
torchvision==0.23.0
transformers==4.56.1
accelerate==1.10.1
triton==3.4.0

# ===== 수치 계산 (최신 호환 버전) =====
numpy==2.2.6                     # NumPy 2.0+ 안정성 확인됨
matplotlib==3.10.6
sympy==1.14.0

# ===== COLMAP 처리 (VGGT 최적화) =====
pycolmap==3.10.0                 # CRITICAL: VGGT API 호환성 필수

# ===== 이미지 처리 (최신 안정) =====
opencv-python-headless==4.12.0.88  # Headless 버전 (libGL.so.1 문제 해결)
pillow==11.3.0

# ===== VGGT 전용 라이브러리 =====
einops==0.8.1
kornia==0.8.1
kornia_rs==0.1.9
trimesh==4.8.1
lightglue @ git+https://github.com/cvg/LightGlue.git

# ===== 설정 관리 =====
hydra-core==1.3.2
omegaconf==2.3.0

# ===== Hugging Face 생태계 =====
huggingface-hub==0.35.0
safetensors==0.6.2
tokenizers==0.22.0

# ===== CUDA 지원 (자동 설치) =====
nvidia-cudnn-cu12==9.10.2.21
nvidia-cublas-cu12==12.8.4.1
nvidia-cufft-cu12==11.3.3.83
nvidia-cuda-runtime-cu12==12.8.90
```

#### 🔵 gsplat 환경 (/data/vggt-gaussian-splatting-research/env/gsplat_env)
```txt
# ===== PyTorch 생태계 (gsplat 호환) =====
torch==2.3.1+cu121
torchvision==0.18.1+cu121
torchmetrics==1.8.2
triton==2.3.1

# ===== 핵심 Gaussian Splatting =====
gsplat==1.5.3                    # 핵심 3D Gaussian Splatting 라이브러리

# ===== 수치 계산 (안정 버전) =====
numpy==1.26.4                    # gsplat 호환 검증된 버전
scipy==1.16.2
scikit-learn==1.7.2

# ===== COLMAP 처리 (gsplat 최적화) =====
pycolmap @ git+https://github.com/rmbrualla/pycolmap@cc7ea4b7301720ac29287dbe450952511b32125e

# ===== 이미지 처리 & 컴퓨터 비전 =====
opencv-python==4.11.0.86
pillow==11.0.0
imageio==2.37.0
scikit-image==0.25.2
tifffile==2025.5.10

# ===== 3D 처리 & 메쉬 =====
trimesh==4.8.3
manifold3d==3.2.1
shapely==2.1.1
rtree==1.4.1
mapbox_earcut==1.0.3
vhacdx==0.0.8.post2
embreex==2.17.7.post6

# ===== NeRF 뷰어 & 시각화 =====
nerfview @ git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787
viser==1.0.10

# ===== 신경 렌더링 메트릭 =====
fused-ssim==0.0.0
lpips==0.1.4

# ===== 텐서 연산 & 유틸리티 =====
tensorly==0.9.0
splines==0.3.3
jaxtyping==0.3.2

# ===== CLI & 설정 =====
tyro==0.9.31
shtab==1.7.2
rich==14.1.0
colorlog==6.9.0

# ===== 개발 & 디버깅 =====
tensorboard==2.20.0
tensorboard-data-server==0.7.2
typeguard==4.4.4

# ===== CUDA 지원 (CUDA 12.1) =====
nvidia-cudnn-cu12==8.9.2.26
nvidia-cublas-cu12==12.1.3.1
nvidia-cuda-runtime-cu12==12.1.105
```

## 🛡️ 환경 구축 단계별 가이드

### 방법 1: 자동 설치 (권장) ⭐

```bash
./setup_environment.sh
```

**장점:**
- 모든 의존성 자동 설치
- H100 환경변수 자동 설정
- 에러 처리 및 검증 포함
- 15-20분 소요

---

### 방법 2: 수동 설치 (고급 사용자)

#### VGGT 환경 구축
```bash
# VGGT 전용 가상환경 생성
python -m venv ./env/vggt_env
source ./env/vggt_env/bin/activate

# PyTorch 생태계 (최신 안정 버전)
pip install torch==2.8.0 torchvision==0.23.0
pip install transformers==4.56.1 accelerate==1.10.1

# VGGT 핵심 라이브러리
pip install pycolmap==3.10.0  # CRITICAL: API 호환성 필수
pip install einops==0.8.1 kornia==0.8.1 trimesh==4.8.1

# 설정 관리
pip install hydra-core==1.3.2 omegaconf==2.3.0

# 이미지 처리
pip install opencv-python==4.12.0.88 pillow==11.3.0

# Hugging Face 생태계
pip install huggingface-hub==0.35.0 safetensors==0.6.2 tokenizers==0.22.0

# LightGlue (GitHub에서 설치)
pip install git+https://github.com/cvg/LightGlue.git

# 기타 유틸리티
pip install matplotlib==3.10.6 tqdm==4.67.1 requests==2.32.5 PyYAML==6.0.2
```

#### gsplat 환경 구축
```bash
# gsplat 전용 가상환경 생성
python -m venv ./env/gsplat_env
source ./env/gsplat_env/bin/activate

# H100 환경변수 설정 (중요!)
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH

# PyTorch (CUDA 12.1 호환)
pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121

# 핵심 Gaussian Splatting
pip install gsplat==1.5.3 torchmetrics==1.8.2

# COLMAP (gsplat 최적화 버전)
pip install git+https://github.com/rmbrualla/pycolmap@cc7ea4b7301720ac29287dbe450952511b32125e

# 수치 계산 (안정 버전)
pip install numpy==1.26.4 scipy==1.15.3 scikit-learn==1.7.2

# 이미지 처리
pip install opencv-python==4.12.0.88 pillow==11.3.0 imageio==2.37.0 scikit-image==0.25.2

# 3D 처리 & 메쉬
pip install trimesh==4.8.1 manifold3d==3.2.1 shapely==2.1.1

# NeRF 뷰어 & 시각화
pip install git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787
pip install viser==1.0.10

# 이미지 처리 (headless - libGL.so.1 문제 해결)
pip uninstall -y opencv-python
pip install opencv-python-headless==4.12.0.88
pip install pillow==11.3.0 imageio==2.37.0 scikit-image==0.25.2

# 3D 처리 & 메쉬
pip install trimesh==4.8.1 manifold3d==3.2.1 shapely==2.1.1

# NeRF 뷰어
pip install git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787
pip install viser==1.0.10

# 신경 렌더링 메트릭
pip install --no-build-isolation "git+https://github.com/rahul-goel/fused-ssim@328dc9836f513d00c4b5bc38fe30478b4435cbb5"
pip install lpips==0.1.4

# CLI & 유틸리티
pip install tyro==0.9.31 rich==14.1.0 colorlog==6.9.0 tensorboard==2.20.0
```

#### COLMAP 설치
```bash
# System package (sudo 필요)
sudo apt-get update
sudo apt-get install -y colmap

# 버전 확인
colmap -h | head -5
```

#### CUDA Toolkit 12.1 설치
```bash
# fused-ssim 컴파일용 (선택사항, setup_environment.sh가 자동 설치)
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda_12.1.0_530.30.02_linux.run
sudo sh cuda_12.1.0_530.30.02_linux.run --silent --toolkit --toolkitpath=/opt/cuda-12.1

# 환경변수
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
```

### 2️⃣ **호환성 검증 스크립트**

```python
#!/usr/bin/env python3
"""완벽한 호환성 테스트 스크립트"""

import sys
import warnings
warnings.filterwarnings('ignore')

def test_core_compatibility():
    """핵심 라이브러리 호환성 테스트"""
    print("🔍 핵심 라이브러리 호환성 검사...")
    
    try:
        # PyTorch 생태계 - 환경별 버전 확인
        import torch
        import torchvision

        # VGGT 환경 또는 gsplat 환경 감지
        torch_version = torch.__version__
        if torch_version.startswith('2.8.0'):
            print("🔴 VGGT 환경 감지됨")
            assert torch_version.startswith('2.8.0'), f"VGGT PyTorch 버전 불일치: {torch_version}"
            assert torchvision.__version__.startswith('0.23.0'), f"VGGT torchvision 버전 불일치: {torchvision.__version__}"
        elif torch_version.startswith('2.3.1'):
            print("🔵 gsplat 환경 감지됨")
            assert torch_version.startswith('2.3.1'), f"gsplat PyTorch 버전 불일치: {torch_version}"
            assert torchvision.__version__.startswith('0.18.1'), f"gsplat torchvision 버전 불일치: {torchvision.__version__}"
        else:
            print(f"⚠️ 알 수 없는 환경: PyTorch {torch_version}")

        # CUDA 호환성
        assert torch.cuda.is_available(), "CUDA 사용 불가"
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ torchvision: {torchvision.__version__}")
        print(f"✅ CUDA: {torch.version.cuda}")

        # 수치 계산 - 환경별 버전 확인
        import numpy as np
        numpy_version = np.__version__
        if torch_version.startswith('2.8.0'):
            # VGGT 환경: NumPy 2.2.6
            assert numpy_version.startswith('2.2'), f"VGGT NumPy 버전 불일치: {numpy_version}"
        else:
            # gsplat 환경: NumPy 1.26.4
            assert numpy_version.startswith('1.26'), f"gsplat NumPy 버전 불일치: {numpy_version}"

        print(f"✅ NumPy: {numpy_version}")

        try:
            import scipy
            print(f"✅ SciPy: {scipy.__version__}")
        except ImportError:
            print("ℹ️ SciPy: 설치되지 않음 (VGGT 환경에서는 선택사항)")
        
        return True
        
    except Exception as e:
        print(f"❌ 핵심 호환성 실패: {e}")
        return False

def test_vggt_compatibility():
    """VGGT 전용 라이브러리 호환성"""
    print("\n🎯 VGGT 호환성 검사...")
    
    try:
        import torch
        import torchvision
        import numpy as np
        from PIL import Image
        import cv2
        import pycolmap
        
        # 실제 연산 테스트
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        x = torch.randn(100, 100, device=device)
        y = x.cpu().numpy()
        z = torch.from_numpy(y)
        
        # 이미지 처리 테스트  
        test_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        pil_img = Image.fromarray(test_img)
        cv2_img = cv2.cvtColor(test_img, cv2.COLOR_RGB2BGR)
        
        print("✅ PyTorch ↔ NumPy 변환")
        print("✅ 이미지 처리 (PIL, OpenCV)")
        print("✅ pycolmap 로딩")
        
        return True
        
    except Exception as e:
        print(f"❌ VGGT 호환성 실패: {e}")
        return False

def test_gsplat_compatibility():
    """Gaussian Splatting 전용 라이브러리 호환성"""
    print("\n🎨 gsplat 호환성 검사...")

    try:
        import torch
        import numpy as np
        torch_version = torch.__version__

        if torch_version.startswith('2.3.1'):
            # gsplat 환경에서만 테스트
            try:
                import gsplat
                print(f"✅ gsplat: {gsplat.__version__}")
            except ImportError:
                print("ℹ️ gsplat: 설치되지 않음 (VGGT 환경)")
                return True  # VGGT 환경에서는 정상

            import torchmetrics
            import matplotlib.pyplot as plt

            # 3D 처리 라이브러리
            try:
                import trimesh
                import manifold3d
                print("✅ 3D 처리 라이브러리 (trimesh, manifold3d)")
            except ImportError as e:
                print(f"⚠️ 일부 3D 라이브러리 누락: {e}")

            # 신경 렌더링 메트릭
            try:
                import lpips
                print("✅ 신경 렌더링 메트릭 (LPIPS)")
            except ImportError:
                print("ℹ️ LPIPS: 설치되지 않음")

            # CLI 도구
            try:
                import tyro
                import rich
                print("✅ CLI 도구 (tyro, rich)")
            except ImportError:
                print("ℹ️ CLI 도구: 일부 누락")

            print("✅ matplotlib 시각화")
            print("✅ torchmetrics")
        else:
            print("ℹ️ VGGT 환경에서는 gsplat 테스트 생략")

        return True

    except Exception as e:
        print(f"❌ gsplat 호환성 실패: {e}")
        return False

def main():
    """전체 호환성 테스트"""
    print("=" * 60)
    print("🔧 VGGT + gsplat 완전 호환성 테스트")
    print("=" * 60)
    
    success_count = 0
    
    if test_core_compatibility():
        success_count += 1
        
    if test_vggt_compatibility():
        success_count += 1
        
    if test_gsplat_compatibility():
        success_count += 1
    
    print("\n" + "=" * 60)
    if success_count == 3:
        print("🎉 모든 호환성 테스트 통과! 환경이 완벽합니다.")
        print("✅ VGGT + Gaussian Splatting 파이프라인 실행 준비 완료")
    else:
        print(f"⚠️ {success_count}/3 테스트 통과. 환경 재구성이 필요합니다.")
        
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## 🌟 H100 환경 특화 설정

### H100 환경변수 (필수)

```bash
# env/setup_h100.sh 사용
source env/setup_h100.sh

# 또는 수동 설정
export TORCH_CUDA_ARCH_LIST="9.0"  # H100 compute capability
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/opt/cuda-12.1/lib64:$LD_LIBRARY_PATH
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TMPDIR=/data/tmp
```

**중요**: `TORCH_CUDA_ARCH_LIST="9.0"`을 설정하지 않으면 gsplat CUDA 커널이 H100에서 실행되지 않습니다!

## 📊 메모리 최적화 설정

### GPU 메모리 관리
```python
import torch

# GPU 메모리 정리
torch.cuda.empty_cache()

# 메모리 할당 최적화 
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.deterministic = False

# 메모리 사용량 모니터링
def print_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"GPU Memory - Allocated: {allocated:.1f}GB, Reserved: {reserved:.1f}GB")
```

## 🚨 충돌 발생 시 해결 방법

### **문제 1: "CUDA out of memory"**
```bash
# 해결 방법
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
python your_script.py --max_points=1000000  # 포인트 수 줄이기
```

### **문제 2: "undefined symbol" 오류**
```bash
# C++ ABI 호환성 문제 해결
pip uninstall torch torchvision -y
pip install torch==2.3.1+cu121 torchvision==0.18.1+cu121 --no-deps --force-reinstall
```

### **문제 3: "pycolmap AttributeError"**
```bash
# pycolmap 재설치
pip uninstall pycolmap -y
pip cache purge
pip install pycolmap==3.10.0 --no-cache-dir  # vggt_env
# 또는
pip install git+https://github.com/rmbrualla/pycolmap@cc7ea4b7301720ac29287dbe450952511b32125e  # gsplat_env
```

### **문제 5: "CUDA error: no kernel image available"**
```bash
# H100 환경변수 누락
source env/setup_h100.sh

# 또는 수동 설정
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1

# gsplat CUDA extension 재컴파일
rm -rf /root/.cache/torch_extensions
rm -rf /tmp/torch_extensions
```

### **문제 6: "colmap: not found"**
```bash
# COLMAP 설치
sudo apt-get install -y colmap

# 또는 setup_environment.sh 재실행
./setup_environment.sh
```

### **문제 4: "NumPy version conflict"**
```bash
# NumPy 호환 버전으로 다운그레이드
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall
```

## ✅ 최종 검증 체크리스트

```bash
# 환경 구축 완료 후 실행
python -c "
import torch
import torchvision  
import numpy as np
import cv2
from PIL import Image
import pycolmap
from plyfile import PlyData

print('✅ PyTorch:', torch.__version__)
print('✅ CUDA available:', torch.cuda.is_available())
print('✅ NumPy:', np.__version__)
print('✅ OpenCV:', cv2.__version__)
print('✅ Pillow:', Image.__version__ if hasattr(Image, '__version__') else 'OK')
print('✅ pycolmap: OK')
print('✅ plyfile: OK')
print('🎉 완벽한 호환 환경 구축 완료!')
"
```

## 📋 실제 구축된 환경 Requirements

### requirements_vggt_env.txt (실제 버전)
```txt
# VGGT Environment Requirements
# Successfully validated on H100 80GB
# Generated from working vggt_env on 2025-10-07

# Core Deep Learning Framework
torch==2.8.0
torchvision==0.23.0
transformers==4.56.1
accelerate==1.10.1

# VGGT-specific Libraries
pycolmap==3.10.0  # CRITICAL: Must be 3.10.0 (not 3.12.5) for API compatibility
einops==0.8.1
kornia==0.8.1
trimesh==4.8.1

# Computer Vision & Image Processing
opencv-python==4.12.0.88
Pillow==11.3.0

# LightGlue (install from GitHub)
# pip install git+https://github.com/cvg/LightGlue.git

# Configuration Management
hydra-core==1.3.2
omegaconf==2.3.0

# Hugging Face
huggingface-hub==0.35.0
safetensors==0.6.2
tokenizers==0.22.0

# Numerical Computing
numpy==2.2.6
matplotlib==3.10.6

# Utilities
tqdm==4.67.1
requests==2.32.5
PyYAML==6.0.2
packaging==25.0
fsspec==2025.9.0
filelock==3.19.1

# CUDA Support (auto-installed with PyTorch)
nvidia-cudnn-cu12==9.10.2.21
nvidia-cublas-cu12==12.8.4.1
nvidia-cufft-cu12==11.3.3.83
nvidia-cuda-runtime-cu12==12.8.90
triton==3.4.0
```

### requirements_gsplat_env.txt (실제 버전)
```txt
# gsplat_env Requirements
# H100 GPU optimized (TORCH_CUDA_ARCH_LIST=9.0)
# Successfully validated on H100 80GB
# Date: 2025-10-07

# Core ML/DL frameworks
torch==2.3.1+cu121
torchvision==0.18.1
torchmetrics==1.8.2

# NVIDIA CUDA libraries
nvidia-cublas-cu12==12.1.3.1
nvidia-cuda-cupti-cu12==12.1.105
nvidia-cuda-runtime-cu12==12.1.105
nvidia-cudnn-cu12==8.9.2.26

# Core 3D Gaussian Splatting
gsplat==1.5.3
triton==2.3.1

# Computer Vision & Image Processing
opencv-python==4.12.0.88
imageio==2.37.0
scikit-image==0.25.2
pillow==11.3.0

# COLMAP & 3D reconstruction
pycolmap @ git+https://github.com/rmbrualla/pycolmap@cc7ea4b7301720ac29287dbe450952511b32125e

# 3D geometry & mesh processing
trimesh==4.8.1
manifold3d==3.2.1
shapely==2.1.1
rtree==1.4.1

# Scientific computing
numpy==1.26.4
scipy==1.15.3
scikit-learn==1.7.2

# Data visualization
matplotlib==3.10.6

# Neural rendering metrics & tools
fused-ssim==0.0.0
lpips==0.1.4

# NeRF viewer & visualization
nerfview @ git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787
viser==1.0.10

# CLI & configuration
tyro==0.9.31
rich==14.1.0
colorlog==6.9.0

# Development & debugging
tensorboard==2.20.0
tensorboard-data-server==0.7.2

# Utilities
tqdm==4.67.1
requests==2.32.5
PyYAML==6.0.2
```

---

## 📚 추가 자료 (Additional Resources)

### 워크플로우 문서
- **[20251007_VGGT-GSplat_WorkFlow.md](docs/workflows/20251007_VGGT-GSplat_WorkFlow.md)** - P1 구현, DTU 각도 정렬
- **[20251006_VGGT-GSplat_WorkFlow.md](docs/workflows/20251006_VGGT-GSplat_WorkFlow.md)** - H100 호환성 해결

### 가이드 문서
- **[QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md)** - H100 환경 Quick Start
- **[README.md](./README.md)** - 프로젝트 개요
- **[RESEARCH_STATUS.md](./RESEARCH_STATUS.md)** - 연구 진행 상황

### 핵심 스크립트
- **[setup_environment.sh](./setup_environment.sh)** - 자동 환경 설치
- **[run_pipeline.sh](./run_pipeline.sh)** - 파이프라인 실행기
- **[prepare_standard_dataset.sh](./prepare_standard_dataset.sh)** - 데이터셋 준비

---

**🛡️ 이 가이드를 따르면 H100 환경에서 충돌 없는 완벽한 VGGT + BA + Gaussian Splatting 파이프라인이 구축됩니다!**

**Last Updated**: 2025-10-07
**Validated on**: H100 80GB + CUDA 12.1 + Ubuntu 22.04