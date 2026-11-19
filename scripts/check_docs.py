"""Fail if a doc mentions a file path or a `name` in a file that no longer exists."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "AGENTS.md", ROOT / "DESIGN.md", *sorted((ROOT / "docs").glob("*.md"))]
PATH = re.compile(r"`((?:src|tests|docs|skills|scripts|\.github)/[\w./\-]+|[A-Z][\w\-]*\.md)`")
# "`symbol` em/in `path.py`" pairs: the symbol must exist in that file.
SYMBOL = re.compile(r"`(\w+)`(?: (?:em|in|de|of))? `(src/[\w./\-]+\.py)`")


def main() -> int:
    problems = []
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        for path in set(PATH.findall(text)):
            if not (ROOT / path).exists():
                problems.append(f"{doc.name}: path not found: {path}")
        for symbol, path in set(SYMBOL.findall(text)):
            target = ROOT / path
            if target.is_file() and not re.search(rf"\b{re.escape(symbol)}\b", target.read_text(encoding="utf-8")):
                problems.append(f"{doc.name}: `{symbol}` not found in {path}")
    for problem in problems:
        print(problem)
    print(f"{len(DOCS)} docs checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
