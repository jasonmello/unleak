# unleak

Python CLI that blurs sensitive data (e-mail, phone, API keys, passwords, CPF/CNPJ, card numbers) in screen recordings and screenshots. Everything runs locally: OCR (RapidOCR) plus rules. Audience: developers and people who use AI tools, on macOS, Windows and Linux.

## Where things are
| What | Where |
|---|---|
| Command line and options | `src/unleak/cli.py` |
| Video loop (when to read, what to hold back) | `src/unleak/pipeline.py` |
| OCR, boxes, tracking and blur | `src/unleak/regions.py` |
| Reading and writing video (ffmpeg) | `src/unleak/video.py` |
| Text detectors | `src/unleak/detectors/` |
| HTML report and JSON | `src/unleak/report.py` |
| Skill for Claude Code and Codex | `skills/unleak/SKILL.md` |
| Tests | `tests/` |

## Commands
- Install: `uv sync`
- Tests: `uv run pytest -q` (the end-to-end test takes about a minute)
- Check docs: `uv run python scripts/check_docs.py`
- Run: `uv run unleak file.mp4`

## Rules that are never broken
- **Nothing leaves the computer.** No network calls, no LLM in detection, no telemetry.
- **When in doubt, blur.** A false positive is acceptable; a leak is not.
- The report and the JSON never show a hidden value, only the masked form (`mask` in `src/unleak/report.py`).
- The output never overwrites the input.
- Example and test data is always fake.
- A new detector ships with tests for what it catches and what it must not catch.
- Everything in the repository is written in English. `README.pt-BR.md` is the only translation.

## Not verified
- Windows and Linux: only macOS (Apple Silicon) was tested by hand. CI covers all three.
- Real screen recordings: the tests use synthetic videos.
- PyPI: not published yet; installation is from Git.

## Before X, read Y
| Before | Read |
|---|---|
| Touching the video loop, tracking or performance | `docs/architecture.md` |
| Changing a choice already made (libraries, blur, name) | `docs/decisions.md` |
| Touching the HTML report, CLI messages or the READMEs | `DESIGN.md` |
