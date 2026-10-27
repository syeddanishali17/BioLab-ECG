import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.signal import hilbert

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, tokens

PATH = "app_pages/learn_start.py"
L.chapter_header(PATH, "One heartbeat, five sensors",
                 "In class, BIOPAC Student Lab showed several channels stacked on one time axis: respiration, ECG, "
                 "later PPG and an accelerometer. This chapter does the same with real recordings, so you can see "
                 "**which sensor measures what, and in which order things happen** during a single heartbeat.")

if not L.available():
    st.warning("Learning data missing. Run `python scripts/build_learning_data.py`.", icon=":material/hourglass_empty:")
    st.stop()

SENSORS = [
    (":material/ecg:", "ECG", "Electrical", "Voltage difference between two electrodes on the skin, caused by the "
     "heart's electrical activation.", "mV"),
    (":material/stethoscope:", "Heart sounds", "Acoustic", "Vibrations when the heart valves snap "
     "shut: S1 “lub”, S2 “dub”.", "a.u."),
    (":material/fingerprint:", "PPG", "Optical", "Light through the fingertip: more blood in the tissue means "
     "less light comes back. Shows the arriving pulse.", "a.u."),
    (":material/pulmonology:", "Respiration", "Mechanical", "A stretch band around the chest: it expands when "
     "you breathe in.", "a.u."),
    (":material/directions_run:", "Accelerometer", "Motion", "Acceleration along X, Y, Z. Tells you when the "
     "body or the sensor moved.", "g"),
]
for col, (icon, name, kind, what, unit) in zip(st.columns(len(SENSORS), gap="small"), SENSORS):
    with col:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**{icon} {name}**")
            st.badge(kind, color="gray")
            st.caption(what)


@st.cache_data(show_spinner=False)
def one_beat():
    """Ensemble-averaged beat from each recording, aligned at its own R peak (t = 0)."""
    p = L.load("ptt_sit")
    fs = p["fs"]
    pre, post = int(0.25 * fs), int(0.75 * fs)
    ecg = L.ensemble(L.bandpass(p["ecg"], 0.5, 40, fs), p["beats"], pre, post)
    ppg = L.ensemble(L.bandpass(p["ppg_ir"], 0.4, 10, fs), p["beats"], pre, post)
    acc = L.ensemble(np.linalg.norm(np.c_[p["a_x"], p["a_y"], p["a_z"]], axis=1), p["beats"], pre, post)
    lm = L.ppg_landmarks(ppg[pre:], fs)
    h = L.load("pcg")
    hfs = h["fs"]
    rp = L.r_peaks(h["ecg"], hfs)
    env = np.abs(hilbert(h["pcg"].astype(float)))
    hpre, hpost = int(0.25 * hfs), int(0.75 * hfs)
    snd = L.ensemble(h["pcg"].astype(float), rp, hpre, hpost)
    senv = L.ensemble(env, rp, hpre, hpost)
    s1 = np.argmax(senv[hpre:hpre + int(0.15 * hfs)]) / hfs
    s2 = (int(0.2 * hfs) + np.argmax(senv[hpre + int(0.2 * hfs):hpre + int(0.5 * hfs)])) / hfs
    cyc = L.cardiac_cycle(60 * fs / float(np.median(np.diff(p["beats"]))))
    ejection = float(cyc.t[np.flatnonzero(cyc.aortic_open)[0]] - cyc.r)
    return {
        "t": (np.arange(pre + post) - pre) / fs, "ecg": ecg, "ppg": ppg, "acc": acc - np.median(acc),
        "th": (np.arange(hpre + hpost) - hpre) / hfs, "snd": snd / np.abs(snd).max(),
        "s1": float(s1), "s2": float(s2), "foot": lm.foot / fs, "ppg_peak": lm.peak / fs, "ejection": ejection,
        "hr": 60 * fs / float(np.median(np.diff(p["beats"]))),
    }


