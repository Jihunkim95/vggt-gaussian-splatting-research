# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VGGT-Gaussian Splatting Research Extension** - Research project targeting WACV 2026 that extends the original VGGT (Visual Geometry Grounded Transformer) for practical deployment on H100 GPUs. The project compares 5 different 3D reconstruction pipelines (P1-P5) combining VGGT, COLMAP, Bundle Adjustment, and Gaussian Splatting.

**Research Goal**: Optimize VGGT+3DGS pipeline for H100 GPUs (80GB VRAM), comparing speed vs quality trade-offs across multiple configurations.

**Key Innovation**: Dual-environment architecture separating VGGT inference (PyTorch 2.8.0) from gsplat training (PyTorch 2.3.1+cu121) to resolve dependency conflicts.

## Critical Architecture

### Pipeline System (P1-P5)

This project has **5 distinct pipelines** that process images → 3D reconstruction:

- **P1**: COLMAP SfM + gsplat (traditional baseline, 15-25min, ~2.5GB VRAM)
- **P2**: VGGT feed-forward only (~4min, sparse reconstruction only)
- **P3**: VGGT + Bundle Adjustment (~4min, optimized sparse)
- **P4**: VGGT → gsplat (no BA) (~10min, balanced, **recommended for prototyping**)
- **P5**: VGGT + BA → gsplat (~13min, highest quality, ~20GB VRAM)

**Pipeline execution**: `./run_pipeline.sh <P1|P2|P3|P4|P5> <dataset_directory>`

### Dual-Environment System

**CRITICAL**: This project uses **two separate conda environments** due to PyTorch version conflicts:

1. **vggt_env** (PyTorch 2.8.0 + pycolmap 3.10.0)
   - Used for: VGGT inference, Bundle Adjustment
   - Pipelines: P2, P3, and first step of P4/P5

2. **gsplat_env** (PyTorch 2.3.1+cu121 + gsplat 1.5.3)
   - Used for: Gaussian Splatting training
   - Pipelines: P1, and second step of P4/P5

**run_pipeline.sh automatically switches environments** between steps. When modifying pipelines, ensure environment switches are correct.

### H100 GPU Configuration

**MANDATORY** environment variables for H100 (Compute Capability 9.0):
```bash
export TORCH_CUDA_ARCH_LIST="9.0"
export CUDA_HOME=/opt/cuda-12.1
export PATH=/opt/cuda-12.1/bin:$PATH
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

These are set in `run_pipeline.sh` and `env/setup_h100.sh`. **Never remove or modify these**.

### Dataset Preparation

**DTU dataset angle-sorting is critical for COLMAP**:
- DTU images are named like `rect_001_7_r5000.png` where middle number (7) is camera angle (0-6)
- `prepare_standard_dataset.sh` sorts by angle first, then by image number
- This ensures sequential COLMAP matching for 100% camera registration
- Output: 60 images sampled uniformly from 343 originals

**For video inputs**: Use `extract_frames.sh` which extracts 60 frames uniformly using ffmpeg.

## Common Development Commands

### Environment Setup (First Time Only)
```bash
# Automated setup (installs COLMAP, CUDA Toolkit, both envs)
./setup_environment.sh

# Manual verification
colmap -h
ls env/  # Should see: vggt_env/ gsplat_env/ setup_h100.sh
```

### Dataset Preparation
```bash
# From DTU (343 images → 60 angle-sorted)
./prepare_standard_dataset.sh ./datasets/DTU/Rectified/scan1_train

# From video (extract 60 frames)
./extract_frames.sh video.mp4 ./datasets/my_scene

# Verify dataset structure
ls ./datasets/DTU/scan1_standard/images | wc -l  # Should be 60
```

### Running Pipelines
```bash
# Quick test (P4 - balanced, 10min)
./run_pipeline.sh P4 ./datasets/DTU/scan1_standard

# High quality (P5 - full, 13min)
./run_pipeline.sh P5 ./datasets/DTU/scan1_standard

# Baseline comparison (P1 - COLMAP, 15-25min)
./run_pipeline.sh P1 ./datasets/DTU/scan1_standard

# Run in background with logs
./run_pipeline.sh P5 ./datasets/DTU/scan14_standard > /tmp/p5.log 2>&1 &
tail -f /tmp/p5.log
```

### Testing Individual Components
```bash
# Test VGGT inference only (vggt_env)
source env/vggt_env/bin/activate
PYTHONPATH=./libs/vggt:$PYTHONPATH python demo_colmap.py \
    --scene_dir ./datasets/DTU/scan1_standard \
    --conf_thres_value 5.0

