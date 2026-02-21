# Search Engine - Milestone 1: Index Construction

CS 121 Assignment 3 - Inverted index builder for HTML document collections.

## Setup

```bash
pip install -r requirements.txt
```

## Data Sources

Place your HTML files in:

- **Small collection**: `data/information_analyst/`
- **Larger collection**: `data/algorithms_developer/`

A minimal `sample.html` is included for testing.

## Build the Index

```bash
python build_index.py
```

Options:

- `--source analyst`   Index only information analyst collection
- `--source developer` Index only algorithms developer collection  
- `--source both`      Index both (default)
- `--output path`      Custom output path for `index.json`

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
├── data/
│   ├── information_analyst/   # Small HTML collection
│   └── algorithms_developer/  # Larger HTML collection
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
