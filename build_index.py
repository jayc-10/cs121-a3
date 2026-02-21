"""
Build inverted index and output analytics for Milestone 1 report.

Usage:
    python build_index.py

Extract developer.zip into the data/ folder, then run this script.

Output:
  - index.json in the project root
  - Analytics table printed to console (copy to your PDF report)
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.index_builder import build_index_from_directories


def get_index_path() -> Path:
    return Path(__file__).resolve().parent / "index.json"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build inverted index for MS1")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for index JSON (default: index.json)",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    data_dir = base / "data"

    if not data_dir.exists():
        print("No data folder found. Extract developer.zip into the data/ folder.")
        sys.exit(1)

    index, doc_ids = build_index_from_directories(data_dir)

    if not doc_ids:
        print("No HTML or JSON document files found in the data/ folder. Extract developer.zip into data/.")
        sys.exit(1)

    # Serialize and save index
    index_dict = index.to_dict()
    output_path = args.output or get_index_path()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index_dict, f, indent=2, ensure_ascii=False)

    # Compute analytics
    num_docs = len(doc_ids)
    num_tokens = len(index)
    index_size_bytes = output_path.stat().st_size
    index_size_kb = index_size_bytes / 1024

    # Print analytics table for report
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
    print()


if __name__ == "__main__":
    main()
