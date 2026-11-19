"""Text detectors. Each one takes a line of OCR text and returns character spans.

OCR often drops spaces ("CPF529.982.247-25"), so patterns here never rely on
word boundaries: they use digit/letter lookarounds instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from . import custom, pii, secrets


@dataclass(frozen=True)
class Match:
    kind: str
    start: int
    end: int
    text: str


Detector = Callable[[str], Iterable[tuple[int, int]]]

# Order matters only for labelling: when two spans overlap, the first kind wins.
DETECTORS: dict[str, Detector] = {
    "secret": secrets.find_known_keys,
    "credential": secrets.find_keyword_values,
    "email": pii.find_emails,
    "cpf": pii.find_cpfs,
    "cnpj": pii.find_cnpjs,
    "card": pii.find_cards,
    "phone": pii.find_phones,
    "ip": pii.find_ips,
    "token": secrets.find_long_tokens,
}

KINDS = tuple(DETECTORS) + ("custom",)


def scan(
    text: str,
    kinds: Iterable[str] | None = None,
    also: Iterable[str] = (),
    regions: Iterable[str] = ("BR", "US"),
) -> list[Match]:
    """Return non-overlapping matches in ``text``, sorted by position."""
    wanted = set(kinds) if kinds is not None else set(KINDS)
    spans: list[tuple[int, int, str]] = []
    for kind, detector in DETECTORS.items():
        if kind not in wanted:
            continue
        if kind == "phone":
            found = pii.find_phones(text, regions=tuple(regions))
        else:
            found = detector(text)
        spans.extend((s, e, kind) for s, e in found)
    if "custom" in wanted:
        spans.extend((s, e, "custom") for s, e in custom.find_literals(text, also))

    # Merge overlaps; the earliest-registered kind keeps the label.
    order = {k: i for i, k in enumerate(KINDS)}
    spans.sort(key=lambda s: (s[0], order[s[2]]))
    merged: list[list] = []
    for start, end, kind in spans:
        if merged and start < merged[-1][1]:
            last = merged[-1]
            last[1] = max(last[1], end)
            if order[kind] < order[last[2]]:
                last[2] = kind
        else:
            merged.append([start, end, kind])
    return [Match(kind, s, e, text[s:e]) for s, e, kind in merged]
