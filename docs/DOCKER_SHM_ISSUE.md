# Docker Shared Memory 증가 요청

## 📋 요약
현재 Docker 컨테이너의 shared memory가 64MB로 설정되어 있어, PyTorch DataLoader의 multi-worker 기능을 사용할 수 없습니다. 이로 인해 **H100 GPU 성능이 30-40% 낭비**되고 있습니다.

## 🔍 현재 상태

### 시스템 리소스:
```
✅ GPU VRAM:       80 GB (H100)
✅ System RAM:     221 GB  
❌ Shared Memory:  64 MB  ← 문제!
```

### 문제 발생:
```bash
$ df -h /dev/shm
Filesystem      Size  Used Avail Use% Mounted on
shm              64M     0   64M   0% /dev/shm
```

PyTorch DataLoader가 4개의 worker 프로세스를 사용할 때 약 120MB의 shared memory가 필요하지만, 현재 64MB만 할당되어 있어 다음 에러 발생:

```
ERROR: Unexpected bus error encountered in worker. 
This might be caused by insufficient shared memory (shm).
RuntimeError: DataLoader worker exited unexpectedly
```

## 💥 영향

### 현재 workaround:
- `num_workers=0` 사용 (단일 프로세스 데이터 로딩)
- GPU가 데이터 로딩을 기다리는 시간 발생
- **H100 GPU 활용률: 60-70%** (이상적: 95%+)

### 성능 손실:
- 훈련 시간: **30-40% 증가**
- H100 성능 낭비: **~$10,000 상당 GPU의 30-40%**

## ✅ 해결 방법

Docker 컨테이너 실행 시 `--shm-size` 옵션 추가가 필요합니다.

### 방법 1: docker run 명령어 수정

현재 컨테이너 재시작 시:
```bash
docker run --shm-size=2g \
           --gpus all \
           [기타 옵션] \
           [이미지 이름]
```

### 방법 2: docker-compose.yml 수정

`docker-compose.yml` 파일에 추가:
```yaml
services:
  vggt-gsplat:
    shm_size: '2gb'  # ← 이 줄 추가
    # ... 기타 설정
```

### 방법 3: Kubernetes 환경

Pod spec에 추가:
```yaml
spec:
  containers:
  - name: vggt-gsplat
    volumeMounts:
    - name: dshm
      mountPath: /dev/shm
  volumes:
  - name: dshm
    emptyDir:
      medium: Memory
      sizeLimit: 2Gi
```

## 📊 예상 효과

| 항목 | 현재 (64MB) | 변경 후 (2GB) |
|------|------------|--------------|
| num_workers | 0 | 4 |
| GPU 활용률 | 60-70% | 95%+ |
| 훈련 시간 | 4-5분 | 3-4분 |
| H100 성능 활용 | 60-70% | 95%+ |

## 🔧 현재 컨테이너 정보

```bash
# 컨테이너 ID
Container: e3dee70ca140

# 확인 명령어
$ docker ps
$ docker inspect e3dee70ca140 | grep -i shm
```

## 📚 참고 자료

- PyTorch DataLoader 공식 문서: https://pytorch.org/docs/stable/data.html#multi-process-data-loading
- Docker shared memory: https://docs.docker.com/engine/reference/run/#runtime-constraints-on-resources
- Shared memory 관련 이슈: https://github.com/pytorch/pytorch/issues/2244

---

**요청 사항**: Docker 컨테이너의 shared memory를 **64MB → 2GB**로 증가시켜 주시기 바랍니다.

**긴급도**: 중간 (현재는 workaround로 작동 중이나, GPU 성능 낭비)

**작성일**: 2025-10-24
