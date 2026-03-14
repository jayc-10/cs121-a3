# CS 121 Assignment 3: Search Engine

Inverted index search engine over the UCI ICS developer corpus (JSON documents with embedded HTML).

## Setup

```bash
pip install -r requirements.txt
```

## Build the Index

1. Extract `developer.zip` into the `data/` folder.
2. Run:

```bash
python build_index.py
```

**Output (developer flavor):**
- `data/index.jsonl` — inverted index (JSONL, one term per line)
- `data/index_lexicon.json` — term → byte offset (for low-memory search)
- `data/doc_mapping.json` — doc_id → URL

## Search

```bash
python -m src.search_cli --index data/index.jsonl --lexicon data/index_lexicon.json --docmap data/doc_mapping.json
```

If `doc_mapping.json` is in the project root:
```bash
python -m src.search_cli --docmap doc_mapping.json
```

Enter queries (AND semantics). Results are ranked by tf-idf with important-token and URL path boost.

## Project Structure

```
a3/
├── build_index.py       # Index construction
├── src/
│   ├── index_builder.py # Partial indexing, merge, stemming, important-token boost
│   ├── tokenizer.py     # HTML parsing, tokenization, stemming (Porter)
│   ├── posting.py       # Posting / InvertedIndex
│   └── search_cli.py    # Search: AND + tf-idf + URL path boost
└── data/                # developer.zip extracted here
    ├── index.jsonl
    ├── index_lexicon.json
    └── doc_mapping.json
```
