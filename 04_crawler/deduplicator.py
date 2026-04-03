"""
중복 제거 모듈
담당자: 김승환

두 가지 방식의 중복 제거:
1. 정확 매칭: content_hash 기반
2. 유사도 매칭: Title/Abstract 유사도 기반
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from tqdm import tqdm

from config import (
    DEDUP_ABSTRACT_THRESHOLD,
    DEDUP_TITLE_THRESHOLD,
    PROCESSED_DIR,
    RAW_DIR,
)
from utils import (
    load_from_parquet,
    logger,
    normalize_text,
    print_collection_stats,
    save_to_parquet,
)


# =============================================================================
# 텍스트 유사도 계산
# =============================================================================
def tokenize(text: str) -> Set[str]:
    """텍스트를 토큰 집합으로 변환"""
    if not text:
        return set()
    # 소문자 변환 + 알파벳/숫자만 추출
    text = text.lower()
    tokens = re.findall(r"\b\w+\b", text)
    return set(tokens)


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Jaccard 유사도 계산"""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def compute_ngram_hash(text: str, n: int = 3) -> Set[int]:
    """n-gram 해시 생성 (MinHash용)"""
    if not text:
        return set()

    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "", text)

    if len(text) < n:
        return {hash(text)}

    ngrams = set()
    for i in range(len(text) - n + 1):
        ngrams.add(hash(text[i:i+n]))

    return ngrams


