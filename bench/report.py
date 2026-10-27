"""Aggregation of per-window results into tables for the app and the report."""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from .evaluate import bootstrap_ci, summarize

RUN_KEYS = ["dataset", "record", "noise", "snr", "detector", "prefilter"]
GROUP_KEYS = ["dataset", "noise", "snr", "detector", "prefilter"]


def aggregate(windows: pd.DataFrame, by: list[str] = GROUP_KEYS, n_boot: int = 1000) -> pd.DataFrame:
    """Pool windows across records per group, for noisy and clean segments,
    with block-bootstrap 95% CIs (resampling 10 s windows)."""
    rows = []
    for keys, g in windows.groupby(by + ["noisy"], observed=True, sort=True):
        keys = dict(zip(by + ["noisy"], keys if isinstance(keys, tuple) else (keys,)))
        s = summarize(g)
        ci = bootstrap_ci(g, n_boot=n_boot, seed=_seed(keys))
        rows.append({
            **keys,
            "segment": "noisy" if keys.pop("noisy") else "clean",
            **s,
            "n_records": g["record"].nunique() if "record" in g else np.nan,
            **{f"{k}_lo": v[0] for k, v in ci.items()},
            **{f"{k}_hi": v[1] for k, v in ci.items()},
        })
    out = pd.DataFrame(rows)
    return out.drop(columns=["noisy"], errors="ignore")


def _seed(keys: dict) -> int:
    # crc32, not hash(): str hashes are salted per process, CIs must be reproducible
    return zlib.crc32("|".join(str(v) for v in keys.values()).encode())


def run_key(dataset: str, record: str, noise: str, snr: int, detector: str, prefilter: str) -> str:
    return f"{dataset}|{record}|{noise}|{snr}|{detector}|{prefilter}"


def pack_detections(d: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Delta-encode detection arrays so they compress well in an .npz."""
    return {k: np.diff(np.r_[0, v]).astype(np.uint32) for k, v in d.items()}


def unpack_detections(a: np.ndarray) -> np.ndarray:
    return np.cumsum(a.astype(np.int64))


def worst_windows(windows: pd.DataFrame) -> pd.DataFrame:
    """The single worst noisy window (most FP + FN) of every run, for the failure gallery."""
    w = windows[windows["noisy"] & ((windows["fp"] + windows["fn"]) > 0)].copy()
    w["errors"] = w["fp"] + w["fn"]
    w = w.sort_values(["errors", "window"], ascending=[False, True])
    return w.drop_duplicates(RUN_KEYS).reset_index(drop=True)


def per_record(windows: pd.DataFrame) -> pd.DataFrame:
    """Counts and metrics per run and segment (no CIs)."""
    rows = []
    for keys, g in windows.groupby(RUN_KEYS + ["noisy"], observed=True):
        rows.append({**dict(zip(RUN_KEYS + ["noisy"], keys)), **summarize(g)})
    return pd.DataFrame(rows)
