import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import signal as sps

from bench.data import load_record
from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, tokens

PATH = "app_pages/learn_motion.py"
L.chapter_header(PATH, "Motion and interference",
                 "Real biosignals are never clean. Moving changes the electrode–skin contact and squeezes the "
                 "tissue under a PPG sensor; the mains wiring in the room hums at 50 Hz. An **accelerometer** tells "
                 "you when a disturbance is movement rather than physiology.")
tk = tokens()

# ------------------------------------------------------------ 1. accelerometer
st.header("The accelerometer as a motion witness", anchor=False)
st.markdown("It measures acceleration along three axes (**X, Y, Z**) in units of g. At rest it shows only gravity "
            "(a constant); when you move, all three axes come alive.")
act = st.segmented_control("Activity", ["sit", "walk", "run"], default="walk", required=True, wrap=True, key="mo_act",
                           format_func={"sit": "Sitting", "walk": "Walking on the spot", "run": "Running on the spot"}.get)


@st.cache_data(show_spinner=False)
def activity(a: str):
    d = L.load(f"ptt_{a}")
    fs = d["fs"]
    acc = np.c_[d["a_x"], d["a_y"], d["a_z"]].astype(float)
    mag = np.linalg.norm(acc, axis=1)
    motion = np.convolve(np.abs(mag - np.median(mag)), np.ones(fs // 4) / (fs // 4), mode="same")
    ppg = L.bandpass(d["ppg_green"], 0.4, 10, fs)
    ppg = ppg / ppg.std()  # per-activity scale: the raw scale differs a lot between recordings
    ecg = L.bandpass(d["ecg"], 0.5, 40, fs)
    # agreement of PPG heart rate with ECG heart rate, per 5 s window
    beats = d["beats"]
    errs = []
    for w in range(0, ecg.size - 5 * fs, 5 * fs):
        bw = beats[(beats >= w) & (beats < w + 5 * fs)]
        pk, _ = sps.find_peaks(ppg[w:w + 5 * fs], distance=int(0.3 * fs), prominence=0.4)
        if len(bw) >= 2 and len(pk) >= 2:
            errs.append(abs(60 * fs / np.median(np.diff(pk)) - 60 * fs / np.median(np.diff(bw))))
    return {"fs": fs, "acc": acc, "motion": motion, "ppg": ppg, "ecg": ecg, "err": np.array(errs)}


A = activity(act)
fs = A["fs"]
w0 = st.slider("Window start (s)", 0, 110, 30, key="mo_win")
a, b = w0 * fs, (w0 + 10) * fs
t = np.arange(a, b) / fs
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.34, 0.33, 0.33],
                    subplot_titles=["Accelerometer X / Y / Z (g)", "ECG", "Finger PPG (green light)"])
for k, (lab, col) in enumerate((("X", tk["trace"]), ("Y", tk["noise"]), ("Z", tk["tp"]))):
    fig.add_trace(go.Scatter(x=t, y=A["acc"][a:b, k], name=lab, line=dict(color=col, width=1.3)), 1, 1)
fig.add_trace(go.Scatter(x=t, y=A["ecg"][a:b], line=dict(color=tk["trace"], width=1.2), showlegend=False,
                         hoverinfo="skip"), 2, 1)
fig.add_trace(go.Scatter(x=t, y=A["ppg"][a:b], line=dict(color=tk["fp"], width=1.5), showlegend=False,
                         hoverinfo="skip"), 3, 1)
thr = 0.2  # g of smoothed deviation from the resting magnitude: “strong movement”
mv = A["motion"][a:b] > thr
edges = np.flatnonzero(np.diff(np.r_[0, mv.astype(int), 0]))
for s0, s1 in zip(edges[::2], edges[1::2]):
    for row in (1, 2, 3):
        fig.add_vrect(x0=t[s0], x1=t[min(s1, t.size - 1)], fillcolor=tk["noisy_shade"], line_width=0, layer="below",
                      row=row, col=1)
base_layout(fig, height=540)
fig.update_yaxes(showticklabels=False, row=2, col=1)
fig.update_yaxes(showticklabels=False, row=3, col=1)
fig.update_xaxes(title_text="Time (s) · shaded = accelerometer detects strong movement (> 0.2 g)", row=3, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="Accelerometer, ECG and PPG during activity")

m1, m2, m3 = st.columns(3)
m1.metric("Movement (accelerometer spread)", f"{A['acc'].std(axis=0).mean():.2f} g", border=True)
m2.metric("Time with strong movement", f"{(A['motion'] > thr).mean():.0%}", border=True,
          help="Share of time the smoothed acceleration deviates more than 0.2 g from its resting value.")
m3.metric("PPG heart-rate error vs ECG", f"{np.median(A['err']):.1f} bpm" if A["err"].size else "n/a", border=True,
          help="Median over 5-second windows of |HR from PPG peaks − HR from ECG R peaks|. A simple peak picker, "
               "no motion correction.")
st.markdown("**How to read it:** when a disturbance appears in the PPG or ECG **at the same moment** as the "
            "accelerometer moves, it is most likely a motion artefact, not a real change in the heart. Wearables "
            "use exactly this logic to reject or correct bad stretches of signal.")

# ------------------------------------------------------------ 2. interference playground
st.header("Interference playground", anchor=False)
st.markdown("Start from a clean ECG (BIOPAC MP36, lying still) and add the classic disturbances, then try the "
            "standard filters. This is the same problem the **stress-test bench** measures systematically.")

