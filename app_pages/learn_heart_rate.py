import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, tokens

PATH = "app_pages/learn_heart_rate.py"
L.chapter_header(PATH, "Heart rate and breathing",
                 "Heart rate is not measured directly. It is **calculated** from the time between beats, the "
                 "**R-R interval**, just like BIOPAC's “ECG R-R Interval” calculation channel from class.")
tk = tokens()
cebs = L.load("cebs_rest")
fs = cebs["fs"]
beats = cebs["beats"]
ecg = L.bandpass(cebs["lead_I"], 0.5, 40, fs)

# ------------------------------------------------------------ 1. RR -> HR
st.header("From R-R interval to heart rate", anchor=False)
st.latex(r"\text{HR (beats per minute)} = \frac{60}{RR \text{ (seconds)}}")
c1, c2 = st.columns([3, 1.1], gap="large", vertical_alignment="bottom")
start = c1.slider("Window start (s)", 0, int(ecg.size / fs) - 8, 20, key="hr_start")
rr_in = c2.number_input("Try an R-R interval (ms)", 300, 2000, 850, step=50, key="hr_rr")
c2.metric("Heart rate", f"{60_000 / rr_in:.0f} bpm", border=True)

a, b = start * fs, (start + 8) * fs
bw = beats[(beats >= a) & (beats < b)]
t = np.arange(a, b) / fs
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06,
                    subplot_titles=["ECG (lead I) with R peaks", "Calculation channel: beat-by-beat heart rate"])
fig.add_trace(go.Scatter(x=t, y=ecg[a:b], line=dict(color=tk["trace"], width=1.6), hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=bw / fs, y=ecg[bw], mode="markers", marker=dict(color=tk["noise"], size=9),
                         hovertemplate="R peak at %{x:.2f} s<extra></extra>"), 1, 1)
top = float(ecg[a:b].max())
for r0, r1 in zip(bw[:-1], bw[1:]):
    rr = (r1 - r0) / fs
    fig.add_annotation(x=(r0 + r1) / 2 / fs, y=top * 1.18, text=f"{rr * 1000:.0f} ms<br><b>{60 / rr:.0f} bpm</b>",
                       showarrow=False, font=dict(size=11, color=tk["muted"]), row=1, col=1)
    fig.add_shape(type="line", x0=r0 / fs, x1=r1 / fs, y0=top * 1.05, y1=top * 1.05,
                  line=dict(color=tk["muted"], width=1), row=1, col=1)
allb = beats
hr_all = 60 * fs / np.diff(allb)
m = (allb[1:] >= a) & (allb[1:] < b)
fig.add_trace(go.Scatter(x=allb[1:][m] / fs, y=hr_all[m], mode="lines+markers", line=dict(shape="hv", color=tk["noise"]),
                         hovertemplate="%{y:.0f} bpm<extra></extra>"), 2, 1)
base_layout(fig, height=470, showlegend=False)
ecg_grid(fig, row=1, col=1, span_mv=float(np.ptp(ecg[a:b])))
fig.update_yaxes(range=[float(ecg[a:b].min()) - 0.1, top * 1.45], row=1, col=1, title_text="mV")
fig.update_yaxes(title_text="bpm", row=2, col=1)
fig.update_xaxes(title_text="Time (s)", row=2, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG strip with R-R intervals and the resulting heart rate")
st.caption("Notice that the heart rate is **not constant** even at rest: every interval is slightly different. "
           "Section 3 explains a big part of why.")

# ------------------------------------------------------------ 2. rest vs excited
st.header("Resting vs excited", anchor=False)
cA, cB = st.columns(2, gap="large")
with cA:
    st.markdown("**Real recordings, same person:** sitting vs walking on the spot.")


    @st.cache_data(show_spinner=False)
    def strips():
        out = {}
        for act in ("sit", "walk"):
            d = L.load(f"ptt_{act}")
            f = d["fs"]
            x = L.bandpass(d["ecg"], 0.5, 40, f)
            s0 = int(20 * f)
            bb = d["beats"]
            out[act] = (np.arange(5 * f) / f, x[s0:s0 + 5 * f], 60 * f / float(np.median(np.diff(bb))),
                        float(np.median(np.diff(bb))) / f * 1000)
        return out

    S = strips()
    g = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                      subplot_titles=[f"Sitting · {S['sit'][2]:.0f} bpm · RR {S['sit'][3]:.0f} ms",
                                      f"Walking · {S['walk'][2]:.0f} bpm · RR {S['walk'][3]:.0f} ms"])
    for i, act in enumerate(("sit", "walk"), start=1):
        g.add_trace(go.Scatter(x=S[act][0], y=S[act][1], line=dict(color=tk["trace"], width=1.4), hoverinfo="skip"), i, 1)
    base_layout(g, height=360, showlegend=False)
    g.update_yaxes(showticklabels=False)
    g.update_xaxes(title_text="Time (s)", row=2, col=1)
    st.plotly_chart(g, config=PLOT_CONFIG, alt="ECG while sitting and while walking")

