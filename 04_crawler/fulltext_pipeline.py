"""
Full-text 수집 파이프라인
담당자: 김승환

기존 S2 데이터에서 pdf_url이 있는 논문의 PDF를 다운로드하고
텍스트를 추출하여 full_ver parquet로 저장한다.
"""

import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_DIR, LOG_FILE
from utils import (
    load_from_parquet,
    load_progress,
    logger,
    save_progress,
    save_to_parquet,
)

# =============================================================================
# 설정
# =============================================================================
FULL_VER_DIR = BASE_DIR / "05_data" / "full_ver"
PDF_DIR = FULL_VER_DIR / "pdfs"
PROGRESS_FILE = FULL_VER_DIR / "fulltext_progress.json"

PDF_DIR.mkdir(parents=True, exist_ok=True)

# Rate limit: 일반 PDF 다운로드 (2 req/s)
DOWNLOAD_RATE = 2.0
MIN_TEXT_LENGTH = 100  # 이보다 짧으면 스캔 이미지로 간주


# =============================================================================
# 텍스트 정제 (인코딩 깨짐 수정)
# =============================================================================
# PDF에서 자주 깨지는 리거처/특수문자 매핑
PDF_CHAR_FIXES = {
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb00": "ff",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "--",
    "\u2026": "...",
    "\u00a0": " ",       # non-breaking space
    "\u00ad": "",         # soft hyphen
    "\u200b": "",         # zero-width space
    "\u200c": "",         # zero-width non-joiner
    "\u200d": "",         # zero-width joiner
    "\ufeff": "",         # BOM
    "\u0000": "",         # null
    "\uf0b7": "*",        # bullet (Symbol font)
    "\uf0a7": "*",        # bullet variant
    "\uf06c": "l",        # Symbol font 'l'
    "\uf020": " ",        # Symbol font space
}


def clean_extracted_text(text: str) -> str:
    """
    PDF에서 추출한 텍스트의 인코딩 깨짐 및 아티팩트 정리

    Args:
        text: 원본 추출 텍스트

    Returns:
        정제된 텍스트
    """
    if not text:
        return ""

    # 1. Unicode NFC 정규화 (한글 자모 분리 방지, 합성 문자 통일)
    text = unicodedata.normalize("NFC", text)

    # 2. PDF 리거처/특수문자 치환
    for bad_char, replacement in PDF_CHAR_FIXES.items():
        text = text.replace(bad_char, replacement)

    # 3. Private Use Area 문자 제거 (U+E000~U+F8FF, 폰트 내장 특수문자)
    text = re.sub(r"[\uE000-\uF8FF]", "", text)

    # 4. 서로게이트 및 비표준 제어문자 제거 (U+0000~U+001F 중 탭/줄바꿈 제외)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 5. PDF 줄바꿈 아티팩트 정리 (단어 중간 하이픈 줄바꿈)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # 6. 불필요한 연속 공백 정리
    text = re.sub(r"[ \t]+", " ", text)

    # 7. 연속 빈 줄 정리 (3줄 이상 → 2줄)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 8. 앞뒤 공백 제거
    text = text.strip()

    return text


# =============================================================================
# PDF 다운로드
# =============================================================================
def download_pdf(url: str, save_path: Path, timeout: int = 30) -> bool:
    """
    PDF 다운로드

    Args:
        url: PDF URL
        save_path: 저장 경로
        timeout: 타임아웃 (초)

    Returns:
        성공 여부
    """
    if save_path.exists():
        return True

    try:
        response = requests.get(
            url,
            timeout=timeout,
            stream=True,
            headers={"User-Agent": "Mozilla/5.0 (research crawler)"},
        )
        response.raise_for_status()

        # Content-Type 확인
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            return False

        # 저장
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 파일 크기 확인 (너무 작으면 실패)
        if save_path.stat().st_size < 1000:
            save_path.unlink()
            return False

        return True

    except (requests.exceptions.RequestException, OSError) as e:
        logger.debug(f"PDF 다운로드 실패: {url} - {e}")
        if save_path.exists():
            save_path.unlink()
        return False


