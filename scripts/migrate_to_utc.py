"""Migration utility to convert existing raw filenames from local (EET/EEST)
timestamps to UTC timestamps.

Usage:
  python scripts/migrate_to_utc.py [--root DATA_RAW_DIR] [--offset HOURS]
                                   [--apply] [--pattern PATTERN]

Defaults:
  - root: data/raw under project root
  - offset: 3 (subtract 3 hours)
  - dry-run by default; use --apply to perform moves

The script looks for filenames containing a timestamp of the form
`_YYYYMMDD_HHMMSS` and rewrites the filename with the timestamp minus the
specified offset, moving the file into the correct `date=YYYY-MM-DD` UTC
partition if necessary.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

TIMESTAMP_RE = re.compile(r"_(\d{8}_\d{6})")


def find_files(root: Path) -> Iterable[Path]:
    for source_dir in root.glob("source=*/"):
        for date_dir in source_dir.glob("date=*/"):
            for file in date_dir.iterdir():
                if file.is_file():
                    yield file


def parse_timestamp_from_name(name: str) -> datetime | None:
    m = TIMESTAMP_RE.search(name)
    if not m:
        return None
    ts_str = m.group(1)
    try:
        return datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def migrate_file(p: Path, offset_hours: int, apply: bool = False) -> tuple[bool, str]:
    """Return (changed, message)."""
    orig_name = p.name
    parsed = parse_timestamp_from_name(orig_name)
    if parsed is None:
        return False, f"skip (no timestamp): {p}"

    # Interpret parsed time as local (EET/EEST) naive, subtract offset to get UTC
    utc_dt = parsed - timedelta(hours=offset_hours)

    new_ts = utc_dt.strftime("%Y%m%d_%H%M%S")
    new_name = TIMESTAMP_RE.sub(f"_{new_ts}", orig_name, count=1)

    # New partition directory based on UTC date
    utc_date = utc_dt.strftime("%Y-%m-%d")
    new_dir = p.parent.parent / f"date={utc_date}"
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path = new_dir / new_name

    try:
        if new_path.resolve() == p.resolve():
            return False, f"no-op (same path): {p}"
    except Exception:
        # fallback to path compare
        if new_path == p:
            return False, f"no-op (same path): {p}"

    if new_path.exists():
        # Avoid overwriting: append suffix
        suffix = 1
        base = new_path.stem
        while True:
            candidate = new_dir / f"{base}-{suffix}{new_path.suffix}"
            if not candidate.exists():
                new_path = candidate
                break
            suffix += 1

    if apply:
        p.replace(new_path)
        return True, f"moved: {p} -> {new_path}"
    else:
        return True, f"would move: {p} -> {new_path}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "raw",
        help="Root raw data dir (default: data/raw)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=3,
        help="Hours to subtract from timestamps (e.g., 3 for EEST->UTC)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform rename/move (default: dry-run)",
    )
    args = parser.parse_args()

    root = args.root
    if not root.exists():
        print(f"Root not found: {root}")
        return 2

    total = 0
    changed = 0
    for p in find_files(root):
        total += 1
        ok, msg = migrate_file(p, args.offset, apply=args.apply)
        if ok:
            changed += 1
        print(msg)

    print(f"Processed {total} files, {changed} would be/was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
