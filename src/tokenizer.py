"""
HTML parser and tokenizer for the search engine index.
Extracts text from HTML files and tokenizes it.
Supports stemming (Porter) and extraction of important tokens (title, h1-h3, strong, b).
"""

import re
import warnings
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, MarkupResemblesLocatorWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize as _nltk_word_tokenize
from nltk import download as _nltk_download

_STEMMER = PorterStemmer()
_NLTK_AVAILABLE = True

def _ensure_punkt():
    _nltk_download("punkt", quiet=True)
    _nltk_download("punkt_tab", quiet=True)


def stem_token(word: str) -> str:
    """Return Porter stem of word. If nltk not available, return word as-is."""
    if _STEMMER is not None:
        return _STEMMER.stem(word)
    return word


def stem_tokens(tokens: list[str]) -> list[str]:
    """Stem a list of tokens."""
    if _STEMMER is not None:
        return [_STEMMER.stem(t) for t in tokens]
    return list(tokens)


def extract_text_from_html(html_content: str) -> str:
    """
    Extract visible text from HTML content, stripping tags and scripts.
    """
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_content, "lxml")
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
    Tokenize text into words. Uses NLTK's word_tokenize (Penn Treebank) when
    available for better handling of contractions, punctuation, and hyphenation;
    otherwise falls back to regex on alphanumeric runs.
    Returns lowercase, alphanumeric-only tokens (length >= 1).
    """
    if not text:
        return []
    if _NLTK_AVAILABLE and _nltk_word_tokenize is not None:
        if _ensure_punkt is not None:
            _ensure_punkt()
        raw = _nltk_word_tokenize(text)
        # Lowercase, strip to alphanumeric only (drops punctuation tokens like "n't", ",")
        tokens = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in raw]
        return [t for t in tokens if t]
    # Fallback: simple regex
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return tokens


def get_tokens_from_html(html_content: str) -> list[str]:
    """
    Extract text from HTML and return token list (no stemming).
    """
    text = extract_text_from_html(html_content)
    return tokenize(text)


def get_stemmed_tokens_from_html(html_content: str) -> list[str]:
    """
    Extract text from HTML, tokenize, and return stemmed tokens (Porter).
    Use during indexing before counting TF.
    """
    text = extract_text_from_html(html_content)
    tokens = tokenize(text)
    return stem_tokens(tokens)


def get_important_tokens_from_html(html_content: str) -> list[str]:
    """
    Extract tokens from important HTML elements: <title>, <h1>-<h3>, <b>, <strong>.
    Returns stemmed token list for boost counting.
    """
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html_content, "lxml")
    texts: list[str] = []
    for tag in soup.find_all(["title", "h1", "h2", "h3", "b", "strong"]):
        if tag.string:
            texts.append(tag.string)
        else:
            texts.append(tag.get_text(separator=" ", strip=True))
    combined = " ".join(texts)
    tokens = tokenize(combined)
    return stem_tokens(tokens)


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
