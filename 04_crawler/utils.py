"""
유틸리티 함수 모음
담당자: 김승환
"""

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from config import (
    EXCLUDE_KEYWORDS,
    EXCLUDE_PATTERNS,
    KEEP_KEYWORDS,
    LOG_FILE,
    LOG_LEVEL,
    PARQUET_SCHEMA,
)


# =============================================================================
# 로깅 설정
# =============================================================================
def setup_logger(name: str = "crawler") -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # 파일 핸들러
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# =============================================================================
# ID 생성
# =============================================================================
def generate_record_id(prefix: str = "raw") -> str:
    """고유 레코드 ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


def generate_paper_id(source: str, source_id: str) -> str:
    """논문 ID 생성 (소스 + 원본 ID 기반)"""
    combined = f"{source}:{source_id}"
    hash_val = hashlib.md5(combined.encode()).hexdigest()[:12]
    return f"paper_{hash_val}"


# =============================================================================
# 해시 생성
# =============================================================================
def compute_content_hash(text: str) -> str:
    """텍스트 콘텐츠 해시 생성"""
    if not text:
        return ""
    normalized = text.lower().strip()
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()
    return f"sha256:{hash_val}"


# =============================================================================
# 텍스트 정규화
# =============================================================================
def normalize_text(text: Optional[str]) -> str:
    """텍스트 정규화"""
    if not text:
        return ""

    # 연속 공백 제거
    text = re.sub(r"\s+", " ", text)
    # 앞뒤 공백 제거
    text = text.strip()

    return text


def clean_title(title: Optional[str]) -> str:
    """제목 정리"""
    if not title:
        return ""

    title = normalize_text(title)
    # 특수문자 일부 제거
    title = re.sub(r"[<>]", "", title)

    return title


def count_words(text: Optional[str]) -> int:
    """단어 수 계산"""
    if not text:
        return 0
    words = text.split()
    return len(words)


# =============================================================================
# medicine/healthcare 필터링
# =============================================================================
def is_medical_content(title: str, abstract: str) -> bool:
    """
    medicine/healthcare 관련 콘텐츠인지 확인

    Returns:
        True: 의료 관련 (제외 대상)
        False: 기초 과학 (수집 대상)
    """
    combined_text = f"{title} {abstract}".lower()

    # 1. KEEP_KEYWORDS가 있으면 기초 연구로 간주
    for keep_kw in KEEP_KEYWORDS:
        if keep_kw.lower() in combined_text:
            # 추가 확인: 임상 시험 등 명확한 의료 콘텐츠는 제외
            if any(p.search(combined_text) for p in EXCLUDE_PATTERNS[:3]):
                return True
            return False

    # 2. EXCLUDE_PATTERNS 검사 (정규식)
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(combined_text):
            return True

    # 3. EXCLUDE_KEYWORDS 검사 (단순 포함)
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in combined_text:
            return True

    return False


# =============================================================================
# Rate Limiting
# =============================================================================
class RateLimiter:
    """API 요청 rate limiting"""

    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    def wait(self):
        """다음 요청까지 대기"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()


