"""Find the rectangles to hide in a frame, and blur them."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .detectors import scan

OCR_MAX_SIDE = 1920  # larger frames (Retina) are downscaled before OCR
STYLES = ("blur", "pixel", "box")


@dataclass
class Region:
    kind: str
    text: str
    box: tuple[int, int, int, int]  # x0, y0, x1, y1 in frame pixels
    patch: np.ndarray | None = field(default=None, repr=False, compare=False)

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.text


class Ocr:
    """Thin wrapper around RapidOCR, loaded on first use (it is slow to import)."""

    def __init__(self) -> None:
        self._engine = None

    def lines(self, frame: np.ndarray, rows: tuple[int, int] | None = None):
        """Text lines as ``((x0, y0, x1, y1), text)``. ``rows`` limits OCR to a horizontal strip."""
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        top = 0
        if rows is not None:
            top = rows[0]
            frame = frame[rows[0]:rows[1]]
        h, w = frame.shape[:2]
        scale = min(1.0, OCR_MAX_SIDE / max(h, w))
        image = frame
        if scale < 1.0:
            image = cv2.resize(frame, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
        # Screen text is upright, so the rotation classifier is skipped.
        result, _ = self._engine(image, use_cls=False)
        out = []
        for quad, text, _score in result or []:
            xs = [p[0] / scale for p in quad]
            ys = [p[1] / scale + top for p in quad]
            out.append(((int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1), text))
        return out


def _gray(frame: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    return cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)


def detect(frame: np.ndarray, ocr: Ocr, kinds=None, also=(), phone_regions=("BR", "US"), rows=None) -> list[Region]:
    """OCR the frame (or just the strip ``rows``) and return one region per sensitive text."""
    h, w = frame.shape[:2]
    regions: list[Region] = []
    for (x0, y0, x1, y1), text in ocr.lines(frame, rows):
        if not text:
            continue
        line_w, line_h = x1 - x0, y1 - y0
        char_w = line_w / len(text)
        for m in scan(text, kinds=kinds, also=also, regions=phone_regions):
            # Character positions are only approximate (proportional fonts,
            # dropped spaces), so pad generously on both sides.
            pad_x = max(2 * char_w, 0.08 * (m.end - m.start) * char_w, 4)
            pad_y = max(0.15 * line_h, 2)
            box = (
                max(0, int(x0 + m.start * char_w - pad_x)),
                max(0, int(y0 - pad_y)),
                min(w, int(x0 + m.end * char_w + pad_x) + 1),
                min(h, int(y1 + pad_y) + 1),
            )
            if box[2] > box[0] and box[3] > box[1]:
                regions.append(Region(m.kind, m.text, box, _gray(frame, box)))
    return regions


def still_there(region: Region, frame: np.ndarray, tolerance: float = 6.0) -> bool:
    """True if the pixels under ``region`` look the same as when it was found."""
    if region.patch is None:
        return False
    now = _gray(frame, region.box)
    if now.shape != region.patch.shape:
        return False
    return float(cv2.absdiff(now, region.patch).mean()) < tolerance


def locate(region: Region, frame: np.ndarray, score: float = 0.75) -> tuple[int, int, int, int] | None:
    """Find where ``region`` moved to on ``frame`` by matching its pixels nearby.

    Much cheaper than OCR, and enough to follow text while the page scrolls.
    """
    if region.patch is None:
        return None
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = region.box
    sx0, sx1 = max(0, x0 - int(0.15 * w)), min(w, x1 + int(0.15 * w))
    sy0, sy1 = max(0, y0 - int(0.35 * h)), min(h, y1 + int(0.35 * h))
    window = cv2.cvtColor(frame[sy0:sy1, sx0:sx1], cv2.COLOR_BGR2GRAY)
    ph, pw = region.patch.shape
    if window.shape[0] < ph or window.shape[1] < pw:
        return None
    scores = cv2.matchTemplate(window, region.patch, cv2.TM_CCOEFF_NORMED)
    _, best, _, (bx, by) = cv2.minMaxLoc(scores)
    if not np.isfinite(best) or best < score:
        return None
    return sx0 + bx, sy0 + by, sx0 + bx + pw, sy0 + by + ph


def carry_over(previous: list[Region], current: list[Region], frame: np.ndarray) -> list[Region]:
    """Keep regions OCR missed this time while their pixels have not changed.

    OCR is not perfectly stable from frame to frame. Without this, a secret
    that sits still on screen could flash visible whenever OCR skips it.
    """
    covered = [r.box for r in current]
    kept = list(current)
    for region in previous:
        if any(_contains(box, region.box) for box in covered):
            continue
        if still_there(region, frame):
            kept.append(region)
    return kept


def _contains(outer, inner) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _similar_size(a: Region, b: Region, slack: float = 0.25) -> bool:
    aw, ah = a.box[2] - a.box[0], a.box[3] - a.box[1]
    bw, bh = b.box[2] - b.box[0], b.box[3] - b.box[1]
    return abs(aw - bw) <= slack * max(aw, bw) and abs(ah - bh) <= slack * max(ah, bh)


def _distance(a: Region, b: Region) -> float:
    ax, ay = (a.box[0] + a.box[2]) / 2, (a.box[1] + a.box[3]) / 2
    bx, by = (b.box[0] + b.box[2]) / 2, (b.box[1] + b.box[3]) / 2
    return abs(ax - bx) + abs(ay - by)


def between(previous: list[Region], current: list[Region]):
    """Plan how to hide the frames that sit between two OCR passes.

    Returns ``(boxes, loose)``:

    - ``boxes`` covers both passes. When a region of the same kind and size is
      in both (scrolling, a window being dragged), the path between the two
      positions is covered too.
    - ``loose`` are regions seen in only one pass: text that appeared or went
      away in between. Where it was meanwhile is unknown, so the caller must
      look at each in-between frame (see ``still_there``).

    Text is matched by kind, size and distance, not by its characters: OCR
    rarely reads a long key the same way twice.
    """
    boxes = [r.box for r in previous] + [r.box for r in current]
    unused = list(previous)
    loose: list[Region] = []
    for region in current:
        candidates = [p for p in unused if p.kind == region.kind and _similar_size(p, region)]
        if not candidates:
            loose.append(region)
            continue
        match = min(candidates, key=lambda p: _distance(p, region))
        unused.remove(match)
        a, b = match.box, region.box
        if a != b:
            boxes.append((min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])))
    return boxes, loose + unused


def redact(frame: np.ndarray, boxes, style: str = "blur") -> np.ndarray:
    """Hide ``boxes`` in place. No style keeps enough detail to read the text back.

    "blur" and "pixel" first shrink the area to a handful of pixels (a text line
    becomes a single row of cells, each about two characters wide), then enlarge
    it again. A plain Gaussian blur or a fine mosaic can sometimes be reversed;
    here the detail is thrown away first. "box" paints a solid rectangle.
    """
    for x0, y0, x1, y1 in boxes:
        area = frame[y0:y1, x0:x1]
        h, w = area.shape[:2]
        if h == 0 or w == 0:
            continue
        if style == "box":
            area[:] = (24, 24, 24)
            continue
        cell = max(16, h)
        small = cv2.resize(area, (max(1, w // cell), max(1, h // cell)), interpolation=cv2.INTER_AREA)
        mode = cv2.INTER_NEAREST if style == "pixel" else cv2.INTER_CUBIC
        hidden = cv2.resize(small, (w, h), interpolation=mode)
        # Thin text averages out to the background colour, which would look like
        # nothing was there. A touch of grey keeps the hidden area visible.
        frame[y0:y1, x0:x1] = cv2.addWeighted(hidden, 0.8, np.full_like(hidden, 128), 0.2, 0)
    return frame
