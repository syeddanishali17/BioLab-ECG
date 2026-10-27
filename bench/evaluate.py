"""Beat matching, detection metrics, heart-rate error and bootstrap CIs.

EC57-style evaluation: a detection matches a reference beat if it lies within
+/-150 ms, one-to-one. This is not a claim of EC57 compliance.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import MATCH_TOL_S, WINDOW_S


@dataclass(frozen=True)
class Match:
    tp_ref: np.ndarray  # indices into ref of matched beats
    tp_det: np.ndarray  # indices into det of matched detections
    fn: np.ndarray  # indices into ref of missed beats
    fp: np.ndarray  # indices into det of false detections


def match_beats(ref: np.ndarray, det: np.ndarray, tol: int) -> Match:
    """One-to-one matching, closest pairs first, within +/- tol samples."""
    ref = np.asarray(ref, dtype=np.int64)
    det = np.asarray(det, dtype=np.int64)
    if ref.size == 0 or det.size == 0:
        return Match(np.array([], int), np.array([], int), np.arange(ref.size), np.arange(det.size))
    lo = np.searchsorted(det, ref - tol, side="left")
    hi = np.searchsorted(det, ref + tol, side="right")
    counts = hi - lo
    ri = np.repeat(np.arange(ref.size), counts)
    starts = np.repeat(lo, counts)
    offs = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    di = starts + offs
    dist = np.abs(ref[ri] - det[di])
    order = np.lexsort((di, ri, dist))  # by distance, ties broken deterministically
    used_r = np.zeros(ref.size, bool)
    used_d = np.zeros(det.size, bool)
    pr, pd_ = [], []
    for k in order:
        r, d = ri[k], di[k]
        if not used_r[r] and not used_d[d]:
            used_r[r] = used_d[d] = True
            pr.append(r)
            pd_.append(d)
    tp_ref = np.array(sorted(pr), dtype=np.int64)
    tp_det = np.array(sorted(pd_), dtype=np.int64)
    return Match(tp_ref, tp_det, np.flatnonzero(~used_r), np.flatnonzero(~used_d))


def metrics(tp: float, fp: float, fn: float) -> dict[str, float]:
    se = tp / (tp + fn) if tp + fn else np.nan
    ppv = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else np.nan
    return {"se": se, "ppv": ppv, "f1": f1}


def _window_hr(beats: np.ndarray, starts: np.ndarray, win: int, fs: float) -> np.ndarray:
    out = np.full(starts.size, np.nan)
    lo = np.searchsorted(beats, starts, side="left")
    hi = np.searchsorted(beats, starts + win, side="left")
    for k, (a, b) in enumerate(zip(lo, hi)):
        if b - a >= 2:
            rr = np.diff(beats[a:b]) / fs
            out[k] = 60.0 / rr.mean()
    return out


def window_table(ref: np.ndarray, det: np.ndarray, noisy_mask: np.ndarray, fs: float,
                 tol_s: float = MATCH_TOL_S, window_s: float = WINDOW_S) -> pd.DataFrame:
    """Per-window TP/FP/FN, noisy flag and heart rate (reference vs detected).

    Matching runs on the whole record so beats at window edges match
    correctly; events are then assigned to the window they fall in (TP and
    FN by reference beat time, FP by detection time).
    """
    n = noisy_mask.size
    win = int(round(window_s * fs))
    m = match_beats(ref, det, int(round(tol_s * fs)))
    n_win = n // win
    starts = np.arange(n_win) * win

    def per_window(samples: np.ndarray) -> np.ndarray:
        w = samples // win
        w = w[w < n_win]
        return np.bincount(w, minlength=n_win)

    tp = per_window(ref[m.tp_ref])
    fn = per_window(ref[m.fn])
    fp = per_window(det[m.fp])
    frac_noisy = noisy_mask[: n_win * win].reshape(n_win, win).mean(axis=1)
    hr_ref = _window_hr(ref, starts, win, fs)
    hr_det = _window_hr(det, starts, win, fs)
    return pd.DataFrame({
        "window": np.arange(n_win),
        "t0_s": starts / fs,
        "noisy": frac_noisy >= 0.5,
        "tp": tp, "fp": fp, "fn": fn,
        "hr_ref": hr_ref, "hr_det": hr_det,
    })


def summarize(windows: pd.DataFrame) -> dict[str, float]:
    """Aggregate counts and HR error over a set of windows."""
    tp, fp, fn = (float(windows[c].sum()) for c in ("tp", "fp", "fn"))
    out = {"tp": tp, "fp": fp, "fn": fn, "n_windows": float(len(windows)), **metrics(tp, fp, fn)}
    err = (windows["hr_det"] - windows["hr_ref"]).abs()
    valid_ref = windows["hr_ref"].notna()
    out["hr_mae"] = float(err[valid_ref].mean()) if valid_ref.any() else np.nan
    # windows where the detector gives no HR count as outside the tolerance
    out["hr_within5"] = float((err[valid_ref] <= 5).mean()) if valid_ref.any() else np.nan
    return out


def bootstrap_ci(windows: pd.DataFrame, n_boot: int = 1000, alpha: float = 0.05,
                 seed: int = 0) -> dict[str, tuple[float, float]]:
    """Percentile CIs for Se, +P and F1 by resampling whole windows.

    Windows, not beats, are resampled because neighbouring beats share noise
    and are correlated.
    """
    counts = windows[["tp", "fp", "fn"]].to_numpy(dtype=np.float64)
    if counts.shape[0] == 0:
        return {k: (np.nan, np.nan) for k in ("se", "ppv", "f1")}
    rng = np.random.default_rng(seed)
    w = rng.multinomial(counts.shape[0], np.full(counts.shape[0], 1 / counts.shape[0]), size=n_boot)
    tot = w @ counts  # (n_boot, 3)
    tp, fp, fn = tot.T
    with np.errstate(invalid="ignore", divide="ignore"):
        stats = {"se": tp / (tp + fn), "ppv": tp / (tp + fp), "f1": 2 * tp / (2 * tp + fp + fn)}
    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    return {k: tuple(float(v) for v in np.nanpercentile(s, q)) for k, s in stats.items()}
