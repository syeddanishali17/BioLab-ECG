"""Rebuild the small app tables from results/windows.parquet without re-running detectors.

Usage:  python scripts/derive_tables.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.config import RESULTS_DIR  # noqa: E402
from bench.report import per_record, worst_windows  # noqa: E402

win = pd.read_parquet(RESULTS_DIR / "windows.parquet")
per_record(win).to_parquet(RESULTS_DIR / "per_record.parquet", index=False)
worst_windows(win).to_parquet(RESULTS_DIR / "worst_windows.parquet", index=False)
print("wrote per_record.parquet and worst_windows.parquet")
