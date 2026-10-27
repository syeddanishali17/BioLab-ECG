"""Download the PhysioNet records used by the bench.

MIT-BIH Arrhythmia DB comes from PhysioNet's AWS Open Data mirror (fast).
The Noise Stress Test DB is not on that mirror, so it comes from physionet.org
in parallel (single connections to physionet.org can be very slow).

Usage:  python scripts/fetch_data.py [--mitdb-all]
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

NSTDB_URL = "https://physionet.org/files/nstdb/1.0.0/"
MITDB_URLS = [
    "https://physionet-open.s3.amazonaws.com/mitdb/1.0.0/",
    "https://physionet.org/files/mitdb/1.0.0/",
]

NSTDB_RECORDS = [f"{s}e{snr}" for s in ("118", "119") for snr in ("24", "18", "12", "06", "00", "_6")]
NOISE_RECORDS = ["bw", "ma", "em"]

# Default MIT-BIH set: the NSTDB clean sources plus the extension records
# selected in bench/config.py (mostly-normal-rhythm records, no pacing).
sys.path.insert(0, str(ROOT))
from bench.config import EXTENSION_RECORDS  # noqa: E402


def _fetch(urls: list[str], dest: Path, timeout: int = 900) -> str:
    if dest.exists() and dest.stat().st_size > 0:
        return f"skip  {dest.name}"
    last_err = None
    for base in urls:
        try:
            with urllib.request.urlopen(base + dest.name, timeout=timeout) as r:
                data = r.read()
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return f"ok    {dest.name} ({len(data) / 1e6:.2f} MB)"
        except Exception as e:  # noqa: BLE001 - try the next mirror
            last_err = e
    return f"FAIL  {dest.name}: {last_err}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mitdb-all", action="store_true", help="download all 48 MIT-BIH records")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    jobs: list[tuple[list[str], Path]] = []
    nst = DATA / "nstdb"
    nst.mkdir(parents=True, exist_ok=True)
    for rec in NSTDB_RECORDS:
        for ext in ("hea", "dat", "atr"):
            jobs.append(([NSTDB_URL], nst / f"{rec}.{ext}"))
    for rec in NOISE_RECORDS:
        for ext in ("hea", "dat"):
            jobs.append(([NSTDB_URL], nst / f"{rec}.{ext}"))

    mit = DATA / "mitdb"
    mit.mkdir(parents=True, exist_ok=True)
    if args.mitdb_all:
        with urllib.request.urlopen(MITDB_URLS[0] + "RECORDS", timeout=60) as r:
            mit_records = r.read().decode().split()
    else:
        mit_records = sorted({"118", "119", *EXTENSION_RECORDS})
    for rec in mit_records:
        for ext in ("hea", "dat", "atr"):
            jobs.append((MITDB_URLS, mit / f"{rec}.{ext}"))

    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_fetch, urls, dest) for urls, dest in jobs]
        for f in as_completed(futs):
            msg = f.result()
            failed += msg.startswith("FAIL")
            print(msg, flush=True)
    print(f"done, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
