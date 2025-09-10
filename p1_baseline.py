#!/usr/bin/env python3
"""
P1 Baseline Pipeline: Traditional COLMAP + gsplat
DTU scan24에서 기존 COLMAP sparse 재구성을 사용해 Gaussian Splatting 학습
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """Execute command and print output"""
    print(f"\n🔄 {description}")
    print(f"Command: {cmd}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed_time = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ Success ({elapsed_time:.1f}s)")
        if result.stdout:
            print("Output:", result.stdout[:500])  # First 500 chars
    else:
        print(f"❌ Failed ({elapsed_time:.1f}s)")
        print("Error:", result.stderr[:500])
        
    return result

def setup_gsplat_env():
    """Setup gsplat environment"""
    print("🔧 Setting up gsplat environment...")
    
    # Activate gsplat environment
    activate_cmd = "source /workspace/envs/gsplat_env/bin/activate"
    
    # Check if gsplat is installed
    check_cmd = "python -c 'import gsplat; print(f\"gsplat version: {gsplat.__version__}\")'"
    
    return f"{activate_cmd} && {check_cmd}"

def run_p1_baseline(data_dir, output_dir, max_steps=30000):
    """
    Run P1 Baseline: Traditional COLMAP + gsplat
    
    Args:
        data_dir: DTU scan24 directory path
        output_dir: Output directory for results
        max_steps: Maximum training steps
    """
    
    # Ensure directories exist
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📊 P1 Baseline Pipeline Starting")
    print(f"Data: {data_path}")
    print(f"Output: {output_path}")
    print(f"Max steps: {max_steps}")
    
    # Check data structure
    required_paths = {
        'images': data_path / 'images',
        'sparse': data_path / 'sparse' / '0',
        'cameras.bin': data_path / 'sparse' / '0' / 'cameras.bin',
        'images.bin': data_path / 'sparse' / '0' / 'images.bin',
        'points3D.bin': data_path / 'sparse' / '0' / 'points3D.bin'
    }
    
    for name, path in required_paths.items():
        if not path.exists():
            print(f"❌ Missing required path: {name} at {path}")
            return False
        print(f"✅ Found: {name}")
    
    # Count images
    image_count = len(list((data_path / 'images').glob('*.png')))
    print(f"📸 Images: {image_count}")
    
    # Step 1: Setup environment
    env_cmd = setup_gsplat_env()
    result = run_command(env_cmd, "Setting up gsplat environment")
    if result.returncode != 0:
        print("❌ Failed to setup gsplat environment")
        return False
    
    # Step 2: Find gsplat training script
    # Look for gsplat examples or training scripts
    potential_scripts = [
        "/workspace/envs/gsplat_env/lib/python3.10/site-packages/gsplat/examples/simple_trainer.py",
        "/workspace/gsplat/examples/simple_trainer.py",
        "simple_trainer.py"
    ]
    
    gsplat_script = None
    for script in potential_scripts:
        if Path(script).exists():
            gsplat_script = script
            break
    
    if not gsplat_script:
        print("❌ Could not find gsplat training script")
        print("Available scripts in gsplat environment:")
        # Try to find any training scripts
        find_cmd = "find /workspace/envs/gsplat_env -name '*train*' -o -name '*simple*' | head -10"
        run_command(find_cmd, "Searching for training scripts")
        return False
    
    print(f"📝 Using gsplat script: {gsplat_script}")
    
    # Step 3: Run gsplat training
    # Common gsplat training command structure
    training_cmd = f"""
    source /workspace/envs/gsplat_env/bin/activate && \
    python {gsplat_script} \
        --data-dir {data_path} \
        --result-dir {output_path} \
        --max-steps {max_steps} \
        --eval-steps 7000 15000 30000 \
        --save-steps 7000 15000 30000 \
        --ply-steps 7000 15000 30000 \
        --save-ply \
        --disable-viewer
    """
    
    result = run_command(training_cmd.strip(), "Running P1 Baseline Training (COLMAP + gsplat)")
    
    if result.returncode == 0:
        print("🎉 P1 Baseline training completed successfully!")
        
        # Check output files
        output_files = list(output_path.glob('**/*'))
        print(f"📁 Generated {len(output_files)} files")
        
        # Look for important files
        for pattern in ['*.ply', '*.pt', '*.png']:
            files = list(output_path.glob(f'**/{pattern}'))
            if files:
                print(f"✅ Found {len(files)} {pattern} files")
        
        return True
    else:
        print("❌ P1 Baseline training failed")
        return False

def main():
    parser = argparse.ArgumentParser(description="P1 Baseline Pipeline: COLMAP + gsplat")
    parser.add_argument("--data-dir", 
                      default="/workspace/datasets/DTU/scan24",
                      help="DTU scan24 data directory")
    parser.add_argument("--output-dir",
                      default="/workspace/results/P1_baseline/scan24", 
                      help="Output directory")
    parser.add_argument("--max-steps", type=int, default=30000,
                      help="Maximum training steps")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 P1 Baseline Pipeline: Traditional COLMAP + gsplat")
    print("=" * 60)
    
    success = run_p1_baseline(args.data_dir, args.output_dir, args.max_steps)
    
    if success:
        print("\n🎉 P1 Baseline pipeline completed successfully!")
    else:
        print("\n❌ P1 Baseline pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()