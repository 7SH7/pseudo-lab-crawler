"""
메인 실행 파일
담당자: 김승환

생명과학 고전(1970~1999) 데이터 수집 파이프라인

사용법:
    python main.py --mode crawl      # 크롤링 실행
    python main.py --mode dedup      # 중복 제거
    python main.py --mode stats      # 통계 확인
    python main.py --mode all        # 전체 파이프라인
"""

import argparse
import sys
from pathlib import Path

# 현재 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    FIELDS_OF_STUDY,
    PROCESSED_DIR,
    RAW_DIR,
    SEARCH_QUERIES,
    YEAR_RANGE,
)
from deduplicator import Deduplicator
from semantic_scholar_crawler import SemanticScholarCrawler
from utils import (
    load_from_parquet,
    logger,
    print_collection_stats,
    save_to_parquet,
)


def run_crawl(
    max_per_query: int = 10000,
    save_interval: int = 1000,
):
    """크롤링 실행"""
    logger.info("=" * 60)
    logger.info("크롤링 시작")
    logger.info(f"연도 범위: {YEAR_RANGE[0]} ~ {YEAR_RANGE[1]}")
    logger.info(f"검색 쿼리 수: {len(SEARCH_QUERIES)}")
    logger.info(f"분야 수: {len(FIELDS_OF_STUDY)}")
    logger.info("=" * 60)

    crawler = SemanticScholarCrawler()

    records = crawler.crawl_all(
        queries=SEARCH_QUERIES,
        fields=FIELDS_OF_STUDY,
        year_range=YEAR_RANGE,
        max_per_query=max_per_query,
        save_interval=save_interval,
    )

    print_collection_stats(records)

    return records


def run_dedup():
    """중복 제거 실행"""
    logger.info("=" * 60)
    logger.info("중복 제거 시작")
    logger.info("=" * 60)

    # 입력 파일 찾기
    input_file = RAW_DIR / "biology_classic_raw.parquet"

    if not input_file.exists():
        # partial 파일들 합치기
        partial_files = list(RAW_DIR.glob("biology_classic_partial_*.parquet"))
        if partial_files:
            logger.info(f"{len(partial_files)}개의 partial 파일 발견, 합치는 중...")
            all_records = []
            for pf in partial_files:
                records = load_from_parquet(pf)
                all_records.extend(records)

            if all_records:
                save_to_parquet(all_records, input_file)
                logger.info(f"합쳐진 파일 저장: {input_file}")
        else:
            logger.error("처리할 파일이 없습니다.")
            return []

    # 로드
    records = load_from_parquet(input_file)

    if not records:
        logger.error("레코드가 없습니다.")
        return []

    # 중복 제거
    dedup = Deduplicator()
    unique_records = dedup.deduplicate(records, exact_first=True, fuzzy=True)

    # medicine 콘텐츠 필터링
    filtered_records = [
        r for r in unique_records
        if not r.get("is_excluded_medical", False)
    ]
    excluded_count = len(unique_records) - len(filtered_records)
    logger.info(f"medicine 콘텐츠 제외: {excluded_count}개")

    # 저장
    output_file = PROCESSED_DIR / "biology_classic_deduped.parquet"
    save_to_parquet(filtered_records, output_file)

    print_collection_stats(filtered_records)

    return filtered_records


def run_stats():
    """통계 확인"""
    logger.info("=" * 60)
    logger.info("통계 확인")
    logger.info("=" * 60)

    # Raw 데이터
    raw_file = RAW_DIR / "biology_classic_raw.parquet"
    if raw_file.exists():
        logger.info("\n[Raw 데이터]")
        records = load_from_parquet(raw_file)
        print_collection_stats(records)

    # 처리된 데이터
    processed_file = PROCESSED_DIR / "biology_classic_deduped.parquet"
    if processed_file.exists():
        logger.info("\n[처리된 데이터]")
        records = load_from_parquet(processed_file)
        print_collection_stats(records)


def run_all(max_per_query: int = 10000):
    """전체 파이프라인 실행"""
    logger.info("=" * 60)
    logger.info("전체 파이프라인 시작")
    logger.info("=" * 60)

    # 1. 크롤링
    run_crawl(max_per_query=max_per_query)

    # 2. 중복 제거
    run_dedup()

    # 3. 최종 통계
    run_stats()

    logger.info("전체 파이프라인 완료!")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="생명과학 고전(1970~1999) 데이터 수집 파이프라인"
    )
    parser.add_argument(
        "--mode",
        choices=["crawl", "dedup", "stats", "all"],
        default="all",
        help="실행 모드 (기본: all)"
    )
    parser.add_argument(
        "--max-per-query",
        type=int,
        default=10000,
        help="쿼리당 최대 결과 수 (기본: 10000)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Semantic Scholar API 키 (선택)"
    )

    args = parser.parse_args()

    # API 키 설정
    if args.api_key:
        import os
        os.environ["S2_API_KEY"] = args.api_key

    # 모드별 실행
    if args.mode == "crawl":
        run_crawl(max_per_query=args.max_per_query)
    elif args.mode == "dedup":
        run_dedup()
    elif args.mode == "stats":
        run_stats()
    elif args.mode == "all":
        run_all(max_per_query=args.max_per_query)


if __name__ == "__main__":
    main()
