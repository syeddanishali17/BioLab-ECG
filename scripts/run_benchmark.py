"""Precompute the full benchmark offline and write the result tables to results/.

Datasets
  nstdb : the 12 official NSTDB records (electrode motion only), noisy-segment
          mask recovered by subtracting the clean MIT-BIH record.
  mixed : our nst-style mixer, MIT-BIH 118, 119 + extension records,
          noise em / ma / bw, nst default schedule.

Outputs
  results/windows.parquet      per 10 s window counts and HR, every run
  results/summary.parquet      pooled metrics with bootstrap CIs per group
  results/per_record.parquet   metrics per record (no CIs)
  results/worst_windows.parquet  worst noisy window of every run (failure gallery)
  results/detections.npz       detections of every run (delta-encoded)
  results/meta.json            versions, settings, run time

Usage:  python scripts/run_benchmark.py [--workers N] [--quick]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.config import (CHANNEL, MATCH_TOL_S, MIXED_RECORDS, NOISE_TYPES, NSTDB_SNRS,  # noqa: E402
                          NSTDB_SOURCES, RESULTS_DIR, WINDOW_S)
from bench.detectors import DETECTORS, detect  # noqa: E402
from bench.evaluate import window_table  # noqa: E402
from bench.filters import PREFILTERS, prefilter  # noqa: E402
from bench.report import (RUN_KEYS, aggregate, pack_detections, per_record, run_key,  # noqa: E402
                          worst_windows)
from bench.signals import mixed_signal, nstdb_signal  # noqa: E402


def run_one(job: tuple[str, str, str, int]) -> tuple[list[pd.DataFrame], dict[str, np.ndarray]]:
    dataset, record, noise, snr = job
    if dataset == "nstdb":
        x, ref, mask, fs = nstdb_signal(record, snr)
    else:
        x, ref, mask, fs = mixed_signal(record, noise, snr)
    frames, dets = [], {}
    for pf in PREFILTERS:
        y = prefilter(x, fs, pf)
        for det in DETECTORS:
            peaks = detect(det, y, fs)
            wt = window_table(ref, peaks, mask, fs)
            for k, v in zip(RUN_KEYS, (dataset, record, noise, snr, det, pf)):
                wt[k] = v
            frames.append(wt)
            dets[run_key(dataset, record, noise, snr, det, pf)] = peaks
    return frames, dets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (__import__("os").cpu_count() or 2) - 1))
    ap.add_argument("--quick", action="store_true", help="2 records, 2 SNRs (smoke test)")
    args = ap.parse_args()

    snrs = NSTDB_SNRS if not args.quick else [24, 0]
    mixed = MIXED_RECORDS if not args.quick else NSTDB_SOURCES
    jobs = [("nstdb", s, "em", snr) for s in NSTDB_SOURCES for snr in snrs]
    jobs += [("mixed", r, n, snr) for r in mixed for n in NOISE_TYPES for snr in snrs]
    print(f"{len(jobs)} signals x {len(PREFILTERS)} pre-filters x {len(DETECTORS)} detectors "
          f"on {args.workers} workers", flush=True)

    t0 = time.time()
    frames, dets = [], {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            fr, d = f.result()
            frames += fr
            dets.update(d)
            print(f"[{i}/{len(jobs)}] {futs[f]}  {time.time() - t0:.0f}s", flush=True)

    win = pd.concat(frames, ignore_index=True)
    for c in ("dataset", "record", "noise", "detector", "prefilter"):
        win[c] = win[c].astype("category")
    win["snr"] = win["snr"].astype(np.int8)
    for c in ("tp", "fp", "fn", "window"):
        win[c] = win[c].astype(np.int16)
    for c in ("hr_ref", "hr_det"):
        win[c] = win[c].astype(np.float32)

    out = RESULTS_DIR
    out.mkdir(exist_ok=True)
    win.to_parquet(out / "windows.parquet", index=False, compression="zstd")
    print("aggregating with bootstrap CIs ...", flush=True)
    aggregate(win).to_parquet(out / "summary.parquet", index=False)
    per_record(win).to_parquet(out / "per_record.parquet", index=False)
    worst_windows(win).to_parquet(out / "worst_windows.parquet", index=False)
    np.savez_compressed(out / "detections.npz", **pack_detections(dets))

    import neurokit2, scipy, wfdb  # noqa: E401
    meta = {
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "runtime_s": round(time.time() - t0, 1),
        "n_signals": len(jobs),
        "n_runs": len(dets),
        "detectors": {k: {"name": d.name, "library": d.library, "reference": d.reference}
                      for k, d in DETECTORS.items()},
        "prefilters": list(PREFILTERS),
        "channel": CHANNEL,
        "match_tolerance_s": MATCH_TOL_S,
        "window_s": WINDOW_S,
        "bootstrap": {"n_boot": 1000, "unit": "10 s window", "ci": "percentile 95%"},
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "scipy": scipy.__version__, "wfdb": wfdb.__version__,
                     "neurokit2": neurokit2.__version__, "pandas": pd.__version__},
        "quick": args.quick,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"done in {time.time() - t0:.0f}s, {len(dets)} runs")


if __name__ == "__main__":
    main()
