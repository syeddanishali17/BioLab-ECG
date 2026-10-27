"""Checkpoint 0 data audit. Writes results/audit.json (read by the app).

Usage:  python scripts/data_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench import audit  # noqa: E402
from bench.config import RESULTS_DIR  # noqa: E402


def main() -> None:
    out = {
        "headers": audit.headers(),
        "symbols": {f"{db}/{n}": audit.symbol_counts(db, n)
                    for db, n in [("mitdb", "118"), ("mitdb", "119"), ("nstdb", "118e24"), ("nstdb", "119e24")]},
        "masks": audit.mask_report(),
        "noise_per_channel": audit.both_channels_noisy(),
        "mains": audit.mains_check(),
        "mixer_validation": audit.mixer_validation(),
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "audit.json").write_text(json.dumps(out, indent=2, default=float))
    fs = {h["fs"] for h in out["headers"]}
    mv = out["mixer_validation"]
    print(f"sampling rates: {fs}")
    print(f"mask agreement with protocol: min {min(m['agreement_with_protocol'] for m in out['masks']):.5f}")
    print(f"mains: {out['mains']}")
    print(f"mixer gain error (dB): {min(r['gain_error_db'] for r in mv):.3f} .. {max(r['gain_error_db'] for r in mv):.3f}")
    print(f"remix rms diff (uV): {min(r['rms_diff_uV'] for r in mv):.1f} .. {max(r['rms_diff_uV'] for r in mv):.1f}")


if __name__ == "__main__":
    main()
