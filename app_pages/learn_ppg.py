import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import signal as sps

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, tokens

PATH = "app_pages/learn_ppg.py"
L.chapter_header(PATH, "PPG: the pulse you can see with light",
                 "A **photoplethysmogram (PPG)** shines light into the skin and measures how much comes back. With "
                 "every heartbeat a pulse of blood arrives, the tissue holds more blood, absorbs more light, and the "
                 "signal changes. It is **optical and mechanical**, a consequence of the heartbeat, not its electricity.")
tk = tokens()


@st.cache_data(show_spinner=False)
def per_beat(act: str):
    """Per-beat pulse arrival time (R peak → PPG foot), PPG peak times and amplitudes."""
    d = L.load(f"ptt_{act}")
    fs = d["fs"]
    ppg = L.bandpass(d["ppg_ir"], 0.4, 10, fs)
    ecg = L.bandpass(d["ecg"], 0.5, 40, fs)
    rows = []
    for r0, r1 in zip(d["beats"][:-1], d["beats"][1:]):
        seg = ppg[r0:r1]
        if seg.size < int(0.35 * fs):
            continue
        d1 = np.gradient(seg)
        up = int(np.argmax(d1[int(0.08 * fs):int(0.45 * fs)])) + int(0.08 * fs)
        mn = int(np.argmin(seg[:up])) if up else 0
        foot = int(np.clip(up - (seg[up] - seg[mn]) / max(d1[up], 1e-9), 0, up))
        pk = up + int(np.argmax(seg[up:up + int(0.25 * fs)]))
        rows.append((r0, r0 + foot, r0 + pk, foot / fs * 1000, seg[pk] - seg[mn]))
    arr = np.array(rows)
    return {"fs": fs, "ppg": ppg, "ecg": ecg, "r": arr[:, 0].astype(int), "foot": arr[:, 1].astype(int),
            "peak": arr[:, 2].astype(int), "pat": arr[:, 3], "amp": arr[:, 4], "beats": d["beats"]}


@st.cache_data(show_spinner=False)
def avg_pulses():
    d = L.load("ptt_sit")
    fs = d["fs"]
    out = {}
    for k in ("ppg_red", "ppg_ir", "ppg_green"):
        x = L.ensemble(L.bandpass(d[k], 0.4, 10, fs), d["beats"], 0, int(0.85 * fs))
        out[k] = (x - x.min()) / (x.max() - x.min())
    return out, fs


# ------------------------------------------------------------ 1. anatomy of a pulse
st.header("Anatomy of one pulse", anchor=False)
pulses, fs = avg_pulses()
lm = L.ppg_landmarks(pulses["ppg_ir"], fs)
FEATS = {
    "Pulse arrival (foot)": (lm.foot, "The pressure wave reaches the finger and blood volume starts to rise."),
    "Systolic upstroke": (lm.upstroke, "The steepest rise: blood rushing in while the heart is still ejecting."),
    "Systolic peak": (lm.peak, "Maximum blood volume in the fingertip during this beat."),
    "Dicrotic notch": (lm.notch, "A small dip/kink: linked to the aortic valve closing and the pressure wave "
                                 "reflecting back from the periphery."),
    "Diastolic runoff": (lm.diastolic, "Blood drains away while the heart refills, until the next pulse arrives."),
}
c1, c2 = st.columns([2, 1], gap="large")
with c1:
    pick = st.pills("Feature", list(FEATS), default="Systolic peak", required=True, wrap=True, key="pp_feat")
    t = np.arange(pulses["ppg_ir"].size) / fs * 1000
    fig = go.Figure(go.Scatter(x=t, y=pulses["ppg_ir"], line=dict(color=tk["fp"], width=3),
                               hovertemplate="%{x:.0f} ms after R<extra></extra>"))
    for name, (i, _) in FEATS.items():
        active = name == pick
        fig.add_trace(go.Scatter(x=[t[i]], y=[pulses["ppg_ir"][i]], mode="markers+text",
                                 text=[name] if active else [""], textposition="top right",
                                 marker=dict(size=14 if active else 8, color=tk["noise"] if active else tk["muted"]),
                                 hoverinfo="skip"))
    fig.add_vline(x=0, line=dict(color=tk["trace"], dash="dot"), annotation_text="ECG R peak", annotation_position="top")
    base_layout(fig, height=340, showlegend=False)
    fig.update_xaxes(title_text="Time after the ECG R peak (ms)")
    fig.update_yaxes(title_text="Blood volume (normalized)", showticklabels=False)
    st.plotly_chart(fig, config=PLOT_CONFIG, alt="Averaged PPG pulse with its features")
