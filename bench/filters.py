"""Filter designs, application and response data for plots."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps


@dataclass(frozen=True)
class FilterSpec:
    kind: str  # "highpass" | "lowpass" | "bandpass" | "notch"
    family: str = "iir"  # "iir" (Butterworth / notch) or "fir" (windowed)
    f1: float = 0.5  # cutoff (Hz) or lower edge / notch frequency
    f2: float | None = None  # upper edge for bandpass
    order: int = 2  # IIR order, or FIR number of taps
    q: float = 30.0  # notch quality factor

    @property
    def label(self) -> str:
        if self.kind == "notch":
            return f"Notch {self.f1:g} Hz (Q={self.q:g})"
        band = f"{self.f1:g}-{self.f2:g} Hz" if self.kind == "bandpass" else f"{self.f1:g} Hz"
        fam = f"Butterworth order {self.order}" if self.family == "iir" else f"FIR {self.order} taps"
        return f"{self.kind.capitalize()} {band}, {fam}"


@dataclass(frozen=True)
class Design:
    spec: FilterSpec
    fs: float
    sos: np.ndarray | None = None  # IIR, second-order sections
    b: np.ndarray | None = None  # FIR / notch numerator
    a: np.ndarray | None = None  # notch denominator


def design(spec: FilterSpec, fs: float) -> Design:
    nyq = fs / 2
    if spec.kind == "notch":
        b, a = sps.iirnotch(spec.f1, spec.q, fs=fs)
        return Design(spec, fs, b=b, a=a)
    wn = [spec.f1, spec.f2] if spec.kind == "bandpass" else spec.f1
    if spec.family == "iir":
        sos = sps.butter(spec.order, wn, btype=spec.kind, fs=fs, output="sos")
        return Design(spec, fs, sos=sos)
    numtaps = spec.order | 1  # odd length -> type I linear phase
    pass_zero = {"highpass": False, "lowpass": True, "bandpass": False}[spec.kind]
    b = sps.firwin(numtaps, wn, pass_zero=pass_zero, fs=fs, window="hamming")
    if np.any(np.asarray(wn) >= nyq):
        raise ValueError("cutoff must be below Nyquist")
    return Design(spec, fs, b=b, a=np.array([1.0]))


def apply(d: Design, x: np.ndarray, zero_phase: bool = True) -> np.ndarray:
    """Filter x. zero_phase=True uses forward-backward filtering (no delay)."""
    if d.sos is not None:
        return sps.sosfiltfilt(d.sos, x) if zero_phase else sps.sosfilt(d.sos, x)
    if zero_phase:
        padlen = min(3 * max(len(d.a), len(d.b)), x.size - 1)
        return sps.filtfilt(d.b, d.a, x, padlen=padlen)
    return sps.lfilter(d.b, d.a, x)


@dataclass(frozen=True)
class Response:
    f: np.ndarray  # Hz
    mag_db: np.ndarray
    phase_deg: np.ndarray  # unwrapped
    group_delay_ms: np.ndarray


def response(d: Design, n: int = 4096, zero_phase: bool = False) -> Response:
    """Frequency response. With zero_phase=True the magnitude is squared and
    phase / group delay are zero (forward-backward filtering)."""
    if d.sos is not None:
        f, h = sps.sosfreqz(d.sos, worN=n, fs=d.fs)
        b, a = sps.sos2tf(d.sos)
    else:
        b, a = d.b, d.a
        f, h = sps.freqz(b, a, worN=n, fs=d.fs)
    mag = np.abs(h)
    if zero_phase:
        mag_db = 20 * np.log10(np.maximum(mag ** 2, 1e-12))
        return Response(f, mag_db, np.zeros_like(f), np.zeros_like(f))
    mag_db = 20 * np.log10(np.maximum(mag, 1e-12))
    phase = np.degrees(np.unwrap(np.angle(h)))
    gd = _group_delay(b, a, f, d.fs, mag)
    return Response(f, mag_db, phase, gd)


def _group_delay(b, a, f, fs, mag) -> np.ndarray:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, gd = sps.group_delay((b, a), w=f, fs=fs)
    gd = gd / fs * 1000.0
    # group delay is meaningless in the deep stopband; hide it there
    gd[mag < 10 ** (-40 / 20)] = np.nan
    return gd


# Pre-filter settings used by the detector benchmark.
PREFILTERS: dict[str, list[FilterSpec]] = {
    "none": [],
    "hp_notch": [FilterSpec("highpass", "iir", 0.5, order=2), FilterSpec("notch", f1=60.0, q=30.0)],
}
PREFILTER_LABELS = {
    "none": "No pre-filter",
    "hp_notch": "High-pass 0.5 Hz + 60 Hz notch",
}


def prefilter(x: np.ndarray, fs: float, setting: str) -> np.ndarray:
    for spec in PREFILTERS[setting]:
        x = apply(design(spec, fs), x, zero_phase=True)
    return x
