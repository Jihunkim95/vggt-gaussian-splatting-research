#!/usr/bin/env python3
"""
P1 Baseline Pipeline: Original COLMAP SfM + gsplat (Images Only)
이미지만으로 COLMAP SfM 재구성 후 gsplat 학습
run_pipeline.sh P1 파이프라인과 동일한 동작

명령어 참고:
    # 다른 스캔 사용
        python p1_baseline.py --data-dir ./datasets/DTU/scan14_standard --output-dir ./results/P1_scan14
    # run_pipeline.sh P1과 동일하게 호출
        python p1_baseline.py \
          --data-dir ./datasets/DTU/scan14_standard \
          --output-dir ./results/P1_baseline \
          --data-factor 1 \
          --max-steps 30000 \
          --eval-steps 30000 \
          --save-steps 7000 15000 30000 \
          --ply-steps 7000 15000 30000 \
          --save-ply \
          --disable-viewer \
          --tb-every 1000
          
"""

import os
import sys
import time
import subprocess
import argparse
import shutil
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

def run_training_with_monitoring(cmd, max_steps, description=""):
    """Execute training command with simple terminal progress monitoring"""
    print(f"\n🔄 {description}")
    print(f"📊 Max steps: {max_steps}")
    print("📈 진행률을 모니터링합니다...")

    import re

    # Start the training process
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
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

        # 에러 로그 출력을 위해 다시 실행
        print("\n🔍 에러 상세 정보:")
        error_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if error_result.stderr:
            print("STDERR:", error_result.stderr[:1000])
        if error_result.stdout:
            print("STDOUT:", error_result.stdout[:1000])

    return MockResult(return_code)

def setup_gsplat_env():
    """Setup gsplat environment with H100 GPU support"""
    print("🔧 gsplat 환경 활성화 중...")

    # Set H100 GPU environment variables (compute capability 9.0)
    os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0'
    os.environ['CUDA_HOME'] = '/opt/cuda-12.1'
    os.environ['PATH'] = '/opt/cuda-12.1/bin:' + os.environ.get('PATH', '')
    os.environ['TMPDIR'] = '/data/tmp'

    # PyTorch CUDA memory fragmentation prevention
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

    print("📦 필요 패키지 설치 확인 중...")

    # Install additional required packages (gsplat environment)
    install_cmd = "pip install --no-deps imageio tqdm tyro > /dev/null 2>&1 || true"
    subprocess.run(install_cmd, shell=True)

    print("✅ 환경 설정 완료")