# =============================================================================
# 중복 제거기
# =============================================================================
class Deduplicator:
    """논문 중복 제거"""

    def __init__(
        self,
        title_threshold: float = DEDUP_TITLE_THRESHOLD,
        abstract_threshold: float = DEDUP_ABSTRACT_THRESHOLD,
    ):
        """
        Args:
            title_threshold: 제목 유사도 임계값
            abstract_threshold: 초록 유사도 임계값
        """
        self.title_threshold = title_threshold
        self.abstract_threshold = abstract_threshold

    def deduplicate_exact(
        self,
        records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        정확 중복 제거 (content_hash 기반)

        Args:
            records: 레코드 리스트

        Returns:
            (중복 제거된 리스트, 제거된 수)
        """
        seen_hashes = {}
        unique_records = []
        duplicates = 0

        for record in tqdm(records, desc="정확 중복 제거"):
            content_hash = record.get("content_hash", "")

            if not content_hash:
                # 해시가 없으면 일단 포함
                unique_records.append(record)
                continue

            if content_hash in seen_hashes:
                # 중복 - 인용 수가 더 많은 것 유지
                existing_idx = seen_hashes[content_hash]
                existing = unique_records[existing_idx]

                if (record.get("citation_count", 0) or 0) > (existing.get("citation_count", 0) or 0):
                    # 새 레코드가 인용 수가 더 많으면 교체
                    unique_records[existing_idx] = record

                duplicates += 1
                record["is_duplicate"] = True
            else:
                seen_hashes[content_hash] = len(unique_records)
                unique_records.append(record)

        logger.info(f"정확 중복 제거: {len(records)} -> {len(unique_records)} ({duplicates}개 제거)")

        return unique_records, duplicates

    def deduplicate_fuzzy(
        self,
        records: List[Dict[str, Any]],
        use_abstract: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        유사도 기반 중복 제거

        Args:
            records: 레코드 리스트
            use_abstract: Abstract 유사도도 검사할지

        Returns:
            (중복 제거된 리스트, 제거된 수)
        """
        if len(records) < 2:
            return records, 0

        # 제목 토큰화
        title_tokens = []
        for record in records:
            title = normalize_text(record.get("title", ""))
            tokens = tokenize(title)
            title_tokens.append(tokens)

        # Abstract 토큰화 (선택적)
        abstract_tokens = []
        if use_abstract:
            for record in records:
                abstract = normalize_text(record.get("abstract", ""))
                tokens = tokenize(abstract)
                abstract_tokens.append(tokens)

        # 블로킹: 첫 단어로 그룹화 (성능 최적화)
        blocks = defaultdict(list)
        for idx, record in enumerate(records):
            title = normalize_text(record.get("title", ""))
            words = title.lower().split()
            if words:
                # 첫 2개 단어를 키로
                key = " ".join(words[:2])
                blocks[key].append(idx)

        # 중복 마킹
        is_duplicate = [False] * len(records)
        duplicate_pairs = []

        for block_key, indices in tqdm(blocks.items(), desc="유사도 중복 검사"):
            if len(indices) < 2:
                continue

            # 블록 내에서 비교
            for i in range(len(indices)):
                if is_duplicate[indices[i]]:
                    continue

                for j in range(i + 1, len(indices)):
                    if is_duplicate[indices[j]]:
                        continue

                    idx1, idx2 = indices[i], indices[j]

                    # 제목 유사도
                    title_sim = jaccard_similarity(title_tokens[idx1], title_tokens[idx2])

                    if title_sim >= self.title_threshold:
                        # Abstract 유사도 (선택적)
                        if use_abstract and abstract_tokens:
                            abs_sim = jaccard_similarity(
                                abstract_tokens[idx1],
                                abstract_tokens[idx2]
                            )
                            if abs_sim < self.abstract_threshold:
                                continue

                        # 인용 수가 적은 것을 중복으로 마킹
                        cite1 = records[idx1].get("citation_count", 0) or 0
                        cite2 = records[idx2].get("citation_count", 0) or 0

                        if cite1 >= cite2:
                            is_duplicate[idx2] = True
                        else:
                            is_duplicate[idx1] = True

                        duplicate_pairs.append((idx1, idx2))

        # 중복 제거
        unique_records = []
        duplicates = 0

        for idx, record in enumerate(records):
            if is_duplicate[idx]:
                record["is_duplicate"] = True
                duplicates += 1
            else:
                unique_records.append(record)

        logger.info(f"유사도 중복 제거: {len(records)} -> {len(unique_records)} ({duplicates}개 제거)")

        return unique_records, duplicates

    def deduplicate(
        self,
        records: List[Dict[str, Any]],
        exact_first: bool = True,
        fuzzy: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        전체 중복 제거 파이프라인

        Args:
            records: 레코드 리스트
            exact_first: 정확 중복 제거 먼저 실행
            fuzzy: 유사도 중복 제거 실행

        Returns:
            중복 제거된 레코드 리스트
        """
        logger.info(f"중복 제거 시작: {len(records)}개 레코드")

        result = records
        total_removed = 0

        if exact_first:
            result, removed = self.deduplicate_exact(result)
            total_removed += removed

        if fuzzy:
            result, removed = self.deduplicate_fuzzy(result)
            total_removed += removed

        logger.info(f"중복 제거 완료: {len(records)} -> {len(result)} (총 {total_removed}개 제거)")

        return result


# =============================================================================
# 크로스 소스 중복 제거
# =============================================================================
def deduplicate_cross_source(
    records_list: List[List[Dict[str, Any]]],
    source_priority: List[str] = ["arxiv", "semantic_scholar"],
) -> List[Dict[str, Any]]:
    """
    여러 소스의 데이터 간 중복 제거

    Args:
        records_list: 소스별 레코드 리스트들
        source_priority: 우선순위 (먼저 나온 소스 우선)

    Returns:
        통합된 레코드 리스트
    """
    # 모든 레코드 합치기
    all_records = []
    for records in records_list:
        all_records.extend(records)

    # 소스 우선순위에 따라 정렬
    priority_map = {source: idx for idx, source in enumerate(source_priority)}

    def sort_key(record):
        source = record.get("source", "")
        priority = priority_map.get(source, 999)
        citations = record.get("citation_count", 0) or 0
        return (priority, -citations)

    all_records.sort(key=sort_key)

    # 중복 제거
    dedup = Deduplicator()
    result = dedup.deduplicate(all_records, exact_first=True, fuzzy=True)

    return result


# =============================================================================
# 메인 실행
# =============================================================================
def main():
    """중복 제거 실행"""
    logger.info("=" * 50)
    logger.info("중복 제거 시작")
    logger.info("=" * 50)

    # 입력 파일
    input_file = RAW_DIR / "biology_classic_raw.parquet"

    if not input_file.exists():
        logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
        return

    # 로드
    records = load_from_parquet(input_file)

    # 중복 제거
    dedup = Deduplicator(
        title_threshold=DEDUP_TITLE_THRESHOLD,
        abstract_threshold=DEDUP_ABSTRACT_THRESHOLD,
    )
    unique_records = dedup.deduplicate(records, exact_first=True, fuzzy=True)

    # medicine 콘텐츠 필터링
    filtered_records = [
        r for r in unique_records
        if not r.get("is_excluded_medical", False)
    ]
    logger.info(f"medicine 콘텐츠 제외: {len(unique_records)} -> {len(filtered_records)}")

    # 저장
    output_file = PROCESSED_DIR / "biology_classic_deduped.parquet"
    save_to_parquet(filtered_records, output_file)

    # 통계
    print_collection_stats(filtered_records)

    logger.info("중복 제거 완료!")


if __name__ == "__main__":
    main()