cebs = L.load("cebs_rest")
fs = cebs["fs"]
seg = slice(40 * fs, 48 * fs)
clean = L.bandpass(cebs["lead_I"], 0.5, 100, fs)[seg]
t = np.arange(clean.size) / fs


@st.cache_data(show_spinner=False)
def em_noise(n: int, fs_out: int) -> np.ndarray:
    em = load_record("nstdb", "em").signal[: 360 * 30, 0].astype(float)
    x = sps.resample_poly(em, fs_out, 360)[:n]
    return (x - x.mean()) / x.std()


c1, c2 = st.columns([1, 1.1], gap="large")
with c1:
    st.markdown("**Add interference**")
    mains_f = st.segmented_control("Mains frequency", [50, 60], default=50, required=True, wrap=True, key="mo_mf",
                                   format_func=lambda f: f"{f} Hz · " + ("Europe (your lab)" if f == 50 else "USA"))
    mains = st.slider("Mains hum (mV)", 0.0, 0.5, 0.15, 0.01, key="mo_mains",
                      help="Electric fields from cables and lights couple into the body and the leads.")
    bw = st.slider("Baseline wander (mV)", 0.0, 1.5, 0.5, 0.05, key="mo_bw",
                   help="Slow drift from breathing, sweating or changing electrode contact.")
    emg = st.slider("Muscle noise (mV)", 0.0, 0.3, 0.0, 0.01, key="mo_emg",
                    help="Electrical activity of skeletal muscles (shivering, tensing). Broadband.")
    em = st.slider("Electrode motion, real recording (mV)", 0.0, 0.8, 0.0, 0.05, key="mo_em",
                   help="Recorded electrode-motion artefact from the MIT-BIH Noise Stress Test Database.")
with c2:
    st.markdown("**Filter it**")
    hp = st.toggle("High-pass 0.5 Hz (removes baseline wander)", value=False, key="mo_hp")
    notch = st.toggle(f"Notch at {mains_f} Hz (removes mains hum)", value=False, key="mo_notch")
    lp = st.toggle("Low-pass 40 Hz (smooths muscle noise)", value=False, key="mo_lp")
    st.caption("Notice which disturbance each filter removes, and which one **no** filter removes: electrode motion "
               "shares the ECG's frequencies.")

rng = np.random.default_rng(7)
noise = (mains * np.sin(2 * np.pi * mains_f * t + 0.3) + bw * np.sin(2 * np.pi * 0.3 * t) + 0.4 * bw * np.sin(2 * np.pi * 0.11 * t + 1)
         + emg * L.bandpass(rng.standard_normal(t.size), 20, 150, fs) / 0.35
         + em * em_noise(t.size, fs))
x = clean + noise
y = x.copy()
if hp:
    y = sps.filtfilt(*sps.butter(2, 0.5, btype="high", fs=fs), y)
if notch:
    y = sps.filtfilt(*sps.iirnotch(mains_f, 30, fs=fs), y)
if lp:
    y = sps.filtfilt(*sps.butter(4, 40, btype="low", fs=fs), y)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                    subplot_titles=["What the electrodes pick up", "After your filters"])
fig.add_trace(go.Scatter(x=t, y=clean, line=dict(color=tk["clean"], width=1), name="Clean ECG", hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=t, y=x, line=dict(color=tk["noise"], width=1.1), name="Recorded", hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=t, y=clean, line=dict(color=tk["clean"], width=1), showlegend=False, hoverinfo="skip"), 2, 1)
fig.add_trace(go.Scatter(x=t, y=y, line=dict(color=tk["trace"], width=1.3), name="Filtered", hoverinfo="skip"), 2, 1)
base_layout(fig, height=460)
ecg_grid(fig, row=1, col=1, span_mv=float(np.ptp(x)))
ecg_grid(fig, row=2, col=1, span_mv=float(np.ptp(y)))
fig.update_xaxes(title_text="Time (s)", row=2, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG with added interference, before and after filtering")
err = np.sqrt(np.mean((y - y.mean() - (clean - clean.mean())) ** 2)) * 1000
st.metric("Remaining error vs the clean ECG", f"{err:.0f} µV RMS", border=True,
          help="Root-mean-square difference between the filtered signal and the original clean ECG.")
with st.container(horizontal=True):
    st.page_link("app_pages/noise_lab.py", label="Open the full noise lab", icon=":material/graphic_eq:")
    st.page_link("app_pages/benchmark.py", label="See how detectors cope", icon=":material/query_stats:")

# ------------------------------------------------------------ 3. smartwatch
with st.container(border=True):
    st.subheader(":material/watch: Putting it together: a smartwatch", anchor=False)
    st.markdown(
        "- **Green-light PPG** on the back of the wrist for routine heart rate.\n"
        "- **Accelerometer and gyroscope** to know when you move, so motion-corrupted PPG can be rejected or "
        "corrected, and to count steps.\n"
        "- An **electrical ECG** on demand: one electrode on the back of the watch, one in the crown you touch with "
        "the other hand. Two contact points → one voltage difference across the body, a **single-lead** ECG "
        "(similar in direction to Lead I).\n\n"
        "Same physics as the BIOPAC lab, squeezed into a wrist.")

L.key_idea("If a disturbance in the PPG or ECG lines up with movement in the accelerometer, suspect a motion "
           "artefact. Mains hum and baseline wander can be filtered away; electrode-motion artefact overlaps the "
           "ECG's own frequencies and cannot.")
L.source_note("ptt_sit", "ptt_walk", "ptt_run", "cebs_rest")
L.chapter_nav(PATH)
