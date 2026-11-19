"""Read and write video frames through the ffmpeg binary bundled with imageio-ffmpeg."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import imageio_ffmpeg
import numpy as np

# Containers we write back as-is. Anything else (webm, avi, gif...) becomes .mp4.
SAME_CONTAINER = {".mp4", ".mov", ".m4v", ".mkv"}


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float

    @property
    def frames(self) -> int:
        return max(1, round(self.duration * self.fps))


def probe(path: Path) -> VideoInfo:
    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        meta = next(reader)
    finally:
        reader.close()
    width, height = meta["size"]
    return VideoInfo(width, height, float(meta["fps"]), float(meta.get("duration") or 0.0))


def read(path: Path, info: VideoInfo) -> Iterator[np.ndarray]:
    """Yield BGR frames at a constant frame rate, so audio stays in sync."""
    reader = imageio_ffmpeg.read_frames(
        str(path),
        pix_fmt="bgr24",
        output_params=["-fps_mode", "cfr", "-r", f"{info.fps:.6f}"],
    )
    try:
        next(reader)  # metadata
        for raw in reader:
            yield np.frombuffer(raw, np.uint8).reshape(info.height, info.width, 3).copy()
    finally:
        reader.close()


class Writer:
    """Encode BGR frames to H.264 and copy the audio track from ``source``."""

    def __init__(self, target: Path, source: Path, info: VideoInfo) -> None:
        copy_audio = source.suffix.lower() in SAME_CONTAINER
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{info.width}x{info.height}", "-r", f"{info.fps:.6f}", "-i", "-",
            "-i", str(source),
            "-map", "0:v:0", "-map", "1:a?",
            # H.264 needs even dimensions.
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy" if copy_audio else "aac",
            "-shortest", "-movflags", "+faststart",
            str(target),
        ]
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, frame: np.ndarray) -> None:
        try:
            self._proc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            self.close()

    def close(self) -> None:
        if self._proc.stdin and not self._proc.stdin.closed:
            try:
                self._proc.stdin.close()
            except BrokenPipeError:
                pass
        error = self._proc.stderr.read().decode(errors="replace")
        if self._proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed while writing the video:\n{error.strip()}")
