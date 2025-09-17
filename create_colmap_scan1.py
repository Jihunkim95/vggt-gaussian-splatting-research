#!/usr/bin/env python3
"""
scan1용 COLMAP sparse 재구성 생성
"""

import os
import pycolmap
from pathlib import Path

def create_colmap_reconstruction():
    """scan1 이미지들로 COLMAP sparse 재구성 생성"""
    
    # 경로 설정
    data_dir = Path("./datasets/DTU/scan1_processed")
    image_dir = data_dir / "images"
    sparse_dir = data_dir / "sparse" / "0"
    
    print("🔧 COLMAP Sparse Reconstruction for scan1")
    print(f"📁 Image directory: {image_dir}")
    print(f"📁 Sparse output: {sparse_dir}")
    
    # sparse 디렉토리 생성
    sparse_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미지 개수 확인
    image_files = list(image_dir.glob("*.png"))
    print(f"📸 Found {len(image_files)} images")
    
    # COLMAP 실행
    try:
        print("\n🚀 Starting COLMAP feature extraction...")
        
        # Feature extraction
        pycolmap.extract_features(
            database_path=str(sparse_dir / "database.db"),
            image_path=str(image_dir),
            camera_mode=pycolmap.CameraMode.SINGLE,  # 단일 카메라 모드
            camera_model="PINHOLE",
        )
        
        print("✅ Feature extraction completed")
        
        print("\n🔍 Starting feature matching...")
        
        # Feature matching
        pycolmap.match_exhaustive(
            database_path=str(sparse_dir / "database.db"),
        )
        
        print("✅ Feature matching completed")
        
        print("\n🏗️ Starting incremental mapping...")
        
        # Incremental mapping
        maps = pycolmap.incremental_mapping(
            database_path=str(sparse_dir / "database.db"),
            image_path=str(image_dir),
            output_path=str(sparse_dir),
        )
        
        if not maps:
            print("❌ Incremental mapping failed - no reconstructions created")
            return False
            
        print(f"✅ Created {len(maps)} reconstruction(s)")
        
        # 가장 큰 재구성 선택
        largest_map = max(maps.values(), key=lambda x: len(x.images))
        
        print(f"📊 Selected reconstruction:")
        print(f"   - Images: {len(largest_map.images)}")
        print(f"   - Points: {len(largest_map.points3D)}")
        print(f"   - Cameras: {len(largest_map.cameras)}")
        
        # Binary 형식으로 저장
        largest_map.write_binary(str(sparse_dir))
        
        print("✅ Sparse reconstruction saved successfully!")
        
        # 파일 확인
        required_files = ['cameras.bin', 'images.bin', 'points3D.bin']
        for file in required_files:
            file_path = sparse_dir / file
            if file_path.exists():
                print(f"✅ {file}: {file_path.stat().st_size} bytes")
            else:
                print(f"❌ {file}: not found")
        
        return True
        
    except Exception as e:
        print(f"❌ COLMAP failed: {e}")
        return False

if __name__ == "__main__":
    success = create_colmap_reconstruction()
    
    if success:
        print("\n🎉 COLMAP sparse reconstruction completed!")
        print("📁 Ready for gsplat pipeline testing")
    else:
        print("\n❌ COLMAP reconstruction failed!")