"""Command line: ``unleak recording.mp4``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .detectors import KINDS
from .regions import STYLES

RC_NAME = ".unleakrc"


def read_rc() -> list[str]:
    """Extra terms to hide, one per line, from ./.unleakrc and ~/.unleakrc."""
    terms: list[str] = []
    for folder in (Path.cwd(), Path.home()):
        rc = folder / RC_NAME
        if rc.is_file():
            for line in rc.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    terms.append(line)
    return terms


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unleak",
        description="Blur e-mails, phone numbers, API keys and other sensitive data "
        "in screen recordings and screenshots. Runs 100% on your computer.",
    )
    p.add_argument("input", type=Path, help="video or image file")
    p.add_argument("-o", "--output", type=Path, help="output file (default: NAME.unleaked.EXT)")
    p.add_argument("--also", action="append", default=[], metavar="TEXT",
                   help="also hide this text (repeatable); .unleakrc lists more, one per line")
    p.add_argument("--only", action="append", choices=KINDS, metavar="KIND",
                   help=f"detect only these kinds (repeatable): {', '.join(KINDS)}")
    p.add_argument("--skip", action="append", default=[], choices=KINDS, metavar="KIND",
                   help="do not detect this kind (repeatable)")
    p.add_argument("--style", choices=STYLES, default="blur", help="how to hide (default: blur)")
    p.add_argument("--ocr-fps", type=float, default=2.0, metavar="N",
                   help="how often to read the screen while it changes, per second "
                        "(default: 2; higher is safer and slower; 0 reads every changed frame)")
    p.add_argument("--phone-regions", default="BR,US", metavar="CC,CC",
                   help="countries for phone numbers written without +code (default: BR,US)")
    p.add_argument("--dry-run", action="store_true", help="only report, write no output file")
    p.add_argument("--no-report", action="store_true", help="do not write the HTML report")
    p.add_argument("--json", action="store_true", help="print the findings as JSON")
    p.add_argument("--version", action="version", version=f"unleak {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source: Path = args.input
    if not source.is_file():
        print(f"unleak: file not found: {source}", file=sys.stderr)
        return 2

    # Imported late so --help and --version stay instant.
    from . import report
    from .pipeline import Options, default_output, process

    kinds = tuple(k for k in (args.only or KINDS) if k not in args.skip)
    options = Options(
        kinds=kinds,
        also=tuple(args.also + read_rc()),
        phone_regions=tuple(r.strip().upper() for r in args.phone_regions.split(",") if r.strip()),
        style=args.style,
        ocr_fps=args.ocr_fps,
        dry_run=args.dry_run,
    )
    output = args.output or default_output(source)
    if output.resolve() == source.resolve():
        print("unleak: the output would overwrite the input; choose another name with -o", file=sys.stderr)
        return 2

    interactive = sys.stderr.isatty()

    def progress(done: int, total: int) -> None:
        if interactive:
            pct = min(100, round(100 * done / max(total, 1)))
            print(f"\rReading the video... {pct:3d}%", end="", file=sys.stderr, flush=True)

    try:
        result = process(source, output, options, progress=progress)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"\nunleak: {error}", file=sys.stderr)
        return 1
    if interactive:
        print("\r" + " " * 40 + "\r", end="", file=sys.stderr)

    report_path = None
    if not args.no_report:
        report_path = report.write_html(result, output.with_name(f"{source.stem}.unleak-report.html"))

    if args.json:
        print(report.to_json(result, report_path))
        return 0

    count = len(result.findings)
    print(f"{count} item{'s' if count != 1 else ''} hidden" if count else "Nothing sensitive found")
    for f in result.findings:
        when = f"  {report.clock(f.first_seen)}" if result.frames > 1 else ""
        print(f"  {report.LABELS.get(f.kind, f.kind):<24} {report.mask(f.text)}{when}")
    if result.output:
        print(f"Output: {result.output}")
    if report_path:
        print(f"Report: {report_path}")
    print("Check the output before you share it. unleak lowers the risk, it does not remove it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
