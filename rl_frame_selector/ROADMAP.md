# 🗺️ RL Frame Selector - 연구 로드맵

**마지막 업데이트**: 2025-11-13
**프로젝트 상태**: ✅ 인프라 구축 완료 → 🔬 실험 단계

---

## 📊 현재 상태

### ✅ 완료 항목 (2025-11-12 ~ 2025-11-13)

1. **핵심 인프라**
   - ✅ `phase1_surrogate/env.py`: Surrogate reward를 사용하는 Gymnasium 환경
   - ✅ `phase1_surrogate/train.py`: Multi-video 지원 PPO 학습
   - ✅ `utils/dataset_loader.py`: CO3Dv2/DTU/Custom 데이터셋 로더
   - ✅ `utils/quality_metrics.py`: Sharpness, BRISQUE, brightness 메트릭
   - ✅ `utils/overlap_utils.py`: SIFT 기반 overlap 계산

2. **문서화**
   - ✅ `RL_PROJECT_PROPOSAL.md`: CO3Dv2 마이그레이션 포함 학술 제안서
   - ✅ `QUICKSTART.md`: 5분 시작 가이드
   - ✅ `OVERLAP_FIX.md`: Overlap constraint 구현 설명
   - ✅ `CO3D_MIGRATION.md`: Zero-shot generalization 마이그레이션 가이드

3. **주요 기능**
   - ✅ Multi-video 학습 (episode마다 랜덤 비디오 선택)
   - ✅ 병렬 환경 (SubprocVecEnv, 4-8개 환경)
   - ✅ Overlap constraint (COLMAP 호환을 위한 max_gap=10)
   - ✅ Surrogate reward (temporal uniformity + quality + diversity + overlap)

---

## 🎯 다음 단계

### Priority 1: 즉시 실행 (오늘/이번 주)

#### 1.1 DTU Quick Test (30분) 완료

**목표**: End-to-end 구현 검증

**실행 커맨드**:
```bash
cd /data/vggt-gaussian-splatting-research/rl_frame_selector/phase1_surrogate

# 환경 활성화
source ../../env/vggt_env/bin/activate

# DTU 스캔으로 빠른 테스트
python train.py \
    --dataset dtu \
    --num-train-videos 3 \
    --num-eval-videos 1 \
    --total-timesteps 10000 \
    --n-envs 2 \
    --output-dir ./trained_models/dtu_quicktest \
    --tensorboard-log ./logs/dtu_quicktest
```

**예상 결과**:
- 에러 없이 학습 완료
- 최종 모델 저장: `./trained_models/dtu_quicktest/final_model.zip`
- Tensorboard 로그 생성
- Episode reward가 10k timesteps 동안 ~0.3 → ~0.5+ 증가

**성공 기준**:
- ✅ 데이터셋 로딩 에러 없음
- ✅ 환경 리셋 성공
- ✅ PPO agent가 크래시 없이 학습
- ✅ Reward가 상승 추세

---

#### 1.2 `evaluate.py` 생성 (필수)

**목표**: 학습된 모델을 새 비디오에서 테스트 (zero-shot evaluation)

**파일**: `./rl_frame_selector/evaluate.py`

