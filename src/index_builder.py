"""
Index builder: constructs inverted index from HTML documents.
"""

from pathlib import Path
from collections import Counter

from .tokenizer import get_tokens_from_html, read_html_file
from .posting import InvertedIndex, Posting


def build_index_from_directory(
    data_dir: Path,
    *,
    root_dir: Path | None = None,
) -> tuple[InvertedIndex, set[str]]:
    """
    Build inverted index from all HTML files in a directory (recursive).
    Returns (index, set of doc_ids).
    Uses path relative to root_dir for doc_id to avoid collisions across subfolders.
    """
    index = InvertedIndex()
    doc_ids: set[str] = set()
    data_dir = Path(data_dir)
    root = Path(root_dir) if root_dir else data_dir

    html_files = list(data_dir.glob("*.html"))
    if not html_files:
        html_files = list(data_dir.rglob("*.html"))

    for filepath in html_files:
        try:
            html_content = read_html_file(filepath)
        except Exception as e:
            print(f"Warning: could not read {filepath}: {e}")
            continue

        # Use path relative to root for unique doc_ids across nested folders
        try:
            doc_id = str(filepath.relative_to(root))
        except ValueError:
            doc_id = filepath.name
        doc_id = doc_id.replace("\\", "/")
        doc_ids.add(doc_id)

        tokens = get_tokens_from_html(html_content)
        term_freq = Counter(tokens)

        for token, tf in term_freq.items():
            index.add_posting(token, doc_id, tf)

    return index, doc_ids


def build_index_from_directories(
    *data_dirs: Path,
) -> tuple[InvertedIndex, set[str]]:
    """
    Build a single inverted index from multiple data directories.
    Document IDs are filenames; if duplicates exist, later overwrites.
    """
    index = InvertedIndex()
    doc_ids: set[str] = set()

    for data_dir in data_dirs:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            continue
        sub_index, sub_docs = build_index_from_directory(
            data_dir, root_dir=data_dir
        )
        doc_ids.update(sub_docs)
        for token in sub_index.tokens():
            for p in sub_index.get_postings(token):
                index.add_posting(token, p.doc_id, p.tf)

    return index, doc_ids