# =============================================================================
# PDF → 텍스트 추출
# =============================================================================
def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """
    PDF에서 텍스트 추출 (pdfplumber 사용)

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        추출된 텍스트 또는 None
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber가 설치되어 있지 않습니다: pip install pdfplumber")
        return None

    try:
        text_parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        full_text = "\n".join(text_parts).strip()

        # 너무 짧으면 스캔 이미지로 간주
        if len(full_text) < MIN_TEXT_LENGTH:
            return None

        return full_text

    except Exception as e:
        logger.debug(f"텍스트 추출 실패: {pdf_path} - {e}")
        return None


# =============================================================================
# 메인 파이프라인
# =============================================================================
def run_fulltext_pipeline(
    input_parquet: Path,
    max_downloads: int = 0,
    save_interval: int = 500,
):
    """
    Full-text 수집 파이프라인

    Args:
        input_parquet: 입력 parquet 파일 경로
        max_downloads: 최대 다운로드 수 (0이면 전체)
        save_interval: 중간 저장 간격
    """
    logger.info("=" * 60)
    logger.info("Full-text 수집 파이프라인 시작")
    logger.info("=" * 60)

    # 진행 상황 먼저 로드
    progress = load_progress(PROGRESS_FILE)
    completed_ids = set(progress.get("completed_ids", []))
    stats = progress.get("stats", {
        "total_attempted": 0,
        "pdf_downloaded": 0,
        "text_extracted": 0,
        "failed": 0,
    })
    logger.info(f"이전 진행: {len(completed_ids):,}건 완료")

    # 경량 로드: 필요한 컬럼만 먼저 읽어서 대상 필터링
    import pyarrow.parquet as pq
    table = pq.read_table(input_parquet, columns=["source_paper_id", "pdf_url"])
    df = table.to_pandas()
    pdf_df = df[(df["pdf_url"] != "") & (df["pdf_url"].notna())]
    todo_ids = pdf_df[~pdf_df["source_paper_id"].isin(completed_ids)]["source_paper_id"].tolist()

    logger.info(f"PDF URL 있는 레코드: {len(pdf_df):,}")
    logger.info(f"처리 대상: {len(todo_ids):,}건")

    if max_downloads > 0:
        todo_ids = todo_ids[:max_downloads]

    # 대상 레코드만 전체 로드
    all_records_table = pq.read_table(input_parquet)
    records = all_records_table.to_pydict()
    # dict of lists → list of dicts
    num_rows = len(records["source_paper_id"])
    keys = list(records.keys())

    # source_paper_id → index 매핑
    id_to_idx = {}
    for i in range(num_rows):
        pid = records["source_paper_id"][i]
        id_to_idx[pid] = i

    # 처리 대상 레코드 추출
    todo_set = set(todo_ids)
    todo = []
    for pid in todo_ids:
        if pid in id_to_idx:
            idx = id_to_idx[pid]
            row = {k: records[k][idx] for k in keys}
            todo.append(row)

    logger.info(f"로드 완료, 처리 시작: {len(todo):,}건")

    # 결과 저장용
    updated_records = []
    last_request_time = 0.0

    total_todo = len(todo)
    for i, record in enumerate(todo):
        paper_id = record.get("source_paper_id", "")
        pdf_url = record.get("pdf_url", "")

        # Rate limiting
        elapsed = time.time() - last_request_time
        min_interval = 1.0 / DOWNLOAD_RATE
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        stats["total_attempted"] += 1

        # PDF 다운로드
        safe_name = paper_id.replace("/", "_").replace(":", "_")[:50]
        pdf_path = PDF_DIR / f"{safe_name}.pdf"

        last_request_time = time.time()
        downloaded = download_pdf(pdf_url, pdf_path)

        if not downloaded:
            stats["failed"] += 1
            completed_ids.add(paper_id)
            continue

        stats["pdf_downloaded"] += 1

        # 텍스트 추출
        full_text = extract_text_from_pdf(pdf_path)

        if full_text:
            stats["text_extracted"] += 1

            # 레코드 업데이트
            updated = dict(record)
            updated["has_full_text"] = True
            updated["full_text"] = full_text
            updated["full_text_format"] = "text"
            updated["full_text_source_type"] = "pdf_extracted"
            updated["full_text_status"] = "success"
            updated["pdf_path"] = str(pdf_path)
            updated["word_count"] = len(full_text.split())
            updated_records.append(updated)
        else:
            # PDF는 있지만 텍스트 추출 실패 (스캔 이미지 등)
            stats["failed"] += 1

        completed_ids.add(paper_id)

        # 중간 저장
        if (i + 1) % save_interval == 0:
            _save_intermediate(updated_records, stats, completed_ids)
            logger.info(
                f"[{i+1}/{total_todo}] "
                f"시도: {stats['total_attempted']:,}, "
                f"다운: {stats['pdf_downloaded']:,}, "
                f"추출: {stats['text_extracted']:,}, "
                f"실패: {stats['failed']:,}"
            )

    # 최종 저장
    _save_intermediate(updated_records, stats, completed_ids)

    # 최종 parquet 생성 (full-text가 있는 레코드 + 기존 abstract 레코드 통합)
    _build_final_parquet(records, updated_records)

    # 결과 출력
    logger.info("=" * 60)
    logger.info("Full-text 수집 완료")
    logger.info(f"총 시도: {stats['total_attempted']:,}")
    logger.info(f"PDF 다운로드 성공: {stats['pdf_downloaded']:,}")
    logger.info(f"텍스트 추출 성공: {stats['text_extracted']:,}")
    logger.info(f"실패: {stats['failed']:,}")
    if stats['total_attempted'] > 0:
        success_rate = stats['text_extracted'] / stats['total_attempted'] * 100
        logger.info(f"성공률: {success_rate:.1f}%")
    logger.info("=" * 60)


def _save_intermediate(
    updated_records: List[Dict[str, Any]],
    stats: Dict[str, int],
    completed_ids: set,
):
    """중간 결과 저장"""
    # 진행 상황 저장
    progress = {
        "completed_ids": list(completed_ids),
        "stats": stats,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    save_progress(progress, PROGRESS_FILE)

    # full-text 레코드 저장
    if updated_records:
        output_path = FULL_VER_DIR / "fulltext_records.parquet"
        save_to_parquet(updated_records, output_path)


def _build_final_parquet(
    original_records: List[Dict[str, Any]],
    fulltext_records: List[Dict[str, Any]],
):
    """
    최종 parquet 생성
    - full-text가 있는 레코드는 업데이트된 버전 사용
    - 나머지는 원본 유지
    """
    # full-text 레코드를 paper_id 기준으로 인덱싱
    fulltext_map = {}
    for r in fulltext_records:
        fulltext_map[r.get("source_paper_id")] = r

    # 통합
    final_records = []
    for r in original_records:
        pid = r.get("source_paper_id")
        if pid in fulltext_map:
            final_records.append(fulltext_map[pid])
        else:
            final_records.append(r)

    # 저장
    output_path = FULL_VER_DIR / "biology_classic_full.parquet"
    save_to_parquet(final_records, output_path)

    # 통계
    ft_count = sum(1 for r in final_records if r.get("full_text_status") == "success")
    abs_count = sum(1 for r in final_records if r.get("abstract"))
    logger.info(f"최종 파일 저장: {output_path}")
    logger.info(f"총 {len(final_records):,}건 (full-text: {ft_count:,}, abstract: {abs_count:,})")


# =============================================================================
# 후처리: 기존 parquet의 텍스트 정제
# =============================================================================
def postprocess_clean(input_path: Path, output_path: Optional[Path] = None):
    """
    이미 수집된 parquet 파일의 텍스트를 정제

    Args:
        input_path: 입력 parquet 파일
        output_path: 출력 경로 (None이면 덮어쓰기)
    """
    if output_path is None:
        output_path = input_path

    logger.info(f"텍스트 정제 시작: {input_path}")
    records = load_from_parquet(input_path)
    logger.info(f"총 {len(records):,}건 로드")

    cleaned_count = 0
    for record in tqdm(records, desc="텍스트 정제"):
        changed = False

        # full_text 정제
        ft = record.get("full_text", "")
        if ft:
            cleaned = clean_extracted_text(ft)
            if cleaned != ft:
                record["full_text"] = cleaned
                record["word_count"] = len(cleaned.split())
                changed = True

        # abstract 정제
        ab = record.get("abstract", "")
        if ab:
            cleaned = clean_extracted_text(ab)
            if cleaned != ab:
                record["abstract"] = cleaned
                changed = True

        # title 정제
        ti = record.get("title", "")
        if ti:
            cleaned = clean_extracted_text(ti)
            if cleaned != ti:
                record["title"] = cleaned
                changed = True

        if changed:
            cleaned_count += 1

    save_to_parquet(records, output_path)
    logger.info(f"텍스트 정제 완료: {cleaned_count:,}건 수정, 저장: {output_path}")


# =============================================================================
# CLI
# =============================================================================
def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="Full-text 수집 파이프라인")
    parser.add_argument(
        "--mode",
        choices=["download", "clean"],
        default="download",
        help="실행 모드: download(PDF 수집) 또는 clean(텍스트 정제)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(BASE_DIR / "05_data" / "processed" / "biology_classic_deduped.parquet"),
        help="입력 parquet 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 parquet 파일 경로 (clean 모드, 미지정 시 덮어쓰기)",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=0,
        help="최대 다운로드 수 (0이면 전체)",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=500,
        help="중간 저장 간격",
    )

    args = parser.parse_args()

    if args.mode == "download":
        run_fulltext_pipeline(
            input_parquet=Path(args.input),
            max_downloads=args.max_downloads,
            save_interval=args.save_interval,
        )
    elif args.mode == "clean":
        output = Path(args.output) if args.output else None
        postprocess_clean(Path(args.input), output)


if __name__ == "__main__":
    main()