**구현**:
```python
#!/usr/bin/env python3
"""
Zero-shot 평가 스크립트

사용법:
    python evaluate.py \
        --model ./trained_models/final_model.zip \
        --video /path/to/new/video.mp4 \
        --output-dir ./eval_results/video1
"""
import argparse
import json
import sys
sys.path.append('./phase1_surrogate')

from pathlib import Path
from stable_baselines3 import PPO
from env import FrameSelectionEnv


def evaluate_video(
    model_path: str,
    video_path: str,
    num_source_frames: int = 300,
    target_frames: int = 60,
    max_gap: int = 10,
    output_dir: str = None
):
    """
    단일 비디오에 대한 Zero-shot 평가

    반환값:
        dict: {
            'selected_frames': [0, 5, 10, ...],
            'final_reward': 0.75,
            'temporal_uniformity': 0.8,
            'avg_quality': 0.75,
            'diversity': 0.6,
            'overlap_score': 0.85,
            'num_frames': 60
        }
    """
    print(f"📹 비디오 로딩: {video_path}")

    # 학습된 모델 로드
    model = PPO.load(model_path)
    print(f"✅ 모델 로드 완료: {model_path}")

    # 환경 생성
    env = FrameSelectionEnv(
        video_path=video_path,
        num_source_frames=num_source_frames,
        target_frames=target_frames,
        max_gap=max_gap
    )

    # Episode 실행
    obs, _ = env.reset()
    selected_frames = []

    print(f"🎯 {num_source_frames}개 중 {target_frames}개 프레임 선택 중...")

    for step in range(num_source_frames):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)

        if action == 1:
            selected_frames.append(info['current_step'] - 1)

        if done or truncated:
            break

    # Info에서 최종 메트릭 추출
    results = {
        'video_path': video_path,
        'model_path': model_path,
        'selected_frames': selected_frames,
        'num_frames': len(selected_frames),
        'final_reward': float(reward),
        'temporal_uniformity': float(info.get('temporal_uniformity', 0)),
        'avg_quality': float(info.get('avg_quality', 0)),
        'diversity': float(info.get('diversity', 0)),
        'overlap_score': float(info.get('overlap_score', 0))
    }

    print("\n" + "="*70)
    print("📊 평가 결과")
    print("="*70)
    print(f"선택된 프레임: {len(selected_frames)}/{target_frames}")
    print(f"최종 Reward: {results['final_reward']:.4f}")
    print(f"  - Temporal Uniformity: {results['temporal_uniformity']:.4f}")
    print(f"  - 평균 Quality: {results['avg_quality']:.4f}")
    print(f"  - Diversity: {results['diversity']:.4f}")
    print(f"  - Overlap Score: {results['overlap_score']:.4f}")
    print("="*70)

    # 결과 저장
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results_file = output_path / "evaluation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 결과 저장: {results_file}")

        # 선택된 프레임 인덱스 저장
        frames_file = output_path / "selected_frames.txt"
        with open(frames_file, 'w') as f:
            f.write('\n'.join(map(str, selected_frames)))

        print(f"💾 프레임 인덱스 저장: {frames_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Zero-shot 평가')

    parser.add_argument('--model', type=str, required=True,
                       help='학습된 모델 경로 (.zip)')
    parser.add_argument('--video', type=str, required=True,
                       help='비디오 파일 또는 데이터셋 디렉토리 경로')
    parser.add_argument('--num-source-frames', type=int, default=300,
                       help='비디오에서 추출할 프레임 수')
    parser.add_argument('--target-frames', type=int, default=60,
                       help='선택할 프레임 수')
    parser.add_argument('--max-gap', type=int, default=10,
                       help='연속 선택 프레임 간 최대 gap')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='결과 저장 디렉토리 (선택)')

    args = parser.parse_args()

    evaluate_video(
        model_path=args.model,
        video_path=args.video,
        num_source_frames=args.num_source_frames,
        target_frames=args.target_frames,
        max_gap=args.max_gap,
        output_dir=args.output_dir
    )


if __name__ == '__main__':
    main()
```

**사용 예시**:
```bash
# 새 DTU 스캔에서 테스트
python evaluate.py \
    --model ./trained_models/dtu_quicktest/final_model.zip \
    --video ../datasets/DTU/scan37_standard \
    --output-dir ./eval_results/scan37

# 커스텀 비디오에서 테스트
python evaluate.py \
    --model ./trained_models/dtu_quicktest/final_model.zip \
    --video ../datasets/custom/cLectern.mp4 \
    --output-dir ./eval_results/cLectern
```

---

### Priority 2: 논문용 필수 (이번 주/다음 주)

#### 2.1 `baselines.py` 생성

**목표**: 비교를 위한 baseline 방법 구현

**파일**: `./rl_frame_selector/baselines.py`

**구현할 방법들**:

1. **Random Baseline**
   ```python
   def random_selection(frames, target_frames, seed=42):
       """랜덤하게 target_frames개 선택"""
       np.random.seed(seed)
       return sorted(np.random.choice(len(frames), target_frames, replace=False))
   ```

2. **Uniform Baseline**
   ```python
   def uniform_selection(frames, target_frames):
       """균등 간격으로 프레임 선택"""
       step = len(frames) / target_frames
       return [int(i * step) for i in range(target_frames)]
   ```

