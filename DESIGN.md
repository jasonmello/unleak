# Design

Taken from the code: `src/unleak/report.py` (report) and `src/unleak/cli.py` (messages). If it changes there, change it here.

## Principles
- **Honest before reassuring.** Every output reminds the reader that the tool lowers the risk and does not remove it.
- **Never show what was hidden.** Text is always masked (`mask`), thumbnails always come from the already-blurred output.
- **One file, no network.** The report is a single HTML file with inline CSS and base64 images. No external font, no script.

## Colours (CSS variables in the report)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f6f5f1` | `#151412` | page background |
| `--card` | `#ffffff` | `#1e1d1a` | card of each item |
| `--ink` | `#1c1b19` | `#f1efe9` | text |
| `--muted` | `#6b6862` | `#a19d94` | secondary text, times |
| `--line` | `#e3e0d8` | `#33312c` | borders and dividers |
| `--accent` | `#c2410c` | `#fb923c` | bar of the limits note |

The dark theme follows `prefers-color-scheme`. In a thumbnail, the hidden area gets a 2 px red outline (BGR 60, 60, 235, in `_thumbnail` in `src/unleak/pipeline.py`).

## Typography
- Text: system font (`ui-sans-serif, system-ui`), 15 px, line height 1.5.
- Title: 26 px. Headline numbers: 22 px, tabular figures.
- Masked value: system monospace, 13 px.

## Space and components
- Single column up to 880 px wide, with a 16 px side gutter.
- Stats row (items hidden, video length, frames read) between two rules.
- Limits note: a paragraph with a 3 px bar on the left, no box.
- Item: card with a 10 px radius and a 1 px border; kind, masked value, time range and thumbnail.
- Hidden area in the video and image: blur with 20% grey on top (`redact` in `src/unleak/regions.py`), so it stays visible on light and dark backgrounds.
- No motion: the report is static.

## Voice
- Plain English everywhere. `README.pt-BR.md` is the only translation.
- Short sentences, direct verbs: "3 items hidden", "Check the output before you share it."
- Say what happened and what the person does next. No exclamation marks, no promise of total safety.
- Errors start with `unleak:` and say how to fix the problem.
- Times use the `m:ss.s` format.

## Content
- Examples and images use fake data only, and say so.
- The kind name shown to people comes from `LABELS` in `src/unleak/report.py`.

## Landing page (`docs/index.html`)
One HTML file with inline CSS and JS, no build step and no external request. Personality: calm, warm paper, mono for anything technical, and one idea repeated everywhere: **the page redacts itself**.

- **Redaction bar** (`.s`): the only decorative device. A bar grows from the left over the text (240 ms) and the text turns transparent. It is used on the logo, one word of the headline, the demo screen, the try-it box and the detector cards. Nothing else on the page animates for show.
- **Tokens**: the report palette above, plus surface steps (`--surface`, `--surface-2`, `--surface-3`), three text levels (`--ink`, `--muted`, `--subtle`) and borders drawn as 1 px shadow rings (`--shadow-rest`, `--shadow-float`). Light and dark follow the system; the sun button overrides it.
- **Type**: system sans for prose, system mono for labels, commands, samples and counters. Headline tracking goes from -0.035em (section titles) to -0.05em (hero). Labels are 11 px mono, uppercase, +0.09em.
- **Radius by role**: controls 8 px, cards 14 px, panels 18 px.
- **Motion**: one curve, `cubic-bezier(.22, 1, .36, 1)`; 140 ms for hover and press, 240 ms for the bar. Buttons scale to .97 when pressed. The hero scan line crosses the demo once in 1.1 s and each secret hides as the line reaches it. With reduced motion everything switches instantly.
- **Honesty rules**: every value shown is fake and the page says so twice. The try-it box runs a JS port of the detectors and states that it skips OCR. The limits section is on the page, not only in the README.
- **Copy**: facts and verbs. No "seamless", no "powerful". The primary button is solid ink; the accent colour is kept for the bar, focus rings, counters and step numbers.

Changing a detector in `src/unleak/detectors/` means updating the `RULES` list in `docs/index.html` too.
