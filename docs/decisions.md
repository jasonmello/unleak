# Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-19 | Name: `unleak` | `hush` was taken on PyPI; `unleak` was free on PyPI and had no relevant project on GitHub. |
| 2026-11-19 | v1 processes the video after recording; live mode comes later (OBS filter) | Blurring while recording on Mac and Windows is much harder; post-processing already solves the problem. |
| 2026-11-19 | No LLM in detection: local OCR plus rules | An LLM per frame would be slow and costly and would send the screen to the cloud. The agent (Claude Code, Codex) only calls the CLI. |
| 2026-11-19 | No GUI in v1; the HTML report is the review screen | Shortest path to something useful. A drag-and-drop app only if there is traction. |
| 2026-11-19 | `imageio-ffmpeg` instead of PyAV | PyAV and OpenCV each ship their own copy of the ffmpeg libraries, and macOS prints duplicate-class warnings on every run. The ffmpeg binary avoids that and needs no separate ffmpeg install. |
| 2026-11-19 | Constant frame rate output | Screen recordings often have a variable rate; fixing it keeps audio in sync when raw frames are piped through ffmpeg. |
| 2026-11-19 | RapidOCR (ONNX) as the only OCR engine | Runs the same on macOS, Windows and Linux, with no GPU and no model download on first run. Apple Vision is a possible later optimisation. |
| 2026-11-19 | The blur shrinks the area to a few cells before enlarging | Gaussian blur and fine mosaic can be reversed; here the detail is discarded. |
| 2026-11-19 | Report and JSON show only masked values and thumbnails from the already-blurred output | The report is often shared with the video; it must not become another leak. |
| 2026-11-19 | Regions are paired by kind, size and distance | The end-to-end test showed that pairing by text fails: OCR reads the same key differently each time. |
| 2026-11-19 | All repository content in English | The project is public and aimed at a global audience. `README.pt-BR.md` is the only translation. |
| 2026-11-19 | Licence changed from MIT to AGPL-3.0-or-later | The author wants contributions but not closed or uncredited republishing. AGPL is the strongest protection that is still open source. Copies made while the code was MIT keep that licence. |
