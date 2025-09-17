#!/bin/bash

echo "🚀 VGGT-Gaussian Splatting Research Context Restore"
echo "=================================================="

echo ""
echo "📊 GPU Status:"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits

echo ""
echo "📁 Dataset Status:"
echo "DTU SampleSet: $(ls ./datasets/DTU/ 2>/dev/null | wc -l) items"
echo "DTU scan1 images: $(ls ./datasets/DTU/SampleSet/MVS\ Data/Cleaned/scan1/ 2>/dev/null | wc -l) frames"
echo "Current focus: DTU MVS benchmark dataset"

echo ""
echo "🎯 Research Progress:"
if [ -d "/workspace/results/" ]; then
    echo "✅ Research results exist:"
    echo "   - P1 Baseline: $(ls /workspace/results/P1_baseline*/ckpts/ 2>/dev/null | wc -l) checkpoints"
    echo "   - P2 VGGT: $(ls /workspace/results/P2_VGGT*/*.ply 2>/dev/null | wc -l) PLY files"
    echo "   - P3 VGGT+BA: $(ls /workspace/results/P3_VGGT*/*.ply 2>/dev/null | wc -l) PLY files"
else
    echo "❌ No results found - ready for pipeline experiments"
fi

echo ""
echo "📋 Current Research Pipeline:"
echo "1. P1: COLMAP + gsplat baseline (✅ completed)"
echo "2. P2: VGGT feed-forward only (✅ completed)"
echo "3. P3: VGGT + Bundle Adjustment (✅ completed with issues)"
echo "4. P4: VGGT → gsplat (⏳ pending)"
echo "5. P5: VGGT + BA → gsplat (⏳ pending)"

echo ""
echo "🔧 Environment:"
echo "Active conda env: $(conda info --envs | grep '*' | awk '{print $1}')"
echo "VGGT env: $(ls -d /workspace/vggt-gaussian-splatting-research/env/vggt_env 2>/dev/null || echo 'Not found')"
echo "gsplat env: $(ls -d /workspace/vggt-gaussian-splatting-research/env/gsplat_env 2>/dev/null || echo 'Not found')"

echo ""
echo "📚 Key Documents:"
ls -t /workspace/docs/workflows/*.md /workspace/docs/analysis/*.md 2>/dev/null | head -3 | while read file; do
    echo "   - $(basename "$file") ($(stat -c %y "$file" | cut -d' ' -f1))"
done

echo ""
echo "⚡ Quick Commands:"
echo "   # Download DTU SampleSet (6.3GB):"
echo "   cd ./datasets/DTU && wget -c \"http://roboimagedata2.compute.dtu.dk/data/MVS/SampleSet.zip\""
echo ""
echo "   # Check DTU SampleSet download:"
echo "   ls -la ./datasets/DTU/SampleSet.zip"
echo ""
echo "   # Extract DTU SampleSet:"
echo "   cd ./datasets/DTU && unzip SampleSet.zip"
echo ""
echo "   # Switch environments:"
echo "   source scripts/utils/switch_env.sh [vggt|gsplat|status]"
echo ""
echo "   # Memory profiling:"
echo "   nvidia-smi dmon -s m -i 0"

echo ""
echo "🎯 Research Goal: RTX 6000 Ada optimization for VGGT+3DGS pipeline"
echo "   Target: WACV 2026 submission"
echo "   Focus: P1-P5 pipeline comparison on DTU MVS dataset"
echo "=================================================="