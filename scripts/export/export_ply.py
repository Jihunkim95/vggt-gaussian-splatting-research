#!/usr/bin/env python3
"""
체크포인트에서 PLY 파일을 생성하는 스크립트
VGGT+Gaussian Splatting 워크플로우의 결과를 PLY 형식으로 추출
"""

import torch
import sys
import os
from pathlib import Path

# gsplat 모듈 임포트
sys.path.append('/workspace/gsplat')
from gsplat.exporter import export_splats

def load_checkpoint(ckpt_path):
    """체크포인트 파일 로드"""
    print(f"체크포인트 로딩: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location='cpu')
    return ckpt

def extract_splat_data(ckpt):
    """체크포인트에서 Gaussian Splat 데이터 추출"""
    # 체크포인트 구조 확인
    print("체크포인트 키:", list(ckpt.keys()))
    
    # 일반적인 gsplat 체크포인트 구조
    if 'splats' in ckpt:
        splats = ckpt['splats']
    else:
        # 다른 구조일 수 있으므로 확인
        splats = ckpt
    
    # Gaussian Splat 파라미터 추출
    means = splats['means']  # (N, 3) - 위치
    scales = splats['scales']  # (N, 3) - 크기
    quats = splats['quats']  # (N, 4) - 회전 쿼터니언
    opacities = splats['opacities']  # (N,) - 불투명도
    sh0 = splats['sh0']  # (N, 1, 3) - DC 성분
    shN = splats['shN'] if 'shN' in splats else torch.zeros(means.shape[0], 0, 3)  # (N, K, 3) - 추가 SH
    
    print(f"Gaussian 개수: {means.shape[0]}")
    print(f"means: {means.shape}, scales: {scales.shape}")
    print(f"quats: {quats.shape}, opacities: {opacities.shape}")
    print(f"sh0: {sh0.shape}, shN: {shN.shape}")
    
    return means, scales, quats, opacities, sh0, shN

def export_to_ply(ckpt_path, output_path, format='ply'):
    """체크포인트를 PLY 파일로 추출"""
    try:
        # 체크포인트 로드
        ckpt = load_checkpoint(ckpt_path)
        
        # Splat 데이터 추출
        means, scales, quats, opacities, sh0, shN = extract_splat_data(ckpt)
        
        # PLY 파일로 내보내기
        print(f"PLY 파일 생성 중: {output_path}")
        export_splats(
            means=means,
            scales=scales, 
            quats=quats,
            opacities=opacities,
            sh0=sh0,
            shN=shN,
            format=format,
            save_to=output_path
        )
        
        print(f"✅ PLY 파일 생성 완료: {output_path}")
        print(f"파일 크기: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 체크포인트 구조 상세 출력
        ckpt = load_checkpoint(ckpt_path)
        print("\n=== 체크포인트 구조 디버깅 ===")
        def print_dict_structure(d, prefix=""):
            for k, v in d.items():
                if isinstance(v, torch.Tensor):
                    print(f"{prefix}{k}: {v.shape} ({v.dtype})")
                elif isinstance(v, dict):
                    print(f"{prefix}{k}: dict")
                    print_dict_structure(v, prefix + "  ")
                else:
                    print(f"{prefix}{k}: {type(v)}")
        print_dict_structure(ckpt)

if __name__ == "__main__":
    # 체크포인트 경로들
    ckpt_dir = Path("/workspace/book/gsplat_output/ckpts")
    output_dir = Path("/workspace/book/gsplat_output/ply")
    output_dir.mkdir(exist_ok=True)
    
    # 사용 가능한 체크포인트들
    checkpoints = [
        "ckpt_49999_rank0.pt",  # 최종 체크포인트 (50K steps) ✨
        "ckpt_29999_rank0.pt",  # 이전 최종 (30K steps)
        "ckpt_6999_rank0.pt"    # 중간 체크포인트 (7K steps)
    ]
    
    print("=== VGGT+Gaussian Splatting PLY 추출기 ===")
    print("워크플로우: VGGT+BA → COLMAP → Gaussian Splatting → PLY")
    print()
    
    for ckpt_name in checkpoints:
        ckpt_path = ckpt_dir / ckpt_name
        if ckpt_path.exists():
            # 출력 파일명 생성
            steps = ckpt_name.replace("ckpt_", "").replace("_rank0.pt", "")
            output_name = f"gaussians_step_{steps}.ply"
            output_path = output_dir / output_name
            
            print(f"📥 처리 중: {ckpt_name} → {output_name}")
            export_to_ply(str(ckpt_path), str(output_path))
            print()
        else:
            print(f"⚠️  체크포인트 없음: {ckpt_path}")
    
    print("=== PLY 추출 완료 ===")
    print(f"출력 디렉토리: {output_dir}")
    
    # 생성된 PLY 파일들 확인
    ply_files = list(output_dir.glob("*.ply"))
    if ply_files:
        print("\n생성된 PLY 파일들:")
        for ply_file in sorted(ply_files):
            size_mb = ply_file.stat().st_size / (1024*1024)
            print(f"  📄 {ply_file.name} ({size_mb:.1f} MB)")
        
        print(f"\n🎯 추천: 최종 모델을 사용하세요:")
        print(f"cp {output_dir}/gaussians_step_29999.ply {output_dir}/final_model.ply")
    else:
        print("\n❌ PLY 파일이 생성되지 않았습니다.")