3. **Quality-based Baseline**
   ```python
   def quality_selection(frames, target_frames):
       """상위 품질 프레임 선택 (sharpness 기준)"""
       qualities = [compute_sharpness(f) for f in frames]
       top_indices = np.argsort(qualities)[-target_frames:]
       return sorted(top_indices)
   ```

4. **Stratified Baseline** (현재 최고 heuristic)
   ```python
   def stratified_selection(frames, target_frames, num_segments=10):
       """
       구간별로 나누고 각 구간에서 최고 품질 프레임 선택
       (원래 파이프라인에서 사용하는 baseline)
       """
       segment_size = len(frames) // num_segments
       selected = []

       for i in range(num_segments):
           start = i * segment_size
           end = start + segment_size
           segment = frames[start:end]

           # 구간 내 최고 품질 프레임 선택
           qualities = [compute_sharpness(f) for f in segment]
           best_idx = start + np.argmax(qualities)
           selected.append(best_idx)

       return sorted(selected[:target_frames])
   ```

**비교 스크립트**:
```python
def compare_baselines(video_path, output_dir):
    """
    단일 비디오에서 모든 baseline 비교

    출력:
        - 비교 표 (markdown)
        - 메트릭 JSON
        - 선택된 프레임 시각화
    """
    methods = {
        'Random': random_selection,
        'Uniform': uniform_selection,
        'Quality': quality_selection,
        'Stratified': stratified_selection
    }

    results = {}
    for name, method in methods.items():
        selected = method(frames, target_frames=60)
        reward = compute_surrogate_reward(frames, selected)
        results[name] = {
            'reward': reward,
            'selected_frames': selected
        }

    # 비교 표 생성
    print_comparison_table(results)

    # 결과 저장
    save_results(results, output_dir)
```

**예상 Baseline 성능** (CO3D_MIGRATION.md 기준):
```
| 방법          | Temporal | Quality | Diversity | Reward |
|--------------|----------|---------|-----------|--------|
| Random       | 0.3      | 0.5     | 0.6       | 0.45   |
| Uniform      | 0.9      | 0.4     | 0.3       | 0.52   |
| Quality-only | 0.2      | 0.9     | 0.4       | 0.50   |
| Stratified   | 0.7      | 0.7     | 0.5       | 0.63   |
| RL Agent     | 0.8      | 0.8     | 0.6       | 0.73   |  ← 목표
```

---

#### 2.2 본격 DTU 학습 (1-2시간)

**목표**: 더 많은 DTU 스캔으로 학습하여 일반화 성능 향상

**실행 커맨드**:
```bash
cd /data/vggt-gaussian-splatting-research/rl_frame_selector/phase1_surrogate

python train.py \
    --dataset dtu \
    --num-train-videos 10 \
    --num-eval-videos 2 \
    --total-timesteps 100000 \
    --n-envs 4 \
    --output-dir ./trained_models/dtu_10scans \
    --tensorboard-log ./logs/dtu_10scans
```

**성공 기준**:
- Episode reward가 0.7+ 수렴
- 평가 세트에서 모든 baseline 성능 초과
- 미학습 DTU 스캔에서 zero-shot 성능 확인

---

#### 2.3 실험 보고서 작성

**파일**: `./rl_frame_selector/EXPERIMENT_RESULTS.md`

**내용 구조**:
```markdown
# 실험 결과

## 설정
- 데이터셋: DTU (학습 10개 스캔, 평가 2개 스캔)
- 학습: 100k timesteps, 4개 병렬 환경
- 평가: 미학습 스캔에서 Zero-shot

## 결과

### 표 1: Baseline 비교 (DTU scan37)
| 방법       | Reward | Temporal | Quality | Diversity | Overlap |
|-----------|--------|----------|---------|-----------|---------|
| Random    | 0.45   | 0.30     | 0.50    | 0.60      | 0.40    |
| Uniform   | 0.52   | 0.90     | 0.40    | 0.30      | 0.85    |
| Quality   | 0.50   | 0.20     | 0.90    | 0.40      | 0.30    |
| Stratified| 0.63   | 0.70     | 0.70    | 0.50      | 0.70    |
| **RL Agent** | **0.73** | **0.80** | **0.80** | **0.60** | **0.85** |

### 그림 1: 학습 곡선
[Reward 수렴을 보여주는 Tensorboard 스크린샷]

### 표 2: Zero-shot 일반화
| 테스트 비디오 | RL Agent | 최고 Baseline | 개선율 |
|-------------|----------|--------------|--------|
| scan37      | 0.73     | 0.63         | +15.9% |
| scan40      | 0.71     | 0.61         | +16.4% |
| cLectern    | 0.69     | 0.58         | +19.0% |

## 논의
- RL agent가 다목적 최적화를 성공적으로 학습
- 모든 휴리스틱 baseline 성능 초과
- Zero-shot 일반화 달성
```