# Test gsplat training only (gsplat_env)
source env/gsplat_env/bin/activate
python ./libs/gsplat/examples/simple_trainer.py default \
    --data-dir ./temp_work_test \
    --result-dir ./results/test \
    --max-steps 1000
```

### Analyzing Results
```bash
# Check output structure
ls ./results/P5_scan1_*/

# View metrics (PSNR, SSIM, LPIPS)
cat ./results/P5_scan1_*/stats/val_step29999.json

# Check sparse reconstruction quality
source env/vggt_env/bin/activate
python -c "
import pycolmap
rec = pycolmap.Reconstruction('./results/P5_scan1_*/vggt_ba_sparse')
print(f'Cameras: {len(rec.cameras)}')
print(f'Images: {len(rec.images)}')
print(f'Points: {len(rec.points3D)}')
"

# Extract PLY from checkpoint
python scripts/export/export_ply.py \
    --checkpoint ./results/P5_scan1_*/ckpts/ckpt_29999_rank0.pt \
    --output ./my_model.ply
```

## Critical Implementation Details

### run_pipeline.sh Workflow

**P4/P5 multi-step execution**:
1. Creates isolated temp work directory (`temp_work_<pipeline>_<timestamp>`)
2. Step 1: Activates vggt_env → runs VGGT/BA
3. Step 2: Activates gsplat_env → runs gsplat training
4. Copies results to `./results/<pipeline>_<dataset>_<timestamp>/`
5. Cleans up temp directory

**When modifying pipelines**:
- Always verify temp directory cleanup (line 324)
- Check sparse directory naming: `sparse/` (P2/P3), `vggt_sparse/` (P4), `vggt_ba_sparse/` (P5)
- Ensure environment switches happen between VGGT and gsplat steps

### COLMAP Format Export (demo_colmap.py)

**VGGT outputs**:
- `cameras.bin`: Camera intrinsics (SIMPLE_PINHOLE by default)
- `images.bin`: Camera extrinsics + image associations
- `points3D.bin`: 3D point cloud from depth map unprojection

**Bundle Adjustment** (`--use_ba` flag):
- Refinement parameters: `max_reproj_error=8.0`, `max_query_pts=4096`, `query_frame_num=8`
- Uses point tracking for correspondence
- Significantly improves accuracy but adds ~30s processing time

### gsplat Training (libs/gsplat/examples/simple_trainer.py)

**Standard configuration** (used in all pipelines):
- `--max-steps 30000`
- `--eval-steps 7000 15000 30000`
- `--save-steps 7000 15000 30000` (checkpoints)
- `--ply-steps 7000 15000 30000` (point cloud exports)
- `--data-factor 1` (full resolution)
- `--test-every 8` (validation frequency)

**Output artifacts**:
- `ckpts/ckpt_*.pt`: Gaussian parameters + optimizer state
- `ply/point_cloud_*.ply`: 3D Gaussian point clouds
- `renders/val_step*.png`: Validation renderings
- `stats/val_step*.json`: PSNR/SSIM/LPIPS metrics

## Data Flow Architecture

```
Input Images (60 frames)
    ↓
[prepare_standard_dataset.sh] → Angle-sorted 60 images
    ↓
┌───────────────────────────────────────────────┐
│ Pipeline Selection (P1/P2/P3/P4/P5)          │
└───────────────────────────────────────────────┘
    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ P1: COLMAP SfM  │  │ P2: VGGT Only   │  │ P4: VGGT+gsplat │
│ (gsplat_env)    │  │ (vggt_env)      │  │ (both envs)     │
│ ├─ Feature      │  │ ├─ Feed-forward │  │ ├─ VGGT         │
│ ├─ Matching     │  │ └─ Export       │  │ ├─ gsplat       │
│ ├─ Sparse Recon │  │                 │  │ └─ Metrics      │
│ └─ gsplat       │  └─────────────────┘  └─────────────────┘
└─────────────────┘
    ↓
