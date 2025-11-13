#!/usr/bin/env python3
"""
Overlap 및 Feature Matching 유틸리티
"""
import cv2
import numpy as np
from typing import List


def compute_sift_matches(frame1: np.ndarray, frame2: np.ndarray,
                         ratio_threshold: float = 0.75) -> int:
    """
    두 프레임 간 SIFT feature matching 수 계산

    Args:
        frame1, frame2: 연속 프레임
        ratio_threshold: Lowe's ratio test threshold

    Returns:
        Good matches 개수
    """
    # Grayscale 변환
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # SIFT feature detection
    sift = cv2.SIFT_create(nfeatures=500)  # 속도를 위해 500개 제한
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
        return 0

    # BFMatcher
    bf = cv2.BFMatcher()
    try:
        matches = bf.knnMatch(des1, des2, k=2)
    except Exception:
        return 0

    # Lowe's ratio test
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

    return len(good_matches)


def compute_pairwise_overlap(frames: List[np.ndarray],
                             selected_indices: List[int]) -> float:
    """
    선택된 프레임들의 pairwise overlap score 계산

    Args:
        frames: 전체 프레임 리스트
        selected_indices: 선택된 프레임 인덱스

    Returns:
        평균 overlap score (0-1, 높을수록 좋음)
    """
    if len(selected_indices) < 2:
        return 0.0

    overlap_scores = []

    for i in range(len(selected_indices) - 1):
        idx1 = selected_indices[i]
        idx2 = selected_indices[i + 1]

        frame1 = frames[idx1]
        frame2 = frames[idx2]

        num_matches = compute_sift_matches(frame1, frame2)
        overlap_scores.append(num_matches)

    # 평균 매칭 수
    avg_matches = np.mean(overlap_scores)

    # 정규화 (50+ matches = 매우 좋음, 100+ = 완벽)
    normalized = min(avg_matches / 100.0, 1.0)

    return float(normalized)


def estimate_min_gap_for_overlap(frame1: np.ndarray, frame2: np.ndarray,
                                 frames_between: List[np.ndarray],
                                 min_matches: int = 30) -> int:
    """
    Overlap을 유지하기 위한 최소 프레임 gap 추정

    Args:
        frame1: 시작 프레임
        frame2: 끝 프레임
        frames_between: 중간 프레임들
        min_matches: 필요한 최소 매칭 수

    Returns:
        권장 최대 gap
    """
    # 연속 프레임 간 매칭 수 계산
    consecutive_matches = []

    all_frames = [frame1] + frames_between + [frame2]
    for i in range(len(all_frames) - 1):
        matches = compute_sift_matches(all_frames[i], all_frames[i+1])
        consecutive_matches.append(matches)

    # 평균 연속 매칭 수
    avg_consecutive = np.mean(consecutive_matches)

    # 최소 매칭을 유지하는 gap 추정
    if avg_consecutive > min_matches:
        # Gap 1당 매칭 감소율
        decay_rate = avg_consecutive / len(frames_between)
        max_gap = int(min_matches / decay_rate)
    else:
        max_gap = 1  # 매우 보수적

    return max(1, min(max_gap, 15))  # 1-15 범위로 제한


def check_colmap_feasibility(frames: List[np.ndarray],
                             selected_indices: List[int],
                             min_matches: int = 30) -> bool:
    """
    선택된 프레임들이 COLMAP으로 재구성 가능한지 체크

    Args:
        frames: 전체 프레임 리스트
        selected_indices: 선택된 프레임 인덱스
        min_matches: 필요한 최소 매칭 수

    Returns:
        True if feasible, False otherwise
    """
    if len(selected_indices) < 2:
        return False

    for i in range(len(selected_indices) - 1):
        idx1 = selected_indices[i]
        idx2 = selected_indices[i + 1]

        frame1 = frames[idx1]
        frame2 = frames[idx2]

        num_matches = compute_sift_matches(frame1, frame2)

        if num_matches < min_matches:
            return False

    return True