---

### Priority 3: 선택 사항 / 향후 작업

#### 3.1 Phase 2 구현

**목표**: 실제 3DGS 메트릭(PSNR/SSIM/LPIPS)으로 fine-tuning

**파일**: `./rl_frame_selector/phase2_finetune/finetune.py` (이미 존재)

**현재 상태**: 골격 구현 존재, 통합 필요

**구현 단계**:
1. `finetune.py`를 Phase 1 모델을 초기화로 사용하도록 수정
2. `run_3dgs_pipeline()` 통합 구현:
   ```python
   def run_3dgs_pipeline(selected_frames, dataset_dir):
       """
       실제 3DGS 파이프라인 실행 및 메트릭 반환

       단계:
           1. 선택된 프레임을 임시 디렉토리에 복사
           2. VGGT/COLMAP reconstruction 실행
           3. gsplat 1000 steps로 빠르게 학습
           4. PSNR/SSIM/LPIPS 반환

       반환값:
           dict: {'psnr': 19.5, 'ssim': 0.73, 'lpips': 0.21}
       """
       # run_pipeline.sh 사용 또는 파이프라인 스크립트 직접 호출
       pass
   ```

3. Reward 함수 업데이트:
   ```python
   # Phase 1: Surrogate reward (빠름)
   reward_phase1 = 0.2*temporal + 0.3*quality + 0.1*diversity + 0.4*overlap

   # Phase 2: 실제 3DGS 메트릭 (느리지만 정확)
   metrics = run_3dgs_pipeline(selected_frames, dataset_dir)
   reward_phase2 = metrics['psnr'] / 30.0  # [0, 1]로 정규화
   ```

4. Fine-tuning 전략:
   ```bash
   # Phase 1 모델 로드 및 실제 메트릭으로 fine-tune
   python finetune.py \
       --pretrained-model ../phase1_surrogate/trained_models/dtu_10scans/final_model.zip \
       --dataset dtu \
       --num-videos 5 \
       --total-timesteps 10000 \
       --pipeline P4  # 빠른 파이프라인 사용
   ```

**예상 결과**:
- Phase 1 reward: 0.73 (surrogate)
- Phase 2 fine-tuning 후: PSNR 19→20, SSIM 0.73→0.75

**참고**: Phase 2는 계산 비용이 높음 (~10분/episode). Phase 1 결과가 유망할 때만 진행.

---

#### 3.2 CO3Dv2 본격 학습

**목표**: 1000+ 비디오로 학습하여 진정한 zero-shot 일반화 달성

**사전 준비**:
1. CO3Dv2 데이터셋 다운로드 (100+ GB)
   ```bash
   # 지침 참고: https://github.com/facebookresearch/co3d
   # /data/co3d/ 에 압축 해제
   ```

2. 데이터셋 구조 확인:
   ```bash
   ls /data/co3d/
   # 결과: apple/ backpack/ ball/ banana/ ... (50개 카테고리)

   ls /data/co3d/apple/
   # 결과: 110_13051_23361/ ... (다수의 시퀀스)
   ```

**학습 커맨드**:
```bash
cd /data/vggt-gaussian-splatting-research/rl_frame_selector/phase1_surrogate

python train.py \
    --dataset co3d \
    --num-train-videos 1000 \
    --num-eval-videos 100 \
    --total-timesteps 500000 \
    --n-envs 8 \
    --output-dir ./trained_models/co3d_1k \
    --tensorboard-log ./logs/co3d_1k
```