# =============================================================================
# 데이터 변환
# =============================================================================
def paper_to_record(
    paper_data: Dict[str, Any],
    source: str = "semantic_scholar",
    crawl_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    API 응답을 표준 레코드 형식으로 변환

    Args:
        paper_data: API 응답 데이터
        source: 데이터 소스
        crawl_date: 크롤링 날짜

    Returns:
        표준화된 레코드 딕셔너리
    """
    if crawl_date is None:
        crawl_date = datetime.utcnow().isoformat() + "Z"

    # 기본 필드 추출
    paper_id_raw = paper_data.get("paperId", "")
    title = clean_title(paper_data.get("title", ""))
    abstract = normalize_text(paper_data.get("abstract", ""))

    # 저자 처리
    authors_raw = paper_data.get("authors", [])
    authors = []
    for author in authors_raw:
        if isinstance(author, dict):
            authors.append(author.get("name", ""))
        elif isinstance(author, str):
            authors.append(author)

    # 연도 처리
    year = paper_data.get("year")
    if year:
        try:
            year = int(year)
        except (ValueError, TypeError):
            year = None

    # 카테고리/분야 처리
    fields = paper_data.get("fieldsOfStudy", []) or []
    categories = [f for f in fields if isinstance(f, str)]

    # 인용 수
    citation_count = paper_data.get("citationCount", 0)
    if citation_count is None:
        citation_count = 0

    # DOI / arXiv ID
    external_ids = paper_data.get("externalIds", {}) or {}
    doi = external_ids.get("DOI")
    arxiv_id = external_ids.get("ArXiv")

    # URL
    open_access = paper_data.get("openAccessPdf", {}) or {}
    pdf_url = open_access.get("url")

    # medicine 필터링
    is_medical = is_medical_content(title, abstract)

    # 레코드 생성
    record = {
        "record_id": generate_record_id("raw"),
        "paper_id": generate_paper_id(source, paper_id_raw),
        "source": source,
        "source_paper_id": paper_id_raw,

        "arxiv_id": arxiv_id,
        "doi": doi,

        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "categories": categories,

        "pdf_url": pdf_url,
        "pdf_path": None,
        "latex_source_path": None,

        "has_full_text": bool(abstract),  # abstract만 있어도 True
        "full_text": abstract,  # 현재는 abstract만
        "full_text_format": "text" if abstract else None,
        "full_text_source_type": "semantic_scholar_abstract" if abstract else None,
        "full_text_status": "abstract_only",

        "citation_count": citation_count,

        "crawl_date": crawl_date,
        "fetch_success": True,
        "error_message": None,

        "content_hash": compute_content_hash(f"{title}{abstract}"),
        "is_duplicate": False,

        "raw_source_payload": json.dumps(paper_data, ensure_ascii=False),

        # 추가 필드
        "domain": "biology",
        "subdomain": categories[0] if categories else None,
        "level": "research",
        "is_excluded_medical": is_medical,
        "language": "en",
        "word_count": count_words(abstract),
    }

    return record


# =============================================================================
# Parquet 저장
# =============================================================================
def save_to_parquet(
    records: List[Dict[str, Any]],
    output_path: Path,
    append: bool = False
) -> int:
    """
    레코드를 Parquet 파일로 저장

    Args:
        records: 레코드 리스트
        output_path: 출력 경로
        append: 기존 파일에 추가 여부

    Returns:
        저장된 레코드 수
    """
    if not records:
        logger.warning("저장할 레코드가 없습니다.")
        return 0

    # 데이터 정리 (None -> 기본값)
    cleaned_records = []
    for record in records:
        cleaned = {}
        for key, value in record.items():
            if value is None:
                # 타입에 따라 기본값 설정
                if key in ["authors", "categories"]:
                    cleaned[key] = []
                elif key in ["year", "citation_count", "word_count"]:
                    cleaned[key] = 0
                elif key in ["has_full_text", "fetch_success", "is_duplicate", "is_excluded_medical"]:
                    cleaned[key] = False
                else:
                    cleaned[key] = ""
            else:
                cleaned[key] = value
        cleaned_records.append(cleaned)

    # PyArrow Table 생성
    table = pa.Table.from_pylist(cleaned_records)

    # 저장
    if append and output_path.exists():
        # 기존 파일 읽기
        existing_table = pq.read_table(output_path)
        # 병합
        combined_table = pa.concat_tables([existing_table, table])
        pq.write_table(combined_table, output_path)
        logger.info(f"기존 파일에 {len(records)}개 레코드 추가: {output_path}")
    else:
        pq.write_table(table, output_path)
        logger.info(f"새 파일에 {len(records)}개 레코드 저장: {output_path}")

    return len(records)


def load_from_parquet(input_path: Path) -> List[Dict[str, Any]]:
    """Parquet 파일에서 레코드 로드"""
    if not input_path.exists():
        logger.error(f"파일을 찾을 수 없습니다: {input_path}")
        return []

    table = pq.read_table(input_path)
    records = table.to_pylist()
    logger.info(f"{len(records)}개 레코드 로드: {input_path}")

    return records


# =============================================================================
# 진행 상황 저장/로드
# =============================================================================
def save_progress(progress_data: Dict[str, Any], progress_file: Path):
    """진행 상황 저장"""
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)
    logger.debug(f"진행 상황 저장: {progress_file}")


def load_progress(progress_file: Path) -> Dict[str, Any]:
    """진행 상황 로드"""
    if not progress_file.exists():
        return {}

    with open(progress_file, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# 통계
# =============================================================================
def print_collection_stats(records: List[Dict[str, Any]]):
    """수집 통계 출력"""
    if not records:
        print("수집된 데이터가 없습니다.")
        return

    total = len(records)
    medical_excluded = sum(1 for r in records if r.get("is_excluded_medical", False))
    with_abstract = sum(1 for r in records if r.get("abstract"))
    with_pdf = sum(1 for r in records if r.get("pdf_url"))

    # 연도별 분포
    year_dist = {}
    for r in records:
        year = r.get("year", 0)
        if year:
            decade = (year // 10) * 10
            year_dist[decade] = year_dist.get(decade, 0) + 1

    # 분야별 분포
    field_dist = {}
    for r in records:
        for cat in r.get("categories", []):
            field_dist[cat] = field_dist.get(cat, 0) + 1

    print("\n" + "=" * 50)
    print("수집 통계")
    print("=" * 50)
    print(f"총 레코드 수: {total:,}")
    print(f"의료 콘텐츠 (제외 대상): {medical_excluded:,} ({medical_excluded/total*100:.1f}%)")
    print(f"Abstract 있음: {with_abstract:,} ({with_abstract/total*100:.1f}%)")
    print(f"PDF URL 있음: {with_pdf:,} ({with_pdf/total*100:.1f}%)")

    print("\n연도별 분포:")
    for decade in sorted(year_dist.keys()):
        count = year_dist[decade]
        print(f"  {decade}s: {count:,}")

    print("\n분야별 분포 (상위 10개):")
    sorted_fields = sorted(field_dist.items(), key=lambda x: x[1], reverse=True)[:10]
    for field, count in sorted_fields:
        print(f"  {field}: {count:,}")

    print("=" * 50 + "\n")
