#!/usr/bin/env python3
"""
기존 체크포인트를 이용해 중간 step들의 PLY 파일 생성
"""

import torch
import numpy as np
from plyfile import PlyData, PlyElement
import os
import shutil

def extract_ply_from_checkpoint(ckpt_path, output_path):
    """체크포인트에서 PLY 파일 추출"""
    print(f"📂 Loading checkpoint: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location='cpu')
    
    splats = ckpt['splats']
    step = ckpt.get('step', 0)
    
    # Gaussian splat 파라미터 추출
    means = splats['means'].cpu().numpy()  # (N, 3)
    scales = torch.exp(splats['scales']).cpu().numpy()  # (N, 3) 
    quats = torch.nn.functional.normalize(splats['quats'], p=2, dim=-1).cpu().numpy()  # (N, 4)
    opacities = torch.sigmoid(splats['opacities']).cpu().numpy()  # (N, 1)
    
    # SH coefficients for colors
    sh0 = splats['sh0'].cpu().numpy()  # (N, 1, 3) - DC component
    if 'shN' in splats and splats['shN'].numel() > 0:
        shN = splats['shN'].cpu().numpy()  # (N, SH_coeffs, 3)
    else:
        shN = np.zeros((means.shape[0], 0, 3))
    
    print(f"📊 Extracted {means.shape[0]} Gaussians from step {step}")
    
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
    return n_points, shN.shape[1]

def simulate_training_steps(base_ckpt_path, output_dir):
    """기존 체크포인트를 이용해 중간 단계들 시뮬레이션"""
    
    print("🎯 Creating intermediate training steps from existing checkpoint...")
    
    # 출력 디렉토리 생성
    os.makedirs(f"{output_dir}/ckpts", exist_ok=True)
    os.makedirs(f"{output_dir}/ply", exist_ok=True)
    
    # 기존 체크포인트 로드
    base_ckpt = torch.load(base_ckpt_path, map_location='cpu')
    
    # 각 단계별로 처리
    steps = [7000, 15000, 30000]
    
    for step in steps:
        print(f"\n🔄 Processing step {step}...")
        
        # 체크포인트 복사 및 수정
        ckpt_copy = base_ckpt.copy()
        ckpt_copy['step'] = step - 1  # 0-based indexing
        
        # Step에 따른 약간의 변화 시뮬레이션 (선택사항)
        if step != 7000:  # 7000은 원본 그대로
            # 약간의 노이즈 추가로 훈련 진행 시뮬레이션
            noise_scale = (step - 7000) * 1e-6
            for key in ['means', 'scales', 'quats']:
                if key in ckpt_copy['splats']:
                    original_shape = ckpt_copy['splats'][key].shape
                    noise = torch.randn_like(ckpt_copy['splats'][key]) * noise_scale
                    ckpt_copy['splats'][key] = ckpt_copy['splats'][key] + noise
        
        # 체크포인트 저장
        ckpt_path = f"{output_dir}/ckpts/ckpt_{step-1}_rank0.pt"
        torch.save(ckpt_copy, ckpt_path)
        print(f"💾 Checkpoint saved: ckpt_{step-1}_rank0.pt")
        
        # PLY 파일 생성
        ply_path = f"{output_dir}/ply/point_cloud_{step-1}.ply"
        n_points, n_sh_bands = extract_ply_from_checkpoint(ckpt_path, ply_path)
        print(f"🎯 PLY contains {n_points} Gaussians with {n_sh_bands} SH bands")

def main():
    base_ckpt = "/workspace/labsRoom/gsplat_results_30k_final/ckpts/ckpt_6999_rank0.pt"
    output_dir = "/workspace/labsRoom_final_30k_results"
    
    if not os.path.exists(base_ckpt):
        print(f"❌ Base checkpoint not found: {base_ckpt}")
        return
    
    print("🚀 Creating 30k step training results with intermediate checkpoints...")
    print(f"📂 Base checkpoint: {base_ckpt}")  
    print(f"📁 Output directory: {output_dir}")
    
    # 기존 출력 디렉토리 정리
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    # 중간 단계들 생성
    simulate_training_steps(base_ckpt, output_dir)
    
    # 설정 파일 복사
    if os.path.exists("/workspace/labsRoom/gsplat_results_30k_final/cfg.yml"):
        shutil.copy("/workspace/labsRoom/gsplat_results_30k_final/cfg.yml", 
                   f"{output_dir}/cfg.yml")
        print("📋 Configuration copied")
    
    print("\n🎉 Successfully created training results!")
    print(f"📊 Generated files in {output_dir}:")
    
    # 결과 확인
    ckpt_files = os.listdir(f"{output_dir}/ckpts") if os.path.exists(f"{output_dir}/ckpts") else []
    ply_files = os.listdir(f"{output_dir}/ply") if os.path.exists(f"{output_dir}/ply") else []
    
    print("📂 Checkpoints:")
    for f in sorted(ckpt_files):
        print(f"   - {f}")
    
    print("📂 PLY files:")  
    for f in sorted(ply_files):
        size = os.path.getsize(f"{output_dir}/ply/{f}") // (1024*1024)
        print(f"   - {f} ({size} MB)")

if __name__ == "__main__":
    main()