**예상 소요 시간**: H100 GPU에서 1-2시간

**예상 결과**:
- 모든 비디오(DTU, CO3D, custom)에서 zero-shot 성능
- 다양한 물체 카테고리, 조명, 시점에 걸쳐 일반화
- WACV 2026 제출 준비 완료

**성공 기준**:
- ✅ 50개 카테고리에서 1000+ 비디오로 학습
- ✅ 미학습 카테고리에서 zero-shot 평가
- ✅ 다양한 테스트 세트에서 baseline 초과 성능
- ✅ 공개 데이터셋 사용으로 재현 가능한 결과

---

## 📋 체크리스트 요약

### 즉시 실행 (오늘)
- [ ] DTU quick test 실행 (10k timesteps, 3개 스캔)
- [ ] `evaluate.py` 스크립트 생성
- [ ] 미학습 DTU 스캔에서 zero-shot 평가 테스트

### 이번 주
- [ ] 4가지 baseline 방법으로 `baselines.py` 생성
- [ ] 본격 DTU 학습 실행 (100k timesteps, 10개 스캔)
- [ ] RL agent vs baselines 비교
- [ ] `EXPERIMENT_RESULTS.md` 생성

### 선택 사항 / 향후
- [ ] Phase 2 fine-tuning 구현 (실제 3DGS 메트릭)
- [ ] CO3Dv2 데이터셋 다운로드
- [ ] CO3Dv2로 학습 (1000개 비디오)
- [ ] WACV 2026 제출

---

## 🎓 학술 마일스톤

### 최소 논문 요구사항
- ✅ 새로운 문제: RL 기반 적응형 프레임 선택
- ✅ 기술적 기여: Overlap-aware MDP 공식화
- ⏳ 실험 검증: RL agent > baselines
- ⏳ Zero-shot 일반화: DTU 학습 → custom 비디오 테스트

### 강력한 논문 (WACV 2026 목표)
위 요구사항 + 추가:
- ⏳ 대규모 학습: CO3Dv2 (1000+ 비디오)
- ⏳ Phase 2 결과: 실제 3DGS 메트릭
- ⏳ Ablation 연구: Overlap constraint, reward 구성 요소
- ⏳ 재현성: 공개 데이터셋, 오픈소스 코드

---

## 📚 주요 참고 자료

1. **RL_PROJECT_PROPOSAL.md**: 전체 방법론 포함 학술 제안서
2. **CO3D_MIGRATION.md**: Zero-shot 일반화 마이그레이션 가이드
3. **QUICKSTART.md**: 5분 시작 가이드
4. **OVERLAP_FIX.md**: Overlap constraint 구현 세부사항
5. **../docs/workflows/20251112_VGGT-GSplat_WorkFlow.md**: 구현 과정 문서

---

## 🚀 빠른 시작 (복사-붙여넣기 커맨드)

```bash
# 1. DTU Quick Test (30분)
cd /data/vggt-gaussian-splatting-research/rl_frame_selector/phase1_surrogate
source ../../env/vggt_env/bin/activate

python train.py \
    --dataset dtu \
    --num-train-videos 3 \
    --num-eval-videos 1 \
    --total-timesteps 10000 \
    --n-envs 2 \
    --output-dir ./trained_models/dtu_quicktest \
    --tensorboard-log ./logs/dtu_quicktest

# 2. 학습 모니터링 (새 터미널)
tensorboard --logdir ./logs/dtu_quicktest --port 6006

# 3. evaluate.py 생성 (TODO: 먼저 구현)
# python ../evaluate.py \
#     --model ./trained_models/dtu_quicktest/final_model.zip \
#     --video ../../datasets/DTU/scan37_standard \
#     --output-dir ./eval_results/scan37

# 4. 본격 학습 (1-2시간)
python train.py \
    --dataset dtu \
    --num-train-videos 10 \
    --num-eval-videos 2 \
    --total-timesteps 100000 \
    --n-envs 4 \
    --output-dir ./trained_models/dtu_10scans \
    --tensorboard-log ./logs/dtu_10scans
```

---

**마지막 업데이트**: 2025-11-13
**다음 리뷰**: DTU quick test 완료 후
