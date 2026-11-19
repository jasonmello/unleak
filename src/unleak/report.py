"""Review report: what was hidden, when, and where. HTML for people, JSON for agents."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import cv2

from . import __version__
from .pipeline import Finding, Result

LABELS = {
    "secret": "API key or token",
    "credential": "Password or credential",
    "email": "E-mail address",
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "card": "Card number",
    "phone": "Phone number",
    "ip": "IP address",
    "token": "Long random string",
    "custom": "Your own term",
}


def mask(text: str) -> str:
    """Show just enough to recognise the item, never the item itself."""
    keep = min(4, len(text) // 4)
    return text[:keep] + "•" * min(8, max(3, len(text) - keep))


def clock(seconds: float) -> str:
    minutes, rest = divmod(max(0.0, seconds), 60)
    return f"{int(minutes)}:{rest:04.1f}"


def to_dict(result: Result, report: Path | None = None) -> dict:
    return {
        "version": __version__,
        "source": str(result.source),
        "output": str(result.output) if result.output else None,
        "report": str(report) if report else None,
        "duration_seconds": round(result.duration, 2),
        "frames": result.frames,
        "ocr_passes": result.ocr_passes,
        "findings": [
            {
                "kind": f.kind,
                "label": LABELS.get(f.kind, f.kind),
                "text_masked": mask(f.text),
                "first_seen_seconds": round(f.first_seen, 2),
                "last_seen_seconds": round(f.last_seen, 2),
                "box": list(f.box),
            }
            for f in result.findings
        ],
    }


def to_json(result: Result, report: Path | None = None) -> str:
    return json.dumps(to_dict(result, report), indent=2, ensure_ascii=False)


def _image_tag(finding: Finding) -> str:
    if finding.thumbnail is None:
        return ""
    ok, data = cv2.imencode(".jpg", finding.thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        return ""
    encoded = base64.b64encode(data.tobytes()).decode()
    return f'<img alt="Hidden area in the output" src="data:image/jpeg;base64,{encoded}">'


_CSS = """
:root { --bg:#f6f5f1; --card:#ffffff; --ink:#1c1b19; --muted:#6b6862; --line:#e3e0d8; --accent:#c2410c; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#151412; --card:#1e1d1a; --ink:#f1efe9; --muted:#a19d94; --line:#33312c; --accent:#fb923c; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 26px; line-height:1.2; margin: 0 0 6px; letter-spacing:-0.01em; }
.sub { color: var(--muted); margin: 0 0 28px; overflow-wrap:anywhere; }
.stats { display:flex; flex-wrap:wrap; gap:24px; padding:16px 0; margin-bottom:28px;
  border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.stats b { display:block; font-size:22px; font-variant-numeric: tabular-nums; }
.stats span { color: var(--muted); font-size:13px; }
.note { border-left:3px solid var(--accent); padding:2px 0 2px 14px; margin:0 0 32px; }
.item { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:16px; margin-bottom:12px; display:grid; gap:12px; }
.head { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline; }
.kind { font-weight:600; }
.text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:13px; }
.time { color:var(--muted); font-size:13px; margin-left:auto; font-variant-numeric: tabular-nums; }
img { max-width:100%; height:auto; border-radius:6px; border:1px solid var(--line); display:block; }
.empty { color:var(--muted); padding:28px 0; }
footer { color:var(--muted); font-size:13px; margin-top:36px; }
"""


def to_html(result: Result) -> str:
    esc = html.escape
    count = len(result.findings)
    is_video = result.frames > 1
    items = []
    for f in result.findings:
        when = f"{clock(f.first_seen)} to {clock(f.last_seen)}" if is_video else ""
        items.append(
            '<div class="item"><div class="head">'
            f'<span class="kind">{esc(LABELS.get(f.kind, f.kind))}</span>'
            f'<span class="text">{esc(mask(f.text))}</span>'
            f'<span class="time">{when}</span></div>{_image_tag(f)}</div>'
        )
    body = "\n".join(items) or '<p class="empty">Nothing sensitive was found. Watch the video once before sharing anyway.</p>'
    stats = f"<div><b>{count}</b><span>item{'s' if count != 1 else ''} hidden</span></div>"
    if is_video:
        stats += (
            f"<div><b>{clock(result.duration)}</b><span>video length</span></div>"
            f"<div><b>{result.ocr_passes}</b><span>frames read with OCR</span></div>"
        )
    output = esc(result.output.name) if result.output else "no file written (dry run)"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>unleak report: {esc(result.source.name)}</title>
<style>{_CSS}</style></head>
<body><main>
<h1>What unleak hid</h1>
<p class="sub">{esc(result.source.name)} → {output}</p>
<div class="stats">{stats}</div>
<p class="note">unleak lowers the risk, it does not remove it. Text that is tiny, stylised,
or on screen for a fraction of a second can be missed. Check the output before you share it.</p>
{body}
<footer>Made by unleak {__version__}. Everything ran on this computer. The pictures above come from the output file, so this report shows no hidden text.</footer>
</main></body></html>
"""


def write_html(result: Result, path: Path) -> Path:
    path.write_text(to_html(result), encoding="utf-8")
    return path
