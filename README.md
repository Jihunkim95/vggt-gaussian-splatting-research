# 🚀 VGGT-Gaussian Splatting Research

RTX 6000 Ada optimization for VGGT+3DGS pipeline research project targeting **WACV 2026**.

## 📊 Project Overview

This repository contains research on optimizing the **VGGT (VGGSfM) + Gaussian Splatting** pipeline for practical deployment on RTX 6000 Ada GPUs (48GB VRAM), as opposed to the typical H100 requirements.

### 🎯 Research Goals
- **Scalability**: 80 frame processing optimization 
- **Pipeline Comparison**: 5 different configurations (P1-P5)
- **Adaptive Selection**: Scene-based automatic pipeline selection
- **Memory Optimization**: Efficient VRAM utilization for RTX 6000 Ada

## 📁 Repository Structure

```
├── docs/                    # Research documentation
│   ├── archive/            # Archived old documents
│   └── EXPERIMENT_LOG.md   # Experiment tracking
├── scripts/                # Utilities and tools
│   ├── export/             # PLY model extraction
│   └── utils/              # Context restoration & environment
├── datasets/               # Experimental datasets
│   └── DTU/                # DTU dataset (scan24, scan37, etc.)
├── libs/                   # External libraries (VGGT, gsplat)
├── setup_libs.sh          # External library setup
└── .gitignore             # Optimized for large ML projects
```

## 🛠️ Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Jihunkim95/vggt-gaussian-splatting-research.git
cd vggt-gaussian-splatting-research
```

### 2. Setup External Libraries
```bash
./setup_libs.sh
```

### 3. Environment Setup
```bash
source scripts/utils/switch_env.sh
```

### 4. Restore Context
```bash
./scripts/utils/context_restore.sh
```

## 🔧 Environment Requirements

- **GPU**: RTX 6000 Ada (48GB VRAM) or equivalent
- **CUDA**: 11.8+ or 12.x
- **Python**: 3.10+
- **Libraries**: VGGT, gsplat, PyTorch

## 🧪 Pipeline Configurations

| Pipeline | Components | Use Case |
|----------|------------|----------|
| **P1_baseline** | COLMAP + gsplat | Traditional approach |
| **P2_vggt_only** | VGGT (feed-forward) | Fast processing |
| **P3_vggt_ba** | VGGT + Bundle Adjustment | Quality focused |
| **P4_vggt_gsplat** | VGGT + gsplat (no BA) | Balanced approach |
| **P5_full** | VGGT + BA + gsplat | Maximum quality |

## 📈 Current Status

### ✅ Completed
- [x] Environment setup and separation (vggt_env + gsplat_env)
- [x] pycolmap version standardization (0.6.1)
- [x] Frame target adjustment (80 frames realistic max)
- [x] Research plan documentation (20250903)

### 🔄 In Progress  
- [ ] DTU dataset download and preprocessing
- [ ] P1-P5 pipeline implementation
- [ ] VGGT integration with gsplat
- [ ] Memory optimization for 80 frames

### 🎯 Target Metrics
- **Quality**: PSNR, SSIM, LPIPS, Chamfer Distance
- **Efficiency**: Processing time, peak VRAM, FPS
- **Robustness**: Failure rate, generalization

## 📊 Experimental Results

Currently targeting **80 frames** (RTX 6000 Ada realistic maximum). Research focus: Memory optimization and pipeline comparison.

| Dataset | Frames | VRAM (GB) | Processing Time | PSNR | Status |
|---------|--------|-----------|----------------|------|--------|
| DTU scan24 | 80 | TBD | TBD | TBD | 🔄 Planned |
| DTU scan37 | 80 | TBD | TBD | TBD | 🔄 Planned |
| ETH3D courtyard | 80 | TBD | TBD | TBD | 🔄 Planned |

## 🔍 Key Scripts

- **`scripts/export/export_ply.py`**: Extract PLY models from checkpoints
- **`scripts/utils/context_restore.sh`**: Quick project status overview
- **`scripts/utils/switch_env.sh`**: Environment management
- **`setup_libs.sh`**: Clone and setup external dependencies

## 📚 Documentation

- **[Research Workflow](docs/workflows/)**: Detailed research plans and progress
- **[VRAM Analysis](docs/analysis/)**: Memory optimization strategies  
- **[Experiment Log](docs/EXPERIMENT_LOG.md)**: Tracking all experiments

## 🤝 Contributing

This is a research project. For collaboration:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

Research project - please cite if used in publications.

## 🎯 Target Conference

**WACV 2026** - Workshop on Applications of Computer Vision

---

## 🔧 Troubleshooting

### VRAM Issues
- Reduce batch size in gsplat config
- Use mixed precision (bf16)
- Enable gradient checkpointing

### Environment Issues  
- Run `./scripts/utils/context_restore.sh` for diagnostics
- Check CUDA compatibility with `nvidia-smi`
- Verify conda environments exist

### Missing Libraries
- Run `./setup_libs.sh` to reinstall
- Check that both VGGT and gsplat are properly cloned

---

**Last Updated**: 2025-09-03  
**Maintainer**: [@Jihunkim95](https://github.com/Jihunkim95)

🤖 *Generated with [Claude Code](https://claude.ai/code)*