with c2:
    st.markdown(f"**{pick}**")
    st.markdown(FEATS[pick][1])
    st.metric("Time after R peak", f"{FEATS[pick][0] / fs * 1000:.0f} ms", border=True)
    st.caption("Average of all pulses while sitting, infrared light. The sensor's raw signal goes *down* when blood "
               "arrives (more absorption); like most devices we flip it so the pulse points up.")

with st.expander("Red, infrared, green: why devices use different colours", icon=":material/palette:"):
    g = go.Figure()
    for k, col, lab in (("ppg_green", "#2A8C82", "Green 537 nm"), ("ppg_red", tk["fp"], "Red 660 nm"),
                        ("ppg_ir", tk["muted"], "Infrared 880 nm")):
        g.add_trace(go.Scatter(x=t, y=pulses[k], name=lab, line=dict(color=col, width=2)))
    base_layout(g, height=260)
    g.update_xaxes(title_text="ms after R peak")
    g.update_yaxes(showticklabels=False)
    st.plotly_chart(g, config=PLOT_CONFIG, alt="PPG pulse at three wavelengths")
    st.markdown("**Green** light stays near the surface and copes better with movement, so wrist devices such as the "
                "Apple Watch use it for routine heart rate. **Red and infrared** go deeper; comparing the two is how "
                "pulse oximeters estimate blood oxygen. Same heartbeat, slightly different shapes.")

# ------------------------------------------------------------ 2. ECG then PPG
st.header("ECG first, PPG later", anchor=False)
st.markdown("The R peak is electrical and travels instantly through the body. The PPG has to wait for the "
            "ventricles to contract, the aortic valve to open, and the pressure wave to travel down the arm to the "
            "finger. That delay is the **pulse arrival time (PAT)**.")
sit = per_beat("sit")
fs = sit["fs"]
w0 = st.slider("Window start (s)", 0, 110, 10, key="pp_win")
a, b = w0 * fs, (w0 + 5) * fs
tt = np.arange(a, b) / fs
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=["ECG (electrical)", "Finger PPG (optical)"])
fig.add_trace(go.Scatter(x=tt, y=sit["ecg"][a:b], line=dict(color=tk["trace"], width=1.5), hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=tt, y=sit["ppg"][a:b], line=dict(color=tk["fp"], width=2), hoverinfo="skip"), 2, 1)
sel = (sit["r"] >= a) & (sit["foot"] < b)
for r, f, pat in zip(sit["r"][sel], sit["foot"][sel], sit["pat"][sel]):
    fig.add_vline(x=r / fs, line=dict(color=tk["trace"], width=1, dash="dot"))
    fig.add_trace(go.Scatter(x=[f / fs], y=[sit["ppg"][f]], mode="markers", marker=dict(color=tk["noise"], size=9),
                             hovertemplate=f"PAT {pat:.0f} ms<extra></extra>"), 2, 1)
    fig.add_annotation(x=(r + f) / 2 / fs, y=float(sit["ppg"][a:b].max()), text=f"{pat:.0f} ms", showarrow=False,
                       row=2, col=1, font=dict(size=11, color=tk["noise"]))
