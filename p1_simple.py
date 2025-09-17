#!/usr/bin/env python3
"""
P1 Baseline Pipeline: Simple validation and setup
DTU scan24 데이터 구조 확인 및 gsplat 환경 검증
"""

import os
from pathlib import Path

def check_data_structure():
    """Check DTU scan24 data structure"""
    print("🔍 Checking DTU scan24 data structure...")
    
    data_path = Path("./datasets/DTU/scan1_processed")
    
    if not data_path.exists():
        print(f"❌ Data path not found: {data_path}")
        return False
    
    # Check required paths
    required_paths = {
        'images': data_path / 'images',
        'sparse': data_path / 'sparse' / '0',
        'cameras.bin': data_path / 'sparse' / '0' / 'cameras.bin',
        'images.bin': data_path / 'sparse' / '0' / 'images.bin',
        'points3D.bin': data_path / 'sparse' / '0' / 'points3D.bin'
    }
    
    for name, path in required_paths.items():
        if path.exists():
            print(f"✅ Found: {name} at {path}")
        else:
            print(f"❌ Missing: {name} at {path}")
    
    # Count images
    if (data_path / 'images').exists():
        image_files = list((data_path / 'images').glob('*.png'))
        print(f"📸 Images: {len(image_files)} PNG files")
        if image_files:
            print(f"   First: {image_files[0].name}")
            print(f"   Last: {image_files[-1].name}")
    
    return True

def check_environments():
    """Check virtual environments"""
    print("\n🔧 Checking virtual environments...")
    
    vggt_env = Path("/workspace/envs/vggt_env")
    gsplat_env = Path("/workspace/envs/gsplat_env")
    
    if vggt_env.exists():
        print(f"✅ VGGT environment: {vggt_env}")
        # Check if activate script exists
        if (vggt_env / "bin" / "activate").exists():
            print(f"   ✅ Activation script found")
    else:
        print(f"❌ VGGT environment not found")
    
    if gsplat_env.exists():
        print(f"✅ gsplat environment: {gsplat_env}")
        # Check if activate script exists
        if (gsplat_env / "bin" / "activate").exists():
            print(f"   ✅ Activation script found")
    else:
        print(f"❌ gsplat environment not found")

def find_gsplat_scripts():
    """Find gsplat training scripts"""
    print("\n📝 Looking for gsplat training scripts...")
    
    # Common locations for gsplat scripts
    potential_locations = [
        "/workspace/gsplat",
        "/workspace/envs/gsplat_env/lib/python3.10/site-packages/gsplat",
        "/workspace"
    ]
    
    training_scripts = []
    
    for location in potential_locations:
        location_path = Path(location)
        if location_path.exists():
            print(f"🔍 Searching in: {location}")
            # Look for training scripts
            scripts = list(location_path.rglob("*train*.py"))
            scripts.extend(list(location_path.rglob("*simple*.py")))
            scripts.extend(list(location_path.rglob("*gsplat*.py")))
            
            for script in scripts[:5]:  # Show first 5
                print(f"   📄 {script}")
                training_scripts.append(script)
    
    if training_scripts:
        print(f"\n✅ Found {len(training_scripts)} potential training scripts")
        return training_scripts[0]  # Return first one
    else:
        print("\n❌ No training scripts found")
        return None

def create_output_dir():
    """Create output directory for P1 results"""
    output_dir = Path("/workspace/results/P1_baseline/scan1")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    return output_dir

def main():
    print("=" * 60)
    print("🚀 P1 Baseline Pipeline - Setup & Validation")
    print("=" * 60)
    
    # Step 1: Check data structure
    check_data_structure()
    
    # Step 2: Check environments
    check_environments()
    
    # Step 3: Find training scripts
    script = find_gsplat_scripts()
    
    # Step 4: Create output directory
    output_dir = create_output_dir()
    
    print("\n" + "=" * 60)
    print("📋 P1 Baseline Ready!")
    print("=" * 60)
    
    if script:
        print(f"🎯 Next step: Run training with {script}")
        print(f"📁 Output will go to: {output_dir}")
        
        # Provide command template
        print("\n🔧 Suggested command:")
        print(f"source /workspace/envs/gsplat_env/bin/activate")
        print(f"python {script} --data-dir ./datasets/DTU/scan1_processed --result-dir {output_dir}")
    else:
        print("❌ Cannot proceed - no training script found")

if __name__ == "__main__":
    main()