"""
HTML parser and tokenizer for the search engine index.
Extracts text from HTML files and tokenizes it.
"""

import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def extract_text_from_html(html_content: str) -> str:
    """
    Extract visible text from HTML content, stripping tags and scripts.
    """
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)
    else:
        # Fallback: simple regex to strip HTML tags
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str) -> list[str]:
    """
    Tokenize text: lowercase, split on non-alphanumeric, filter empty tokens.
    """
    if not text:
        return []
    # Lowercase and split on non-word characters
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return tokens


def get_tokens_from_html(html_content: str) -> list[str]:
    """
    Extract text from HTML and return token list.
    """
    text = extract_text_from_html(html_content)
    return tokenize(text)


def read_html_file(filepath: Path) -> str:
    """
    Read HTML file content, handling common encodings.
    """
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return Path(filepath).read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file: {filepath}")
