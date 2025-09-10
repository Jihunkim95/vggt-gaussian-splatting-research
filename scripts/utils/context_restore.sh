#!/bin/bash

echo "🚀 VGGT-Gaussian Splatting Research Context Restore"
echo "=================================================="

echo ""
echo "📊 GPU Status:"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits

echo ""
echo "📁 Dataset Status:"
echo "Book dataset images: $(ls /workspace/datasets/book/images/ 2>/dev/null | wc -l) frames"
echo "Original target: 200 frames → Current limitation: 80 frames (VRAM)"

echo ""
echo "🎯 Research Progress:"
if [ -d "/workspace/datasets/book/gsplat_output" ]; then
    echo "✅ Gaussian Splatting output exists:"
    echo "   - Checkpoints: $(ls /workspace/datasets/book/gsplat_output/ckpts/ 2>/dev/null | wc -l)"
    echo "   - PLY files: $(ls /workspace/datasets/book/gsplat_output/ply/ 2>/dev/null | wc -l)"
    echo "   - Latest checkpoint: $(ls -t /workspace/datasets/book/gsplat_output/ckpts/*rank0.pt 2>/dev/null | head -1 | xargs basename)"
else
    echo "❌ No gsplat output found"
fi

echo ""
echo "📋 Current Todo Items:"
echo "1. Extract 50K PLY model (ckpt_49999_rank0.pt → PLY)"
echo "2. Test 80-frame baseline processing"  
echo "3. Implement memory optimization (bf16, gradient checkpointing)"
echo "4. Target: 80 → 150+ frames processing"

echo ""
echo "🔧 Environment:"
echo "Active conda env: $(conda info --envs | grep '*' | awk '{print $1}')"
echo "VGGT env: $(ls -d /workspace/envs/vggt_env 2>/dev/null || echo 'Not found')"
echo "gsplat env: $(ls -d /workspace/envs/gsplat_env 2>/dev/null || echo 'Not found')"

echo ""
echo "📚 Key Documents:"
ls -t /workspace/docs/workflows/*.md /workspace/docs/analysis/*.md 2>/dev/null | head -3 | while read file; do
    echo "   - $(basename "$file") ($(stat -c %y "$file" | cut -d' ' -f1))"
done

echo ""
echo "⚡ Quick Commands:"
echo "   # Check 50K checkpoint exists:"
echo "   ls -la /workspace/datasets/book/gsplat_output/ckpts/ckpt_49999_rank0.pt"
echo ""
echo "   # Extract PLY model:"
echo "   python /workspace/scripts/export/export_ply.py --checkpoint ckpt_49999_rank0.pt"
echo ""
echo "   # Memory profiling:"
echo "   nvidia-smi dmon -s m -i 0"

echo ""
echo "🎯 Research Goal: RTX 6000 Ada memory optimization for VGGT+3DGS"
echo "   Target: WACV 2025 submission"
echo "=================================================="