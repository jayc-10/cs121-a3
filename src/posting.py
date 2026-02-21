"""
Posting and inverted index data structures.

A posting represents a token's occurrence in a document.
For MS1: document_id and term frequency.
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Posting:
    """
    Represents a token's occurrence in a document.
    - doc_id: document name/identifier
    - tf: term frequency (count of token in document) for MS1
    """

    doc_id: str
    tf: int

    def __repr__(self) -> str:
        return f"Posting(doc_id={self.doc_id!r}, tf={self.tf})"


class InvertedIndex:
    """
    Inverted index: map from token -> list of postings.
    """

    def __init__(self) -> None:
        self._index: dict[str, list[Posting]] = {}

    def add_posting(self, token: str, doc_id: str, tf: int) -> None:
        """Add or update a posting for a token in a document."""
        if token not in self._index:
            self._index[token] = []
        postings = self._index[token]
        for p in postings:
            if p.doc_id == doc_id:
                p.tf = tf  # update if same doc
                return
        postings.append(Posting(doc_id=doc_id, tf=tf))

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
            token: [{"doc_id": p.doc_id, "tf": p.tf} for p in postings_list]
            for token, postings_list in self._index.items()
        }
