"""API keys, tokens, passwords and other credentials."""

from __future__ import annotations

import re
from typing import Iterator

Span = tuple[int, int]

# Known key formats. Lengths are looser than the official ones on purpose:
# OCR may drop or swap a character, and blurring too much beats leaking.
_KNOWN = [
    r"sk-ant-[A-Za-z0-9_\-]{16,}",                 # Anthropic
    r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}",  # OpenAI and lookalikes
    r"gh[pousr]_[A-Za-z0-9]{30,}",                 # GitHub
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"glpat-[A-Za-z0-9_\-]{18,}",                  # GitLab
    r"(?:AKIA|ASIA)[0-9A-Z]{16}",                  # AWS access key id
    r"AIza[0-9A-Za-z_\-]{30,}",                    # Google
    r"xox[abprs]-[A-Za-z0-9\-]{10,}",              # Slack
    r"(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}",  # Stripe
    r"hf_[A-Za-z0-9]{30,}",                        # Hugging Face
    r"npm_[A-Za-z0-9]{30,}",                       # npm
    r"SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}",  # SendGrid
    r"eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}",  # JWT
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----",
]
_KNOWN_RE = re.compile("|".join(f"(?:{p})" for p in _KNOWN))


def find_known_keys(text: str) -> Iterator[Span]:
    for m in _KNOWN_RE.finditer(text):
        yield m.span()


# name = value pairs, such as API_KEY=abc123 or "password": "hunter2".
_PASSWORD_WORDS = r"pass(?:word|wd|phrase)?|pwd|senha"
_SECRET_WORDS = r"api[_\-]?key|apikey|secret|token|bearer|auth|credential|private[_\-]?key|access[_\-]?key"
_KEYWORD_RE = re.compile(
    rf"(?P<name>{_PASSWORD_WORDS}|{_SECRET_WORDS})[A-Za-z0-9_\-]*[\"']?\s*[:=]\s*[\"']?(?P<value>[^\s\"',;]+)",
    re.IGNORECASE,
)
_PASSWORD_RE = re.compile(_PASSWORD_WORDS, re.IGNORECASE)
_PLACEHOLDERS = {"true", "false", "null", "none", "undefined", "string", "required"}


def _looks_secret(value: str) -> bool:
    has_digit = any(c.isdigit() for c in value)
    has_alpha = any(c.isalpha() for c in value)
    return len(value) >= 12 and has_digit and has_alpha


# user:password@host inside a connection string.
_URL_PASSWORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s/:@]+:(?P<value>[^\s/@]+)@")


def find_keyword_values(text: str) -> Iterator[Span]:
    for m in _URL_PASSWORD_RE.finditer(text):
        yield m.span("value")
    for m in _KEYWORD_RE.finditer(text):
        value = m.group("value")
        if value.lower() in _PLACEHOLDERS:
            continue
        is_password = _PASSWORD_RE.fullmatch(m.group("name")) is not None
        if (is_password and len(value) >= 4) or _looks_secret(value):
            yield m.span("value")


# Long random-looking strings: unknown key formats, or a key wrapped to a new line.
_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9_\-])")


def find_long_tokens(text: str) -> Iterator[Span]:
    for m in _TOKEN_RE.finditer(text):
        value = m.group()
        classes = (
            any(c.islower() for c in value),
            any(c.isupper() for c in value),
            any(c.isdigit() for c in value),
        )
        # Lowercase hex (git hashes) has only two classes and is left alone.
        if all(classes):
            yield m.span()
