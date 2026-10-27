"""Data and models for the Learn chapters.

Real recordings (data/learn/*.npz, built by scripts/build_learning_data.py):
  cebs_rest  BIOPAC MP36, healthy volunteer lying still: ECG leads I + II, respiration band, SCG
  ptt_*      sit / walk / run: ECG, finger PPG (red, IR, green), 3-axis accelerometer
  pcg        heart sounds (phonocardiogram) with simultaneous ECG

Models (schematic, clearly labelled as such in the pages):
  cardiac_cycle()  pressures, volume, valve states and heart sounds over one beat
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import streamlit as st
from scipy import signal as sps

from bench.config import DATA_DIR

LEARN_DIR = DATA_DIR / "learn"


@st.cache_resource(show_spinner=False)
def load(name: str) -> dict:
    """One excerpt as float32 arrays (read-only, shared)."""
    with np.load(LEARN_DIR / f"{name}.npz") as z:
        out = {}
        for k in z.files:
            v = z[k]
            v = v.astype(np.float32) if v.dtype == np.float16 else v
            if isinstance(v, np.ndarray):
                v.flags.writeable = False
            out[k] = v
    out["fs"] = int(out["fs"])
    return out


@st.cache_data(show_spinner=False)
def manifest() -> dict:
    p = LEARN_DIR / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def available() -> bool:
    return (LEARN_DIR / "cebs_rest.npz").exists()


def bandpass(x: np.ndarray, lo: float, hi: float, fs: float, order: int = 2) -> np.ndarray:
    return sps.filtfilt(*sps.butter(order, [lo, hi], btype="band", fs=fs), np.asarray(x, dtype=np.float64))


def ensemble(x: np.ndarray, beats: np.ndarray, pre: int, post: int) -> np.ndarray:
    beats = beats[(beats - pre >= 0) & (beats + post < x.size)]
    return np.mean([x[b - pre:b + post] for b in beats], axis=0)


def r_peaks(ecg: np.ndarray, fs: float) -> np.ndarray:
    """Simple R-peak finder for the short teaching excerpts that have no annotations."""
    f = np.abs(bandpass(ecg, 5, 25, fs))
    pk, _ = sps.find_peaks(f, distance=int(0.33 * fs), height=np.percentile(f, 98) * 0.4)
    # refine to the true extreme of the raw ECG within +/- 40 ms
    w = int(0.04 * fs)
    raw = np.asarray(ecg, dtype=np.float64)
    sign = np.sign(np.median([raw[max(p - w, 0):p + w].max() + raw[max(p - w, 0):p + w].min() for p in pk])) or 1
    return np.array([max(p - w, 0) + int(np.argmax(sign * raw[max(p - w, 0):p + w])) for p in pk])


# ---------------------------------------------------------------- ECG landmarks
@dataclass(frozen=True)
class EcgLandmarks:
    p: int
    q: int
    r: int
    s: int
    t: int


def ecg_landmarks(avg: np.ndarray, r_index: int, fs: float) -> EcgLandmarks:
    """P, Q, R, S, T on an averaged beat (indices into avg). R is at r_index."""
    ms = lambda v: int(v * fs / 1000)  # noqa: E731
    seg = lambda a, b: slice(r_index + ms(a), r_index + ms(b))  # noqa: E731
    p = seg(-260, -90).start + int(np.argmax(avg[seg(-260, -90)]))
    q = seg(-60, 0).start + int(np.argmin(avg[seg(-60, 0)]))
    s = seg(0, 70).start + int(np.argmin(avg[seg(0, 70)]))
    t = seg(150, 420).start + int(np.argmax(avg[seg(150, 420)]))
    return EcgLandmarks(p, q, r_index, s, t)


def net_qrs(avg: np.ndarray, r_index: int, fs: float) -> float:
    """Net QRS deflection (R height minus S depth, relative to the PR baseline)."""
    ms = lambda v: int(v * fs / 1000)  # noqa: E731
    base = np.median(avg[r_index - ms(120): r_index - ms(70)])
    qrs = avg[r_index - ms(60): r_index + ms(70)] - base
    return float(qrs.max() + qrs.min())


# ---------------------------------------------------------------- PPG landmarks
@dataclass(frozen=True)
class PpgLandmarks:
    foot: int  # pulse arrival (tangent intersection)
    upstroke: int  # steepest rise
    peak: int  # systolic peak
    notch: int  # dicrotic notch
    diastolic: int  # a point on the diastolic runoff


def ppg_landmarks(avg: np.ndarray, fs: float) -> PpgLandmarks:
    """Landmarks on an averaged PPG pulse that starts at the ECG R peak."""
    d1 = np.gradient(avg)
    up = int(np.argmax(d1[: int(0.45 * fs)]))
    pre_min = int(np.argmin(avg[:up])) if up > 0 else 0
    # intersecting-tangent foot: tangent at the steepest point meets the pre-pulse minimum level
    foot = int(np.clip(up - (avg[up] - avg[pre_min]) / max(d1[up], 1e-9), 0, up))
    peak = up + int(np.argmax(avg[up: up + int(0.25 * fs)]))
    # notch: the deepest point of the second derivative's positive bump after the peak
    d2 = np.gradient(d1)
    win = slice(peak + int(0.05 * fs), min(peak + int(0.35 * fs), avg.size - 1))
    notch = win.start + int(np.argmax(d2[win]))
    # diastolic runoff: the decay after the notch (a point 120 ms into it, for labelling)
    dia = min(notch + int(0.12 * fs), avg.size - 1)
    return PpgLandmarks(foot, up, peak, notch, dia)


# ---------------------------------------------------------------- cardiac cycle model
@dataclass(frozen=True)
class Cycle:
    t: np.ndarray  # s, one beat starting at the P wave
    ecg: np.ndarray
    lv: np.ndarray  # left-ventricular pressure, mmHg
    ao: np.ndarray  # aortic pressure
    la: np.ndarray  # left-atrial pressure
    vol: np.ndarray  # left-ventricular volume, mL
    mitral_open: np.ndarray
    aortic_open: np.ndarray
    s1: float  # time of mitral closure
    s2: float  # time of aortic closure
    r: float  # time of the R peak


def _bump(t, t0, tp, t1):
    """Smooth asymmetric 0..1..0 bump: rises t0->tp, falls tp->t1."""
    y = np.zeros_like(t)
    a = (t >= t0) & (t < tp)
    b = (t >= tp) & (t < t1)
    y[a] = 0.5 - 0.5 * np.cos(np.pi * (t[a] - t0) / (tp - t0))
    y[b] = 0.5 + 0.5 * np.cos(np.pi * (t[b] - tp) / (t1 - tp))
    return y


@st.cache_data(show_spinner=False)
def cardiac_cycle(hr: float = 70.0, fs: int = 1000) -> Cycle:
    """Schematic Wiggers diagram for the left heart. Valves are not scripted: each one is
    open exactly when the pressure behind it is higher than the pressure in front of it."""
    T = 60.0 / hr
    sc = T / 0.857  # timings scale with the beat (diastole shrinks most in reality; kept simple)
    n = int(round(T * fs))
    t = np.arange(n) / fs
    r = 0.16 * min(sc, 1.0)
    # ECG (schematic): P, QRS, T
    ecg = (0.15 * _bump(t, 0.02, 0.06, 0.10) - 0.1 * _bump(t, r - 0.03, r - 0.015, r - 0.005)
           + 1.0 * _bump(t, r - 0.01, r, r + 0.012) - 0.25 * _bump(t, r + 0.012, r + 0.025, r + 0.04)
           + 0.3 * _bump(t, r + 0.16 * sc ** 0.5, r + 0.26 * sc ** 0.5, r + 0.34 * sc ** 0.5))
    # left-ventricular pressure: contraction starts ~40 ms after R
    sys0, sysp, sys1 = r + 0.04, r + 0.22 * sc ** 0.5, r + 0.50 * sc ** 0.5
    # diastole: LV pressure low and slowly rising as it fills, small bump from the atrial kick
    lv = (4 + 2 * np.clip(t / max(sys0, 1e-9), 0, 1) * (t < sys0) + 121 * _bump(t, sys0, sysp, sys1)
          + 2.5 * _bump(t, 0.07, 0.12, sys0))
    # LA sits just above LV in diastole (so the mitral valve is open); a wave = atrial contraction,
    # v wave = filling against the closed mitral valve during systole
    la = 8 + 5 * _bump(t, 0.04, 0.10, 0.17) + 7 * _bump(t, sys0 + 0.05, sys1 - 0.02, sys1 + 0.12)
    # aortic pressure, two-element Windkessel: flow through the open valve is proportional to the
    # pressure difference (k), the elastic aorta stores it and drains to the body (tau = R*C)
    ao = np.empty(n)
    tau, k = 1.9, 22.0
    p = 80.0
    for _ in range(4):  # a few beats to reach the periodic steady state
        for i in range(n):
            q = k * (lv[i] - p) if lv[i] > p else 0.0
            p += (q - p / tau) / fs
            ao[i] = p
    aortic_open = (lv > ao) & (t >= sys0)
    k2 = min(int(np.flatnonzero(aortic_open)[-1]) + 1, n - 1)  # aortic valve closes -> S2
    # dicrotic notch (incisura) after aortic closure
    ao = ao - 5 * np.exp(-((t - t[k2] - 0.012) / 0.008) ** 2) + 3 * _bump(t, t[k2] + 0.02, t[k2] + 0.05, t[k2] + 0.12)
    mitral_open = la > lv
    s1 = float(t[int(np.flatnonzero(~mitral_open & (t > 0.1))[0])])  # mitral closes as LV pressure rises
    # volume: fills while mitral open (fast early, atrial kick late), empties while aortic open
    vol = np.empty(n)
    v = 120.0
    flow_out = np.clip(lv - ao, 0, None) * aortic_open
    flow_out *= 70 / (flow_out.sum() / fs)
    flow_in = np.clip(la - lv, 0, None) * mitral_open
    flow_in *= 70 / max(flow_in.sum() / fs, 1e-9)
    v = 120.0 - (flow_in[: int(0.15 * fs)].sum()) / fs  # start of beat: before atrial kick completes
    for i in range(n):
        v += (flow_in[i] - flow_out[i]) / fs
        vol[i] = v
    return Cycle(t, ecg, lv, ao, la, vol, mitral_open, aortic_open, s1, float(t[k2]), r)


# ---------------------------------------------------------------- circulation diagram
FLOW_STEPS = [
    ("body", "Body → right atrium", "Oxygen-poor blood returns from the body through the venae cavae into the "
     "**right atrium**."),
    ("tricuspid", "Right atrium → right ventricle", "The **tricuspid valve** opens because atrial pressure is higher "
     "than ventricular pressure, and blood fills the **right ventricle**."),
    ("pulmonary", "Right ventricle → lungs", "The right ventricle contracts. The **pulmonary valve** opens and blood "
     "goes to the lungs to pick up oxygen. This is the **pulmonary circulation**."),
    ("lungs", "Lungs → left atrium", "Oxygen-rich blood returns through the pulmonary veins into the **left atrium**."),
    ("mitral", "Left atrium → left ventricle", "The **mitral valve** opens and blood fills the **left ventricle**, "
     "the strongest chamber."),
    ("aortic", "Left ventricle → body", "The left ventricle contracts. The **aortic valve** opens and blood is ejected "
     "into the aorta and out to the whole body. This is the **systemic circulation**."),
]


def circulation_svg(step: str, dark: bool) -> str:
    """Schematic four-chamber heart with lungs and body; the active step is highlighted."""
    ink = "#ECE7DE" if dark else "#24221E"
    muted = "#6B6559" if dark else "#B9B1A3"
    blue = "#8FA2FF" if dark else "#1F3A93"  # oxygen-poor
    red = "#F06A5E" if dark else "#B8322A"  # oxygen-rich
    hl = "#F0874B" if dark else "#D2602A"
    paper = "#1A1D2A" if dark else "#EFE9DF"

    def on(key):
        return step == key

    def stroke(key, base):
        return hl if on(key) else base

    def w(key):
        return 5 if on(key) else 2.5

    def valve(x, y, key, label, lx, ly, anchor="middle"):
        col = hl if on(key) else ink
        return (f'<rect x="{x - 14}" y="{y - 4}" width="28" height="8" rx="3" fill="{col}" opacity="{1 if on(key) else .55}"/>'
                f'<text x="{lx}" y="{ly}" font-size="14" fill="{col}" text-anchor="{anchor}" '
                f'font-weight="{600 if on(key) else 400}">{label}</text>')

    chamber = lambda x, y, wd, ht, fill, label, key_list: (  # noqa: E731
        f'<rect x="{x}" y="{y}" width="{wd}" height="{ht}" rx="18" fill="{fill}" fill-opacity="'
        f'{.32 if step in key_list else .14}" stroke="{fill}" stroke-width="{3 if step in key_list else 1.5}"/>'
        f'<text x="{x + wd / 2}" y="{y + ht / 2 + 6}" font-size="17" fill="{ink}" text-anchor="middle">{label}</text>')
    marker = ('<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
              'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs>')
    svg = [f'<svg viewBox="0 0 640 420" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Schematic of the heart and circulation" style="width:100%;max-width:640px;'
           f'font-family:Geist,system-ui,sans-serif">{marker}',
           f'<rect x="0" y="0" width="640" height="420" rx="14" fill="{paper}"/>',
           # lungs and body
           f'<rect x="230" y="18" width="180" height="56" rx="28" fill="none" stroke="{stroke("lungs", muted)}" '
           f'stroke-width="{w("lungs") if on("lungs") or on("pulmonary") else 2}"/>'
           f'<text x="320" y="51" font-size="18" fill="{ink}" text-anchor="middle">Lungs</text>',
           f'<rect x="230" y="350" width="180" height="56" rx="28" fill="none" stroke="{stroke("body", muted)}" '
           f'stroke-width="{w("body") if on("body") or on("aortic") else 2}"/>'
           f'<text x="320" y="383" font-size="18" fill="{ink}" text-anchor="middle">Body</text>',
           # chambers: viewer's left = patient's right
           chamber(150, 120, 140, 80, blue, "Right atrium", ("body", "tricuspid")),
           chamber(150, 230, 140, 95, blue, "Right ventricle", ("tricuspid", "pulmonary")),
           chamber(350, 120, 140, 80, red, "Left atrium", ("lungs", "mitral")),
           chamber(350, 230, 140, 95, red, "Left ventricle", ("mitral", "aortic")),
           valve(220, 215, "tricuspid", "Tricuspid", 140, 220, "end"),
           valve(420, 215, "mitral", "Mitral", 500, 220, "start"),
           valve(195, 108, "pulmonary", "Pulmonary valve", 178, 98, "end"),
           valve(445, 335, "aortic", "Aortic valve", 520, 352, "start"),
           # flow paths
           f'<path d="M230 378 C 90 378, 90 160, 150 160" fill="none" stroke="{stroke("body", blue)}" '
           f'stroke-width="{w("body")}" marker-end="url(#ah)"/>',
           f'<path d="M195 120 C 195 70, 210 46, 230 46" fill="none" stroke="{stroke("pulmonary", blue)}" '
           f'stroke-width="{w("pulmonary")}" marker-end="url(#ah)"/>',
           f'<path d="M410 46 C 460 46, 470 80, 445 120" fill="none" stroke="{stroke("lungs", red)}" '
           f'stroke-width="{w("lungs")}" marker-end="url(#ah)"/>',
           f'<path d="M445 325 C 560 340, 520 378, 410 378" fill="none" stroke="{stroke("aortic", red)}" '
           f'stroke-width="{w("aortic")}" marker-end="url(#ah)"/>',
           f'<path d="M220 200 L 220 228" stroke="{stroke("tricuspid", blue)}" stroke-width="{w("tricuspid")}" '
           f'marker-end="url(#ah)"/>',
           f'<path d="M420 200 L 420 228" stroke="{stroke("mitral", red)}" stroke-width="{w("mitral")}" '
           f'marker-end="url(#ah)"/>',
           f'<text x="16" y="300" font-size="14" fill="{blue}">oxygen-poor</text>',
           f'<text x="624" y="300" font-size="14" fill="{red}" text-anchor="end">oxygen-rich</text>',
           f'<text x="320" y="219" font-size="13" fill="{muted}" text-anchor="middle">septum</text>',
           '</svg>']
    return "".join(svg)


# ---------------------------------------------------------------- chapter chrome
CHAPTERS = [
    ("app_pages/learn_start.py", "Start here", ":material/flag:"),
    ("app_pages/learn_ecg.py", "The ECG", ":material/ecg:"),
    ("app_pages/learn_heart_rate.py", "Heart rate & breathing", ":material/pulmonology:"),
    ("app_pages/learn_cardiac_cycle.py", "Heart, valves & sounds", ":material/cardiology:"),
    ("app_pages/learn_ppg.py", "PPG: the pulse", ":material/fingerprint:"),
    ("app_pages/learn_motion.py", "Motion & interference", ":material/directions_run:"),
    ("app_pages/learn_acquisition.py", "How signals are recorded", ":material/settings_input_component:"),
    ("app_pages/learn_quiz.py", "Exam practice", ":material/quiz:"),
]


def chapter_header(path: str, title: str, lead: str) -> None:
    from .style import overline

    i = [c[0] for c in CHAPTERS].index(path)
    overline(f"Learn · chapter {i} of {len(CHAPTERS) - 1}" if i else "Learn · start here", f"learn{i}")
    st.title(title)
    st.markdown(lead)


def key_idea(text: str) -> None:
    st.info(text, icon=":material/lightbulb:", title="Key idea")


KEY_TERMS = {
    "app_pages/learn_start.py": ["ecg", "pcg", "ppg", "respiration_signal", "accelerometer", "synchronization",
                                 "pulse_arrival_time"],
    "app_pages/learn_ecg.py": ["potential_difference", "electrode", "lead", "electrical_axis", "einthoven", "p_wave",
                               "qrs", "t_wave", "depolarization", "repolarization"],
    "app_pages/learn_heart_rate.py": ["rr_interval", "heart_rate", "calculation_channel", "rest_vs_excited",
                                      "inspiration", "expiration", "rsa", "venous_return"],
    "app_pages/learn_cardiac_cycle.py": ["pulmonary_circulation", "systemic_circulation", "heart_valve", "mitral_valve",
                                         "aortic_valve", "s1", "s2", "systole", "diastole", "wiggers"],
    "app_pages/learn_ppg.py": ["ppg", "pulse_arrival", "systolic_upstroke", "systolic_peak", "dicrotic_notch",
                               "diastolic_runoff", "pulse_arrival_time", "ppg_wavelength", "respiratory_ppg"],
    "app_pages/learn_motion.py": ["accelerometer", "motion_artefact", "mains_interference", "baseline_wander",
                                  "emg_noise", "electrode_motion", "notch_filter", "current_body", "earth_ground",
                                  "smartwatch"],
    "app_pages/learn_acquisition.py": ["daq", "differential_amplifier", "isolation", "sampling_rate", "nyquist",
                                       "aliasing", "anti_aliasing", "resolution", "calculation_channel", "biopac"],
}


def key_terms(path: str) -> None:
    """Links that open the glossary directly at each key term of a chapter."""
    from .terms import TERMS

    keys = KEY_TERMS.get(path, [])
    if not keys:
        return
    st.markdown("**Key terms in this chapter**")
    with st.container(horizontal=True, gap="small"):
        for k in keys:
            st.page_link("app_pages/learn_glossary.py", label=TERMS[k].name, query_params={"term": k},
                         icon=":material/dictionary:", help=TERMS[k].short)


def chapter_nav(path: str) -> None:
    i = [c[0] for c in CHAPTERS].index(path)
    key_terms(path)
    st.space("small")
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        if i > 0:
            p, t, _ = CHAPTERS[i - 1]
            st.page_link(p, label=f"Previous: {t}", icon=":material/arrow_back:")
        else:
            st.space("small")
        st.page_link("app_pages/learn_glossary.py", label="Glossary", icon=":material/dictionary:")
        if i < len(CHAPTERS) - 1:
            p, t, _ = CHAPTERS[i + 1]
            st.page_link(p, label=f"Next: {t}", icon=":material/arrow_forward:")
        else:
            st.space("small")


def source_note(*names: str) -> None:
    """Caption naming the real recordings shown on a page."""
    m = manifest()
    text = {
        "cebs_rest": lambda d: f"CEBS database record {d['record']} (healthy volunteer lying still, recorded with a "
                               "BIOPAC MP36, resampled 5 kHz → 500 Hz)",
        "ptt_sit": lambda d: f"Pulse Transit Time PPG dataset, {d['record']} (sitting, 120 s excerpt)",
        "ptt_walk": lambda d: f"Pulse Transit Time PPG dataset, {d['record']} (walking on the spot)",
        "ptt_run": lambda d: f"Pulse Transit Time PPG dataset, {d['record']} (running on the spot)",
        "pcg": lambda d: f"PhysioNet/CinC Challenge 2016, record {d['record']} (heart sounds + ECG, labelled normal)",
    }
    parts = [text[n](m[n]) for n in names if n in m]
    if parts:
        st.caption(":material/database: Real recording: " + "; ".join(parts) + ". PhysioNet, open licence.")
