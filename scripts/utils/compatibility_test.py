#!/usr/bin/env python3
"""완벽한 호환성 테스트 스크립트"""

import sys
import warnings
warnings.filterwarnings('ignore')

def test_core_compatibility():
    """핵심 라이브러리 호환성 테스트"""
    print("🔍 핵심 라이브러리 호환성 검사...")
    
    try:
        # PyTorch 생태계
        import torch
        import torchvision
        assert torch.__version__.startswith('2.3.1'), f"PyTorch 버전 불일치: {torch.__version__}"
        assert torchvision.__version__.startswith('0.18.1'), f"torchvision 버전 불일치: {torchvision.__version__}"
        
        # CUDA 호환성
        assert torch.cuda.is_available(), "CUDA 사용 불가"
        assert torch.version.cuda == '12.1', f"CUDA 버전 불일치: {torch.version.cuda}"
        
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ torchvision: {torchvision.__version__}")
        print(f"✅ CUDA: {torch.version.cuda}")
        
        # 수치 계산
        import numpy as np
        import scipy
        assert np.__version__.startswith('1.26'), f"NumPy 버전 위험: {np.__version__}"
        
        print(f"✅ NumPy: {np.__version__}")
        print(f"✅ SciPy: {scipy.__version__}")
        
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
        from plyfile import PlyData, PlyElement
        import matplotlib.pyplot as plt
        import torchmetrics
        
        # PLY 파일 처리 테스트
        dtype = [('x', 'f4'), ('y', 'f4'), ('z', 'f4')]
        test_data = np.array([(1.0, 2.0, 3.0)], dtype=dtype)
        el = PlyElement.describe(test_data, 'vertex')
        
        print("✅ PLY 파일 처리")
        print("✅ matplotlib 시각화")
        print("✅ torchmetrics")
        
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