with cB:
    st.markdown("**Simulated from a real beat template:** drag the heart rate.")
    hr_sim = st.slider("Heart rate (bpm)", 40, 180, 70, key="hr_sim")

    @st.cache_data(show_spinner=False)
    def template():
        pre, post = int(0.3 * fs), int(0.6 * fs)
        return L.ensemble(ecg, beats, pre, post), pre

    tpl, pre = template()
    rr_s = 60 / hr_sim
    n = int(6 * fs)
    sim = np.zeros(n)
    k = int(0.4 * fs)
    while k < n:
        # the QRS keeps its shape; the T wave comes a bit earlier at high rates (QT shortens)
        qt_scale = np.sqrt(rr_s / 0.86)
        seg = tpl.copy()
        tail = seg[pre + int(0.08 * fs):]
        idx = np.clip(np.arange(tail.size) / qt_scale, 0, tail.size - 1)
        seg[pre + int(0.08 * fs):] = np.interp(idx, np.arange(tail.size), tail)
        lo, hi = max(0, k - pre), min(n, k - pre + seg.size)
        sim[lo:hi] += seg[lo - (k - pre):hi - (k - pre)] - seg[0]
        k += int(rr_s * fs)
    h = go.Figure(go.Scatter(x=np.arange(n) / fs, y=sim, line=dict(color=tk["trace"], width=1.4), hoverinfo="skip"))
    base_layout(h, height=230, showlegend=False, margin=dict(l=8, r=8, t=10, b=8))
    ecg_grid(h, span_mv=float(np.ptp(sim)))
    h.update_xaxes(title_text="Time (s)")
    st.plotly_chart(h, config={"displayModeBar": False}, alt="Simulated ECG at the chosen heart rate")
    st.markdown(f"R-R interval = 60 / {hr_sim} = **{rr_s * 1000:.0f} ms**. As the rate goes up, the flat stretch "
                "between the T wave and the next P wave (when the heart fills) shrinks the most.")

# ------------------------------------------------------------ 3. breathing and RSA
st.header("Breathing changes the heart rate", anchor=False)
st.markdown("The respiration channel from class (a stretch band around the chest) changes **much more slowly** "
            "than the ECG: one breath takes several heartbeats. Watch the heart rate during each breath.")


@st.cache_data(show_spinner=False)
def rsa():
    resp = cebs["resp"].astype(float)
    hr = 60 * fs / np.diff(beats)
    tb = beats[1:] / fs
    t_all = np.arange(resp.size) / fs
    hri = np.interp(t_all, tb, hr)
    corr = float(np.corrcoef(resp[::10], hri[::10])[0, 1])
    rising = np.gradient(L.bandpass(resp, 0.05, 0.7, fs)) > 0
    from scipy.signal import find_peaks

    pk, _ = find_peaks(resp, distance=int(1.5 * fs), prominence=0.5)
    return resp, tb, hr, rising, corr, 60 / (np.median(np.diff(pk)) / fs)


resp, tb, hr, rising, corr, br = rsa()
w0 = st.slider("Window start (s)", 0, int(resp.size / fs) - 40, 30, key="hr_rsa")
a, b = w0 * fs, (w0 + 40) * fs
t = np.arange(a, b) / fs
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.32, 0.36, 0.32],
                    subplot_titles=["Respiration (chest band): up = inspiration", "ECG",
                                    "Heart rate, beat by beat"])
# shade inspiration (rising chest band)
ins = rising[a:b]
edges = np.flatnonzero(np.diff(ins.astype(int))) + 1
segs = np.split(np.arange(ins.size), edges)
for sgi in segs:
    if sgi.size and ins[sgi[0]]:
        for row in (1, 2, 3):
            fig.add_vrect(x0=t[sgi[0]], x1=t[sgi[-1]], fillcolor=tk["band"], line_width=0, layer="below", row=row, col=1)
fig.add_trace(go.Scatter(x=t, y=resp[a:b], line=dict(color=tk["tp"], width=2), hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=t, y=ecg[a:b], line=dict(color=tk["trace"], width=1), hoverinfo="skip"), 2, 1)
mm = (tb >= w0) & (tb < w0 + 40)
fig.add_trace(go.Scatter(x=tb[mm], y=hr[mm], mode="lines+markers", line=dict(color=tk["noise"], width=2),
                         hovertemplate="%{y:.0f} bpm<extra></extra>"), 3, 1)
base_layout(fig, height=520, showlegend=False)
fig.update_yaxes(showticklabels=False, row=1, col=1)
fig.update_yaxes(showticklabels=False, row=2, col=1)
fig.update_yaxes(title_text="bpm", row=3, col=1)
fig.update_xaxes(title_text="Time (s) · shaded = inspiration", row=3, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="Respiration, ECG and heart rate on one time axis")

m1, m2, m3 = st.columns(3)
m1.metric("Breathing rate", f"{br:.0f} /min", border=True)
m2.metric("Heart-rate range", f"{np.percentile(hr, 5):.0f}–{np.percentile(hr, 95):.0f} bpm", border=True,
          help="5th to 95th percentile over the whole recording, at rest.")
m3.metric("Breathing ↔ heart-rate correlation", f"{corr:+.2f}", border=True,
          help="Correlation between the chest-band signal and the beat-to-beat heart rate. Positive: the heart "
               "speeds up as the chest expands.")
st.markdown(
    "**Respiratory sinus arrhythmia (RSA):** heart rate rises during **inspiration** and falls during "
    "**expiration**. Breathing in lowers the pressure inside the chest, so more blood returns to the right heart "
    "(**venous return** increases), and the vagus nerve's braking effect on the heart eases off. Breathing out "
    "reverses both. RSA is normal and usually strongest in young, relaxed people; despite the name it is not a "
    "disease.")

L.key_idea("HR = 60 / RR. Shorter R-R interval = higher heart rate. At rest the heart rate still rises and falls "
           "with every breath (RSA), so a single R-R interval is never the whole story.")
L.source_note("cebs_rest", "ptt_sit", "ptt_walk")
L.chapter_nav(PATH)
