"""QRS detectors behind one interface.

Each detector is the published pipeline as implemented in its library,
including that method's own pre-processing (for NeuroKit2 methods:
`ecg_clean(method=...)` then `ecg_findpeaks(method=...)`). Every detector
returns R-peak sample indices as a sorted int64 array.
"""
from __future__ import annotations

import contextlib
import io
import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class Detector:
    key: str
    name: str
    library: str
    reference: str
    fn: Callable[[np.ndarray, float], np.ndarray]


def _nk(clean_method: str | None, peak_method: str) -> Callable[[np.ndarray, float], np.ndarray]:
    def run(x: np.ndarray, fs: float) -> np.ndarray:
        import neurokit2 as nk

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y = nk.ecg_clean(x, sampling_rate=int(fs), method=clean_method) if clean_method else x
            out = nk.ecg_findpeaks(y, sampling_rate=int(fs), method=peak_method)
        return np.asarray(out["ECG_R_Peaks"], dtype=np.int64)

    return run


def _xqrs(x: np.ndarray, fs: float) -> np.ndarray:
    from wfdb import processing

    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        q = processing.XQRS(sig=x, fs=fs)
        q.detect(verbose=False)
    return np.asarray(q.qrs_inds, dtype=np.int64)


DETECTORS: dict[str, Detector] = {
    d.key: d
    for d in [
        Detector("neurokit", "NeuroKit2", "neurokit2", "Makowski et al. 2021 (default method)",
                 _nk("neurokit", "neurokit")),
        Detector("pantompkins", "Pan-Tompkins", "neurokit2", "Pan & Tompkins 1985",
                 _nk("pantompkins1985", "pantompkins1985")),
        Detector("hamilton", "Hamilton", "neurokit2", "Hamilton 2002",
                 _nk("hamilton2002", "hamilton2002")),
        Detector("elgendi", "Elgendi", "neurokit2", "Elgendi et al. 2010",
                 _nk("elgendi2010", "elgendi2010")),
        Detector("xqrs", "XQRS", "wfdb", "PhysioNet WFDB XQRS",
                 _xqrs),
    ]
}


def detect(key: str, x: np.ndarray, fs: float) -> np.ndarray:
    """Run detector `key`. Returns sorted unique R-peak indices within range."""
    peaks = DETECTORS[key].fn(np.asarray(x, dtype=np.float64), fs)
    peaks = np.unique(peaks[(peaks >= 0) & (peaks < len(x))])
    return peaks.astype(np.int64)
