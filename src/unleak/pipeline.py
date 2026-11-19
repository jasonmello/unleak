"""Run detection over a video or an image and write the redacted copy."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from . import video
from .regions import Ocr, Region, between, carry_over, detect, locate, redact, still_there

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class Options:
    kinds: tuple[str, ...] | None = None
    also: tuple[str, ...] = ()
    phone_regions: tuple[str, ...] = ("BR", "US")
    style: str = "blur"
    ocr_fps: float = 2.0
    dry_run: bool = False


@dataclass
class Finding:
    kind: str
    text: str
    first_seen: float
    last_seen: float
    box: tuple[int, int, int, int]
    thumbnail: np.ndarray | None = field(default=None, repr=False)


@dataclass
class Result:
    source: Path
    output: Path | None
    findings: list[Finding]
    duration: float = 0.0
    ocr_passes: int = 0
    frames: int = 0


class _Findings:
    """One entry per hidden item. OCR reads the same text slightly differently
    from frame to frame, so near-identical readings count as the same item."""

    def __init__(self) -> None:
        self._items: list[Finding] = []

    def _known(self, region: Region) -> Finding | None:
        for item in self._items:
            if item.kind == region.kind and (
                item.text == region.text or SequenceMatcher(None, item.text, region.text).ratio() >= 0.7
            ):
                return item
        return None

    def add(self, regions: list[Region], time: float, redacted: np.ndarray) -> None:
        for r in regions:
            known = self._known(r)
            if known:
                known.last_seen = max(known.last_seen, time)
                known.first_seen = min(known.first_seen, time)
                if len(r.text) > len(known.text):
                    known.text = r.text  # keep the most complete reading
            else:
                self._items.append(Finding(r.kind, r.text, time, time, r.box, _thumbnail(redacted, r.box)))

    def list(self) -> list[Finding]:
        return sorted(self._items, key=lambda f: f.first_seen)


def _thumbnail(redacted: np.ndarray | None, box, context: int = 180, max_width: int = 520) -> np.ndarray | None:
    """A crop of the already-redacted frame around ``box``, with the box outlined."""
    if redacted is None:
        return None
    h, w = redacted.shape[:2]
    x0, y0, x1, y1 = box
    cx0, cy0 = max(0, x0 - context), max(0, y0 - context // 3)
    cx1, cy1 = min(w, x1 + context), min(h, y1 + context // 3)
    crop = redacted[cy0:cy1, cx0:cx1].copy()
    cv2.rectangle(crop, (x0 - cx0, y0 - cy0), (x1 - cx0 - 1, y1 - cy0 - 1), (60, 60, 235), 2)
    if crop.shape[1] > max_width:
        scale = max_width / crop.shape[1]
        crop = cv2.resize(crop, (max_width, max(1, round(crop.shape[0] * scale))), interpolation=cv2.INTER_AREA)
    return crop


def _small(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (320, max(1, round(320 * h / w))), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def _changed(a: np.ndarray, b: np.ndarray) -> bool:
    """True if two downscaled frames differ by more than compression noise.

    One typed character is enough: it moves a couple of pixels by a wide margin.
    """
    return int(np.count_nonzero(cv2.absdiff(a, b) > 24)) >= 2


def _changed_rows(a: np.ndarray, b: np.ndarray, height: int, pad: int = 48) -> tuple[int, int] | None:
    """The horizontal strip of the full frame where ``a`` and ``b`` differ.

    Returns None when the change is too tall for a strip to save any time.
    """
    rows = np.flatnonzero((cv2.absdiff(a, b) > 24).any(axis=1))
    if rows.size == 0:
        return None
    scale = height / a.shape[0]
    top = max(0, int(rows[0] * scale) - pad)
    bottom = min(height, int((rows[-1] + 1) * scale) + pad)
    return (top, bottom) if bottom - top <= 0.4 * height else None


def default_output(source: Path) -> Path:
    suffix = source.suffix.lower()
    if suffix not in IMAGE_SUFFIXES and suffix not in video.SAME_CONTAINER:
        suffix = ".mp4"
    return source.with_name(f"{source.stem}.unleaked{suffix}")


def process_image(source: Path, output: Path, options: Options, ocr: Ocr | None = None) -> Result:
    frame = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError(f"could not read image: {source}")
    regions = detect(frame, ocr or Ocr(), options.kinds, options.also, options.phone_regions)
    redact(frame, [r.box for r in regions], options.style)
    findings = _Findings()
    findings.add(regions, 0.0, frame)
    if not options.dry_run:
        if not cv2.imwrite(str(output), frame):
            raise ValueError(f"could not write image: {output}")
    return Result(source, None if options.dry_run else output, findings.list(), ocr_passes=1, frames=1)


def process_video(
    source: Path,
    output: Path,
    options: Options,
    ocr: Ocr | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> Result:
    """Redact a video.

    OCR is slow, so it only runs when the picture changes, at most
    ``options.ocr_fps`` times per second. Frames seen while waiting for the next
    OCR pass are held back and written with the boxes of BOTH surrounding
    passes, so text is already hidden on the first frame where it appears.
    """
    ocr = ocr or Ocr()
    info = video.probe(source)
    writer = None if options.dry_run else video.Writer(output, source, info)
    interval = 1.0 / options.ocr_fps if options.ocr_fps > 0 else 0.0

    findings = _Findings()
    current: list[Region] = []
    reference: np.ndarray | None = None
    last_ocr = float("-inf")
    held: list[tuple[float, np.ndarray, np.ndarray]] = []  # time, frame, downscaled
    passes = count = 0

    def find(frame: np.ndarray, rows=None) -> list[Region]:
        nonlocal passes
        passes += 1
        return detect(frame, ocr, options.kinds, options.also, options.phone_regions, rows)

    def emit(frame: np.ndarray, boxes) -> np.ndarray:
        redact(frame, boxes, options.style)
        if writer:
            writer.write(frame)
        return frame

    def ocr_pass(frame: np.ndarray, small: np.ndarray, time: float) -> None:
        nonlocal current, reference, last_ocr
        # Small change (typing, a blinking cursor): read only that strip and
        # keep what is already known about the rest of the screen.
        rows = _changed_rows(small, reference, frame.shape[0]) if reference is not None else None
        fresh = find(frame, rows)
        if rows:
            fresh += [r for r in current if r.box[3] <= rows[0] or r.box[1] >= rows[1]]
        found = carry_over(current, fresh, frame)
        boxes, loose = between(current, found)

        # Frames held since the last pass. `boxes` already covers both passes;
        # the work left is text that appeared or vanished in between, which may
        # have been somewhere else on these frames (scrolling in or out of view).
        solved: list[tuple[np.ndarray, list]] = [(small, [])]
        if reference is not None:
            solved.append((reference, []))
        for held_time, waiting, waiting_small in held[:-1]:
            extra = next((b for s, b in solved if not _changed(waiting_small, s)), None)
            if extra is None:
                extra, lost = [], False
                for region in loose:
                    if still_there(region, waiting):
                        continue
                    moved = locate(region, waiting)
                    if moved:
                        extra.append(moved)
                    else:
                        lost = True
                if lost:  # could not follow it by its pixels: read this frame
                    seen = find(waiting)
                    extra += [r.box for r in seen]
                    findings.add(seen, held_time, None)
                solved.append((waiting_small, extra))
            emit(waiting, boxes + extra)
        findings.add(found, time, emit(frame, boxes))
        held.clear()
        current, reference, last_ocr = found, small, time

    try:
        for index, frame in enumerate(video.read(source, info)):
            count = index + 1
            time = index / info.fps
            small = _small(frame)
            if reference is not None and not held and not _changed(small, reference):
                emit(frame, [r.box for r in current])
            else:
                held.append((time, frame, small))
                if time - last_ocr >= interval:
                    ocr_pass(frame, small, time)
            if progress and count % 10 == 0:
                progress(count, info.frames)
        if held:
            ocr_pass(held[-1][1], held[-1][2], held[-1][0])
        if progress:
            progress(count, count)
    finally:
        if writer:
            writer.close()
    return Result(source, None if options.dry_run else output, findings.list(), count / info.fps, passes, count)


def process(source: Path, output: Path | None = None, options: Options | None = None, progress=None) -> Result:
    options = options or Options()
    output = output or default_output(source)
    if source.suffix.lower() in IMAGE_SUFFIXES:
        return process_image(source, output, options)
    return process_video(source, output, options, progress=progress)