b = one_beat()
EVENTS = [
    ("R peak: electrical activation", 0.0, "ecg",
     "The **QRS complex** is the electrical wave spreading through the ventricles (ventricular depolarization). "
     "The R peak is its tallest point. Nothing has moved yet: this is pure electricity."),
    ("S1: mitral and tricuspid valves close", b["s1"], "snd",
     f"About **{b['s1'] * 1000:.0f} ms** later the ventricles start to contract. Their pressure rises above the "
     "atria, so the **AV valves (mitral, tricuspid) snap shut**: the first heart sound, **S1 “lub”**."),
    ("Aortic valve opens: blood is ejected", b["ejection"], None,
     f"When ventricular pressure exceeds aortic pressure (about **{b['ejection'] * 1000:.0f} ms**, from the model in "
     "chapter 3), the aortic valve opens and blood is pushed into the aorta. A pressure wave starts to travel "
     "down the arteries."),
    ("Pulse arrives at the finger: PPG upstroke", b["foot"], "ppg",
     f"The pressure wave reaches the fingertip after about **{b['foot'] * 1000:.0f} ms**. Blood volume in the tissue "
     "rises, so the PPG goes up: the **systolic upstroke**. This delay from R peak to the PPG pulse is the **pulse "
     "arrival time**."),
    ("S2: aortic and pulmonary valves close", b["s2"], "snd",
     f"At about **{b['s2'] * 1000:.0f} ms** the ventricles relax, their pressure drops below the arteries, and the "
     "**semilunar valves (aortic, pulmonary) close**: the second heart sound, **S2 “dub”**. This is near the end "
     "of the T wave (ventricular repolarization)."),
]

with st.container(border=True):
    st.subheader("Step through one heartbeat", anchor=False)
    labels = [f"{i + 1}. {e[0]}" for i, e in enumerate(EVENTS)]
    pick = st.select_slider("Event", options=labels, value=labels[0], key="ls_event", label_visibility="collapsed")
    k = labels.index(pick)
    name, t_ev, row, text = EVENTS[k]

    tk = tokens()
    rows = [("ECG (electrical)", "ecg"), ("Heart sound (mechanical)", "snd"), ("Finger PPG (optical)", "ppg"),
            ("Accelerometer (motion)", "acc")]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=[r[0] for r in rows])
    fig.add_trace(go.Scatter(x=b["t"], y=b["ecg"], line=dict(color=tk["trace"], width=2), hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=b["th"], y=b["snd"], line=dict(color=tk["noise"], width=1), hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=b["t"], y=b["ppg"], line=dict(color=tk["fp"], width=2), hoverinfo="skip"), 3, 1)
    fig.add_trace(go.Scatter(x=b["t"], y=b["acc"], line=dict(color=tk["muted"], width=1.5), hoverinfo="skip"), 4, 1)
    for j, (_, t_j, _, _) in enumerate(EVENTS):
        active = j == k
        fig.add_vline(x=t_j, line=dict(color=tk["noise"] if active else tk["muted"], width=2.5 if active else 1,
                                       dash="solid" if active else "dot"), opacity=1 if active else 0.5)
    if t_ev > 0:
        fig.add_vrect(x0=0, x1=t_ev, fillcolor=tk["band"], line_width=0, layer="below")
    fig.add_annotation(x=t_ev, y=1.0, yref="paper", text=f"<b>{t_ev * 1000:.0f} ms</b>", showarrow=False,
                       yanchor="bottom", xanchor="left", xshift=6, font=dict(color=tk["noise"], size=12))
    base_layout(fig, height=560, showlegend=False, margin=dict(l=8, r=8, t=44, b=8))
    fig.update_yaxes(showticklabels=False)
    fig.update_yaxes(range=[-0.5, 0.5], row=4, col=1)  # fixed ±0.5 g: sitting still reads as flat
    fig.update_xaxes(title_text="Time after the R peak (s)", row=4, col=1, range=[-0.25, 0.75])
    st.plotly_chart(fig, config=PLOT_CONFIG, alt="One averaged heartbeat seen by ECG, heart sound, PPG and accelerometer")
    st.markdown(f"**{k + 1}. {name}.** {text}")

L.key_idea("Electrical activation → ventricular contraction → valves close (S1) → blood is ejected → the pressure "
           "wave travels → the PPG pulse arrives at the finger → valves close (S2). The ECG always comes first; "
           "mechanical and optical signals follow. The accelerometer stays flat here because the person sat still.")
st.caption(f"Each row is an average of all beats in the recording, aligned at its own R peak (heart rate here "
           f"{b['hr']:.0f} bpm). The heart-sound row comes from a different person, so its timing is typical, not "
           "identical.")
L.source_note("ptt_sit", "pcg")
L.chapter_nav(PATH)
