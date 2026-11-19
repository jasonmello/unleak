"""Build a fake screen recording, run unleak, then OCR the result: nothing may be left."""

import json
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
import pytest

from unleak.cli import main
from unleak.detectors import scan
from unleak.regions import Ocr
from unleak import video

W, H, FPS = 1280, 720, 10
SECRETS = [
    "jane.doe@example.com",
    "sk-ant-api03-FAKEfake1234567890abcdefXYZ",
    "529.982.247-25",
]


def _frame(lines, offset=0):
    img = np.full((H, W, 3), 250, np.uint8)
    cv2.putText(img, "Quarterly report (public)", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2, cv2.LINE_AA)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (60, 200 + offset + i * 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2, cv2.LINE_AA)
    return img


@pytest.fixture(scope="module")
def recording(tmp_path_factory):
    """4 seconds, with a beep: empty, then text appears, then it scrolls, then it goes away."""
    path = tmp_path_factory.mktemp("video") / "demo.mp4"
    text = [f"Contact: {SECRETS[0]}", f"KEY={SECRETS[1]}", f"CPF {SECRETS[2]}"]
    frames = [_frame([])] * 10 + [_frame(text)] * 10
    frames += [_frame(text, offset=i * 12) for i in range(1, 11)]
    frames += [_frame([])] * 10
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ]
    subprocess.run(cmd, input=b"".join(f.tobytes() for f in frames), check=True)
    return path


def _leaks(path):
    """Sensitive text still readable in any frame of ``path``."""
    ocr, info, found = Ocr(), video.probe(path), []
    for index, frame in enumerate(video.read(path, info)):
        for _box, text in ocr.lines(frame):
            found += [(index, m.kind, m.text) for m in scan(text)]
    return found


def test_source_really_has_secrets(recording):
    assert {kind for _i, kind, _t in _leaks(recording)} >= {"email", "secret", "cpf"}


def test_video_is_redacted(recording, capsys):
    out = recording.with_name("demo.unleaked.mp4")
    assert main([str(recording), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)

    assert {f["kind"] for f in data["findings"]} >= {"email", "secret", "cpf"}
    for secret in SECRETS:  # the JSON must not carry the values it hid
        assert secret not in json.dumps(data)
    report = recording.with_name("demo.unleak-report.html").read_text()
    for secret in SECRETS:
        assert secret not in report

    assert _leaks(out) == []

    before, after = video.probe(recording), video.probe(out)
    assert (after.width, after.height) == (before.width, before.height)
    assert abs(after.duration - before.duration) < 0.3
    probe = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(out)], capture_output=True, text=True)
    assert "Audio:" in probe.stderr  # the sound track survived

    # Public text must stay readable: only the sensitive parts are hidden.
    frame = list(video.read(out, after))[15]
    assert any("Quarterly" in text for _box, text in Ocr().lines(frame))


def test_image_is_redacted(tmp_path, capsys):
    src = tmp_path / "shot.png"
    cv2.imwrite(str(src), _frame([f"Contact: {SECRETS[0]}", f"KEY={SECRETS[1]}"]))
    assert main([str(src)]) == 0
    out = tmp_path / "shot.unleaked.png"
    lines = Ocr().lines(cv2.imread(str(out)))
    assert [m for _b, text in lines for m in scan(text)] == []
    assert "2 items hidden" in capsys.readouterr().out


def test_dry_run_writes_no_video(recording, tmp_path, capsys):
    target = tmp_path / "x.mp4"
    assert main([str(recording), "-o", str(target), "--dry-run", "--no-report"]) == 0
    assert not target.exists()
