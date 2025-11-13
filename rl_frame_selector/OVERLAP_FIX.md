# 🔧 Overlap 제약 수정 사항

## 문제점 발견

**원래 설계의 치명적 결함**:
- RL agent가 300프레임에서 자유롭게 60개 선택
- 프레임 간 gap이 너무 크면 **overlap 없음** → COLMAP 실패!

**예시**:
```python
# RL이 이렇게 선택하면?
selected = [0, 50, 100, 150, 200, 250]  # Gap 50프레임!
→ COLMAP feature matching 실패 → 3DGS 불가능
```

---

## 해결 방법

### 1. Hard Constraint: max_gap

연속 선택 프레임 간 최대 gap 제한:

```python
class FrameSelectionEnv:
    def __init__(self, ..., max_gap=10):
        self.max_gap = max_gap  # 10프레임 이내 선택 필수

    def step(self, action):
        if action == SELECT:
            gap = current_frame - last_selected
            if gap > max_gap:
                reward = -5.0  # 큰 페널티!
                return # 강제 SKIP
```

**효과**: Overlap 물리적으로 보장

---

### 2. Soft Reward: SIFT Overlap Score

Reward에 overlap 메트릭 추가:

```python
def _compute_final_reward(self):
    # 기존 메트릭
    temporal_uniformity = ...  # 20%
    avg_quality = ...  # 30%
    diversity = ...  # 10%

    # 새로 추가!
    overlap_score = compute_sift_matches()  # 40% ← 가장 중요!

    reward = (
        0.2 * temporal_uniformity +
        0.3 * avg_quality +
        0.1 * diversity +
        0.4 * overlap_score
    )
```

**효과**: RL이 overlap 높이는 방향으로 학습

---

## 수정된 파일

### 1. `utils/overlap_utils.py` (NEW)

SIFT feature matching 기반 overlap 계산:

```python
def compute_sift_matches(frame1, frame2):
    """
    두 프레임 간 SIFT feature 매칭 수 계산
    Returns: 매칭 개수 (50+ = 좋음, 100+ = 매우 좋음)
    """
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(frame1, None)
    kp2, des2 = sift.detectAndCompute(frame2, None)

    matches = bf.knnMatch(des1, des2, k=2)
    good_matches = [m for m,n in matches if m.distance < 0.75*n.distance]

    return len(good_matches)
```

### 2. `phase1_surrogate/env.py` (UPDATED)

**변경사항**:
- `max_gap` 파라미터 추가 (default: 10)
- `step()`에 gap 체크 로직 추가
- `_compute_final_reward_with_overlap()` - overlap score 40% 반영

**주요 로직**:
```python
def step(self, action):
    if action == SELECT and gap > max_gap:
        reward = -5.0  # 페널티
        return  # 강제 SKIP
```

### 3. `phase1_surrogate/train.py` (UPDATED)

**추가된 인자**:
```bash
--max-gap 10  # 최대 gap (default: 10)
```

**사용 예시**:
```bash
# 보수적 (overlap 강화)
python train.py --videos video.mp4 --max-gap 5

# 균형 (권장)
python train.py --videos video.mp4 --max-gap 10

# 자유로움 (성능 위험)
python train.py --videos video.mp4 --max-gap 20
```

---

## max_gap 선택 가이드

| max_gap | Overlap | 자유도 | 권장 상황 |
|---------|---------|--------|-----------|
| 5 | ★★★★★ | ★ | DTU (정적, 고해상도) |
| 10 | ★★★★ | ★★★ | **일반적 (권장)** |
| 15 | ★★★ | ★★★★ | 빠른 움직임 비디오 |
| 20 | ★★ | ★★★★★ | 실험용 (위험) |

**권장**: `max_gap=10` (60개 선택 시 평균 5프레임 간격)

---

## 예상 개선 효과

### Before (Unconstrained RL)
```
Selected: [5, 50, 95, 140, 185, 230, 275]  # Gap 45프레임
Overlap: ❌ 30 matches/pair
COLMAP: 50% success
PSNR: N/A (실패)
```

### After (Constrained RL, max_gap=10)
```
Selected: [5, 12, 19, 26, 33, ...]  # Gap 5-10프레임
Overlap: ✅ 80+ matches/pair
COLMAP: 100% success
PSNR: 18.5+
```

---

## 검증 방법

### 1. Overlap Score 확인

학습 중 로그:
```
🔍 Overlap 계산 중... (SIFT matching)
   Overlap score: 0.78  # 0.7+ 이면 성공!
   Temporal uniformity: 0.85
   Avg quality: 0.72
   Diversity: 0.42
   → Final reward: 0.74
```

### 2. Gap 분포 확인

```python
gaps = np.diff(sorted(selected_indices))
print(f"Gap 분포: min={gaps.min()}, max={gaps.max()}, mean={gaps.mean()}")
# 목표: max <= 10, mean ~5
```

### 3. COLMAP 성공률 (Phase 2)

```bash
# 실제 3DGS 파이프라인 실행
./run_pipeline.sh P4 selected_frames_dir

# analysis.json 확인
cat results/.../analysis.json
# "num_registered_images": 60  # 모두 등록되어야 함!
```

---

## 추가 개선 아이디어

### 1. Adaptive max_gap

비디오 움직임에 따라 동적 조정:
```python
# 빠른 움직임 → max_gap 증가
# 정적 장면 → max_gap 감소
```

### 2. Local Optimization

각 구간에서 최적 프레임 미세 조정:
```python
# 10프레임 window 내에서 SIFT 최대화
```

### 3. Multi-objective RL

Overlap + Quality 동시 최적화:
```python
reward = pareto_front(overlap, quality)
```

---

## 결론

✅ **Overlap 제약 반영 완료**
- Hard constraint (max_gap) + Soft reward (SIFT score)
- COLMAP 성공률 100% 목표
- 실용적인 RL 프레임 선택 시스템

**다음 단계**: Phase 1 학습 실행 후 overlap score 검증!
