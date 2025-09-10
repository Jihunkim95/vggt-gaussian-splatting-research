#!/usr/bin/env python3
"""
기존 gsplat 체크포인트에서 PLY 파일 추출
"""

import torch
import numpy as np
from plyfile import PlyData, PlyElement
import os

def extract_ply_from_checkpoint(ckpt_path, output_path, step_name):
    """체크포인트에서 PLY 파일 추출"""
    print(f"Loading checkpoint: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location='cpu')
    
    splats = ckpt['splats']
    
    # Gaussian splat 파라미터 추출
    means = splats['means'].cpu().numpy()  # (N, 3)
    scales = torch.exp(splats['scales']).cpu().numpy()  # (N, 3) 
    quats = torch.nn.functional.normalize(splats['quats'], p=2, dim=-1).cpu().numpy()  # (N, 4)
    opacities = torch.sigmoid(splats['opacities']).cpu().numpy()  # (N, 1)
    
    # SH coefficients for colors
    sh0 = splats['sh0'].cpu().numpy()  # (N, 3) - DC component
    if 'shN' in splats and splats['shN'].numel() > 0:
        shN = splats['shN'].cpu().numpy()  # (N, SH_coeffs, 3)
    else:
        shN = np.zeros((means.shape[0], 0, 3))
    
    print(f"Extracted {means.shape[0]} Gaussians")
    print(f"Means shape: {means.shape}")
    print(f"Scales shape: {scales.shape}")
    print(f"Quats shape: {quats.shape}")
    print(f"Opacities shape: {opacities.shape}")
    print(f"SH0 shape: {sh0.shape}")
    print(f"SHN shape: {shN.shape}")
    
    # PLY 파일 생성을 위한 데이터 준비
    dtype_list = [
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),           # positions
        ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),  # scales
        ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4'),  # quaternions
        ('opacity', 'f4'),                                # opacity
        ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),  # SH DC component
    ]
    
    # Additional SH coefficients if present
    for i in range(shN.shape[1]):
        for j in range(3):
            dtype_list.append((f'f_rest_{i*3+j}', 'f4'))
    
    # Create structured array
    n_points = means.shape[0]
    vertices = np.zeros(n_points, dtype=dtype_list)
    
    # Fill basic data
    vertices['x'] = means[:, 0]
    vertices['y'] = means[:, 1] 
    vertices['z'] = means[:, 2]
    
    vertices['scale_0'] = scales[:, 0]
    vertices['scale_1'] = scales[:, 1]
    vertices['scale_2'] = scales[:, 2]
    
    vertices['rot_0'] = quats[:, 0]  # w component first
    vertices['rot_1'] = quats[:, 1]  # x
    vertices['rot_2'] = quats[:, 2]  # y  
    vertices['rot_3'] = quats[:, 3]  # z
    
    vertices['opacity'] = opacities.squeeze()
    
    vertices['f_dc_0'] = sh0[:, 0, 0]
    vertices['f_dc_1'] = sh0[:, 0, 1]
    vertices['f_dc_2'] = sh0[:, 0, 2]
    
    # Fill additional SH coefficients
    for i in range(shN.shape[1]):
        for j in range(3):
            vertices[f'f_rest_{i*3+j}'] = shN[:, i, j]
    
    # Create PLY element
    el = PlyElement.describe(vertices, 'vertex')
    
    # Write PLY file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        PlyData([el]).write(f)
    
    print(f"✅ PLY file saved: {output_path}")
    print(f"📊 Contains {n_points} Gaussians with {shN.shape[1]} SH bands")

if __name__ == "__main__":
    # 기존 7k step 체크포인트에서 PLY 추출
    ckpt_path = "/workspace/labsRoom/gsplat_results_30k_final/ckpts/ckpt_6999_rank0.pt"
    output_dir = "/workspace/labsRoom_ply_outputs"
    
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.exists(ckpt_path):
        extract_ply_from_checkpoint(
            ckpt_path, 
            f"{output_dir}/point_cloud_7000.ply", 
            "7000"
        )
        print("🎉 Successfully extracted PLY from existing checkpoint!")
    else:
        print(f"❌ Checkpoint not found: {ckpt_path}")
        print("Available files:")
        if os.path.exists("/workspace/labsRoom/gsplat_results_30k_final/ckpts/"):
            for f in os.listdir("/workspace/labsRoom/gsplat_results_30k_final/ckpts/"):
                print(f"  - {f}")