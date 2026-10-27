"""Download the raw records used by the Learn chapters (PhysioNet AWS Open Data mirror).

  cebsdb                 ECG leads I + II, thoracic respiration band, seismocardiogram (SCG),
                         healthy volunteers lying still, recorded with a BIOPAC MP36, 5 kHz
  pulse-transit-time-ppg ECG, finger PPG (red / IR / green), 3-axis accelerometer and gyroscope,
                         while sitting, walking on the spot and running, 500 Hz
  challenge-2016         heart sounds (PCG, 2 kHz) with simultaneous ECG, training-a set

Raw files go to data/learn_raw/ (not committed). scripts/build_learning_data.py
then extracts the small excerpts in data/learn/ that the app uses.

Usage:  python scripts/fetch_learning_data.py
"""
from __future__ import annotations

import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "learn_raw"
S3 = "https://physionet-open.s3.amazonaws.com/"

JOBS = {
    "cebsdb/1.0.0": [f"b00{i}" for i in range(1, 6)],
    "pulse-transit-time-ppg/1.1.0": [f"s{s}_{a}" for s in (1, 2, 3, 4) for a in ("sit", "walk", "run")],
    "challenge-2016/1.0.0/training-a": ["a0007", "a0009", "a0011", "a0012", "a0016", "a0019", "a0025", "a0027"],
}
EXTS = {"cebsdb/1.0.0": ("hea", "dat", "atr"),
        "pulse-transit-time-ppg/1.1.0": ("hea", "dat", "atr"),
        "challenge-2016/1.0.0/training-a": ("hea", "dat", "wav")}


def fetch(url: str, dest: Path) -> str:
    if dest.exists() and dest.stat().st_size > 0:
        return f"skip  {dest.name}"
    try:
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
    except Exception as e:  # noqa: BLE001
        return f"FAIL  {dest.name}: {e}"
    dest.write_bytes(data)
    return f"ok    {dest.name} ({len(data) / 1e6:.1f} MB)"


def main() -> int:
    tasks = []
    for db, recs in JOBS.items():
        out = RAW / db.split("/")[0]
        out.mkdir(parents=True, exist_ok=True)
        for rec in recs:
            for ext in EXTS[db]:
                tasks.append((f"{S3}{db}/{rec}.{ext}", out / f"{rec}.{ext}"))
    failed = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for f in as_completed([ex.submit(fetch, u, d) for u, d in tasks]):
            msg = f.result()
            failed += msg.startswith("FAIL")
            print(msg, flush=True)
    print(f"done, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
