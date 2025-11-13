#!/usr/bin/env python3
"""
이미지 품질 평가 메트릭
"""
import cv2
import numpy as np
from skimage import color, filters
from typing import Dict


def compute_sharpness(frame: np.ndarray) -> float:
    """
    Laplacian variance로 선명도 측정
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()

    # 0-1 정규화 (휴리스틱)
    normalized = min(variance / 1000.0, 1.0)
    return float(normalized)


def compute_brisque_simple(frame: np.ndarray) -> float:
    """
    BRISQUE 간단 버전 (local contrast 기반)
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = gray.astype(float) / 255.0

    # Local mean and std
    mu = cv2.GaussianBlur(gray, (7, 7), 1.5)
    mu_sq = mu * mu
    sigma = cv2.GaussianBlur(gray * gray, (7, 7), 1.5) - mu_sq
    sigma = np.sqrt(np.abs(sigma))

    # Normalized quality
    quality = 1.0 / (1.0 + sigma.std())
    return float(quality)


def compute_brightness(frame: np.ndarray) -> float:
    """
    밝기 측정
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean() / 255.0)


def compute_all_metrics(frame: np.ndarray) -> Dict[str, float]:
    """
    모든 품질 메트릭 계산

    Returns:
        {'sharpness': ..., 'brisque': ..., 'brightness': ...}
    """
    return {
        'sharpness': compute_sharpness(frame),
        'brisque': compute_brisque_simple(frame),
        'brightness': compute_brightness(frame)
    }
