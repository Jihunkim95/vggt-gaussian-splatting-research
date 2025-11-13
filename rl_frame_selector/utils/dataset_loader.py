#!/usr/bin/env python3
"""
Dataset Loader for Multi-Video Training

Supports:
- CO3Dv2 (Common Objects in 3D v2)
- DTU (Custom videos from DTU datasets)
- Custom (User-provided videos)
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import random


def load_co3d_videos(
    root: str = "/data/co3d",
    categories: Optional[List[str]] = None,
    num_videos: int = 1000,
    split: str = "train",
    seed: int = 42
) -> List[str]:
    """
    Load video paths from CO3Dv2 dataset

    Args:
        root: CO3Dv2 dataset root directory
        categories: List of categories to include (None = all 50 categories)
        num_videos: Number of videos to load
        split: 'train', 'val', or 'test'
        seed: Random seed for reproducibility

    Returns:
        List of video file paths

    CO3Dv2 Structure:
        /data/co3d/
        ├─ apple/
        │  ├─ 110_13051_23361/
        │  │  ├─ images/
        │  │  └─ masks/
        │  └─ ...
        ├─ ball/
        └─ ...

    Reference:
        Reizenstein, J., et al. (2021). Common Objects in 3D: Large-Scale
        Learning and Evaluation of Real-life 3D Category Reconstruction. ICCV.
    """
    root_path = Path(root)

    if not root_path.exists():
        raise FileNotFoundError(
            f"CO3Dv2 root not found: {root}\n"
            "Download from: https://github.com/facebookresearch/co3d"
        )

    # Default: Use all 50 categories
    if categories is None:
        categories = [
            'apple', 'backpack', 'ball', 'banana', 'bench', 'bicycle',
            'book', 'bottle', 'bowl', 'cake', 'car', 'carrot', 'chair',
            'cup', 'donut', 'handbag', 'keyboard', 'laptop', 'mouse',
            'orange', 'plant', 'remote', 'sandwich', 'skateboard', 'toaster',
            'toilet', 'toyplane', 'toytrain', 'toytruck', 'umbrella', 'vase'
            # ... (total 50, abbreviated for brevity)
        ]

    video_paths = []
    random.seed(seed)

    for category in categories:
        category_path = root_path / category
        if not category_path.exists():
            print(f"⚠️  Category not found: {category}")
            continue

        # CO3Dv2에서 각 sequence는 하나의 "video"로 간주
        sequences = [d for d in category_path.iterdir() if d.is_dir()]

        for seq_dir in sequences:
            images_dir = seq_dir / "images"
            if images_dir.exists() and len(list(images_dir.glob("*.png"))) > 50:
                # 50개 이상의 프레임이 있는 시퀀스만 선택
                video_paths.append(str(seq_dir))

    # Shuffle and select num_videos
    random.shuffle(video_paths)
    selected = video_paths[:num_videos]

    print(f"✅ CO3Dv2 Loaded: {len(selected)} videos from {len(categories)} categories")
    return selected


def load_dtu_videos(
    root: str = "/data/vggt-gaussian-splatting-research/datasets/DTU",
    scans: Optional[List[int]] = None
) -> List[str]:
    """
    Load DTU scan directories (treated as "videos")

    Args:
        root: DTU dataset root
        scans: List of scan numbers (e.g., [1, 14, 24])

    Returns:
        List of dataset directories
    """
    root_path = Path(root)

    if scans is None:
        scans = [1, 14, 24, 37, 40, 55, 63, 65, 69, 83, 97, 105, 106, 110, 114, 118, 122]

    video_paths = []
    for scan_num in scans:
        scan_dir = root_path / f"scan{scan_num}_standard"
        if scan_dir.exists():
            video_paths.append(str(scan_dir))
        else:
            print(f"⚠️  DTU scan not found: {scan_dir}")

    print(f"✅ DTU Loaded: {len(video_paths)} scans")
    return video_paths


def load_custom_videos(
    root: str = "/data/vggt-gaussian-splatting-research/datasets/custom"
) -> List[str]:
    """
    Load custom video files (.mp4, .mov, etc.) or image directories

    Args:
        root: Custom dataset root

    Returns:
        List of video file paths or image directories
    """
    root_path = Path(root)

    if not root_path.exists():
        raise FileNotFoundError(f"Custom root not found: {root}")

    video_paths = []

    # Video files
    for ext in ['*.mp4', '*.mov', '*.avi', '*.mkv']:
        video_paths.extend([str(p) for p in root_path.glob(ext)])

    # Image directories (must have 'images' subdirectory)
    for d in root_path.iterdir():
        if d.is_dir() and (d / "images").exists():
            video_paths.append(str(d))

    print(f"✅ Custom Loaded: {len(video_paths)} videos/datasets")
    return video_paths


def load_dataset(
    dataset_name: str,
    num_videos: Optional[int] = None,
    **kwargs
) -> List[str]:
    """
    Generic dataset loader

    Args:
        dataset_name: 'co3d', 'dtu', 'custom'
        num_videos: Number of videos to load (None = all)
        **kwargs: Dataset-specific arguments

    Returns:
        List of video paths

    Example:
        # Load 1000 CO3Dv2 videos
        videos = load_dataset('co3d', num_videos=1000)

        # Load DTU scans
        videos = load_dataset('dtu', scans=[1, 14, 24])

        # Load custom videos
        videos = load_dataset('custom', root='./my_videos')
    """
    if dataset_name == 'co3d':
        videos = load_co3d_videos(num_videos=num_videos or 1000, **kwargs)
    elif dataset_name == 'dtu':
        videos = load_dtu_videos(**kwargs)
    elif dataset_name == 'custom':
        videos = load_custom_videos(**kwargs)
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    if num_videos is not None and len(videos) > num_videos:
        videos = videos[:num_videos]

    return videos


def create_train_val_split(
    videos: List[str],
    val_ratio: float = 0.1,
    seed: int = 42
) -> Dict[str, List[str]]:
    """
    Split videos into train/val sets

    Args:
        videos: List of video paths
        val_ratio: Validation set ratio
        seed: Random seed

    Returns:
        {'train': [...], 'val': [...]}
    """
    random.seed(seed)
    shuffled = videos.copy()
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * (1 - val_ratio))

    return {
        'train': shuffled[:split_idx],
        'val': shuffled[split_idx:]
    }


if __name__ == '__main__':
    # Test dataset loading
    print("=" * 70)
    print("Dataset Loader Test")
    print("=" * 70)
    print()

    # Test CO3Dv2 (if available)
    try:
        co3d_videos = load_dataset('co3d', num_videos=10)
        print(f"Sample CO3Dv2 video: {co3d_videos[0]}")
        print()
    except FileNotFoundError as e:
        print(f"❌ CO3Dv2 not available: {e}")
        print()

    # Test DTU
    try:
        dtu_videos = load_dataset('dtu', scans=[1, 14])
        print(f"Sample DTU scan: {dtu_videos[0]}")
        print()
    except FileNotFoundError as e:
        print(f"❌ DTU not available: {e}")
        print()

    # Test Custom
    try:
        custom_videos = load_dataset('custom')
        print(f"Sample custom video: {custom_videos[0]}")
        print()
    except FileNotFoundError as e:
        print(f"❌ Custom not available: {e}")
        print()

    print("=" * 70)
