"""Build the test signals used by the benchmark and the app (deterministic)."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .config import CHANNEL
from .data import Record, load_record, nstdb_name
from .mixer import MixResult, mix
from .segments import protocol_mask, subtraction_mask


def official_mask(noisy: Record, clean: Record, channel: int = CHANNEL) -> np.ndarray:
    """Noisy-segment mask of an official NSTDB record, by subtraction.

    Compares in physical units with half-LSB tolerance, so it works even
    though NSTDB and MIT-BIH store different ADC baselines (0 vs 1024).
    Data-audit finding: the residual is not zero in the "clean" segments.
    After each noisy segment nst leaves a constant DC offset (e.g. -44 LSB =
    -0.22 mV in 118e24). So noise is where the residual *changes* from one
    sample to the next, not where it is non-zero.
    """
    a = noisy.signal[:, channel].astype(np.float64)
    b = clean.signal[:, channel].astype(np.float64)
    if a.shape != b.shape:
        return protocol_mask(a.size, noisy.fs)
    tol = 0.5 / min(noisy.gain[channel], clean.gain[channel])
    step = np.abs(np.diff(a - b, prepend=a[0] - b[0])) > tol
    changing = step.astype(np.int16)
    return subtraction_mask(changing, np.zeros_like(changing), noisy.fs)


@lru_cache(maxsize=16)
def nstdb_mask(source: str, snr: int) -> np.ndarray:
    return official_mask(load_record("nstdb", nstdb_name(source, snr)), load_record("mitdb", source))


def nstdb_signal(source: str, snr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """(signal, reference beats, noisy mask, fs) for an official NSTDB record."""
    rec = load_record("nstdb", nstdb_name(source, snr))
    return rec.signal[:, CHANNEL].astype(np.float64), rec.beats, nstdb_mask(source, snr), rec.fs


def mixed(record: str, noise: str, snr: float) -> MixResult:
    return mix(load_record("mitdb", record), load_record("nstdb", noise), snr, channel=CHANNEL)


def mixed_signal(record: str, noise: str, snr: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """(signal, reference beats, noisy mask, fs) for our own mixture."""
    clean = load_record("mitdb", record)
    m = mixed(record, noise, snr)
    return m.signal.astype(np.float64), clean.beats, m.mask, clean.fs


def get_signal(dataset: str, record: str, noise: str, snr: float):
    if dataset == "nstdb":
        return nstdb_signal(record, int(snr))
    return mixed_signal(record, noise, snr)
