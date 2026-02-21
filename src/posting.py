"""
Posting and inverted index data structures.

A posting represents a token's occurrence in a document.
For MS1: document_id (int for compactness), term frequency, optional important-token count.
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Posting:
    """
    Represents a token's occurrence in a document.
    - doc_id: document identifier (int for compact index, or str)
    - tf: term frequency (body)
    - tf_imp: optional count from important fields (title, h1-h3, strong, b) for boost
    """

    doc_id: int | str
    tf: int
    tf_imp: int = 0

    def __repr__(self) -> str:
        return f"Posting(doc_id={self.doc_id!r}, tf={self.tf}, tf_imp={self.tf_imp})"


class InvertedIndex:
    """
    Inverted index: map from token -> list of postings.
    Append-only add_posting for scale (no O(df) scan when building/merging).
    """

    def __init__(self) -> None:
        self._index: dict[str, list[Posting]] = {}

    def add_posting(
        self,
        token: str,
        doc_id: int | str,
        tf: int,
        tf_imp: int = 0,
    ) -> None:
        """Append a posting for a token in a document (no duplicate check)."""
        if token not in self._index:
            self._index[token] = []
        self._index[token].append(Posting(doc_id=doc_id, tf=tf, tf_imp=tf_imp))

    def get_postings(self, token: str) -> list[Posting]:
        """Return the list of postings for a token, or empty list."""
        return self._index.get(token, [])

    def tokens(self) -> Iterator[str]:
        """Iterate over all tokens in the index."""
        return iter(self._index)

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, token: str) -> bool:
        return token in self._index

    def to_dict(self) -> dict:
        """Serialize to a JSON-serializable dict for saving."""
        return {
            token: [
                {"doc_id": p.doc_id, "tf": p.tf, "tf_imp": getattr(p, "tf_imp", 0)}
                for p in postings_list
            ]
            for token, postings_list in self._index.items()
        }
