"""Checkpoint 0 data audit, as functions (used by the notebook and the app)."""
from __future__ import annotations

import collections

import numpy as np
from scipy import signal as sps

from .config import CHANNEL, NSTDB_SNRS, NSTDB_SOURCES
from .data import load_all_annotations, load_record, nstdb_name
from .mixer import fit_official_gain, mix
from .segments import mask_agreement, protocol_mask, runs
from .signals import nstdb_mask


def headers() -> list[dict]:
    rows = []
    for src in NSTDB_SOURCES:
        for db, name in [("mitdb", src)] + [("nstdb", nstdb_name(src, s)) for s in NSTDB_SNRS]:
            r = load_record(db, name)
            rows.append({"db": db, "record": name, "fs": r.fs, "n_samples": r.n_samples,
                         "duration_min": round(r.duration_s / 60, 2), "channels": ", ".join(r.channels),
                         "gain": r.gain[0], "baseline": r.baseline[0], "n_beats": len(r.beats)})
    for name in ("bw", "ma", "em"):
        r = load_record("nstdb", name)
        rows.append({"db": "nstdb", "record": name, "fs": r.fs, "n_samples": r.n_samples,
                     "duration_min": round(r.duration_s / 60, 2), "channels": ", ".join(r.channels),
                     "gain": r.gain[0], "baseline": r.baseline[0], "n_beats": 0})
    return rows


def symbol_counts(db: str, name: str) -> dict[str, int]:
    _, sym, _ = load_all_annotations(db, name)
    return dict(collections.Counter(sym).most_common())


def mask_report() -> list[dict]:
    rows = []
    for src in NSTDB_SOURCES:
        for snr in NSTDB_SNRS:
            m = nstdb_mask(src, snr)
            noisy = [s for s in runs(m) if s.noisy]
            rows.append({"record": nstdb_name(src, snr), "noisy_segments": len(noisy),
                         "noisy_minutes": round(m.sum() / 360 / 60, 2),
                         "agreement_with_protocol": round(mask_agreement(m, protocol_mask(m.size, 360)), 6)})
    return rows


def both_channels_noisy(src: str = "118", snr: int = 24) -> dict[str, float]:
    n = load_record("nstdb", nstdb_name(src, snr))
    c = load_record("mitdb", src)
    m = nstdb_mask(src, snr)
    out = {}
    for ch in range(2):
        r = n.signal[:, ch].astype(float) - c.signal[:, ch].astype(float)
        out[n.channels[ch]] = float(np.std(np.diff(r)[m[1:]]))
    return out


def mains_check(record: str = "118", db: str = "mitdb") -> dict[str, float]:
    """Spectral peak near 50 vs 60 Hz relative to the neighbouring floor."""
    r = load_record(db, record)
    f, p = sps.welch(r.signal[:, CHANNEL], fs=r.fs, nperseg=8192)

    def peak_db(f0):
        band = (f > f0 - 1) & (f < f0 + 1)
        floor = ((f > f0 - 6) & (f < f0 - 2)) | ((f > f0 + 2) & (f < f0 + 6))
        return float(10 * np.log10(p[band].max() / np.median(p[floor])))

    return {"peak_50Hz_dB_above_floor": peak_db(50), "peak_60Hz_dB_above_floor": peak_db(60)}


def mixer_validation() -> list[dict]:
    """Remix every official record with our mixer and compare.

    1. Gain: regress the official residual (noisy - clean) on the em record
       to recover the gain nst used, and compare with the gain our mixer
       computes, using the nst estimators and the plain-variance estimator.
    2. Waveform: compare our remix with the official record sample by sample
       (in ADC units, after rounding to integers as nst does).
    """
    rows = []
    em = load_record("nstdb", "em")
    for src in NSTDB_SOURCES:
        clean = load_record("mitdb", src)
        for snr in NSTDB_SNRS:
            noisy = load_record("nstdb", nstdb_name(src, snr))
            mask = nstdb_mask(src, snr)
            fit = fit_official_gain(noisy, clean, em, mask, channel=CHANNEL)
            ours = mix(clean, em, snr, channel=CHANNEL, mask=protocol_mask(clean.n_samples, clean.fs))
            plain = mix(clean, em, snr, channel=CHANNEL, estimator="variance")
            g = noisy.gain[CHANNEL]
            ours_adc = np.round(ours.signal * g).astype(np.int64)
            off_adc = noisy.digital[:, CHANNEL].astype(np.int64) - noisy.baseline[CHANNEL]
            diff = ours_adc - off_adc
            rows.append({
                "record": nstdb_name(src, snr), "nominal_snr_db": snr,
                "nst_gain_fitted": fit.gain, "fit_r": fit.r,
                "our_gain": ours.gain,
                "gain_error_db": 20 * np.log10(ours.gain / fit.gain),
                "variance_estimator_gain_error_db": 20 * np.log10(plain.gain / fit.gain),
                # the final sample of the clean source is invalid, so it is excluded
                "within_5lsb_pct": 100 * float(np.mean(np.abs(diff[:-1]) <= 5)),
                "median_abs_diff_uV": float(np.median(np.abs(diff[:-1])) / g * 1000),
                "rms_diff_uV": float(np.sqrt(np.mean((diff[:-1] / g) ** 2)) * 1000),
            })
    return rows
