# Search Engine - Milestone 1: Index Construction

CS 121 Assignment 3 - Inverted index builder for HTML document collections.

## Setup

```bash
pip install -r requirements.txt
```

## Data

Extract `developer.zip` into the `data/` folder. The script will recursively find all HTML files (e.g. `data/DEV/.../*.html`).

## Build the Index

```bash
python build_index.py
```

Options:

- `--output path`   Custom output path for `index.json`

## Output

1. **index.json** - The inverted index on disk (token → list of {doc_id, tf})
2. **Analytics** - Printed to console for your PDF report:
   - Number of indexed documents
   - Number of unique tokens
   - Total size of index (KB)

Copy the analytics table into your report.

## Project Structure

```
a3/
├── build_index.py      # Main script
├── requirements.txt
├── data/               # Extract developer.zip here
├── src/
│   ├── tokenizer.py    # HTML parsing, tokenization
│   ├── posting.py      # Posting & InvertedIndex
│   └── index_builder.py
└── index.json          # Generated index
```

## Report

Include a PDF with a table containing (minimum):

| Metric | Value |
|--------|-------|
| Number of indexed documents | ... |
| Number of unique tokens | ... |
| Total size of index (KB) | ... |
