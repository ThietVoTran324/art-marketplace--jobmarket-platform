"""Vietnamese-friendly text fold for search (case + diacritics)."""
from __future__ import annotations

import unicodedata


def fold_search_text(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value.strip())
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    return without_marks.casefold()
