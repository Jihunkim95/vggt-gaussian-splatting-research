#!/usr/bin/env python3
"""
빠른 의존성 수정 - imageio부터
"""

import subprocess
import sys

def install_package(package):
    """패키지 설치"""
    print(f"🔧 Installing {package}...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                      check=True, capture_output=True, text=True)
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e.stderr}")
        return False

def main():
    print("🚀 Quick fix for missing dependencies")
    
    # 즉시 필요한 패키지들
    packages = [
        "imageio[ffmpeg]==2.37.0",
        "tyro>=0.8.8", 
        "viser==1.0.6",
        "torchmetrics[image]==1.8.1"
    ]
    
    for pkg in packages:
        install_package(pkg)
    
    # 테스트
    try:
        import imageio
        print(f"✅ imageio version: {imageio.__version__}")
    except ImportError:
        print("❌ imageio still not available")
    
    print("🎉 Quick fix completed!")

if __name__ == "__main__":
    main()