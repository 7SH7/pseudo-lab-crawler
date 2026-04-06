# 생명과학 고전(1970~1999) 데이터 수집 최종 결과

## 담당자: 김승환
## 최종 업데이트: 2026-04-06

---

## 1. 수집 파이프라인 요약

```
[1] Semantic Scholar bulk search API로 메타데이터 수집
    - 39개 키워드 + 11개 분야 검색
    - 토큰 기반 페이지네이션 (쿼리당 최대 10,000건)
    → 261,934건 수집
         ↓
[2] 중복 제거
    - 1차: content_hash(SHA-256) 정확 매칭 → 2,701건 제거
    - 2차: title/abstract Jaccard 유사도 (0.9/0.85) → 40건 제거
    → 259,193건
         ↓
[3] Medicine/Healthcare 필터링
    - 키워드 + 정규식 패턴 기반 → 12,213건 제거
    - 기초연구 키워드(cancer cell, disease model 등)는 예외 처리
    → 246,980건
         ↓
[4] Full-text 수집 (PDF URL 보유 56,569건 대상)
    - PDF 다운로드 → pdfplumber 텍스트 추출 → 인코딩 정제
    - PDF 다운로드 성공: 6,067건
    - 텍스트 추출 성공: 5,684건 (성공률 10.0%)
         ↓
[5] 최종 parquet 생성
    → 246,980건 (full-text 5,684 + abstract 12,163 + title only 229,133)
```

---

## 2. 최종 데이터 현황

### 2.1 전체 파이프라인 결과

| 단계 | 건수 | 변화 |
|------|------|------|
| 원본 수집 | 261,934 | - |
| 정확 중복 제거 후 | 259,233 | -2,701 |
| 유사도 중복 제거 후 | 259,193 | -40 |
| Medicine 필터링 후 | **246,980** | -12,213 |

### 2.2 텍스트 확보 현황

| 텍스트 유형 | 건수 | 비율 | 출처 |
|-------------|------|------|------|
| Full-text (본문 전체) | 5,684 | 2.3% | PDF 다운로드 → 텍스트 추출 |
| Abstract only | 12,163 | 4.9% | Semantic Scholar API |
| Title only (텍스트 없음) | 229,133 | 92.8% | 메타데이터만 존재 |
| **합계** | **246,980** | **100%** | |

### 2.3 Full-text 수집 상세

| 항목 | 건수 |
|------|------|
| PDF URL 보유 | 56,569 |
| PDF 다운로드 성공 | 6,067 |
| 텍스트 추출 성공 | 5,684 |
| 텍스트 추출 실패 (스캔 이미지 등) | 383 |
| 다운로드 실패 (링크 만료, 접근 제한 등) | 50,502 |

---

## 3. 데이터 분포

### 3.1 연도별 분포

| 연도 | 건수 | 연도 | 건수 | 연도 | 건수 |
|------|------|------|------|------|------|
| 1970 | 2,111 | 1980 | 4,265 | 1990 | 10,502 |
| 1971 | 2,032 | 1981 | 4,498 | 1991 | 10,974 |
| 1972 | 2,147 | 1982 | 4,828 | 1992 | 12,178 |
| 1973 | 2,364 | 1983 | 5,091 | 1993 | 13,290 |
| 1974 | 2,578 | 1984 | 5,636 | 1994 | 14,826 |
| 1975 | 3,120 | 1985 | 5,902 | 1995 | 15,961 |
| 1976 | 3,305 | 1986 | 6,802 | 1996 | 17,633 |
| 1977 | 3,335 | 1987 | 7,261 | 1997 | 18,746 |
| 1978 | 3,647 | 1988 | 8,033 | 1998 | 20,770 |
| 1979 | 3,893 | 1989 | 8,878 | 1999 | 22,374 |

| 연대 | 건수 | 비율 |
|------|------|------|
| 1970s | 28,532 | 11.6% |
| 1980s | 61,194 | 24.8% |
| 1990s | 157,254 | 63.6% |

### 3.2 분야별 분포 (S2 fieldsOfStudy 태깅 기준, 중복 태깅 포함)

| 분야 | 건수 | 비율 |
|------|------|------|
| Biology | 151,810 | 61.5% |
| Medicine | 141,761 | 57.4% |
| Chemistry | 33,331 | 13.5% |
| Geography | 5,650 | 2.3% |
| Computer Science | 4,435 | 1.8% |
| Environmental Science | 4,175 | 1.7% |
| Physics | 3,312 | 1.3% |
| Psychology | 3,085 | 1.2% |
| Engineering | 2,624 | 1.1% |
| Materials Science | 2,180 | 0.9% |
| Mathematics | 2,148 | 0.9% |
| 카테고리 없음 | 5,921 | 2.4% |

