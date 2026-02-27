"""
Build inverted index and output analytics for Milestone 1 report.
M1 Developer: uses partial indexing + merge, doc mapping, stemming, important-token boost.

Usage:
    python build_index.py

Extract developer.zip into the data/ folder, then run this script.

Output (developer flavor, partial indexing enabled):
  - data/index.jsonl          (JSONL inverted index, one term per line)
  - data/index_lexicon.json   (term -> byte offset in index.jsonl)
  - data/doc_mapping.json     (doc_id -> URL, fragment stripped)
  - Analytics table printed to console (copy to your PDF report)
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.index_builder import build_index_with_partials


def get_index_path() -> Path:
    base = Path(__file__).resolve().parent
    return base / "data" / "index.jsonl"


def get_doc_mapping_path() -> Path:
    base = Path(__file__).resolve().parent
    return base / "data" / "doc_mapping.json"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build inverted index for MS1 (M1 Developer)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for index JSON (default: index.json)",
    )
    parser.add_argument(
        "--doc-mapping",
        type=Path,
        default=None,
        help="Output path for doc_id->url mapping (default: doc_mapping.json)",
    )
    parser.add_argument(
        "--no-partials",
        action="store_true",
        help="Disable partial index + merge (single in-memory build)",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    data_dir = base / "data"
    output_path = args.output or get_index_path()
    doc_mapping_path = args.doc_mapping or get_doc_mapping_path()

    if not data_dir.exists():
        print("No data folder found. Extract developer.zip into the data/ folder.")
        sys.exit(1)

    if args.no_partials:
        from src.index_builder import build_index_from_directories
        index, doc_ids = build_index_from_directories(data_dir)
        if not doc_ids:
            print("No HTML or JSON document files found in the data/ folder.")
            sys.exit(1)
        index_dict = index.to_dict()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index_dict, f, indent=2, ensure_ascii=False)
        num_docs = len(doc_ids)
        num_tokens = len(index)
    else:
        num_docs, num_tokens = build_index_with_partials(
            data_dir,
            index_path=output_path,
            doc_mapping_path=doc_mapping_path,
        )
        if num_docs == 0:
            print("No HTML or JSON document files found in the data/ folder.")
            sys.exit(1)

    index_size_bytes = output_path.stat().st_size
    index_size_kb = index_size_bytes / 1024

    print("\n" + "=" * 50)
    print("MILESTONE 1 - INDEX ANALYTICS (for report)")
    print("=" * 50)
    print()
    print("| Metric                    | Value |")
    print("|---------------------------|-------|")
    print(f"| Number of indexed documents | {num_docs} |")
    print(f"| Number of unique tokens     | {num_tokens} |")
    print(f"| Total size of index (KB)    | {index_size_kb:.2f} |")
    print()
    print("=" * 50)
    print(f"\nIndex saved to: {output_path}")
    if not args.no_partials:
        print(f"Doc mapping (doc_id -> url) saved to: {doc_mapping_path}")
    print()


if __name__ == "__main__":
    main()
