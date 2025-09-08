#!/usr/bin/env python3
"""
Dockerfile.gsplat 기반으로 현재 gsplat 환경 수정
"""

import subprocess
import sys
import os

def run_pip_command(cmd):
    """pip 명령 실행"""
    print(f"🔧 Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False

def check_current_environment():
    """현재 환경 확인"""
    print("🔍 Current Environment Check:")
    
    # Python version
    print(f"Python: {sys.version}")
    
    # Check if we're in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"✅ Virtual environment: {sys.prefix}")
    else:
        print("❌ Not in virtual environment")
    
    # Check key packages
    packages_to_check = ['torch', 'numpy', 'pycolmap', 'gsplat']
    for pkg in packages_to_check:
        try:
            module = __import__(pkg)
            version = getattr(module, '__version__', 'unknown')
            print(f"  {pkg}: {version}")
        except ImportError:
            print(f"  {pkg}: NOT INSTALLED")

def fix_pycolmap_version():
    """pycolmap를 0.6.1 표준 버전으로 수정"""
    print("\n🔧 Fixing pycolmap version to 0.6.1 (standardized)...")
    
    # Uninstall current pycolmap
    if not run_pip_command("pip uninstall pycolmap -y"):
        print("Failed to uninstall pycolmap")
        return False
    
    # Install standard version 0.6.1 (VGGT/gsplat compatible)
    if not run_pip_command("pip install pycolmap==0.6.1"):
        print("Failed to install pycolmap 0.6.1")
        return False
    
    return True

def install_gsplat_requirements():
    """Dockerfile.gsplat의 requirements 설치"""
    print("\n🔧 Installing gsplat requirements...")
    
    requirements = [
        "numpy==1.26.1",
        "scipy==1.15.3", 
        "pillow==11.0.0",
        "opencv-python==4.9.0.80",
        "plyfile==1.1.2",
        "trimesh==3.23.5",
        "scikit-learn==1.7.1",
        "torchmetrics==1.8.1",
        "tensorboard",
        "matplotlib==3.10.5",
        "tqdm",
        "viser",
        "imageio[ffmpeg]",
        "tyro",
        "pyyaml"
    ]
    
    success_count = 0
    for req in requirements:
        if run_pip_command(f"pip install {req}"):
            success_count += 1
        else:
            print(f"⚠️ Failed to install: {req}")
    
    print(f"📊 Installed {success_count}/{len(requirements)} packages")
    return success_count == len(requirements)

def install_additional_deps():
    """추가 git 의존성 설치"""
    print("\n🔧 Installing additional git dependencies...")
    
    git_deps = [
        "git+https://github.com/nerfstudio-project/nerfview@4538024fe0d15fd1a0e4d760f3695fc44ca72787",
        "git+https://github.com/rahul-goel/fused-ssim@328dc9836f513d00c4b5bc38fe30478b4435cbb5"
    ]
    
    for dep in git_deps:
        run_pip_command(f"pip install {dep}")

def test_environment():
    """환경 테스트"""
    print("\n🧪 Testing environment...")
    
    test_commands = [
        "import torch; print(f'PyTorch: {torch.__version__}')",
        "import torch; print(f'CUDA available: {torch.cuda.is_available()}')",
        "import pycolmap; print(f'pycolmap imported successfully')", 
        "from pycolmap import SceneManager; print('SceneManager imported')",
        "import numpy; print(f'NumPy: {numpy.__version__}')"
    ]
    
    for cmd in test_commands:
        try:
            result = subprocess.run([sys.executable, '-c', cmd], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ {cmd}: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"❌ {cmd}: {e.stderr.strip()}")

def main():
    print("=" * 60)
    print("🔧 Fixing gsplat environment based on Dockerfile.gsplat")
    print("=" * 60)
    
    # Step 1: Check current environment
    check_current_environment()
    
    # Step 2: Fix pycolmap version
    if fix_pycolmap_version():
        print("✅ pycolmap version fixed")
    else:
        print("❌ Failed to fix pycolmap version")
        return
    
    # Step 3: Install requirements
    if install_gsplat_requirements():
        print("✅ Requirements installed")
    else:
        print("⚠️ Some requirements failed to install")
    
    # Step 4: Install additional dependencies
    install_additional_deps()
    
    # Step 5: Test environment
    test_environment()
    
    print("\n" + "=" * 60)
    print("🎉 gsplat environment fix completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()