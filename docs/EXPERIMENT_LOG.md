# 🧪 **VGGT-Gaussian Splatting 실험 로그**

> **업데이트 방법**: 새로운 실험마다 상단에 추가 (최신이 위로)

---

## 📅 **2025-09-03: 프로젝트 초기 설정**

### **Context Restore Script 개발**
- **Status**: ✅ Complete
- **File**: `/workspace/context_restore.sh`
- **Purpose**: 세션 재시작 시 빠른 상황 파악
- **Usage**: `./context_restore.sh`
- **Result**: 
  - GPU: RTX 6000 Ada (49GB VRAM)
  - Dataset: book 80/200 frames (VRAM 제한)
  - Checkpoint: ckpt_49999_rank0.pt 존재 확인

### **연구 전략 수립**
- **Status**: ✅ Complete
- **Files**: 
  - `/workspace/20250903 VGGT-GSplat Research WORKFLOW.md`
  - `/workspace/VRAM_ANALYSIS_20250903.md`
- **Key Findings**:
  - RTX 6000 Ada VRAM 제약: 200→80 frames
  - 목표: 메모리 최적화로 150+ frames 달성
  - 타겟: WACV 2025 submission
- **Next**: 80-frame baseline 테스트

---

## 📝 **실험 템플릿**

### **실험명: [날짜] [실험내용]**
- **Status**: 🔄 In Progress / ✅ Complete / ❌ Failed
- **Objective**: 실험 목표
- **Method**: 사용한 방법/코드
- **Results**: 
  - Quantitative: 수치 결과
  - Qualitative: 관찰 결과
- **Memory**: Peak VRAM usage
- **Time**: Processing time
- **Issues**: 발생한 문제들
- **Next Steps**: 다음 실험 계획

---

## 🎯 **Pending Experiments**

### **EXP-001: 50K PLY Model Extraction**
- **Objective**: ckpt_49999_rank0.pt → PLY 변환
- **Command**: `python export_ply.py --checkpoint ckpt_49999_rank0.pt`
- **Expected**: ~476MB PLY file with 2M+ Gaussians
- **Status**: 🔄 Pending

### **EXP-002: 80-Frame Baseline Test**
- **Objective**: 현재 80-frame 처리 재현
- **Dataset**: book (80 images)
- **Pipeline**: P5_full (VGGT + BA + gsplat)
- **Status**: 🔄 Pending

### **EXP-003: Memory Profiling**
- **Objective**: 각 단계별 VRAM 사용량 측정
- **Tools**: nvidia-smi, torch profiler
- **Stages**: VGGT → BA → gsplat
- **Status**: 🔄 Pending

---

## 📊 **Results Summary**

| Exp ID | Date | Frames | VRAM (GB) | Time (min) | PSNR | Status |
|--------|------|--------|-----------|------------|------|--------|
| - | - | - | - | - | - | - |

---

## 💡 **Insights & Learnings**

### **VRAM Optimization Insights**
- RTX 6000 Ada: 49,140 MiB total VRAM
- Current limit: 80 frames (실제 경험)
- Optimization targets: bf16, gradient checkpointing

### **Technical Notes**
- book dataset: 실제로는 80개 이미지 (200개 아님)
- Environment: VGGT + gsplat 분리 환경 필요

---

## 🔄 **Quick Update Commands**

```bash
# 새 실험 시작시
echo "### **EXP-XXX: [실험명]**
- **Date**: $(date +%Y-%m-%d)
- **Status**: 🔄 In Progress
- **Objective**: [목표]
- **Command**: \`[실행명령]\`" >> /workspace/EXPERIMENT_LOG.md

# 실험 완료시  
echo "- **Results**: [결과]
- **VRAM**: [메모리사용량]
- **Status**: ✅ Complete" >> /workspace/EXPERIMENT_LOG.md
```

---

**Last Updated**: 2025-09-03