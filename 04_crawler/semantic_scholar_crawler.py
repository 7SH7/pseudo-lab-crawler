"""
Semantic Scholar 크롤러
담당자: 김승환

API 문서: https://api.semanticscholar.org/api-docs/
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import requests
from tqdm import tqdm

from config import (
    BATCH_SIZE,
    FIELDS_OF_STUDY,
    RAW_DIR,
    S2_API_BASE,
    S2_API_KEY,
    S2_REQUESTS_PER_SECOND,
    SEARCH_QUERIES,
    YEAR_RANGE,
)
from utils import (
    RateLimiter,
    load_progress,
    logger,
    paper_to_record,
    print_collection_stats,
    save_progress,
    save_to_parquet,
)


class SemanticScholarCrawler:
    """Semantic Scholar API 크롤러"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Semantic Scholar API 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.getenv("S2_API_KEY") or S2_API_KEY
        self.base_url = S2_API_BASE

        # 세션 설정
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["x-api-key"] = self.api_key
            # API Key 있음: 1 req/sec
            self.rate_limiter = RateLimiter(1.0)
            logger.info("API 키가 설정되었습니다. (1 req/sec)")
        else:
            # API Key 없음: 100 req/5min = 0.33 req/sec (3초에 1번)
            self.rate_limiter = RateLimiter(0.33)
            logger.warning("API 키 없이 실행합니다. Rate limit: 3초당 1회 요청")

        # 기본 필드
        self.default_fields = [
            "paperId",
            "title",
            "abstract",
            "authors",
            "year",
            "citationCount",
            "fieldsOfStudy",
            "externalIds",
            "openAccessPdf",
            "publicationTypes",
        ]

        # 진행 상황 파일
        self.progress_file = RAW_DIR / "crawl_progress.json"

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Optional[Dict[str, Any]]:
        """
        API 요청 실행

        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            method: HTTP 메서드

        Returns:
            응답 JSON 또는 None (오류 시)
        """
        url = f"{self.base_url}/{endpoint}"

        self.rate_limiter.wait()

        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.post(url, json=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit 초과
                logger.warning("Rate limit 초과. 60초 대기 후 재시도...")
                time.sleep(60)
                return self._make_request(endpoint, params, method)
            else:
                logger.error(f"API 오류 {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"요청 타임아웃: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"요청 오류: {e}")
            return None

    def search_papers(
        self,
        query: str,
        year_range: tuple = YEAR_RANGE,
        fields_of_study: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        논문 검색

        Args:
            query: 검색어
            year_range: (시작년도, 종료년도)
            fields_of_study: 분야 필터
            limit: 결과 수 (최대 100)
            offset: 오프셋

        Returns:
            검색 결과
        """
        params = {
            "query": query,
            "fields": ",".join(self.default_fields),
            "limit": min(limit, 100),
            "offset": offset,
        }

        # 연도 필터
        if year_range:
            params["year"] = f"{year_range[0]}-{year_range[1]}"

        # 분야 필터 (단일 값만 지원)
        if fields_of_study and len(fields_of_study) == 1:
            params["fieldsOfStudy"] = fields_of_study[0]

        return self._make_request("paper/search", params)

    def bulk_search(
        self,
        query: str,
        year_range: tuple = YEAR_RANGE,
        max_results: int = 10000,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        대량 검색 (/paper/search/bulk, 토큰 기반 페이지네이션)

        Args:
            query: 검색어
            year_range: 연도 범위
            max_results: 최대 결과 수

        Yields:
            논문 데이터
        """
        total_fetched = 0
        token = None

        while total_fetched < max_results:
            params = {
                "query": query,
                "fields": ",".join(self.default_fields),
                "year": f"{year_range[0]}-{year_range[1]}",
            }
            if token:
                params["token"] = token

            result = self._make_request("paper/search/bulk", params)

            if not result:
                logger.warning(f"Bulk 검색 실패: query={query}")
                break

            papers = result.get("data", [])
            if not papers:
                break

            for paper in papers:
                yield paper
                total_fetched += 1
                if total_fetched >= max_results:
                    break

            # 다음 페이지 토큰
            token = result.get("token")
            if not token:
                break

        logger.info(f"검색 완료: query='{query}', 수집={total_fetched}")

    def search_by_field(
        self,
        field_of_study: str,
        year_range: tuple = YEAR_RANGE,
        max_results: int = 50000,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        분야별 검색 (/paper/search/bulk, 토큰 기반 페이지네이션)

        Args:
            field_of_study: 분야명
            year_range: 연도 범위
            max_results: 최대 결과 수

        Yields:
            논문 데이터
        """
        total_fetched = 0
        token = None

        while total_fetched < max_results:
            params = {
                "query": field_of_study,
                "fields": ",".join(self.default_fields),
                "year": f"{year_range[0]}-{year_range[1]}",
                "fieldsOfStudy": field_of_study,
            }
            if token:
                params["token"] = token

            result = self._make_request("paper/search/bulk", params)

            if not result:
                logger.warning(f"분야 검색 실패: {field_of_study}")
                break

            papers = result.get("data", [])
            if not papers:
                break

            for paper in papers:
                yield paper
                total_fetched += 1
                if total_fetched >= max_results:
                    break

            # 다음 페이지 토큰
            token = result.get("token")
            if not token:
                break

        logger.info(f"분야 검색 완료: field='{field_of_study}', 수집={total_fetched}")

    def crawl_all(
        self,
        queries: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        year_range: tuple = YEAR_RANGE,
        max_per_query: int = 10000,
        save_interval: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        전체 크롤링 실행

        Args:
            queries: 검색 쿼리 리스트
            fields: 분야 리스트
            year_range: 연도 범위
            max_per_query: 쿼리당 최대 결과 수
            save_interval: 저장 간격

        Returns:
            수집된 레코드 리스트
        """
        queries = queries or SEARCH_QUERIES
        fields = fields or FIELDS_OF_STUDY

        all_records = []
        seen_paper_ids = set()  # 중복 방지

        # 진행 상황 로드
        progress = load_progress(self.progress_file)
        completed_queries = set(progress.get("completed_queries", []))
        completed_fields = set(progress.get("completed_fields", []))

        # 기존 데이터 로드 (있으면)
        existing_file = RAW_DIR / "biology_classic_raw.parquet"
        if existing_file.exists():
            from utils import load_from_parquet
            existing_records = load_from_parquet(existing_file)
            for r in existing_records:
                seen_paper_ids.add(r.get("source_paper_id"))
            logger.info(f"기존 레코드 {len(seen_paper_ids)}개 로드")

        # ========== 키워드 검색 ==========
        logger.info(f"키워드 검색 시작: {len(queries)}개 쿼리")

        for query in tqdm(queries, desc="키워드 검색"):
            if query in completed_queries:
                logger.info(f"스킵 (완료됨): {query}")
                continue

            try:
                for paper in self.bulk_search(query, year_range, max_per_query):
                    paper_id = paper.get("paperId")
                    if paper_id and paper_id not in seen_paper_ids:
                        seen_paper_ids.add(paper_id)
                        record = paper_to_record(paper, source="semantic_scholar")
                        all_records.append(record)

                        # 중간 저장
                        if len(all_records) % save_interval == 0:
                            self._save_intermediate(all_records)
                            logger.info(f"중간 저장: {len(all_records)}개")

                # 완료 표시
                completed_queries.add(query)
                progress["completed_queries"] = list(completed_queries)
                save_progress(progress, self.progress_file)

            except Exception as e:
                logger.error(f"쿼리 '{query}' 처리 중 오류: {e}")
                continue

        # ========== 분야별 검색 ==========
        logger.info(f"분야별 검색 시작: {len(fields)}개 분야")

        for field in tqdm(fields, desc="분야별 검색"):
            if field in completed_fields:
                logger.info(f"스킵 (완료됨): {field}")
                continue

            try:
                for paper in self.search_by_field(field, year_range, max_per_query):
                    paper_id = paper.get("paperId")
                    if paper_id and paper_id not in seen_paper_ids:
                        seen_paper_ids.add(paper_id)
                        record = paper_to_record(paper, source="semantic_scholar")
                        all_records.append(record)

                        # 중간 저장
                        if len(all_records) % save_interval == 0:
                            self._save_intermediate(all_records)

                # 완료 표시
                completed_fields.add(field)
                progress["completed_fields"] = list(completed_fields)
                save_progress(progress, self.progress_file)

            except Exception as e:
                logger.error(f"분야 '{field}' 처리 중 오류: {e}")
                continue

        # 최종 저장
        if all_records:
            output_path = RAW_DIR / "biology_classic_raw.parquet"
            save_to_parquet(all_records, output_path)
            logger.info(f"최종 저장 완료: {len(all_records)}개 레코드")

        return all_records

    def _save_intermediate(self, records: List[Dict[str, Any]]):
        """중간 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RAW_DIR / f"biology_classic_partial_{timestamp}.parquet"
        save_to_parquet(records, output_path)


def main():
    """메인 실행"""
    logger.info("=" * 50)
    logger.info("Semantic Scholar 크롤링 시작")
    logger.info(f"연도 범위: {YEAR_RANGE[0]} ~ {YEAR_RANGE[1]}")
    logger.info("=" * 50)

    crawler = SemanticScholarCrawler()

    # 크롤링 실행
    records = crawler.crawl_all(
        queries=SEARCH_QUERIES,
        fields=FIELDS_OF_STUDY,
        year_range=YEAR_RANGE,
        max_per_query=10000,  # 쿼리당 최대 1만 건
        save_interval=1000,
    )

    # 통계 출력
    print_collection_stats(records)

    logger.info("크롤링 완료!")


if __name__ == "__main__":
    main()
