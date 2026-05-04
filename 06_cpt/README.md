# 06_cpt — CPT 중형 모델 학습

**담당자**: 김승환
**실행자**: 박수형 (수형님 서버에서 일괄 실행 예정)

수형님이 정리하신 통합 데이터(8분야, peS2o 스키마)를 입력으로,
80~85% 과학 + 15~20% 일반 비율로 데이터 믹싱하여 CPT 중형 모델을 학습합니다.

---

## 1. 설치

```bash
cd 06_cpt
pip install -r requirements.txt
```

## 2. 설정 (`config.yaml` 수정)

수정해야 할 부분은 4곳입니다:

| 항목 | 위치 | 설명 |
|------|------|------|
| `data.path` | 데이터 | 수형님 서버의 통합 데이터 경로 |
| `data.science_source_values` | 데이터 | 통합본의 source 필드에서 "과학"으로 간주할 값 (기본: `["pes2o_or_crawled"]`) |
| `data.general_source_values` | 데이터 | source 필드에서 "일반"으로 간주할 값 (없으면 빈 리스트) |
| `model.base` | 모델 | 중형 모델 베이스 (현재 미정 — 결정되면 한 줄 수정) |

데이터 포맷 자동 인식:
- HF `save_to_disk` 디렉토리 (`dataset_info.json` 포함)
- `.parquet` 단일 파일 또는 디렉토리
- `.jsonl` 단일 파일 또는 디렉토리

## 3. 실행

```bash
# 단일 GPU
bash run.sh

# 멀티 GPU (예: 4장)
CUDA_VISIBLE_DEVICES=0,1,2,3 bash run.sh
```

## 4. 결과

- 체크포인트: `./checkpoints/checkpoint-<step>/`
- 최종 모델: `./checkpoints/final/`

---

## 데이터 믹싱 동작 (자동)

`data_loader.py`가 통합 데이터를 읽으면서 비율을 검증·보정합니다:

| 상황 | 동작 |
|------|------|
| 비율 80~85% 안에 있음 | 그대로 진행 |
| 과학 > 85% | (1) 일반 HF 데이터셋(`HuggingFaceFW/fineweb`) 보충 → 안 되면 (2) 과학 다운샘플 |
| 과학 < 80% | (1) 과학 HF 데이터셋(`allenai/peS2o`) 보충 → 안 되면 (2) 일반 다운샘플 |
| `auto_balance: false` | 보정 없이 경고만 띄우고 진행 |

콘솔에 비율 변화가 출력되니 학습 시작 전에 한 번 보고 이상 있으면 중단 가능합니다.

### 두 가지 모드 — `auto_balance` 토글

승환님이 "조건문으로 처리해줄래?"라고 요청하셨을 때 해석이 둘 가능했음:

- **🅰️ 검증만 모드** — "80/20 맞나 확인하고 안 맞으면 경고"
- **🅱️ 보정까지 모드** — "안 맞으면 HF에서 자동 보충해서 맞춤"

→ 기본은 **🅱️ (`auto_balance: true`)** 로 깔아뒀고, **🅰️ 동작**을 원하면 `config.yaml`에서 한 줄만 바꾸면 됩니다:

```yaml
data:
  mixing:
    auto_balance: false   # ← true(보정) / false(검증만)
```

`false`로 두면 비율이 안 맞아도 HF 다운로드 없이 그대로 진행하고, 콘솔에 경고만 띄워요.
수형님 통합 데이터가 이미 신뢰할 만하다면 `false`로 두는 것도 안전한 선택입니다.

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|------------|
| `KeyError: 'source'` | `data.path`의 데이터에 `source` 필드 없음 → `config.yaml`의 `data.source_field` 또는 데이터 확인 |
| OOM (메모리 부족) | `per_device_batch_size: 1` 유지 + `gradient_accumulation_steps` 증가, `max_seq_length` 축소 |
| HF 보충 다운로드 느림/실패 | `mixing.fallback_streaming: true` 확인, 또는 `auto_balance: false`로 보충 비활성화 |
| 모델 로드 실패 | `model.base`가 HF에 존재하는 경로인지, 토큰 인증(필요 시 `huggingface-cli login`) |

---

## 파일 구성

```
06_cpt/
├── config.yaml          # 설정 (모델·데이터·학습)
├── data_loader.py       # peS2o 로드 + 80/20 비율 동적 보정
├── train.py             # HF Trainer 학습 진입점
├── run.sh               # 단일/멀티 GPU 실행 래퍼
├── requirements.txt     # Python 의존성
└── README.md            # 이 파일
```
