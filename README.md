# Biology Classic Corpus (1970-1999)

**생명과학 고전 논문 데이터셋 구축 프로젝트**

Semantic Scholar API를 활용하여 1970~1999년 생명과학 분야 논문 메타데이터 및 초록을 수집하고, CPT(Continual Pre-Training) 학습용 데이터셋을 구축합니다.

---

## Project Pipeline Overview

이 프로젝트는 **과학 추론 LLM** 개발을 위한 전체 파이프라인의 일부입니다.

```
Phase 1: Data Construction (데이터 구축)
  ├─ CPT Raw Data ← 현재 이 저장소의 작업 범위
  │   ├─ 논문 수집 (arXiv, Semantic Scholar, PMC)
  │   ├─ 교과서 (OpenStax, LibreTexts)
  │   └─ 강의노트 (MIT OCW, NPTEL)
  └─ SFT Synthetic Data
      └─ Teacher 모델(GPT-4o)로 과학 Q&A 합성 (<think>/<answer> 포맷)
         ↓
Phase 2: Continual Pre-Training (CPT)
  └─ 베이스 모델(Nemotron)에 과학 도메인 지식 주입
     - 데이터 믹싱: 과학 80~85% + 일반 15~20%
     - Objective: Next-token prediction
         ↓
Phase 3: SFT + Reinforcement Learning (GDPO)
  ├─ SFT: <think>/<answer> 구조화된 추론 학습
  └─ GDPO: Multi-Reward 강화학습
      ├─ R_RaR (Rubric): LLM Judge 기반 (수식 정확성, 환각 없음, 논리적 인과관계)
      ├─ R_Format: <think>/<answer> 태그 준수 여부 (룰베이스)
      └─ R_Penalty: 토큰 길이 초과 감점 (룰베이스)
```

### 역할 분담

| 단계 | 역할 | 담당 |
|------|------|------|
| Phase 1 | 데이터 수집 | 전원 (분야별 분담) |
| Phase 2 | CPT 중형 모델 | 승환 |
| Phase 2 | CPT 소형 모델 | 진혁 |
| Phase 2 | CPT Nemotron | 다영 |
| Phase 3 | SFT 중형 모델 | 인헌 |
| Phase 3 | SFT 소형 모델 | 채윤 |
| Phase 3 | RL 중형 모델 | 성민 |
| Phase 3 | RL 소형 모델 | 채연 |

### 데이터 수집 분담

| 분야 | 고전 (1970~1999) | 현대 (2000~2022) |
|------|-----------------|-----------------|
| 물리 | 수형 | 채연 |
| 화학 | 인헌 | 진혁 |
| **생명** | **승환 (이 저장소)** | 성민 |
| 우주과학 | 다영 | 채윤 |

---

## Overview

| 항목 | 내용 |
|------|------|
| **수집 기간** | 1970 ~ 1999 |
| **대상 분야** | Biology, Molecular Biology, Cell Biology, Genetics, Biochemistry 등 |
| **데이터 소스** | Semantic Scholar Academic Graph API (bulk search) |
| **출력 형식** | Apache Parquet (.parquet) |
| **제외 분야** | Medicine, Healthcare, Clinical Studies |

---

## Project Structure

```
psedu/
│
├── 01_planning/                    # 프로젝트 계획
│   └── roadmap.md                  # 전체 로드맵 및 마일스톤
│
├── 02_review/                      # 자료 검토
│   └── review_notes.md             # 원본 자료 검토 및 수정 제안
│
├── 03_keywords/                    # 키워드 정의
│   └── keywords.md                 # 검색 키워드 및 분야 정의
│
├── 04_crawler/                     # 크롤러 코드
│   ├── config.py                   # 설정 (경로, API, 키워드, 스키마)
│   ├── utils.py                    # 유틸리티 함수
│   ├── semantic_scholar_crawler.py # Semantic Scholar 크롤러
│   ├── deduplicator.py             # 중복 제거 모듈
│   └── main.py                     # 메인 실행 파일
│
├── 05_data/                        # 데이터 저장소
│   ├── raw/                        # 원본 수집 데이터
│   └── processed/                  # 전처리 완료 데이터
│
├── requirements.txt                # Python 의존성
├── status_report.md                # 현재 진행 현황
└── README.md                       # 이 파일
```

