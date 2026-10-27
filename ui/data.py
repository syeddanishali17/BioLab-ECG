"""Cached access to precomputed results and to signals for the live views.

Speed rules: pages read only small precomputed tables (summary, per-record,
worst windows); signals are cached as shared resources (no pickling copies);
detections come from the precomputed .npz whenever the run exists.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import streamlit as st

from bench.config import CHANNEL, RESULTS_DIR
from bench.data import load_record
from bench.detectors import DETECTORS, detect
from bench.evaluate import match_beats
from bench.filters import prefilter
from bench.report import run_key, unpack_detections
from bench.signals import get_signal, mixed


def results_available() -> bool:
    return (RESULTS_DIR / "summary.parquet").exists()


@st.cache_data(show_spinner=False)
def summary() -> pd.DataFrame:
    return pd.read_parquet(RESULTS_DIR / "summary.parquet")


@st.cache_data(show_spinner=False)
def per_record() -> pd.DataFrame:
    return pd.read_parquet(RESULTS_DIR / "per_record.parquet")


@st.cache_data(show_spinner=False)
def worst_windows() -> pd.DataFrame:
    return pd.read_parquet(RESULTS_DIR / "worst_windows.parquet")


@st.cache_data(show_spinner=False)
def meta() -> dict:
    p = RESULTS_DIR / "meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner=False)
def json_result(name: str) -> dict | list:
    p = RESULTS_DIR / name
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_resource(show_spinner=False)
def _detections_npz():
    return np.load(RESULTS_DIR / "detections.npz")


def stored_detections(dataset, record, noise, snr, detector, pf) -> np.ndarray | None:
    z = _detections_npz()
    key = run_key(dataset, record, noise, int(snr), detector, pf)
    return unpack_detections(z[key]) if key in z.files else None


@st.cache_resource(show_spinner=False, max_entries=24)
def signal(dataset: str, record: str, noise: str, snr: float):
    """(x, ref, mask, fs) for one test signal, regenerated deterministically.
    Cached as a resource: arrays are shared read-only, never copied."""
    x, ref, mask, fs = get_signal(dataset, record, noise, snr)
    x = x.astype(np.float32)
    x.flags.writeable = False
    return x, ref, mask, fs


@st.cache_resource(show_spinner=False, max_entries=24)
def clean(record: str):
    """(clean channel-0 signal, Record) from MIT-BIH."""
    rec = load_record("mitdb", record)
    return rec.signal[:, CHANNEL], rec


@st.cache_data(show_spinner=False, max_entries=32)
def mix_info(record: str, noise: str, snr: float) -> dict:
    m = mixed(record, noise, snr)
    return {"gain": m.gain, "S": m.S, "N": m.N}


@st.cache_resource(show_spinner=False, max_entries=48)
def live_detections(dataset: str, record: str, noise: str, snr: float, detector: str, pf: str) -> np.ndarray:
    """Use stored detections when the run was precomputed, otherwise run live."""
    if float(snr).is_integer():
        d = stored_detections(dataset, record, noise, int(snr), detector, pf)
        if d is not None:
            return d
    x, _, _, fs = signal(dataset, record, noise, snr)
    return detect(detector, prefilter(x.astype(np.float64), fs, pf), fs)


@st.cache_data(show_spinner=False)
def spectra(record: str) -> dict:
    """Welch spectra of a clean record and the three noise recordings."""
    from scipy import signal as sps

    x, rec = clean(record)
    f, p = sps.welch(x.astype(float), fs=rec.fs, nperseg=4096)
    out = {"f": f, "ecg": 10 * np.log10(p)}
    for k in ("em", "ma", "bw"):
        _, pn = sps.welch(load_record("nstdb", k).signal[:, CHANNEL].astype(float), fs=rec.fs, nperseg=4096)
        out[k] = 10 * np.log10(pn)
    return out


def outcome(ref: np.ndarray, det: np.ndarray, fs: float) -> dict[str, np.ndarray]:
    m = match_beats(ref, det, int(round(0.150 * fs)))
    return {"tp": det[m.tp_det], "fp": det[m.fp], "fn": ref[m.fn]}


def detector_name(key: str) -> str:
    return DETECTORS[key].name
