import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.signal import hilbert, resample_poly

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, is_dark, tokens

PATH = "app_pages/learn_cardiac_cycle.py"
L.chapter_header(PATH, "Heart, valves and sounds",
                 "The ECG is electrical. What it triggers is mechanical: chambers squeeze, valves open and close, "
                 "blood moves. Heart sounds are the noise of the valves **closing**.")
tk = tokens()

# ------------------------------------------------------------ 1. circulation
st.header("Two loops, four chambers", anchor=False)
c1, c2 = st.columns([1.35, 1], gap="large", vertical_alignment="center")
with c2:
    labels = [s[1] for s in L.FLOW_STEPS]
    pick = st.radio("Follow the blood", labels, key="cc_flow")
    k = labels.index(pick)
    st.markdown(L.FLOW_STEPS[k][2])
    pulm = k in (1, 2, 3)
    st.badge("Pulmonary loop" if pulm else "Systemic loop", color="blue" if pulm else "red", icon=":material/sync:")
    st.caption("Pulmonary: right heart → lungs → left heart." if pulm else
               "Systemic: left heart → body → right heart.")
with c1:
    st.image(L.circulation_svg(L.FLOW_STEPS[k][0], is_dark()), width="stretch",
             alt="Schematic heart with the current step of blood flow highlighted")
st.caption("Drawn as if you face the person: their right heart is on your left. Valves open only when the pressure "
           "behind them is higher than the pressure in front of them. They are passive one-way doors.")

# ------------------------------------------------------------ 2. cardiac cycle model
st.header("One cardiac cycle, step by step", anchor=False)
st.markdown("This is a **simplified model of the left heart** (a Wiggers diagram). Nothing about the valves is "
            "scripted: each valve is open exactly when the pressure behind it is higher. Move the cursor and watch "
            "the valves follow the pressures.")
c1, c2 = st.columns([1, 3], vertical_alignment="bottom")
hr = c1.slider("Heart rate (bpm)", 50, 150, 70, step=5, key="cc_hr")
cyc = L.cardiac_cycle(float(hr))
ms_max = int(cyc.t[-1] * 1000)
cur = c2.slider("Time in the beat (ms, from the P wave)", 0, ms_max, int((cyc.s1 + 0.04) * 1000), step=5, key=f"cc_t_{hr}")
i = min(cur, cyc.t.size - 1)  # model runs at 1 kHz: index = ms

mit, aor = bool(cyc.mitral_open[i]), bool(cyc.aortic_open[i])
ti = cyc.t[i]
if aor:
    phase = ("Ejection", "The aortic valve is open: the ventricle pushes blood into the aorta. Volume falls.")
elif mit:
    phase = (("Atrial contraction", "The atria squeeze (after the P wave) and top up the ventricle.")
             if 0.03 <= ti <= 0.17 else
             ("Filling", "The mitral valve is open: blood flows from the atrium into the relaxed ventricle."))
elif ti < cyc.s2:
    phase = ("Isovolumic contraction", "Both valves are shut. The ventricle squeezes, pressure shoots up, but the "
             "volume cannot change yet.")
else:
    phase = ("Isovolumic relaxation", "Both valves are shut again. The ventricle relaxes and pressure falls until "
             "it drops below the atrium and the mitral valve reopens.")

st.markdown(f"#### {phase[0]}")
st.markdown(phase[1])
m1, m2, m3, m4 = st.columns(4)
m1.metric("Mitral valve", "Open" if mit else "Closed", border=True,
          help="Between left atrium and left ventricle (an AV valve, like the tricuspid on the right).")
m2.metric("Aortic valve", "Open" if aor else "Closed", border=True,
          help="Between left ventricle and aorta (a semilunar valve, like the pulmonary valve on the right).")
m3.metric("LV pressure", f"{cyc.lv[i]:.0f} mmHg", border=True)
m4.metric("LV volume", f"{cyc.vol[i]:.0f} mL", border=True)

tt = cyc.t * 1000
fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.18, 0.42, 0.22, 0.18],
                    subplot_titles=["ECG (schematic)", "Pressure (mmHg)", "Left-ventricle volume (mL)",
                                    "Heart sounds"])
fig.add_trace(go.Scatter(x=tt, y=cyc.ecg, line=dict(color=tk["trace"], width=2), hoverinfo="skip",
                         showlegend=False), 1, 1)
fig.add_trace(go.Scatter(x=tt, y=cyc.ao, name="Aorta", line=dict(color=tk["fp"], width=2.2)), 2, 1)
fig.add_trace(go.Scatter(x=tt, y=cyc.lv, name="Left ventricle", line=dict(color=tk["trace"], width=2.2)), 2, 1)
fig.add_trace(go.Scatter(x=tt, y=cyc.la, name="Left atrium", line=dict(color=tk["tp"], width=2, dash="dash")), 2, 1)
fig.add_trace(go.Scatter(x=tt, y=cyc.vol, name="Volume", line=dict(color=tk["noise"], width=2.2), showlegend=False), 3, 1)
rng = np.random.default_rng(1)
snd = np.zeros_like(tt)
for ts, amp in ((cyc.s1, 1.0), (cyc.s2, 0.7)):
    env = np.exp(-((cyc.t - ts - 0.02) / 0.018) ** 2)
    snd += amp * env * np.sin(2 * np.pi * 60 * cyc.t) * (0.7 + 0.3 * rng.standard_normal(tt.size))