base_layout(fig, height=420, showlegend=False)
fig.update_yaxes(showticklabels=False)
fig.update_xaxes(title_text="Time (s) · dotted = R peak, dot = PPG pulse arrival", row=2, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG and PPG with pulse arrival times")

walk = per_beat("walk")
c1, c2 = st.columns([1.4, 1], gap="large")
with c1:
    h = go.Figure()
    for d, lab, col in ((sit, "Sitting", tk["trace"]), (walk, "Walking", tk["noise"])):
        ok = (d["pat"] > 120) & (d["pat"] < 400)
        h.add_trace(go.Histogram(x=d["pat"][ok], name=f"{lab} (median {np.median(d['pat'][ok]):.0f} ms)",
                                 marker_color=col, opacity=0.65, xbins=dict(size=4)))
    base_layout(h, height=280, barmode="overlay")
    h.update_xaxes(title_text="Pulse arrival time per beat (ms)")
    h.update_yaxes(title_text="beats")
    st.plotly_chart(h, config=PLOT_CONFIG, alt="Histogram of pulse arrival times, sitting vs walking")
with c2:
    st.markdown("**Pulse arrival vs pulse transit**")
    st.markdown("PAT = **pre-ejection period** (R peak → aortic valve opens) + **pulse transit time** (heart → "
                "finger). When the heart beats harder and faster, both get shorter, so PAT drops during activity. "
                "That is why PAT and transit time are studied for cuff-less blood-pressure estimation.")

# ------------------------------------------------------------ 3. HR from PPG
st.header("Heart rate from PPG", anchor=False)
pk = sit["peak"]
hr_ppg = 60 * fs / np.diff(pk)
hr_ecg = 60 * fs / np.diff(sit["r"])
diff = hr_ppg - hr_ecg
c1, c2 = st.columns([2, 1], gap="large")
with c1:
    f2 = go.Figure()
    f2.add_trace(go.Scatter(x=sit["r"][1:] / fs, y=hr_ecg, name="From ECG R-R", line=dict(color=tk["trace"], width=2)))
    f2.add_trace(go.Scatter(x=pk[1:] / fs, y=hr_ppg, name="From PPG peak-to-peak",
                            line=dict(color=tk["fp"], width=2, dash="dash")))
    base_layout(f2, height=280)
    f2.update_xaxes(title_text="Time (s)")
    f2.update_yaxes(title_text="bpm")
    st.plotly_chart(f2, config=PLOT_CONFIG, alt="Heart rate from ECG and from PPG")
with c2:
    st.metric("Mean HR from ECG", f"{hr_ecg.mean():.1f} bpm", border=True)
    st.metric("Mean HR from PPG", f"{hr_ppg.mean():.1f} bpm", border=True,
              delta=f"{hr_ppg.mean() - hr_ecg.mean():+.1f} bpm", delta_color="off")
    st.caption(f"Beat by beat they differ by {np.abs(diff).mean():.1f} bpm on average: the transit time wobbles a "
               "little from beat to beat, but the **rhythm is the same**, which is why a watch can count your pulse "
               "with light alone.")

# ------------------------------------------------------------ 4. breathing in the PPG
st.header("Breathing is hiding in the PPG", anchor=False)
amp = sit["amp"]
tb = sit["peak"] / fs
base = L.bandpass(L.load("ptt_sit")["ppg_ir"], 0.05, 0.6, fs)
f, p = sps.welch(amp - amp.mean(), fs=1 / np.median(np.diff(tb)), nperseg=min(64, amp.size))
band = (f > 0.1) & (f < 0.5)
br = f[band][np.argmax(p[band])] * 60
f3 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                   subplot_titles=["Pulse amplitude, beat by beat", "Slow baseline of the PPG"])
f3.add_trace(go.Scatter(x=tb, y=amp, mode="lines+markers", line=dict(color=tk["fp"], width=1.5),
                        marker=dict(size=4), hoverinfo="skip"), 1, 1)
f3.add_trace(go.Scatter(x=np.arange(base.size)[::25] / fs, y=base[::25], line=dict(color=tk["tp"], width=2),
                        hoverinfo="skip"), 2, 1)
base_layout(f3, height=380, showlegend=False)
f3.update_yaxes(showticklabels=False)
f3.update_xaxes(title_text="Time (s)", row=2, col=1)
st.plotly_chart(f3, config=PLOT_CONFIG, alt="PPG amplitude and baseline modulated by breathing")
st.markdown(f"Both traces rise and fall slowly, at about **{br:.0f} cycles per minute**, a typical breathing rate. "
            "Breathing changes the pressure in the chest, which changes **venous return**, how much blood the "
            "heart ejects (**stroke volume**) and how much blood sits in the fingertip. So the PPG's height and "
            "baseline breathe along with you. (This recording has no respiration belt, so the breathing is "
            "inferred from the PPG itself.)")

L.key_idea("PPG = optical measurement of blood-volume changes. Each pulse arrives a couple of hundred milliseconds "
           "after the ECG R peak (pulse arrival time). PPG and ECG give the same heart rate, and breathing slowly "
           "modulates the PPG's amplitude and baseline.")
L.source_note("ptt_sit", "ptt_walk")
L.chapter_nav(PATH)
