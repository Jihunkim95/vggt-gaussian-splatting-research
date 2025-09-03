#!/bin/bash
# VGGT-Gaussian Splatting Libraries Setup Script
# ===============================================

echo "🚀 Setting up external libraries for VGGT-GSplat research..."

# Create libs directory if not exists
mkdir -p libs/

# Clone VGGT repository
echo "📥 Cloning VGGT repository..."
if [ ! -d "libs/vggt" ]; then
    git clone https://github.com/facebookresearch/vggsfm.git libs/vggt
    echo "✅ VGGT cloned successfully"
else
    echo "⏭️ VGGT already exists, skipping..."
fi

# Clone gsplat repository  
echo "📥 Cloning gsplat repository..."
if [ ! -d "libs/gsplat" ]; then
    git clone https://github.com/nerfstudio-project/gsplat.git libs/gsplat
    echo "✅ gsplat cloned successfully"
else
    echo "⏭️ gsplat already exists, skipping..."
fi

echo ""
echo "🎯 Libraries setup complete!"
echo "Next steps:"
echo "1. Activate your conda environment"
echo "2. Install dependencies for each library"
echo "3. Run: source scripts/utils/switch_env.sh"

# Make sure libs directory is in gitignore
if ! grep -q "libs/" .gitignore; then
    echo "libs/" >> .gitignore
    echo "📝 Added libs/ to .gitignore"
fi