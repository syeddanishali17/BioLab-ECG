"""Load PhysioNet records and reference beat annotations."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import wfdb

from .config import BEAT_SYMBOLS, DATA_DIR


@dataclass(frozen=True)
class Record:
    name: str
    db: str
    fs: float
    signal: np.ndarray  # physical units (mV, float32), shape (n_samples, n_channels)
    digital: np.ndarray  # raw ADC values, same shape
    channels: tuple[str, ...]
    gain: tuple[float, ...]
    baseline: tuple[int, ...]
    units: tuple[str, ...]
    beats: np.ndarray = field(repr=False)  # reference beat sample indices
    beat_symbols: np.ndarray = field(repr=False)

    @property
    def n_samples(self) -> int:
        return self.signal.shape[0]

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.fs


def record_path(db: str, name: str) -> Path:
    return DATA_DIR / db / name


def _reference_beats(path: Path, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        ann = wfdb.rdann(str(path), "atr")
    except FileNotFoundError:
        return np.array([], dtype=np.int64), np.array([], dtype="<U1")
    sym = np.asarray(ann.symbol)
    samp = np.asarray(ann.sample, dtype=np.int64)
    keep = np.isin(sym, list(BEAT_SYMBOLS)) & (samp >= 0) & (samp < n_samples)
    return samp[keep], sym[keep]


@lru_cache(maxsize=24)
def load_record(db: str, name: str) -> Record:
    """Load a record from data/<db>/<name>. Cached in-process."""
    path = record_path(db, name)
    rec = wfdb.rdrecord(str(path), physical=False)
    digital = rec.d_signal.astype(np.int16)
    gain = tuple(float(g) for g in rec.adc_gain)
    baseline = tuple(int(b) for b in rec.baseline)
    if db == "nstdb" and any(c.startswith("Created by `nst'") for c in (rec.comments or [])):
        # Data-audit finding: nst removed the ADC zero (1024) from the samples
        # and wrote adczero = 0, but the header baseline still says 1024, which
        # would shift the record by -5.12 mV. The true baseline is the adczero.
        baseline = tuple(int(z) for z in rec.adc_zero)
    signal = (digital - np.asarray(baseline)) / np.asarray(gain)
    beats, symbols = _reference_beats(path, digital.shape[0])
    return Record(
        name=name,
        db=db,
        fs=float(rec.fs),
        signal=signal.astype(np.float32),
        digital=digital,
        channels=tuple(rec.sig_name),
        gain=gain,
        baseline=baseline,
        units=tuple(rec.units),
        beats=beats,
        beat_symbols=symbols,
    )


def load_all_annotations(db: str, name: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """All annotations (beats and non-beats), for the data audit."""
    ann = wfdb.rdann(str(record_path(db, name)), "atr")
    return np.asarray(ann.sample), np.asarray(ann.symbol), list(ann.aux_note)


def nstdb_name(source: str, snr: int) -> str:
    """'118', -6 -> '118e_6'; '119', 6 -> '119e06'."""
    return f"{source}e_{abs(snr)}" if snr < 0 else f"{source}e{snr:02d}"
