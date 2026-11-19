"""Personal data: e-mail, phone, CPF, CNPJ, payment card, IP address."""

from __future__ import annotations

import re
from typing import Iterator

import phonenumbers

Span = tuple[int, int]

_EMAIL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")


def find_emails(text: str) -> Iterator[Span]:
    for m in _EMAIL.finditer(text):
        yield m.span()


_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")


def _digits(s: str) -> list[int]:
    return [int(c) for c in s if c.isdigit()]


def _mod11(digits: list[int], weights: list[int]) -> int:
    rest = sum(d * w for d, w in zip(digits, weights)) % 11
    return 0 if rest < 2 else 11 - rest


def cpf_is_valid(value: str) -> bool:
    d = _digits(value)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    first = _mod11(d[:9], list(range(10, 1, -1)))
    second = _mod11(d[:10], list(range(11, 1, -1)))
    return d[9] == first and d[10] == second


def cnpj_is_valid(value: str) -> bool:
    d = _digits(value)
    if len(d) != 14 or len(set(d)) == 1:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    return d[12] == _mod11(d[:12], w1) and d[13] == _mod11(d[:13], w2)


def find_cpfs(text: str) -> Iterator[Span]:
    for m in _CPF.finditer(text):
        if cpf_is_valid(m.group()):
            yield m.span()


def find_cnpjs(text: str) -> Iterator[Span]:
    for m in _CNPJ.finditer(text):
        if cnpj_is_valid(m.group()):
            yield m.span()


_CARD = re.compile(r"(?<!\d)\d(?:[ \-]?\d){12,18}(?!\d)")


def luhn_is_valid(value: str) -> bool:
    d = _digits(value)
    if not 13 <= len(d) <= 19 or len(set(d)) == 1:
        return False
    total = 0
    for i, n in enumerate(reversed(d)):
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def find_cards(text: str) -> Iterator[Span]:
    for m in _CARD.finditer(text):
        if luhn_is_valid(m.group()):
            yield m.span()


# A phone candidate: optional +, then 10 to 15 digits with common separators.
_PHONE = re.compile(r"(?<![\d.])\+?\(?\d[\d\-\.\(\) ]{6,18}\d(?![\d.])")


def find_phones(text: str, regions: tuple[str, ...] = ("BR", "US")) -> Iterator[Span]:
    for m in _PHONE.finditer(text):
        raw = m.group()
        count = sum(c.isdigit() for c in raw)
        if not 10 <= count <= 15:
            continue
        # Dotted groups of 1-3 digits are version numbers or IPs, not phones.
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){2,}", raw):
            continue
        for region in regions:
            try:
                number = phonenumbers.parse(raw, None if raw.startswith("+") else region)
            except phonenumbers.NumberParseException:
                continue
            if phonenumbers.is_valid_number(number):
                yield m.span()
                break


_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IP_IGNORED = {"0.0.0.0", "127.0.0.1", "255.255.255.255", "255.255.255.0"}


def find_ips(text: str) -> Iterator[Span]:
    for m in _IPV4.finditer(text):
        value = m.group()
        if value in _IP_IGNORED:
            continue
        if all(int(part) <= 255 for part in value.split(".")):
            yield m.span()