fig.add_trace(go.Scatter(x=tt, y=snd, line=dict(color=tk["muted"], width=1), hoverinfo="skip", showlegend=False), 4, 1)
for ts, lab in ((cyc.s1, "S1 “lub”"), (cyc.s2, "S2 “dub”")):
    fig.add_annotation(x=ts * 1000 + 20, y=1.2, text=lab, showarrow=False, row=4, col=1, font=dict(size=12))
# shade valve-open periods
for mask, col, row in ((cyc.aortic_open, tk["noisy_shade"], 2), (cyc.mitral_open, tk["band"], 2)):
    on = np.flatnonzero(np.diff(np.r_[0, mask.astype(int), 0]))
    for s0, s1 in zip(on[::2], on[1::2]):
        fig.add_vrect(x0=tt[s0], x1=tt[min(s1, tt.size - 1)], fillcolor=col, line_width=0, layer="below", row=row, col=1)
fig.add_vline(x=cur, line=dict(color=tk["noise"], width=2))
base_layout(fig, height=640, legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, title_text=""),
            margin=dict(l=8, r=8, t=70, b=8))
fig.update_yaxes(showticklabels=False, row=1, col=1)
fig.update_yaxes(showticklabels=False, row=4, col=1)
fig.update_xaxes(title_text="Time in the beat (ms) · shaded in the pressure panel: blue-grey = mitral open, "
                            "orange = aortic open", row=4, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="Simplified Wiggers diagram of the left heart")
st.caption(f"Model at {hr} bpm: S1 at R + {(cyc.s1 - cyc.r) * 1000:.0f} ms, S2 at R + {(cyc.s2 - cyc.r) * 1000:.0f} ms, "
           f"stroke volume ≈ {cyc.vol.max() - cyc.vol.min():.0f} mL, aortic pressure ≈ {cyc.ao.max():.0f}/{cyc.ao.min():.0f} "
           "mmHg. Schematic only; real curves differ between people. The right heart does the same with about "
           "one fifth of the pressure.")

# ------------------------------------------------------------ 3. real heart sounds
st.header("Listen: real heart sounds with ECG", anchor=False)


@st.cache_data(show_spinner=False)
def sounds():
    h = L.load("pcg")
    hfs = h["fs"]
    pcg = h["pcg"].astype(float)
    ecg = h["ecg"].astype(float)
    rp = L.r_peaks(ecg, hfs)
    env = np.abs(hilbert(pcg))
    s1, s2 = [], []
    for r in rp:
        if r + int(0.5 * hfs) < pcg.size:
            s1.append(r + int(np.argmax(env[r:r + int(0.15 * hfs)])))
            s2.append(r + int(0.22 * hfs) + int(np.argmax(env[r + int(0.22 * hfs):r + int(0.5 * hfs)])))
    audio = resample_poly(pcg, 4, 1)  # 2 kHz -> 8 kHz so every browser plays it
    return pcg, ecg, hfs, rp, np.array(s1), np.array(s2), audio / np.abs(audio).max() * 0.9


pcg, ecg_h, hfs, rp, s1, s2, audio = sounds()
st.audio(audio.astype(np.float32), sample_rate=8000)
st.caption("Use headphones: heart sounds are low-pitched (roughly 25–150 Hz) and laptop speakers barely play them.")
w = st.slider("Window start (s)", 0.0, float(pcg.size / hfs - 4), 2.0, step=0.5, key="cc_snd")
a, b = int(w * hfs), int((w + 4) * hfs)
t = np.arange(a, b) / hfs
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=["ECG (electrical)", "Phonocardiogram: heart sound (mechanical)"])
fig.add_trace(go.Scatter(x=t, y=ecg_h[a:b], line=dict(color=tk["trace"], width=1.5), hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=t, y=pcg[a:b], line=dict(color=tk["muted"], width=0.8), hoverinfo="skip"), 2, 1)
for arr, lab, col in ((s1, "S1", tk["noise"]), (s2, "S2", tk["fp"])):
    sel = arr[(arr >= a) & (arr < b)]
    fig.add_trace(go.Scatter(x=sel / hfs, y=np.full(sel.size, 1.05), mode="markers+text", text=[lab] * sel.size,
                             textposition="top center", marker=dict(color=col, size=9, symbol="triangle-down"),
                             hoverinfo="skip"), 2, 1)
for r in rp[(rp >= a) & (rp < b)]:
    fig.add_vline(x=r / hfs, line=dict(color=tk["muted"], width=1, dash="dot"))
base_layout(fig, height=420, showlegend=False)
fig.update_yaxes(showticklabels=False)
fig.update_yaxes(range=[-1.1, 1.35], row=2, col=1)
fig.update_xaxes(title_text="Time (s) · dotted lines = R peaks", row=2, col=1)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG and heart sounds with S1 and S2 marked")
d1 = np.median([(x - r) for x, r in zip(s1, rp)]) / hfs * 1000
d2 = np.median([(x - r) for x, r in zip(s2, rp)]) / hfs * 1000
m1, m2, m3 = st.columns(3)
m1.metric("R peak → S1", f"{d1:.0f} ms", border=True, help="Ventricles start contracting; AV valves close.")
m2.metric("R peak → S2", f"{d2:.0f} ms", border=True, help="End of ejection; semilunar valves close.")
m3.metric("Heart rate", f"{60 * hfs / np.median(np.diff(rp)):.0f} bpm", border=True)

L.key_idea("S1 “lub” = mitral + tricuspid (AV) valves close as the ventricles start to contract, just after the QRS. "
           "S2 “dub” = aortic + pulmonary (semilunar) valves close as the ventricles relax, near the end of the "
           "T wave. Electrical event first, mechanical sound after.")
L.source_note("pcg")
L.chapter_nav(PATH)
