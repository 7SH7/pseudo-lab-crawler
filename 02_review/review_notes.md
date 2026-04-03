# 자료 검토 및 수정 제안

## 담당자: 김승환
## 검토일: 2026-04-03

---

## 발견된 문제점 및 수정 제안

### 1. arXiv q-bio 카테고리 시작 연도 문제

| 구분 | 내용 |
|------|------|
| **문제** | arXiv q-bio 카테고리는 **2003년에 신설**됨 |
| **영향** | 고전(1970~1999) 생명과학 데이터는 arXiv에서 **수집 불가** |
| **현황** | 성민님이 현대 생명(2000~) 담당으로 q-bio 52,764건 수집 완료 |

#### 수정 제안
```
[기존 계획]
승환: arXiv + Semantic Scholar에서 생명 고전(1970~1999) 수집

[수정 제안]
승환: Semantic Scholar 단독으로 생명 고전(1970~1999) 수집
      (arXiv q-bio는 2003년 이후만 존재하므로 제외)
```

---

### 2. 현대 기간 정의 불일치

| 문서 위치 | 기간 정의 |
|----------|----------|
| 회의록 상단 | 현대: 2000~2022 |
| 진혁님 작업 | 현대화학: 2000~2025 |
| 채윤님 작업 | 우주과학: 2000~ |

#### 수정 제안
- **통일 필요**: 2000~2024 또는 2000~2025로 통일
- 이유: 2022년 이후 논문도 상당수 존재, 최신 데이터 포함이 학습에 유리

---

### 3. 중복 제거 threshold 미정

| 항목 | 현재 상태 | 제안 |
|------|----------|------|
| Title 유사도 | "≥ threshold" (수치 미정) | **≥ 0.90** (Jaccard 또는 cosine) |
| Abstract 유사도 | "≥ threshold" (수치 미정) | **≥ 0.85** |
| 알고리즘 | 미정 | MinHash + LSH (대규모 처리 시) |

---

### 4. medicine/healthcare 제외 기준 모호

**문제**: 생명과학과 의학의 경계가 모호함

#### 제안: 제외 키워드 리스트
```python
EXCLUDE_KEYWORDS = [
    # 임상 관련
    "clinical trial", "patient", "diagnosis", "treatment",
    "therapy", "surgery", "hospital", "physician",
    # 질병 관련
    "disease", "disorder", "syndrome", "cancer", "tumor",
    "infection", "COVID", "diabetes", "alzheimer",
    # 약물 관련
    "drug", "pharmaceutical", "medication", "dosage",
    # 의료 기기
    "medical device", "implant", "prosthetic"
]
```

**주의**: 기초 생명과학 연구도 "cancer cell line"이나 "disease model" 키워드를 포함할 수 있으므로, **필터링 후 샘플 검토 필요**

---

### 5. CPT "중형 모델" 정의 불명확

| 구분 | 현재 상태 | 제안 |
|------|----------|------|
| 모델 크기 | "중형"만 명시 | **7B~13B** 파라미터 범위 명시 |
| Base 모델 | 미정 | Nemotron (문서에 언급됨) 또는 Llama 계열 |
| 소형 (진혁님) | 미정 | **1B~3B** 파라미터 |

---

### 6. Semantic Scholar API 관련

| 항목 | 내용 |
|------|------|
| Rate Limit | 인증 없이 100 req/5min, API key 있으면 1 req/sec |
| Full-text 접근 | 대부분 불가, Open Access 논문만 가능 |
| **필요 조치** | API key 신청 필요 (https://www.semanticscholar.org/product/api) |

---

### 7. 데이터 스키마 개선 제안

기존 스키마에 추가 권장 필드:

```json
{
  // 기존 필드들...

  // 추가 권장
  "domain": "biology",           // 도메인 태그
  "subdomain": "molecular",      // 세부 도메인
  "level": "research",           // intro/inter/adv/research
  "is_excluded_medical": false,  // medicine 필터 통과 여부
  "language": "en",              // 언어 코드
  "word_count": 5000             // 전문 단어 수
}
```

---

### 8. 저장소 전략 미확정

| 옵션 | 장점 | 단점 | 권장 |
|------|------|------|------|
| `.parquet` 로컬 | 무료, 빠름 | 협업 어려움 | **1차 선택** |
| Supabase | 중앙 관리 | 비용, 용량 제한 | 최종 통합 시 |
| HuggingFace | 공유 용이 | 업로드 시간 | 배포용 |
| DuckDB | 무료, SQL 지원 | 분산 처리 안됨 | 로컬 분석용 |

#### 권장 전략
```
[수집 단계] 각자 로컬 .parquet
     ↓
[통합 단계] Git LFS 또는 HuggingFace Dataset
     ↓
[학습 단계] HuggingFace Dataset 스트리밍
```

---

## 누락된 정보 목록

1. [ ] Semantic Scholar API key 발급 여부
2. [ ] 정확한 base 모델 선정 (Nemotron 버전)
3. [ ] 중복 제거 threshold 최종 확정
4. [ ] 팀 전체 데이터 통합 시점 및 방법
5. [ ] CPT 학습 인프라 (GPU 환경)

---

## 팀에 공유/확인이 필요한 사항

1. **현대 기간 통일**: 2000~2024 또는 2000~2025?
2. **중복 제거 threshold**: Title 0.9, Abstract 0.85 괜찮은지?
3. **medicine 제외 키워드**: 추가할 것 있는지?
4. **S2 API key**: 팀 공용 key 있는지?

---

## 요약

| 우선순위 | 이슈 | 상태 |
|---------|------|------|
| **높음** | arXiv q-bio 2003년 시작 (고전 수집 불가) | Semantic Scholar 단독 사용으로 전환 |
| **높음** | S2 API key 필요 | 신청 필요 |
| **중간** | 현대 기간 불일치 | 팀 확인 필요 |
| **중간** | 중복 제거 threshold | 제안값 사용 (0.9/0.85) |
| **낮음** | medicine 제외 기준 | 키워드 리스트 제안 완료 |