---

## Quick Start

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/7SH7/psedu.git
cd psedu

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. API Key 설정 (선택사항)

Semantic Scholar API Key가 있으면 rate limit이 완화됩니다.

```bash
# 환경변수로 설정
export S2_API_KEY="your_api_key_here"

# 또는 실행 시 직접 전달
python main.py --api-key "your_api_key_here"
```

> API Key 신청: https://www.semanticscholar.org/product/api

### 3. 크롤링 실행

```bash
cd 04_crawler

# 전체 파이프라인 실행 (크롤링 → 중복제거 → 통계)
python main.py --mode all

# 또는 단계별 실행
python main.py --mode crawl   # 크롤링만
python main.py --mode dedup   # 중복 제거만
python main.py --mode stats   # 통계 확인
```

### 4. 옵션

```bash
# 쿼리당 최대 수집 건수 조절 (기본: 10000)
python main.py --mode crawl --max-per-query 5000
```

---

## Data Schema

수집된 데이터는 팀 공용 스키마를 따릅니다:

| 필드 | 타입 | 설명 |
|------|------|------|
| `record_id` | string | 고유 레코드 ID |
| `paper_id` | string | 논문 ID (해시 기반) |
| `source` | string | 데이터 소스 (semantic_scholar) |
| `source_paper_id` | string | 원본 소스의 논문 ID |
| `title` | string | 논문 제목 |
| `abstract` | string | 초록 |
| `authors` | list | 저자 목록 |
| `year` | int | 출판 연도 |
| `categories` | list | 분야 카테고리 |
| `doi` | string | DOI |
| `arxiv_id` | string | arXiv ID (있는 경우) |
| `citation_count` | int | 인용 수 |
| `pdf_url` | string | PDF URL (Open Access) |
| `is_duplicate` | bool | 중복 여부 |
| `is_excluded_medical` | bool | 의료 콘텐츠 제외 여부 |
| `crawl_date` | string | 수집 일시 (ISO 8601) |

---

## Current Status

> 상세 현황은 [status_report.md](status_report.md) 참고

| 항목 | 수치 |
|------|------|
| 원본 수집 | 261,934건 |
| 중복 제거 후 | 246,980건 |
| Abstract 확보 | 13,251건 (5.4%) |
| Full-text | 0건 |

---

## Target Domains

### 수집 대상 분야

- **Molecular Biology** - 분자생물학
- **Cell Biology** - 세포생물학
- **Genetics** - 유전학
- **Biochemistry** - 생화학
- **Microbiology** - 미생물학
- **Evolutionary Biology** - 진화생물학
- **Ecology** - 생태학
- **Developmental Biology** - 발생생물학
- **Neuroscience** (기초) - 신경과학
- **Botany / Plant Biology** - 식물생물학

### 제외 대상

- Clinical trials, Patient studies
- Drug therapy, Pharmaceutical
- Medical devices, Surgery
- Healthcare, Hospital studies

---

## Output

| 파일 | 위치 | 설명 |
|------|------|------|
| `biology_classic_raw.parquet` | `05_data/raw/` | 원본 수집 데이터 |
| `biology_classic_deduped.parquet` | `05_data/processed/` | 중복 제거 + 필터링 완료 |
| `crawl_progress.json` | `05_data/raw/` | 크롤링 진행 상황 (재시작용) |

---

## Related Projects

이 프로젝트는 **과학 추론 LLM 개발**을 위한 데이터 구축 프로젝트의 일부입니다.

| 분야 | 담당 | 기간 |
|------|------|------|
| 물리 (고전) | 수형 | 1970~1999 |
| 물리 (현대) | 채연 | 2000~2022 |
| 화학 (고전) | 인헌 | 1970~1999 |
| 화학 (현대) | 진혁 | 2000~2022 |
| **생명 (고전)** | **승환** | **1970~1999** |
| 생명 (현대) | 성민 | 2000~2022 |
| 우주과학 (고전) | 다영 | 1970~1999 |
| 우주과학 (현대) | 채윤 | 2000~2022 |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Semantic Scholar](https://www.semanticscholar.org/) - Academic Graph API
- [가짜연구소](https://pseudo-lab.com/) - 프로젝트 지원
