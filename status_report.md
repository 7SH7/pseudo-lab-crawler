# 생명과학 고전(1970~1999) 데이터 수집 현황 보고

## 담당자: 김승환
## 작성일: 2026-04-03

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **역할** | CPT 중형 모델 담당 (데이터 수집 → CPT 학습) |
| **수집 대상** | 생명과학 고전 논문 (1970~1999) |
| **데이터 소스** | Semantic Scholar Academic Graph API (bulk search) |
| **제외 대상** | medicine / healthcare / 임상 연구 |
| **저장 형식** | Apache Parquet (.parquet) |

---

## 2. 수집 파이프라인

```
[1] Semantic Scholar bulk search API로 메타데이터 수집
    - 39개 키워드 + 11개 분야 검색
    - 토큰 기반 페이지네이션 (쿼리당 최대 10,000건)
         ↓
[2] 표준 스키마로 변환 (팀 공용 parquet 스키마)
         ↓
[3] 중복 제거
    - 1차: content_hash 정확 매칭 → 2,701건 제거
    - 2차: title/abstract Jaccard 유사도 (0.9/0.85) → 40건 제거
         ↓
[4] medicine/healthcare 필터링
    - 키워드 + 정규식 패턴 기반 → 12,213건 제거
         ↓
[5] .parquet 저장
```

---

## 3. 수집 결과 요약

### 3.1 전체 현황

| 단계 | 건수 | 비고 |
|------|------|------|
| 원본 수집 | 261,934 | bulk search 전체 |
| 정확 중복 제거 후 | 259,233 | -2,701 |
| 유사도 중복 제거 후 | 259,193 | -40 |
| medicine 필터링 후 | **246,980** | -12,213 |

### 3.2 연도별 분포

| 연대 | 건수 | 비율 |
|------|------|------|
| 1970s | 28,532 | 11.6% |
| 1980s | 61,194 | 24.8% |
| 1990s | 157,254 | 63.6% |

### 3.3 분야별 분포 (상위 10개)

| 분야 | 건수 |
|------|------|
| Biology | 151,810 |
| Medicine | 141,761 |
| Chemistry | 33,331 |
| Geography | 5,650 |
| Computer Science | 4,435 |
| Environmental Science | 4,175 |
| Physics | 3,312 |
| Psychology | 3,085 |
| Engineering | 2,624 |
| Materials Science | 2,180 |

> **참고**: Medicine 태그가 남아있는 이유 — S2의 fieldsOfStudy에 Medicine이 태그되어 있지만, 키워드 기반 필터에 걸리지 않은 기초 연구 논문들. 추가 필터링 여부 검토 필요.

### 3.4 텍스트 확보 현황

| 항목 | 건수 | 비율 |
|------|------|------|
| Abstract 있음 | 13,251 | 5.4% |
| Abstract 없음 (제목만) | 233,729 | 94.6% |
| Full-text | 0 | 0% |
| PDF URL 있음 | 56,569 | 22.9% |

---

## 4. 파일 구조

```
05_data/
├── raw/
│   ├── biology_classic_raw.parquet           # 원본 수집 데이터 (261,934건)
│   ├── biology_classic_partial_*.parquet     # 중간 저장 파일들
│   └── crawl_progress.json                   # 크롤링 진행 상황
└── processed/
    └── biology_classic_deduped.parquet        # 최종 정제 데이터 (246,980건)
```

---

## 5. 데이터 스키마 (팀 공용)

```json
{
  "record_id": "raw_20260403_a1b2c3d4",
  "paper_id": "paper_abc123def456",
  "source": "semantic_scholar",
  "source_paper_id": "S2_abcdef",
  "arxiv_id": null,
  "doi": "10.1000/example",
  "title": "Gene Expression in E. coli",
  "abstract": "We study gene regulation...",
  "authors": ["Alice Kim", "Bob Lee"],
  "year": 1985,
  "categories": ["Molecular Biology", "Genetics"],
  "pdf_url": "https://...",
  "pdf_path": null,
  "latex_source_path": null,
  "has_full_text": true,
  "full_text": "We study gene regulation...",
  "full_text_format": "text",
  "full_text_source_type": "semantic_scholar_abstract",
  "full_text_status": "abstract_only",
  "citation_count": 150,
  "crawl_date": "2026-04-03T09:00:00Z",
  "fetch_success": true,
  "error_message": null,
  "content_hash": "sha256:...",
  "is_duplicate": false,
  "raw_source_payload": "{...}",
  "domain": "biology",
  "subdomain": "Molecular Biology",
  "level": "research",
  "is_excluded_medical": false,
  "language": "en",
  "word_count": 150
}
```

---

## 6. 핵심 이슈

### 이슈 1: Abstract 확보율 극히 낮음 (5.4%)

- Semantic Scholar는 메타데이터 중심 — full-text 미제공
- 246,980건 중 실제 텍스트가 있는 건은 13,251건
- **CPT 학습에 활용 가능한 데이터가 부족한 상황**

### 이슈 2: Medicine 태그 잔존 (141,761건)

- 키워드 기반 필터링으로 12,213건 제거했으나
- fieldsOfStudy에 Medicine 태그가 붙은 논문이 다수 남아있음
- 기초 생명과학 연구도 Medicine 태그가 붙는 경우가 많아 일괄 제거 시 데이터 손실 우려

### 이슈 3: Full-text 미확보

- PDF URL이 있는 56,569건에서 PDF 다운로드 → 텍스트 추출 가능
- 추가 소스 (PubMed Central, HuggingFace 데이터셋) 활용 검토 필요

---

## 7. 다음 단계 (TODO)

| 우선순위 | 작업 | 목적 |
|---------|------|------|
| 1 | PDF 다운로드 + full-text 추출 (56,569건) | CPT 학습 데이터 확보 |
| 2 | HuggingFace 생명과학 데이터셋 탐색/보충 | 데이터량 보완 |
| 3 | Medicine 태그 추가 필터링 검토 | 데이터 품질 개선 |
| 4 | 다른 팀원 데이터와 교차 중복 제거 | 통합 준비 |
| 5 | CPT 데이터 믹싱 (과학 80~85% + 일반 15~20%) | 학습 준비 |

---

## 8. 기술 스택

- **언어**: Python 3.13
- **API**: Semantic Scholar Academic Graph API (bulk search)
- **데이터 처리**: PyArrow, Pandas
- **저장 형식**: Apache Parquet
- **중복 제거**: content_hash(SHA-256) + Jaccard 유사도
