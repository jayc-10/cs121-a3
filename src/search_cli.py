"""
Search component (M2) for the developer flavor search engine.

Requirements satisfied:
- Uses the same stemming/tokenization as the indexer.
- Supports AND-only boolean queries.
- Does not load the entire inverted index into memory:
  * Postings are stored on disk in a JSONL index file.
  * A small in-memory lexicon maps each term to its byte offset in the index.
- Works over the full developer corpus (tens of thousands of pages).

Usage (from repo root, after building the index):
    python -m src.search_cli \
        --index data/index.jsonl \
        --lexicon data/index_lexicon.json \
        --docmap data/doc_mapping.json
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .tokenizer import tokenize, stem_tokens
from .index_builder import IMPORTANT_BOOST


@dataclass
class PostingEntry:
    doc_id: int
    tf: int
    tf_imp: int


class DiskIndexReader:
    """
    Random-access reader for the on-disk JSONL inverted index.

    The index file format (one line per term) is:
        {"term": str, "postings": [[doc_id, tf, tf_imp], ...]}

    A separate lexicon file stores:
        {term: byte_offset_in_index_file}
    """

    def __init__(self, index_path: Path, lexicon_path: Path) -> None:
        self.index_path = Path(index_path)
        self.lexicon_path = Path(lexicon_path)

        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_path}")
        if not self.lexicon_path.exists():
            raise FileNotFoundError(f"Lexicon file not found: {self.lexicon_path}")

        # Load lexicon (term -> byte offset). This is small compared to postings.
        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            self.lexicon: Dict[str, int] = json.load(f)

        # Open index file once; reuse handle for all queries.
        self._fh = open(self.index_path, "r", encoding="utf-8")

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

    def get_postings(self, term: str) -> List[PostingEntry]:
        """
        Return postings list for a term, or [] if term not in index.
        """
        offset = self.lexicon.get(term)
        if offset is None:
            return []
        self._fh.seek(offset)
        line = self._fh.readline()
        if not line:
            return []
        obj = json.loads(line)
        postings_raw = obj.get("postings", [])
        return [
            PostingEntry(int(doc_id), int(tf), int(tf_imp))
            for doc_id, tf, tf_imp in postings_raw
        ]


def normalize_query(raw_query: str) -> List[str]:
    """
    Tokenize and stem the raw query string using the same logic as indexing.
    """
    tokens = tokenize(raw_query)
    return stem_tokens(tokens)


def intersect_postings_and(
    postings_lists: List[List[PostingEntry]],
) -> List[PostingEntry]:
    """
    Intersect postings lists by doc_id (AND query).
    Assumes each postings list is sorted by doc_id (as produced by the indexer).
    Returns postings for documents that contain all query terms.
    """
    if not postings_lists:
        return []
    # Start from the shortest list for efficiency.
    postings_lists = sorted(postings_lists, key=len)
    result = postings_lists[0]
    for other in postings_lists[1:]:
        i = j = 0
        new_result: List[PostingEntry] = []
        while i < len(result) and j < len(other):
            d1 = result[i].doc_id
            d2 = other[j].doc_id
            if d1 == d2:
                # Combine tf / tf_imp from all terms by summing them.
                combined = PostingEntry(
                    doc_id=d1,
                    tf=result[i].tf + other[j].tf,
                    tf_imp=result[i].tf_imp + other[j].tf_imp,
                )
                new_result.append(combined)
                i += 1
                j += 1
            elif d1 < d2:
                i += 1
            else:
                j += 1
        result = new_result
        if not result:
            break
    return result


def rank_documents_tf_idf(
    postings_by_term: Dict[str, List[PostingEntry]],
    N_docs: int,
) -> List[Tuple[int, float]]:
    """
    Rank documents using a simple tf-idf style score that also boosts important tokens.

    Score(d) = sum_{t in query} ( (tf_body + IMPORTANT_BOOST * tf_imp) * idf(t) )
    where idf(t) = log(1 + N / (1 + df_t))
    """
    if N_docs <= 0:
        return []

    # Compute document scores
    scores: Dict[int, float] = {}
    for term, postings in postings_by_term.items():
        if not postings:
            continue
        df = len(postings)
        idf = math.log(1.0 + (N_docs / (1.0 + df)))
        for p in postings:
            weight = p.tf + IMPORTANT_BOOST * p.tf_imp
            if weight <= 0:
                continue
            scores[p.doc_id] = scores.get(p.doc_id, 0.0) + weight * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def run_search_loop(
    index_path: Path,
    lexicon_path: Path,
    doc_mapping_path: Path,
    top_k: int = 10,
) -> None:
    """
    Interactive command-line search loop.
    """
    reader = DiskIndexReader(index_path=index_path, lexicon_path=lexicon_path)
    try:
        with open(doc_mapping_path, "r", encoding="utf-8") as f:
            doc_id_to_url = json.load(f)
        N_docs = len(doc_id_to_url)

        print(f"Loaded doc mapping for {N_docs} documents.")
        print("Enter queries (AND semantics). Empty line or Ctrl+C to exit.")

        while True:
            try:
                raw_query = input("query> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw_query:
                break

            query_terms = normalize_query(raw_query)
            if not query_terms:
                print("No valid terms in query.")
                continue

            # Fetch postings per term from disk.
            postings_by_term: Dict[str, List[PostingEntry]] = {}
            for term in query_terms:
                postings_by_term[term] = reader.get_postings(term)

            # AND intersection (boolean retrieval requirement).
            non_empty_lists = [pl for pl in postings_by_term.values() if pl]
            if not non_empty_lists:
                print("No documents matched the query.")
                continue

            intersection = intersect_postings_and(non_empty_lists)
            if not intersection:
                print("No documents matched all query terms.")
                continue

            # For ranking, restrict to docs that are in the AND intersection.
            allowed_doc_ids = {p.doc_id for p in intersection}
            filtered_by_term: Dict[str, List[PostingEntry]] = {}
            for term, postings in postings_by_term.items():
                filtered_by_term[term] = [p for p in postings if p.doc_id in allowed_doc_ids]

            ranked = rank_documents_tf_idf(filtered_by_term, N_docs=N_docs)
            if not ranked:
                print("Matched documents, but could not rank them.")
                continue

            print(f"Top {min(top_k, len(ranked))} results:")
            for rank, (doc_id, score) in enumerate(ranked[:top_k], start=1):
                url = doc_id_to_url[doc_id] if 0 <= doc_id < len(doc_id_to_url) else f"<doc {doc_id}>"
                print(f"{rank:2d}. score={score:.4f}  {url}")

    finally:
        reader.close()


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Developer search CLI (M2).")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("data/index.jsonl"),
        help="Path to JSONL index file.",
    )
    parser.add_argument(
        "--lexicon",
        type=Path,
        default=Path("data/index_lexicon.json"),
        help="Path to term->offset lexicon JSON file.",
    )
    parser.add_argument(
        "--docmap",
        type=Path,
        default=Path("data/doc_mapping.json"),
        help="Path to doc_id->URL mapping JSON file.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top results to show.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    run_search_loop(
        index_path=args.index,
        lexicon_path=args.lexicon,
        doc_mapping_path=args.docmap,
        top_k=args.top,
    )


if __name__ == "__main__":
    main()

