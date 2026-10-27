"""Noisy/clean segment masks.

Primary method: subtract the clean MIT-BIH record from its NSTDB copy. Where
the residual is non-zero, noise was added. Fallback: the documented nst
protocol (5 min clean, then alternating 2 min noisy / 2 min clean).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Segment:
    start: int  # sample index, inclusive
    stop: int  # sample index, exclusive
    noisy: bool


def protocol_mask(n_samples: int, fs: float, lead_in_s: float = 300.0, period_s: float = 120.0) -> np.ndarray:
    """Boolean mask following the nst default protocol."""
    t = np.arange(n_samples) / fs
    after = t >= lead_in_s
    block = np.floor((t - lead_in_s) / period_s).astype(np.int64)
    return after & (block % 2 == 0)


def subtraction_mask(noisy_digital: np.ndarray, clean_digital: np.ndarray, fs: float,
                     min_run_s: float = 1.0) -> np.ndarray:
    """Mask of samples where the noisy record differs from the clean one.

    Inputs are raw ADC values of one channel. Additive noise can be exactly
    zero at isolated samples, so short clean gaps inside a noisy run are
    closed, and short isolated noisy blips are dropped (both < min_run_s).
    """
    if noisy_digital.shape != clean_digital.shape:
        raise ValueError("records are not the same length; cannot subtract")
    raw = noisy_digital != clean_digital
    return _clean_runs(raw, int(min_run_s * fs))


def _clean_runs(mask: np.ndarray, min_len: int) -> np.ndarray:
    out = mask.copy()
    for value in (False, True):  # close short gaps first, then drop short blips
        segs = runs(out)
        for s in segs:
            if s.noisy == value and (s.stop - s.start) < min_len and 0 < s.start and s.stop < len(out):
                out[s.start:s.stop] = not value
    return out


def runs(mask: np.ndarray) -> list[Segment]:
    """Split a boolean mask into contiguous segments."""
    if mask.size == 0:
        return []
    edges = np.flatnonzero(np.diff(mask.astype(np.int8))) + 1
    starts = np.r_[0, edges]
    stops = np.r_[edges, mask.size]
    return [Segment(int(a), int(b), bool(mask[a])) for a, b in zip(starts, stops)]


def mask_agreement(a: np.ndarray, b: np.ndarray) -> float:
    """Share of samples on which two masks agree."""
    return float(np.mean(a == b))