> **참고**: Medicine 태그(57.4%)가 높은 이유 — S2의 fieldsOfStudy에서 기초 생명과학 연구에도 Medicine 태그가 붙는 경우가 많음. 키워드 기반 medicine 필터링(임상시험, 환자, 수술 등)은 이미 적용 완료된 상태이며, 남은 것은 기초연구 성격의 논문임.

### 3.3 텍스트 길이 통계

| 유형 | 평균 | 중앙값 | 최소 | 최대 |
|------|------|--------|------|------|
| Full-text | 5,665 words | 3,816 words | 12 words | 333,054 words |
| Abstract | 240 words | 211 words | - | - |

### 3.4 인용 수 통계

| 항목 | 수치 |
|------|------|
| 평균 인용 수 | 55.2회 |
| 중앙값 | 16회 |
| 최대 | 17,051회 |
| 인용 1회 이상 | 208,048건 (84.2%) |

### 3.5 식별자 확보 현황

| 식별자 | 건수 | 비율 |
|--------|------|------|
| DOI | 190,604 | 77.2% |
| arXiv ID | 297 | 0.1% |

---

## 4. 파일 구조

```
05_data/
├── raw/
│   ├── biology_classic_raw.parquet           # 원본 (261,934건, 184MB)
│   ├── biology_classic_partial_*.parquet     # 중간 저장 파일들
│   └── crawl_progress.json                   # 크롤링 체크포인트
├── processed/
│   └── biology_classic_deduped.parquet       # 중복제거+필터링 (246,980건, 166MB)
└── full_ver/
    ├── biology_classic_full.parquet          # ★ 최종본 (246,980건, 283MB)
    ├── fulltext_records.parquet              # full-text 성공 건만 (5,684건, 123MB)
    ├── fulltext_progress.json                # full-text 수집 체크포인트
    └── pdfs/                                 # 다운로드된 PDF 파일 (6,067개)
```

---

## 5. 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.13 |
| API | Semantic Scholar Academic Graph API (bulk search) |
| 데이터 처리 | PyArrow, Pandas |
| PDF 텍스트 추출 | pdfplumber |
| 저장 형식 | Apache Parquet |
| 중복 제거 | content_hash(SHA-256) + Jaccard 유사도 |
| 텍스트 정제 | Unicode NFC 정규화, 리거처 치환, PDF 아티팩트 제거 |

---

## 6. 수집 설정

### 6.1 검색 키워드 (39개)

| 카테고리 | 키워드 |
|----------|--------|
| 핵심 | molecular biology, cell biology, genetics gene, biochemistry enzyme, DNA RNA protein |
| 분자생물학 | gene expression, gene regulation, transcription translation, recombinant DNA, DNA sequencing, PCR polymerase chain reaction |
| 세포생물학 | cell cycle, cell division mitosis, cell signaling, apoptosis programmed cell death |
| 유전학 | genetic mutation, chromosome, genome, population genetics |
| 생화학 | enzyme kinetics, protein structure, metabolism glycolysis |
| 미생물학 | bacteria microbiology, bacteriophage virus, microbial genetics |
| 진화 | evolution phylogeny, natural selection, molecular evolution |
| 발생생물학 | embryo development, developmental biology, morphogenesis |
| 생태학 | ecosystem ecology, population dynamics, biodiversity |
| 신경과학 | neuron synapse, neurotransmitter, action potential |
| 식물 | photosynthesis plant, plant physiology |

### 6.2 제외 키워드 (Medicine/Healthcare)

- 임상: clinical trial, patient, diagnosis, treatment, therapy, surgery, hospital 등
- 약물: drug therapy, pharmaceutical, medication, dosage 등
- 의료기기: medical device, implant, prosthetic 등
- 정규식: `\bclinical\s+trial`, `\bpatient[s]?\b`, `\bdouble[-]blind` 등 7개 패턴

### 6.3 예외 (기초연구 보존)

- disease model, cancer cell, tumor cell line, cell line, pathogen, infection mechanism, drug resistance

---

## 7. 한계 및 향후 과제

### 7.1 한계

| 항목 | 설명 |
|------|------|
| 낮은 텍스트 확보율 | 전체의 7.2%만 텍스트 보유 (full-text + abstract) |
| Full-text 수집 성공률 | PDF URL 56,569건 중 10.0%만 추출 성공 (링크 만료, 접근 제한) |
| S2 fieldsOfStudy 한계 | 세부 카테고리 없음 (arXiv q-bio 수준의 분류 불가) |
| Medicine 경계 모호 | 기초연구에 Medicine 태그가 붙는 경우가 많아 완전한 분리 어려움 |

### 7.2 향후 과제

| 우선순위 | 작업 | 목적 |
|---------|------|------|
| 1 | HuggingFace 데이터셋(S2ORC, PubMed Central OA) 보충 | 텍스트 확보율 개선 |
| 2 | 다른 팀원 데이터와 교차 중복 제거 | 통합 준비 |
| 3 | CPT 데이터 믹싱 (과학 80~85% + 일반 15~20%) | 학습 준비 |
