#!/usr/bin/env python3
"""
scan1용 간단한 COLMAP .bin 파일 생성
gsplat의 COLMAP parser가 요구하는 최소한의 파일들만 생성
gsplat env에서 실행 필요
"""

import os
import struct
import time
from pathlib import Path

def create_colmap_cameras_bin(sparse_dir):
    """Create cameras.bin file with single camera configuration"""
    cameras_path = sparse_dir / "cameras.bin"
    
    with open(cameras_path, 'wb') as f:
        # Header: number of cameras
        f.write(struct.pack('Q', 1))  # 1 camera
        
        # Camera data - DTU dataset standard parameters
        camera_id = 1
        model_id = 1  # PINHOLE model
        width = 1600
        height = 1200
        fx = fy = 1200.0  # focal length
        cx = 800.0  # principal point x
        cy = 600.0  # principal point y
        
        f.write(struct.pack('I', camera_id))
        f.write(struct.pack('I', model_id))
        f.write(struct.pack('Q', width))
        f.write(struct.pack('Q', height))
        f.write(struct.pack('d', fx))
        f.write(struct.pack('d', fy))
        f.write(struct.pack('d', cx))
        f.write(struct.pack('d', cy))
    
    print(f"✅ cameras.bin: {cameras_path.stat().st_size} bytes")

def create_colmap_images_bin(sparse_dir, image_names):
    """Create images.bin file with all 49 images"""
    images_path = sparse_dir / "images.bin"
    
    with open(images_path, 'wb') as f:
        # Header: number of images  
        f.write(struct.pack('Q', len(image_names)))
        
        # Generate poses in a circular pattern for 49 images
        import math
        for i, image_name in enumerate(image_names):
            image_id = i + 1
            
            # Create circular camera positions
            angle = 2 * math.pi * i / len(image_names)
            radius = 2.0  # Distance from center
            
            # Camera position (translation)
            tx = radius * math.cos(angle)
            ty = 0.0  # Keep cameras at same height
            tz = radius * math.sin(angle)
            
            # Camera orientation (quaternion) - look towards center
            # Simple rotation around Y axis
            qw = math.cos(angle / 2)
            qx = 0.0
            qy = math.sin(angle / 2)
            qz = 0.0
            
            camera_id = 1  # All images use same camera
            
            f.write(struct.pack('I', image_id))
            f.write(struct.pack('dddd', qw, qx, qy, qz))
            f.write(struct.pack('ddd', tx, ty, tz))
            f.write(struct.pack('I', camera_id))
            # Write name with null terminator
            f.write(image_name.encode('utf-8') + b'\x00')
            # Number of 2D points (0 for now)
            f.write(struct.pack('Q', 0))
    
    print(f"✅ images.bin: {images_path.stat().st_size} bytes ({len(image_names)} images)")

def create_colmap_points3d_bin(sparse_dir):
    """Create empty points3D.bin file"""
    points_path = sparse_dir / "points3D.bin"
    
    with open(points_path, 'wb') as f:
        # Header: number of 3D points (0)
        f.write(struct.pack('Q', 0))
    
    print(f"✅ points3D.bin: {points_path.stat().st_size} bytes (empty)")

def create_simple_colmap_scan1():
    """Create simple COLMAP files for scan1 that gsplat can read"""
    
    # 경로 설정
    data_dir = Path("./datasets/DTU/scan1_processed")
    image_dir = data_dir / "images"
    sparse_dir = data_dir / "sparse" / "0"
    
    print("🔧 Creating simple COLMAP files for scan1")
    print(f"📁 Data directory: {data_dir}")
    print(f"📸 Images directory: {image_dir}")
    print(f"📁 Sparse output: {sparse_dir}")
    
    # sparse 디렉토리 생성
    sparse_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미지 파일 목록 가져오기
    image_files = sorted([f.name for f in image_dir.glob("*.png")])
    print(f"📸 Found {len(image_files)} images")
    
    if len(image_files) == 0:
        print("❌ No images found!")
        return False
    
    # 시작 시간 측정
    start_time = time.time()
    
    try:
        # COLMAP .bin 파일들 생성
        create_colmap_cameras_bin(sparse_dir)
        create_colmap_images_bin(sparse_dir, image_files)
        create_colmap_points3d_bin(sparse_dir)
        
        # 소요 시간 계산
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ COLMAP .bin 파일 생성 완료!")
        print(f"⏱️ 소요 시간: {elapsed_time:.2f}초")
        print(f"📁 위치: {sparse_dir}")
        
        # 파일 검증
        required_files = ['cameras.bin', 'images.bin', 'points3D.bin']
        all_exist = True
        for file in required_files:
            file_path = sparse_dir / file
            if file_path.exists():
                print(f"✅ {file}: {file_path.stat().st_size} bytes")
            else:
                print(f"❌ {file}: not found")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = create_simple_colmap_scan1()
    
    if success:
        print("\n🎉 gsplat용 COLMAP 파일 준비 완료!")
        print("📋 다음 단계: P1 Baseline training 실행")
    else:
        print("\n❌ COLMAP 파일 생성 실패!")