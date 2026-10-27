"""nst-style noise mixing at a target SNR.

Reimplements PhysioNet's `nst` (WFDB app/nst.c, with the estimators of
app/sigamp.c):

  SNR = 10 log10(S / N),  S = pp^2 / 8,  N = rms^2
  pp  : peak-to-peak amplitude within +/-50 ms of each of the first 300
        normal beats, 5%-trimmed mean               (sigamp -a)
  rms : RMS of each of the first 300 one-second windows of the noise record,
        each window mean-removed, 5%-trimmed mean   (sigamp -r)
  gain a = 10^(-SNR/20) * sqrt(2)/4 * pp / rms

The per-second mean removal in `rms` acts as a high-pass: it is why nst's
SNR is "frequency weighted", and it matters most for baseline wander.

nst also adds a constant offset whenever the noise gain changes, so the
output has no step at segment boundaries; `continuity=True` reproduces it.

A second estimator, "variance" (plain variance of the noise actually added),
is kept for the validation comparison in Methods.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import Record
from .segments import protocol_mask, runs

PP_HALF_WINDOW_S = 0.050  # sigamp default DT1 = DT2 = 0.05 s
N_MEASURE = 300  # sigamp NMAX: beats or one-second windows
# WFDB map1() class NORMAL: normal, bundle branch block, aberrated, escape beats
NORMAL_SYMBOLS = frozenset("NLRBaej")


@dataclass(frozen=True)
class MixResult:
    signal: np.ndarray  # noisy signal, one channel, physical units
    noise: np.ndarray  # what was added (scaled noise minus continuity offsets)
    mask: np.ndarray  # True where noise was added
    gain: float  # noise gain a
    S: float  # signal power estimate
    N: float  # noise power estimate (before gain)
    snr_db: float


def _trimmed_mean(v: np.ndarray, n_max: int = N_MEASURE) -> float:
    """sigamp's trimmed mean: drop the lowest and highest namp/20 values."""
    v = np.sort(np.asarray(v, dtype=np.float64)[:n_max])
    lo = v.size // 20
    return float(v[lo:v.size - lo].mean())


def qrs_peak_to_peak(signal: np.ndarray, beats: np.ndarray, fs: float,
                     symbols: np.ndarray | None = None) -> float:
    """sigamp -a: trimmed mean p-p amplitude around the first 300 normal beats."""
    if symbols is not None:
        beats = beats[np.isin(symbols, list(NORMAL_SYMBOLS))]
    h = int(round(PP_HALF_WINDOW_S * fs))
    beats = beats[(beats - h >= 0) & (beats + h < signal.size)][:N_MEASURE]
    if beats.size == 0:
        raise ValueError("no reference beats to measure QRS amplitude")
    idx = beats[:, None] + np.arange(-h, h)[None, :]
    seg = signal[idx]
    return _trimmed_mean(seg.max(axis=1) - seg.min(axis=1))


def noise_rms(noise: np.ndarray, fs: float) -> float:
    """sigamp -r: trimmed mean of per-second, mean-removed RMS values."""
    w = int(round(fs))
    n = min(noise.size // w, N_MEASURE)
    blocks = noise[: n * w].reshape(n, w).astype(np.float64)
    rms = np.sqrt(((blocks - blocks.mean(axis=1, keepdims=True)) ** 2).mean(axis=1))
    return _trimmed_mean(rms)


def signal_power(signal: np.ndarray, beats: np.ndarray, fs: float, symbols: np.ndarray | None = None) -> float:
    return qrs_peak_to_peak(signal, beats, fs, symbols) ** 2 / 8.0


def gain_for_snr(S: float, N: float, snr_db: float) -> float:
    return float(np.sqrt(S / (N * 10 ** (snr_db / 10.0))))


def snr_for_gain(S: float, N: float, gain: float) -> float:
    return float(10 * np.log10(S / (N * gain ** 2)))


def noise_power(noise: np.ndarray, fs: float, estimator: str = "nst", mask: np.ndarray | None = None) -> float:
    if estimator == "nst":
        return noise_rms(noise, fs) ** 2
    seg = noise[mask] if mask is not None else noise
    return float(np.var(seg))


def mix(clean: Record, noise: Record, snr_db: float, channel: int = 0, mask: np.ndarray | None = None,
        estimator: str = "nst", continuity: bool = True) -> MixResult:
    """Add `noise` to one channel of `clean` at `snr_db` on the masked samples.

    Sample i of the noise record goes onto sample i of the ECG, as in nst.
    Default mask: the nst protocol (5 min clean, then 2 min noisy / 2 min clean).
    """
    x = clean.signal[:, channel].astype(np.float64)
    n = noise.signal[: x.size, channel % noise.signal.shape[1]].astype(np.float64)
    if n.size < x.size:
        n = np.resize(n, x.size)
    if mask is None:
        mask = protocol_mask(x.size, clean.fs)
    S = signal_power(x, clean.beats, clean.fs, clean.beat_symbols)
    N = noise_power(n, clean.fs, estimator, mask)
    a = gain_for_snr(S, N, snr_db)

    gain = np.where(mask, a, 0.0)
    added = gain * n
    if continuity:
        # at each gain change nst subtracts z so the output stays continuous
        z = np.zeros_like(x)
        level = 0.0
        prev_g = 0.0
        for seg in runs(mask)[1:]:
            k = seg.start
            g_new = a if seg.noisy else 0.0
            level = level + (g_new - prev_g) * n[k - 1]
            z[k:] = level
            prev_g = g_new
        added = added - z
    return MixResult(signal=x + added, noise=added, mask=mask, gain=a, S=S, N=N, snr_db=snr_db)


@dataclass(frozen=True)
class OfficialFit:
    gain: float  # least-squares gain of the noise record in the official mix
    r: float  # correlation between residual and noise (per-segment demeaned)


def fit_official_gain(noisy: Record, clean: Record, noise: Record, mask: np.ndarray, channel: int = 0) -> OfficialFit:
    """Recover the gain nst used by regressing the residual on the noise record.

    Each noisy segment is demeaned separately, because nst's continuity
    offsets shift the residual by a different constant in every segment.
    """
    resid = noisy.signal[:, channel].astype(np.float64) - clean.signal[:, channel].astype(np.float64)
    nn = noise.signal[:, channel % noise.signal.shape[1]].astype(np.float64)
    rs, ns = [], []
    for seg in runs(mask):
        if seg.noisy:
            r = resid[seg.start:seg.stop]
            q = nn[seg.start:seg.stop]
            rs.append(r - r.mean())
            ns.append(q - q.mean())
    r_all, n_all = np.concatenate(rs), np.concatenate(ns)
    g = float(np.dot(r_all, n_all) / np.dot(n_all, n_all))
    return OfficialFit(gain=g, r=float(np.corrcoef(r_all, n_all)[0, 1]))
