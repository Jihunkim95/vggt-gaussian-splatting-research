#!/usr/bin/env python3
"""
비디오 처리 유틸리티
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
import tempfile
import subprocess


def extract_frames_uniformly(video_path: str, num_frames: int = 300) -> List[np.ndarray]:
    """
    비디오 파일 또는 이미지 디렉토리에서 균등한 간격으로 프레임 추출

    Args:
        video_path: 비디오 파일 경로 또는 이미지 디렉토리 경로
        num_frames: 추출할 프레임 수

    Returns:
        프레임 리스트 (각 프레임은 numpy array)
    """
    path = Path(video_path)

    # Case 1: 디렉토리인 경우 (DTU, CO3Dv2 등)
    if path.is_dir():
        # images/ 서브디렉토리 확인
        images_dir = path / "images"
        if not images_dir.exists():
            print(f"⚠️  images/ 디렉토리를 찾을 수 없음: {images_dir}")
            return []

        # 이미지 파일 로드 (정렬된 순서)
        image_files = sorted(images_dir.glob("*.png")) + \
                      sorted(images_dir.glob("*.jpg")) + \
                      sorted(images_dir.glob("*.jpeg"))

        if len(image_files) == 0:
            print(f"⚠️  이미지 파일이 없음: {images_dir}")
            return []

        total_images = len(image_files)

        # 균등 샘플링
        if total_images < num_frames:
            indices = list(range(total_images))
        else:
            indices = np.linspace(0, total_images - 1, num_frames, dtype=int)

        frames = []
        for idx in indices:
            img = cv2.imread(str(image_files[idx]))
            if img is not None:
                frames.append(img)

        print(f"✅ 이미지 디렉토리에서 {len(frames)}개 프레임 추출 완료 (총 {total_images}개 중)")
        return frames

    # Case 2: 비디오 파일인 경우
    else:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames < num_frames:
            # 프레임 수가 부족하면 모든 프레임 사용
            indices = list(range(total_frames))
        else:
            # 균등 샘플링
            indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)

        cap.release()

        print(f"✅ 비디오에서 {len(frames)}개 프레임 추출 완료")
        return frames


def save_frames_to_temp(frames: List[np.ndarray], prefix: str = "rl_frames") -> str:
    """
    프레임을 임시 디렉토리에 저장

    Args:
        frames: 프레임 리스트
        prefix: 디렉토리 prefix

    Returns:
        임시 디렉토리 경로
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)

    for i, frame in enumerate(frames):
        frame_path = Path(temp_dir) / f"frame_{i:04d}.jpg"
        cv2.imwrite(str(frame_path), frame)

    return temp_dir


def compute_optical_flow(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """
    두 프레임 간 optical flow magnitude 계산

    Args:
        frame1, frame2: 연속된 프레임

    Returns:
        평균 motion magnitude
    """
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    flow = cv2.calcOpticalFlowFarneback(
        gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )

    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    return float(np.mean(magnitude))
