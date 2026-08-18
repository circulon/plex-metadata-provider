"""Text utilities shared by scoring and source clients."""
import re
import unicodedata


def strip_diacritics(text: str) -> str:
    """Remove diacritical marks, e.g. 'Amelie' <- 'Amélie'."""
    if not text:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_for_scoring(text: str) -> str:
    """Case/diacritic/punctuation-insensitive form used before fuzzy title
    comparison (see app/util/scoring.py)."""
    if not text:
        return ""
    text = strip_diacritics(text).lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    return text.strip()
