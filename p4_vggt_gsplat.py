#!/usr/bin/env python3
"""
P4 Pipeline: VGGT Feed-Forward → gsplat
VGGT로 빠른 포인트 클라우드 생성 후 gsplat으로 고품질 렌더링 훈련
"""

import os
import sys
import time
import subprocess
import argparse
import json
from pathlib import Path

def run_command(cmd, description="", env_vars=None):
    """Execute command and print output"""
    print(f"\n🔄 {description}")
    print(f"Command: {cmd}")

    # Setup environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    elapsed_time = time.time() - start_time

    if result.returncode == 0:
        print(f"✅ Success ({elapsed_time:.1f}s)")
        if result.stdout and len(result.stdout.strip()) > 0:
            print("Output:", result.stdout[:500])  # First 500 chars
    else:
        print(f"❌ Failed ({elapsed_time:.1f}s)")
        if result.stderr:
            print("Error:", result.stderr[:500])
        if result.stdout:
            print("Stdout:", result.stdout[:500])

    return result

def run_training_with_monitoring(cmd, max_steps, description="", env_vars=None):
    """Execute training command with simple terminal progress monitoring"""
    print(f"\n🔄 {description}")
    print(f"📊 Max steps: {max_steps}")
    print("📈 진행률을 모니터링합니다...")

    import re

    # Setup environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Start the training process
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        env=env
    )

    last_step = 0
    start_time = time.time()
    last_update_time = start_time

    # Monitor output in real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break

        if output:
            # Look for step information in the output
            step_match = re.search(r'step\s+(\d+)', output.lower())
            if not step_match:
                step_match = re.search(r'(\d+)/\d+', output)
            if not step_match:
                step_match = re.search(r'iter\s+(\d+)', output.lower())

            if step_match:
                current_step = int(step_match.group(1))
                current_time = time.time()

                # Update every 1000 steps or every 30 seconds
                if (current_step > last_step and
                    (current_step % 1000 == 0 or current_time - last_update_time > 30)):

                    last_step = current_step
                    progress = (current_step / max_steps) * 100
                    elapsed = current_time - start_time
                    last_update_time = current_time

                    if current_step > 0:
                        est_total_time = elapsed * max_steps / current_step
                        remaining_time = est_total_time - elapsed

                        # Simple progress bar
                        bar_length = 20
                        filled_length = int(bar_length * current_step // max_steps)
                        bar = '█' * filled_length + '-' * (bar_length - filled_length)

                        print(f"📊 [{bar}] {current_step:,}/{max_steps:,} ({progress:.1f}%) | "
                              f"소요: {elapsed/60:.1f}분 | "
                              f"남은시간: {remaining_time/60:.1f}분")

    # Wait for process to complete
    return_code = process.wait()

    # Create a mock result object similar to subprocess.run
    class MockResult:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    elapsed_time = time.time() - start_time

    if return_code == 0:
        print(f"✅ 훈련 완료! (총 {elapsed_time/60:.1f}분)")
        print(f"📊 최종: {last_step:,}/{max_steps:,} steps")
    else:
        print(f"❌ 훈련 실패! ({elapsed_time/60:.1f}분)")
        print(f"📊 중단된 지점: {last_step:,}/{max_steps:,} steps")

    return MockResult(return_code)

def run_vggt_feedforward(data_dir, conf_thres_value=5.0):
    """
    Run VGGT feed-forward to generate sparse reconstruction

    Args:
        data_dir: Data directory containing images
        conf_thres_value: Confidence threshold for depth filtering

    Returns:
        bool: Success status
    """
    print(f"\n🔴 ===== VGGT Feed-Forward Stage =====")
    print(f"📁 Data directory: {data_dir}")
    print(f"🎯 Confidence threshold: {conf_thres_value}")

    # Check if images exist
    image_dir = Path(data_dir) / 'images'
    if not image_dir.exists():
        print(f"❌ Images directory not found: {image_dir}")
        return False

    # Count images
    image_files = list(image_dir.glob('*.png')) + list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.JPG'))
    print(f"📸 Found {len(image_files)} images")

    if len(image_files) < 3:
        print(f"❌ Need at least 3 images for VGGT, found {len(image_files)}")
        return False

    # Setup VGGT environment variables
    vggt_env = {
        'PYTHONPATH': './libs/vggt:' + os.environ.get('PYTHONPATH', '')
    }

    # Activate vggt_env and run demo_colmap.py
    activate_cmd = "source ./env/vggt_env/bin/activate"
    vggt_cmd = f"python demo_colmap.py --scene_dir {data_dir} --conf_thres_value {conf_thres_value}"

    full_cmd = f"/bin/bash -c '{activate_cmd} && {vggt_cmd}'"

    result = run_command(full_cmd, "VGGT Feed-Forward Reconstruction", env_vars=vggt_env)

    if result.returncode != 0:
        print("❌ VGGT feed-forward failed!")
        return False

    # Verify sparse reconstruction was created
    sparse_dir = Path(data_dir) / 'sparse'
    required_files = ['cameras.bin', 'images.bin', 'points3D.bin', 'points.ply']

    for file in required_files:
        file_path = sparse_dir / file
        if not file_path.exists():
            print(f"❌ Missing required file: {file}")
            return False
        print(f"✅ Found: {file} ({file_path.stat().st_size:,} bytes)")

    # Analyze reconstruction
    try:
        import pycolmap

        # Load VGGT environment first
        activate_and_check = f"/bin/bash -c 'source ./env/vggt_env/bin/activate && python -c \"import pycolmap; reconstruction = pycolmap.Reconstruction(\\\"{sparse_dir}\\\"); print(f\\\"📊 VGGT Results: {{len(reconstruction.images)}} images, {{len(reconstruction.cameras)}} cameras, {{len(reconstruction.points3D):,}} 3D points\\\")\"'"

        result = run_command(activate_and_check, "Analyze VGGT reconstruction")

        return True

    except Exception as e:
        print(f"⚠️ Could not analyze VGGT reconstruction: {e}")
        return True  # Continue anyway if files exist

def run_gsplat_training(data_dir, output_dir, max_steps=7000):
    """
    Run gsplat training on VGGT sparse reconstruction

    Args:
        data_dir: Directory containing VGGT sparse reconstruction
        output_dir: Output directory for gsplat results
        max_steps: Maximum training steps

    Returns:
        bool: Success status
    """
    print(f"\n🔵 ===== gsplat Training Stage =====")
    print(f"📁 Input: {data_dir}")
    print(f"📁 Output: {output_dir}")
    print(f"🎯 Max steps: {max_steps}")

    # Verify sparse reconstruction exists
    sparse_dir = Path(data_dir) / 'sparse'
    required_files = ['cameras.bin', 'images.bin', 'points3D.bin']

    for file in required_files:
        file_path = sparse_dir / file
        if not file_path.exists():
            print(f"❌ Missing required file for gsplat: {file}")
            return False

    # Find gsplat training script
    gsplat_script = "./libs/gsplat/examples/simple_trainer.py"

    if not Path(gsplat_script).exists():
        print(f"❌ Could not find gsplat training script: {gsplat_script}")
        return False

    print(f"📝 Using gsplat script: {gsplat_script}")

    # Setup gsplat environment variables
    gsplat_env = {
        'TMPDIR': '/data/tmp',
        'TORCH_CUDA_ARCH_LIST': '8.9'
    }

    # Prepare training command
    activate_cmd = "source ./env/gsplat_env/bin/activate"

    # Install any missing packages
    install_cmd = "pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true"

    training_cmd = f"""python {gsplat_script} default \\
        --data-dir {data_dir} \\
        --result-dir {output_dir} \\
        --data-factor 1 \\
        --max-steps {max_steps} \\
        --eval-steps {max_steps} \\
        --save-steps {max_steps} \\
        --ply-steps {max_steps} \\
        --save-ply \\
        --disable-viewer"""

    full_cmd = f"/bin/bash -c '{activate_cmd} && {install_cmd} && {training_cmd}'"

    # Run training with progress monitoring
    result = run_training_with_monitoring(full_cmd.strip(), max_steps, "P4 gsplat Training", env_vars=gsplat_env)

    if result.returncode == 0:
        print("✅ gsplat training completed successfully!")

        # Check output files
        output_path = Path(output_dir)
        output_files = list(output_path.glob('**/*'))
        print(f"📁 Generated {len(output_files)} files")

        # Look for important files
        for pattern in ['*.ply', '*.pt', '*.png']:
            files = list(output_path.glob(f'**/{pattern}'))
            if files:
                print(f"✅ Found {len(files)} {pattern} files")
                # Show the largest PLY file
                if pattern == '*.ply':
                    largest_ply = max(files, key=lambda x: x.stat().st_size)
                    size_mb = largest_ply.stat().st_size / (1024*1024)
                    print(f"📊 Largest PLY: {largest_ply.name} ({size_mb:.1f} MB)")

        return True
    else:
        print("❌ gsplat training failed!")
        return False

def run_p4_pipeline(data_dir, output_dir, conf_thres_value=5.0, max_steps=7000):
    """
    Run P4 Pipeline: VGGT Feed-Forward → gsplat

    Args:
        data_dir: Data directory containing images
        output_dir: Output directory for results
        conf_thres_value: VGGT confidence threshold
        max_steps: gsplat training steps

    Returns:
        bool: Success status
    """

    # Track total pipeline time
    pipeline_start_time = time.time()

    # Ensure directories exist
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"📊 P4 Pipeline: VGGT Feed-Forward → gsplat")
    print(f"📁 Data: {data_path}")
    print(f"📁 Output: {output_path}")
    print(f"🎯 VGGT threshold: {conf_thres_value}")
    print(f"🎯 gsplat steps: {max_steps}")

    # Step 1: Run VGGT Feed-Forward
    vggt_start_time = time.time()

    success = run_vggt_feedforward(data_dir, conf_thres_value)
    vggt_elapsed = time.time() - vggt_start_time

    if not success:
        print("❌ VGGT feed-forward failed!")
        return False

    print(f"✅ VGGT feed-forward completed in {vggt_elapsed:.1f}초")

    # Step 2: Run gsplat training
    gsplat_start_time = time.time()

    success = run_gsplat_training(data_dir, output_dir, max_steps)
    gsplat_elapsed = time.time() - gsplat_start_time

    if not success:
        print("❌ gsplat training failed!")
        return False

    print(f"✅ gsplat training completed in {gsplat_elapsed/60:.1f}분")

    # Calculate total pipeline time
    pipeline_elapsed = time.time() - pipeline_start_time

    # Save timing results
    timing_results = {
        'pipeline_total_seconds': round(pipeline_elapsed, 2),
        'vggt_seconds': round(vggt_elapsed, 2),
        'gsplat_seconds': round(gsplat_elapsed, 2),
        'conf_thres_value': conf_thres_value,
        'max_steps': max_steps
    }

    # Save timing information
    timing_file = output_path / 'timing_results.json'
    with open(timing_file, 'w') as f:
        json.dump(timing_results, f, indent=2)

    print(f"\n🎉 P4 Pipeline completed successfully!")
    print(f"⏱️ 총 파이프라인 시간: {pipeline_elapsed:.1f}초")
    print(f"⏱️ VGGT 시간: {vggt_elapsed:.1f}초")
    print(f"⏱️ gsplat 시간: {gsplat_elapsed:.1f}초")
    print(f"📊 타이밍 결과 저장: {timing_file}")

    return True

def main():
    parser = argparse.ArgumentParser(description="P4 Pipeline: VGGT Feed-Forward → gsplat")
    parser.add_argument("--data-dir",
                      required=True,
                      help="Data directory containing images")
    parser.add_argument("--output-dir",
                      required=True,
                      help="Output directory for results")
    parser.add_argument("--conf-thres-value", type=float, default=5.0,
                      help="VGGT confidence threshold for depth filtering")
    parser.add_argument("--max-steps", type=int, default=7000,
                      help="Maximum gsplat training steps")

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 P4 Pipeline: VGGT Feed-Forward → gsplat")
    print("=" * 60)

    success = run_p4_pipeline(
        args.data_dir,
        args.output_dir,
        args.conf_thres_value,
        args.max_steps
    )

    if success:
        print("\n🎉 P4 Pipeline completed successfully!")
    else:
        print("\n❌ P4 Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()