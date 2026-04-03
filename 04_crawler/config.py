"""
설정 파일 - 생명과학 고전(1970~1999) 데이터 수집
담당자: 김승환
"""

from pathlib import Path
from typing import List, Tuple
import re

# =============================================================================
# 경로 설정
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "05_data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# 디렉토리 생성
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Semantic Scholar API 설정
# =============================================================================
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = None  # API 키가 있으면 여기에 입력 (또는 환경변수 사용)

# Rate limiting
S2_REQUESTS_PER_SECOND = 1  # API 키 있을 때
S2_REQUESTS_PER_5MIN = 100   # API 키 없을 때

# =============================================================================
# 수집 기간
# =============================================================================
YEAR_RANGE: Tuple[int, int] = (1970, 1999)

# =============================================================================
# 생명과학 분야 (Fields of Study)
# =============================================================================
FIELDS_OF_STUDY: List[str] = [
    "Biology",
    "Biochemistry",
    "Molecular Biology",
    "Cell Biology",
    "Genetics",
    "Ecology",
    "Microbiology",
    "Evolutionary Biology",
    "Neuroscience",
    "Botany",
    "Zoology",
]

# =============================================================================
# 검색 키워드
# =============================================================================
SEARCH_QUERIES: List[str] = [
    # Tier 1: 핵심
    "molecular biology",
    "cell biology",
    "genetics gene",
    "biochemistry enzyme",
    "DNA RNA protein",

    # Tier 2: 분자생물학
    "gene expression",
    "gene regulation",
    "transcription translation",
    "recombinant DNA",
    "DNA sequencing",
    "PCR polymerase chain reaction",

    # Tier 2: 세포생물학
    "cell cycle",
    "cell division mitosis",
    "cell signaling",
    "apoptosis programmed cell death",

    # Tier 2: 유전학
    "genetic mutation",
    "chromosome",
    "genome",
    "population genetics",

    # Tier 2: 생화학
    "enzyme kinetics",
    "protein structure",
    "metabolism glycolysis",

    # Tier 2: 미생물학
    "bacteria microbiology",
    "bacteriophage virus",
    "microbial genetics",

    # Tier 2: 진화
    "evolution phylogeny",
    "natural selection",
    "molecular evolution",

    # Tier 2: 발생생물학
    "embryo development",
    "developmental biology",
    "morphogenesis",

    # Tier 2: 생태학
    "ecosystem ecology",
    "population dynamics",
    "biodiversity",

    # Tier 2: 신경과학 (기초)
    "neuron synapse",
    "neurotransmitter",
    "action potential",

    # Tier 2: 식물
    "photosynthesis plant",
    "plant physiology",
]

# =============================================================================
# 제외 키워드 (medicine/healthcare)
# =============================================================================
EXCLUDE_KEYWORDS: List[str] = [
    # 임상 관련
    "clinical trial",
    "clinical study",
    "patient",
    "patients",
    "diagnosis",
    "prognosis",
    "treatment",
    "therapy",
    "therapeutic",
    "surgery",
    "surgical",
    "hospital",
    "physician",
    "healthcare",
    "medical practice",

    # 약물 관련 (임상적)
    "drug therapy",
    "drug treatment",
    "drug delivery",
    "pharmaceutical",
    "medication",
    "dosage",
    "pharmacotherapy",

    # 의료 기기
    "medical device",
    "implant",
    "prosthetic",
]

# 제외 패턴 (정규표현식)
EXCLUDE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bclinical\s+trial", re.IGNORECASE),
    re.compile(r"\bpatient[s]?\b", re.IGNORECASE),
    re.compile(r"\btherapeutic[s]?\b", re.IGNORECASE),
    re.compile(r"\bdrug\s+(therapy|treatment|delivery)\b", re.IGNORECASE),
    re.compile(r"\brandomized\s+controlled", re.IGNORECASE),
    re.compile(r"\bdouble[- ]blind", re.IGNORECASE),
    re.compile(r"\bphase\s+[I1234]+\s+(trial|study)", re.IGNORECASE),
]

# 예외: 기초 연구에서 사용하지만 제외하지 않을 키워드
KEEP_KEYWORDS: List[str] = [
    "disease model",
    "cancer cell",
    "tumor cell line",
    "cell line",
    "pathogen",
    "infection mechanism",
    "drug resistance",  # 분자생물학적 연구
]

# =============================================================================
# 중복 제거 설정
# =============================================================================
DEDUP_TITLE_THRESHOLD: float = 0.90   # Title 유사도 임계값
DEDUP_ABSTRACT_THRESHOLD: float = 0.85  # Abstract 유사도 임계값

# =============================================================================
# 출력 형식
# =============================================================================
OUTPUT_FORMAT = "parquet"  # parquet 또는 json
BATCH_SIZE = 1000  # 파일당 레코드 수

# =============================================================================
# 로깅 설정
# =============================================================================
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "crawler.log"

# =============================================================================
# Parquet 스키마 (pyarrow 타입)
# =============================================================================
PARQUET_SCHEMA = {
    "record_id": "string",
    "paper_id": "string",
    "source": "string",
    "source_paper_id": "string",

    "arxiv_id": "string",
    "doi": "string",

    "title": "string",
    "abstract": "string",
    "authors": "list<string>",
    "year": "int32",
    "categories": "list<string>",

    "pdf_url": "string",
    "pdf_path": "string",
    "latex_source_path": "string",

    "has_full_text": "bool",
    "full_text": "string",
    "full_text_format": "string",
    "full_text_source_type": "string",
    "full_text_status": "string",

    "citation_count": "int32",

    "crawl_date": "string",
    "fetch_success": "bool",
    "error_message": "string",

    "content_hash": "string",
    "is_duplicate": "bool",

    "raw_source_payload": "string",

    # 추가 필드
    "domain": "string",
    "subdomain": "string",
    "level": "string",
    "is_excluded_medical": "bool",
    "language": "string",
    "word_count": "int32",
}
