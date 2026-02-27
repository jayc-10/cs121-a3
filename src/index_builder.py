"""
Index builder: constructs inverted index from HTML documents.
M1 Developer: stemming, important-token boost, partial indexing + merge, doc_id->url mapping.
"""

import json
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

from .tokenizer import (
    get_stemmed_tokens_from_html,
    get_important_tokens_from_html,
    read_html_file,
)
from .posting import InvertedIndex, Posting

# Boost for important tokens (title, h1-h3, strong, b)
IMPORTANT_BOOST = 2

# Minimum number of partial index flushes (M1 requirement: ≥3)
MIN_PARTIALS = 3


def _strip_fragment(url: str) -> str:
    """Remove URL fragment (#...) for doc mapping."""
    parsed = urlparse(url)
    if parsed.fragment:
        parsed = parsed._replace(fragment="")
    return parsed.geturl()


def _read_doc_content_and_url(filepath: Path) -> tuple[str, str | None]:
    """
    Read document content and URL from a file.
    - .json: returns (content, url with fragment stripped). url from "url" key.
    - .html: returns (content, None).
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()
    if suffix == ".json":
        raw = filepath.read_text(encoding="utf-8")
        data = json.loads(raw)
        if "content" not in data:
            raise ValueError(f"JSON file has no 'content' field: {filepath}")
        content = data["content"]
        url = data.get("url")
        if url is not None:
            url = _strip_fragment(url)
        return content, url
    content = read_html_file(filepath)
    return content, None


def _flush_partial_index(
    in_memory: dict[str, list[tuple[int, int, int]]],
    partial_path: Path,
) -> None:
    """
    Write partial index to disk: sorted by term, postings sorted by doc_id.
    Format: one JSON object per line (JSONL) with term and list of [doc_id, tf, tf_imp].
    """
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    with open(partial_path, "w", encoding="utf-8") as f:
        for term in sorted(in_memory.keys()):
            postings = sorted(in_memory[term], key=lambda x: x[0])  # by doc_id
            line = json.dumps({"term": term, "postings": postings}, ensure_ascii=False) + "\n"
            f.write(line)


def _merge_partial_indexes(partial_paths: list[Path], output_path: Path) -> int:
    """
    Merge partial index files into a final on-disk index.

    Input partial format (JSONL, one object per line):
        {"term": str, "postings": [[doc_id, tf, tf_imp], ...]}

    Output index format (also JSONL, sorted by term for easier inspection):
        {"term": str, "postings": [[doc_id, tf, tf_imp], ...]}

    Additionally, create a lexicon file alongside the index that maps each term
    to its byte offset in the index file. This enables the search component to
    seek directly to a term's postings without loading the whole index.
    """
    merged: dict[str, list[tuple[int, int, int]]] = {}
    for path in partial_paths:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                term = obj["term"]
                postings = [tuple(x) for x in obj["postings"]]
                if term not in merged:
                    merged[term] = []
                merged[term].extend(postings)

    # Write final index as JSONL and build lexicon (term -> byte offset).
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lexicon: dict[str, int] = {}
    with open(output_path, "w", encoding="utf-8") as f:
        for term in sorted(merged.keys()):
            postings = merged[term]
            postings.sort(key=lambda x: x[0])
            offset = f.tell()
            lexicon[term] = offset
            line_obj = {
                "term": term,
                "postings": [
                    [doc_id, tf, tf_imp] for doc_id, tf, tf_imp in postings
                ],
            }
            f.write(json.dumps(line_obj, ensure_ascii=False) + "\n")

    # Save lexicon: same directory, "<index_stem>_lexicon.json"
    lexicon_path = output_path.with_name(output_path.stem + "_lexicon.json")
    with open(lexicon_path, "w", encoding="utf-8") as lf:
        json.dump(lexicon, lf, ensure_ascii=False)

    # Return number of unique terms in the final index.
    return len(merged)


def build_index_with_partials(
    data_dir: Path,
    *,
    index_path: Path,
    doc_mapping_path: Path,
    docs_per_partial: int | None = None,
    min_partials: int = MIN_PARTIALS,
    important_boost: int = IMPORTANT_BOOST,
) -> tuple[int, int]:
    """
    Build inverted index using partial indexing + merge (M1 compliant).
    - Uses integer doc_id (0, 1, 2, ...). Saves doc_id -> url in doc_mapping_path.
    - Stems tokens (Porter), counts TF from body and important tokens (title, h1-h3, strong, b) with boost.
    - Flushes partial index when every docs_per_partial documents (or to get ≥ min_partials).
    - Merges partials into index_path.
    Returns (num_docs, num_terms).
    """
    data_dir = Path(data_dir)
    index_path = Path(index_path)
    doc_mapping_path = Path(doc_mapping_path)
    temp_dir = index_path.parent / ".partials"
    temp_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(data_dir.rglob("*.html"))
    json_files = list(data_dir.rglob("*.json"))
    doc_files = sorted(html_files + json_files, key=lambda p: str(p))
    total_docs = len(doc_files)
    if total_docs == 0:
        return 0, 0

    # Ensure we get at least min_partials flushes
    if docs_per_partial is None:
        docs_per_partial = max(1, total_docs // min_partials)
    else:
        docs_per_partial = max(1, min(docs_per_partial, total_docs))

    doc_id_to_url: list[str] = []
    in_memory: dict[str, list[tuple[int, int, int]]] = {}
    partial_paths: list[Path] = []
    next_doc_id = 0
    root = data_dir

    for filepath in doc_files:
        try:
            content, url = _read_doc_content_and_url(filepath)
        except Exception as e:
            print(f"Warning: could not read {filepath}: {e}")
            continue

        try:
            rel = filepath.relative_to(root)
            doc_id_str = str(rel).replace("\\", "/")
        except ValueError:
            doc_id_str = filepath.name

        # Integer doc_id for compact index
        doc_id_int = next_doc_id
        next_doc_id += 1
        doc_id_to_url.append(url if url is not None else doc_id_str)

        # Stemmed body tokens + important tokens with boost
        body_tokens = get_stemmed_tokens_from_html(content)
        imp_tokens = get_important_tokens_from_html(content)
        tf_body = Counter(body_tokens)
        tf_imp = Counter(imp_tokens)

        for token in set(tf_body.keys()) | set(tf_imp.keys()):
            tf = tf_body.get(token, 0)
            imp = tf_imp.get(token, 0)
            # Combined: tf + boost * tf_imp (store both for flexibility)
            if token not in in_memory:
                in_memory[token] = []
            in_memory[token].append((doc_id_int, tf, imp))

        # Flush every docs_per_partial documents (ensures ≥ min_partials partials when total_docs >= min_partials)
        if next_doc_id > 0 and next_doc_id % docs_per_partial == 0:
            partial_path = temp_dir / f"partial_{len(partial_paths)}.jsonl"
            _flush_partial_index(in_memory, partial_path)
            partial_paths.append(partial_path)
            in_memory = {}

    # Final flush if anything left
    if in_memory:
        partial_path = temp_dir / f"partial_{len(partial_paths)}.jsonl"
        _flush_partial_index(in_memory, partial_path)
        partial_paths.append(partial_path)

    # Merge partials into final index and get unique term count
    num_terms = _merge_partial_indexes(partial_paths, index_path)

    # Save doc mapping: doc_id (index) -> url
    with open(doc_mapping_path, "w", encoding="utf-8") as f:
        json.dump(doc_id_to_url, f, indent=2, ensure_ascii=False)

    # Cleanup partials
    for p in partial_paths:
        try:
            p.unlink()
        except OSError:
            pass
    try:
        temp_dir.rmdir()
    except OSError:
        pass

    return len(doc_id_to_url), num_terms


def build_index_from_directory(
    data_dir: Path,
    *,
    root_dir: Path | None = None,
) -> tuple[InvertedIndex, set[str]]:
    """
    Build inverted index from all HTML/document files in a directory (recursive).
    Single-pass in-memory (no partials). Supports .html and .json with "content".
    Uses stemmed tokens and important-token boost.
    Returns (index, set of doc_ids).
    """
    index = InvertedIndex()
    doc_ids: set[str] = set()
    data_dir = Path(data_dir)
    root = Path(root_dir) if root_dir else data_dir

    html_files = list(data_dir.rglob("*.html"))
    json_files = list(data_dir.rglob("*.json"))
    doc_files = html_files + json_files

    for filepath in doc_files:
        try:
            content, _url = _read_doc_content_and_url(filepath)
        except Exception as e:
            print(f"Warning: could not read {filepath}: {e}")
            continue

        try:
            doc_id = str(filepath.relative_to(root)).replace("\\", "/")
        except ValueError:
            doc_id = filepath.name
        doc_ids.add(doc_id)

        body_tokens = get_stemmed_tokens_from_html(content)
        imp_tokens = get_important_tokens_from_html(content)
        tf_body = Counter(body_tokens)
        tf_imp = Counter(imp_tokens)
        for token in set(tf_body.keys()) | set(tf_imp.keys()):
            tf = tf_body.get(token, 0)
            imp = tf_imp.get(token, 0)
            index.add_posting(token, doc_id, tf, tf_imp=imp)

    return index, doc_ids


def build_index_from_directories(
    *data_dirs: Path,
) -> tuple[InvertedIndex, set[str]]:
    """
    Build a single inverted index from multiple data directories (in-memory).
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
                index.add_posting(token, p.doc_id, p.tf, getattr(p, "tf_imp", 0))

    return index, doc_ids