Results (./results/<pipeline>_<dataset>_<timestamp>/)
├─ sparse/ or vggt_sparse/ or vggt_ba_sparse/
├─ ckpts/ (P1/P4/P5 only)
├─ ply/ (P1/P4/P5 only)
├─ stats/ (P1/P4/P5 only)
└─ metadata.json, analysis.json
```

## Important File Locations

**Core Scripts**:
- `run_pipeline.sh`: Main pipeline orchestrator (330 lines)
- `setup_environment.sh`: One-command environment setup
- `prepare_standard_dataset.sh`: Dataset preparation with angle-sorting
- `extract_frames.sh`: Video → 60 frames extraction
- `p1_baseline.py`: P1 pipeline implementation
- `demo_colmap.py`: VGGT → COLMAP export

**Environments**:
- `env/vggt_env/`: PyTorch 2.8.0, pycolmap 3.10.0
- `env/gsplat_env/`: PyTorch 2.3.1+cu121, gsplat 1.5.3
- `env/setup_h100.sh`: H100 environment variables

**External Libraries** (git submodules):
- `libs/vggt/`: VGGT implementation (facebook/vggt)
- `libs/gsplat/`: Gaussian Splatting library (nerfstudio-project/gsplat)

**Documentation**:
- `QUICK_START_GUIDE.md`: Complete setup guide (DTU download → pipeline execution)
- `docs/ARCHITECTURE.md`: Pipeline architecture details (P1-P5)
- `docs/ENVIRONMENT_SETUP.md`: H100 environment setup
- `docs/TOOLS_REFERENCE.md`: All scripts usage reference
- `docs/workflows/`: Daily research logs (2025-09-08 ~ 2025-10-24)

## Known Issues & Solutions

### H100 CUDA Kernel Errors
**Symptom**: "no kernel image available for function" during gsplat training
**Solution**: Ensure `TORCH_CUDA_ARCH_LIST="9.0"` is set. Run `source env/setup_h100.sh`

### COLMAP Registration Failure on DTU
**Symptom**: <60 cameras registered by COLMAP
**Solution**: Verify angle-sorting. DTU images must be sorted by camera angle (0→6), then by image number. Re-run `prepare_standard_dataset.sh`

### fused-ssim Compilation Error
**Symptom**: "nvcc not found" or compilation errors during gsplat_env setup
**Solution**: Install CUDA Toolkit 12.1: `setup_environment.sh` handles this automatically, or manually install to `/opt/cuda-12.1`

### pycolmap Version Conflicts
**Symptom**: "Reconstruction() takes no arguments" or similar pycolmap errors
**Solution**: Activate vggt_env before using pycolmap: `source env/vggt_env/bin/activate`

### Memory Issues on P5
**Symptom**: CUDA OOM during P5 execution
**Solution**: P5 requires ~20GB VRAM. Reduce `--max-steps` to 15000 or use P4 instead (no BA, only ~2.6GB VRAM)

## Pipeline Selection Guide

**When to use each pipeline**:

- **P1**: When you need COLMAP baseline for comparison, or validating dataset quality (DTU angle-sorted datasets guarantee 100% registration)
- **P2/P3**: When you only need sparse reconstruction (cameras + 3D points), no Gaussian Splatting rendering
- **P4**: **Recommended for most use cases** - Best speed/quality trade-off, minimal VRAM (~2.6GB), good for prototyping
- **P5**: When you need highest quality and have sufficient VRAM (20GB), or doing final publication-quality results

**Typical workflow**:
1. Start with P4 for quick validation (~10min)
2. If quality insufficient, try P5 (~13min)
3. Compare against P1 baseline for quantitative evaluation (~20min)

## Expected Outputs & Validation

**Successful P4/P5 execution produces**:
- `vggt_sparse/` or `vggt_ba_sparse/`: COLMAP reconstruction (cameras.bin, images.bin, points3D.bin)
- `ckpts/`: 3 checkpoints at steps 6999, 14999, 29999
- `ply/`: 3 PLY files at same steps
- `renders/`: Validation images (every 8 test images)
- `stats/`: JSON files with PSNR/SSIM/LPIPS at eval steps

**Quality thresholds (DTU dataset, 60 images)**:
- P4: PSNR ~19, SSIM ~0.73 @ step 6999
- P5: PSNR ~16, SSIM ~0.74 @ step 29999
- P1: Baseline comparison (exact values vary by scan)

**Failure indicators**:
- 0 points in sparse reconstruction → Check image quality, try different `conf_thres_value`
- <60 cameras in COLMAP → Dataset not angle-sorted, re-run `prepare_standard_dataset.sh`
- NaN in metrics → CUDA environment issue, verify H100 setup
- Missing PLY files → gsplat training failed, check logs in result directory

## Research Context

**Daily Workflows**: See `docs/workflows/YYYYMMDD_VGGT-GSplat_WorkFlow.md` for detailed research logs, experiments, and decision rationale. When investigating issues or extending pipelines, review recent workflows for context.

**Current Status (2025-10-24)**:
- ✅ All pipelines (P1-P5) validated on H100 80GB
- ✅ DTU scan1/scan14/scan24 tested
- ✅ CO3Dv2 apple dataset tested (video frames → 100% COLMAP registration)
- ✅ H100 CUDA 12.1 + fused-ssim compilation resolved
- ✅ Dual-environment architecture stable

**Target Conference**: WACV 2026 - Submission focuses on H100 optimization and pipeline comparison.
