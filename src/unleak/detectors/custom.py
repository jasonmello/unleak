"""Literal strings the user wants hidden (client names, project names...)."""

from __future__ import annotations

from typing import Iterable, Iterator

Span = tuple[int, int]


def _squash(text: str) -> tuple[str, list[int]]:
    """Lowercase ``text`` without spaces, plus the original index of each char."""
    chars, index = [], []
    for i, c in enumerate(text):
        if not c.isspace():
            chars.append(c.lower())
            index.append(i)
    return "".join(chars), index


def find_literals(text: str, literals: Iterable[str]) -> Iterator[Span]:
    # OCR drops spaces, so "Acme Corp" must also match "AcmeCorp".
    haystack, index = _squash(text)
    for literal in literals:
        needle, _ = _squash(literal)
        if not needle:
            continue
        pos = haystack.find(needle)
        while pos != -1:
            yield index[pos], index[pos + len(needle) - 1] + 1
            pos = haystack.find(needle, pos + 1)