def run_colmap_sfm(data_path, sparse_dir):
    """Run COLMAP SfM pipeline"""

    print(f"\n🏗️ ===== COLMAP Structure-from-Motion =====")

    image_dir = data_path / 'images'
    database_path = sparse_dir / 'database.db'

    # Remove existing sparse reconstruction
    if sparse_dir.exists():
        import shutil
        shutil.rmtree(sparse_dir)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    print(f"📸 Images: {image_dir}")
    print(f"🗄️ Database: {database_path}")

    # Step 1: Feature extraction
    print(f"\n📊 Step 1: COLMAP Feature extraction")

    # Set environment for headless execution
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'
    os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '330'
    os.environ['GALLIUM_DRIVER'] = 'llvmpipe'

    feature_cmd = f"""colmap feature_extractor \\
        --database_path {database_path} \\
        --image_path {image_dir} \\
        --ImageReader.single_camera false \\
        --ImageReader.camera_model PINHOLE \\
        --SiftExtraction.max_image_size 1600 \\
        --SiftExtraction.max_num_features 8192"""

    result = run_command(feature_cmd, "COLMAP Feature Extraction")
    if result.returncode != 0:
        print("❌ COLMAP feature extraction failed. Trying CPU-only mode...")
        # Try with CPU extraction
        feature_cmd = f"""colmap feature_extractor \\
            --database_path {database_path} \\
            --image_path {image_dir} \\
            --ImageReader.single_camera false \\
            --ImageReader.camera_model PINHOLE \\
            --SiftExtraction.max_image_size 1600 \\
            --SiftExtraction.max_num_features 8192 \\
            --SiftExtraction.use_gpu false"""

        result = run_command(feature_cmd, "COLMAP Feature Extraction (CPU)")
        if result.returncode != 0:
            return False

    # Step 2: Feature matching
    print(f"\n🔗 Step 2: COLMAP Feature matching")
    match_cmd = f"""colmap exhaustive_matcher \\
        --database_path {database_path} \\
        --SiftMatching.guided_matching true \\
        --SiftMatching.max_ratio 0.8 \\
        --SiftMatching.max_distance 0.7 \\
        --SiftMatching.use_gpu false"""

    result = run_command(match_cmd, "COLMAP Feature Matching")
    if result.returncode != 0:
        return False

    # Step 3: Sparse reconstruction
    print(f"\n🏗️ Step 3: COLMAP Sparse reconstruction")
    mapper_cmd = f"""colmap mapper \\
        --database_path {database_path} \\
        --image_path {image_dir} \\
        --output_path {sparse_dir} \\
        --Mapper.ba_refine_focal_length true \\
        --Mapper.ba_refine_principal_point true \\
        --Mapper.ba_refine_extra_params true \\
        --Mapper.init_min_num_inliers 100 \\
        --Mapper.abs_pose_max_error 12 \\
        --Mapper.filter_max_reproj_error 4"""

    result = run_command(mapper_cmd, "COLMAP Sparse Reconstruction")
    if result.returncode != 0:
        return False

    # Find the reconstruction directory (usually "0")
    recon_dirs = [d for d in sparse_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not recon_dirs:
        print("❌ No reconstruction found!")
        return False

    model_dir = recon_dirs[0]  # Use the first (usually largest) reconstruction
    print(f"📁 Found reconstruction: {model_dir}")

    # Verify required files exist
    required_files = ['cameras.bin', 'images.bin', 'points3D.bin']
    for file in required_files:
        file_path = model_dir / file
        if not file_path.exists():
            print(f"❌ Missing required file: {file}")
            return False
        print(f"✅ Found: {file} ({file_path.stat().st_size} bytes)")

    # Create "0" directory if it doesn't exist (for gsplat compatibility)
    target_dir = sparse_dir / "0"
    if model_dir != target_dir:
        if target_dir.exists():
            import shutil
            shutil.rmtree(target_dir)
        import shutil
        shutil.copytree(model_dir, target_dir)
        print(f"📁 Copied reconstruction to {target_dir}")

    # Analyze reconstruction
    try:
        import pycolmap
        reconstruction = pycolmap.Reconstruction(str(target_dir))
        print(f"\n📊 COLMAP SfM Results:")
        print(f"📸 Images registered: {len(reconstruction.images)}")
        print(f"📷 Cameras: {len(reconstruction.cameras)}")
        print(f"🔺 3D Points: {len(reconstruction.points3D)}")

        if len(reconstruction.images) < 10:
            print(f"⚠️ Only {len(reconstruction.images)} images registered!")
            return False

        return True
    except Exception as e:
        print(f"⚠️ Could not analyze reconstruction: {e}")
        return True  # Continue anyway if files exist

def run_p1_baseline(data_dir, output_dir, data_factor=1, max_steps=30000,
                   eval_steps=30000, save_steps=None, ply_steps=None,
                   save_ply=True, disable_viewer=True, tb_every=1000):
    """
    Run P1 Baseline: Original COLMAP SfM + gsplat (Images Only)
    run_pipeline.sh P1 파이프라인과 동일한 동작

    Args:
        data_dir: Data directory containing images
        output_dir: Output directory for results
        data_factor: Data downsampling factor
        max_steps: Maximum training steps
        eval_steps: Evaluation steps
        save_steps: List of steps to save checkpoints
        ply_steps: List of steps to save PLY files
        save_ply: Save PLY files
        disable_viewer: Disable viewer
        tb_every: TensorBoard logging frequency
    """

    # Track total pipeline time
    pipeline_start_time = time.time()

    # Ensure directories exist
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"📋 P1: Original COLMAP SfM + gsplat (Images Only) 실행")
    print(f"📁 Data: {data_path}")
    print(f"📁 Output: {output_path}")
    print(f"📊 Max steps: {max_steps}")

    # Setup gsplat environment with H100 GPU support
    setup_gsplat_env()

    # Check for images
    image_dir = data_path / 'images'
    if not image_dir.exists():
        print(f"❌ Images directory not found: {image_dir}")
        return False

    # Count images
    image_count = len(list(image_dir.glob('*.png')))
    if image_count == 0:
        image_count = len(list(image_dir.glob('*.jpg')))
    print(f"📸 Images: {image_count}")

    if image_count < 5:
        print(f"❌ Need at least 5 images for SfM, found {image_count}")
        return False

    # Run COLMAP SfM (start from images only - true COLMAP SfM)
    sparse_dir = data_path / 'sparse'

    # Remove existing sparse reconstruction to start fresh
    if sparse_dir.exists():
        print(f"🧹 기존 sparse 재구성 제거 (이미지만으로 COLMAP SfM 시작)")
        shutil.rmtree(sparse_dir)

    # Run COLMAP SfM
    print(f"\n🏗️ COLMAP Structure-from-Motion 실행 중...")
    colmap_start = time.time()

    success = run_colmap_sfm(data_path, sparse_dir)
    colmap_elapsed = time.time() - colmap_start

    if not success:
        print(f"❌ COLMAP SfM 실패!")
        return False

    print(f"✅ COLMAP SfM 완료! ({colmap_elapsed:.1f}초)")

    # Default save/ply steps if not provided
    if save_steps is None:
        save_steps = [7000, 15000, 30000]
    if ply_steps is None:
        ply_steps = [7000, 15000, 30000]

    # Find gsplat training script
    gsplat_script = "./libs/gsplat/examples/simple_trainer.py"

    if not Path(gsplat_script).exists():
        print(f"❌ Could not find gsplat training script: {gsplat_script}")
        return False

    print(f"📝 Using gsplat script: {gsplat_script}")

    # Build training command (matching run_pipeline.sh P1 section)
    save_steps_str = " ".join(map(str, save_steps))
    ply_steps_str = " ".join(map(str, ply_steps))

    training_cmd = f"""python {gsplat_script} default \\
        --data-dir {data_path} \\
        --result-dir {output_path} \\
        --data-factor {data_factor} \\
        --max-steps {max_steps} \\
        --eval-steps {eval_steps} \\
        --save-steps {save_steps_str} \\
        --ply-steps {ply_steps_str}"""

    if save_ply:
        training_cmd += " \\\n        --save-ply"
    if disable_viewer:
        training_cmd += " \\\n        --disable-viewer"

    training_cmd += f" \\\n        --tb-every {tb_every}"

    # Measure training time and monitor progress
    training_start_time = time.time()

    print(f"\n🚀 P1 Baseline 훈련 시작 (COLMAP SfM + gsplat)")
    print(f"📊 Step 저장: {save_steps}")
    print(f"📊 PLY 저장: {ply_steps}")
    print(f"📊 TensorBoard 로깅: 매 {tb_every} steps")

    # Run training with progress monitoring
    result = run_training_with_monitoring(training_cmd.strip(), max_steps, "P1 Baseline Training")
    training_elapsed = time.time() - training_start_time

    # Calculate total pipeline time
    pipeline_elapsed = time.time() - pipeline_start_time

    # Save timing results
    timing_results = {
        'pipeline_total_seconds': round(pipeline_elapsed, 2),
        'training_seconds': round(training_elapsed, 2),
        'setup_seconds': round(training_start_time - pipeline_start_time, 2)
    }

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

        # Save timing information
        import json
        timing_file = output_path / 'timing_results.json'
        with open(timing_file, 'w') as f:
            json.dump(timing_results, f, indent=2)

        print(f"⏱️ 파이프라인 총 시간: {pipeline_elapsed:.1f}초")
        print(f"⏱️ 훈련 시간: {training_elapsed:.1f}초")
        print(f"📊 타이밍 결과 저장: {timing_file}")

        return True
    else:
        print("❌ P1 Baseline training failed")
        print(f"⏱️ 실패까지 소요 시간: {pipeline_elapsed:.1f}초")
        return False

def main():
    parser = argparse.ArgumentParser(description="P1 Baseline Pipeline: Original COLMAP SfM + gsplat (Images Only)")
    parser.add_argument("--data-dir",
                      default="./datasets/DTU/scan24_standard",
                      help="Data directory containing images")
    parser.add_argument("--output-dir",
                      default="./results/P1_baseline",
                      help="Output directory")
    parser.add_argument("--data-factor", type=int, default=1,
                      help="Data downsampling factor")
    parser.add_argument("--max-steps", type=int, default=30000,
                      help="Maximum training steps")
    parser.add_argument("--eval-steps", type=int, default=30000,
                      help="Evaluation steps")
    parser.add_argument("--save-steps", type=int, nargs='+', default=[7000, 15000, 30000],
                      help="Steps to save checkpoints (space-separated)")
    parser.add_argument("--ply-steps", type=int, nargs='+', default=[7000, 15000, 30000],
                      help="Steps to save PLY files (space-separated)")
    parser.add_argument("--save-ply", action="store_true", default=True,
                      help="Save PLY files")
    parser.add_argument("--disable-viewer", action="store_true", default=True,
                      help="Disable viewer")
    parser.add_argument("--tb-every", type=int, default=1000,
                      help="TensorBoard logging frequency")

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 P1 Baseline Pipeline: Original COLMAP SfM + gsplat (Images Only)")
    print("=" * 80)

    success = run_p1_baseline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        data_factor=args.data_factor,
        max_steps=args.max_steps,
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        ply_steps=args.ply_steps,
        save_ply=args.save_ply,
        disable_viewer=args.disable_viewer,
        tb_every=args.tb_every
    )

    if success:
        print("\n🎉 P1 Baseline pipeline completed successfully!")
    else:
        print("\n❌ P1 Baseline pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()