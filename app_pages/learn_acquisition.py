import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy import signal as sps

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, tokens

PATH = "app_pages/learn_acquisition.py"
L.chapter_header(PATH, "How signals are recorded",
                 "In class the BIOPAC MP36 showed a **Data Acquisition Settings** window with a sampling rate of "
                 "2 kHz and calculation channels such as “ECG R-R Interval”. This chapter is about what those "
                 "settings do: the signals-and-systems part of biosignals.")
tk = tokens()

# ------------------------------------------------------------ chain
STEPS = [(":material/sensors:", "Electrodes / sensor", "Skin contact turns ionic currents into a tiny voltage "
          "(about 1 mV)."),
         (":material/settings_input_component:", "Amplifier", "A differential amplifier boosts the *difference* "
          "between two electrodes and rejects what both share (such as mains hum)."),
         (":material/filter_alt:", "Analogue filters", "Band-limit the signal, e.g. 0.05–150 Hz for ECG, and remove "
          "anything above half the sampling rate."),
         (":material/memory:", "ADC", "Samples the voltage at a fixed rate and rounds each sample to a number."),
         (":material/monitor:", "Software", "Displays channels, applies digital filters, and computes calculation "
          "channels such as R-R interval and BPM.")]
for col, (ic, name, what) in zip(st.columns(len(STEPS), gap="small"), STEPS):
    with col:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**{ic} {name}**")
            st.caption(what)

cebs = L.load("cebs_rest")
fs0 = cebs["fs"]
seg = slice(60 * fs0, 62 * fs0)
x0 = L.bandpass(cebs["lead_I"], 0.5, 150, fs0)[seg]
t0 = np.arange(x0.size) / fs0

# ------------------------------------------------------------ sampling
st.header("Sampling rate: how often you look", anchor=False)
c1, c2 = st.columns([1, 2.2], gap="large")
with c1:
    fs_new = st.select_slider("Sampling rate", options=[25, 40, 60, 75, 100, 150, 250, 500], value=100,
                              key="aq_fs", format_func=lambda f: f"{f} Hz")
    aa = st.toggle("Anti-aliasing filter before sampling", value=True, key="aq_aa",
                   help="A low-pass filter below half the sampling rate, applied before the ADC.")
    hum = st.toggle("Add 50 Hz mains hum", value=False, key="aq_hum")
    st.metric("Nyquist frequency", f"{fs_new / 2:g} Hz", border=True,
              help="Half the sampling rate. Anything faster than this cannot be represented correctly.")
x = x0 + (0.12 * np.sin(2 * np.pi * 50 * t0) if hum else 0)
xin = sps.filtfilt(*sps.butter(4, 0.45 * fs_new, fs=fs0), x) if aa and fs_new < fs0 else x
step = fs0 / fs_new
idx = np.round(np.arange(0, x.size, step)).astype(int)
idx = idx[idx < x.size]
with c2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t0, y=x, name="Continuous signal", line=dict(color=tk["clean"], width=1.2)))
    fig.add_trace(go.Scatter(x=t0[idx], y=xin[idx], name=f"Samples at {fs_new} Hz", mode="lines+markers",
                             line=dict(color=tk["trace"], width=1.6), marker=dict(size=5)))
    base_layout(fig, height=340)
    ecg_grid(fig, span_mv=float(np.ptp(x)))
    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="mV")
    st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG sampled at the chosen rate")
r_true = x0.max()
r_samp = xin[idx].max()
note = f"The tallest sample reaches **{r_samp / r_true:.0%}** of the true R peak. "
if fs_new < 100:
    note += "The QRS lasts only about 0.1 s, so with this few samples per QRS its sharp peak is simply missed. "
if hum and fs_new < 100:
    alias = abs(50 - round(50 / fs_new) * fs_new)
    fake = f"a fake **{alias:g} Hz** wave" if alias else "a fake **constant offset** (0 Hz)"
    note += (f"The 50 Hz hum is above the Nyquist frequency, so it **folds back** and appears as {fake}"
             + (". That is why the anti-aliasing filter matters." if not aa else
                ", unless the anti-aliasing filter removes it first, as it does now."))
st.markdown(note + " BIOPAC's **2 kHz** in class is far above what an ECG needs, so even fast details are kept.")

# ------------------------------------------------------------ resolution
st.header("Resolution: how finely you measure", anchor=False)
c1, c2 = st.columns([1, 2.2], gap="large")
with c1:
    bits = st.slider("ADC resolution (bits)", 3, 16, 6, key="aq_bits")
    rng_mv = 10.0
    lsb = rng_mv / 2 ** bits
    st.metric("Smallest step (1 LSB)", f"{lsb * 1000:.1f} µV" if lsb < 1 else f"{lsb:.2f} mV", border=True,
              help="Input range (here 10 mV) divided by 2^bits.")
    st.caption(f"{2 ** bits:,} levels across a 10 mV input range. The MIT-BIH recordings used 11 bits (≈ 5 µV), "
               "the MP36 uses 24 bits.")
q = np.round(x0 / lsb) * lsb
with c2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t0, y=x0, name="True signal", line=dict(color=tk["clean"], width=1.2)))
    fig.add_trace(go.Scatter(x=t0, y=q, name=f"{bits}-bit samples", line=dict(color=tk["trace"], width=1.6, shape="hv")))
    base_layout(fig, height=320)
    fig.update_xaxes(title_text="Time (s)", range=[0.2, 1.4])
    fig.update_yaxes(title_text="mV")
    st.plotly_chart(fig, config=PLOT_CONFIG, alt="ECG quantized at the chosen ADC resolution")
st.markdown(f"Rounding error (quantization noise) here: **{np.std(q - x0) * 1000:.1f} µV RMS**. Below about 8 bits "
            "the small P and T waves turn into staircases.")

# ------------------------------------------------------------ calculation channels
st.header("Calculation channels", anchor=False)
st.markdown("BIOPAC's **“ECG R-R Interval”** channel is not measured by any sensor: the software finds each R peak "
            "and writes the time since the previous one, as a new channel that updates once per beat. A **BPM** "
            "channel is simply 60 / RR. Chapter 2 shows exactly this, computed from a real BIOPAC recording.")
st.page_link("app_pages/learn_heart_rate.py", label="See the R-R calculation channel in chapter 2",
             icon=":material/arrow_forward:")

L.key_idea("Sample at least twice the highest frequency in the signal (Nyquist), and filter out everything above "
           "that first, or it aliases into fake slow waves. Enough bits keep small waves from becoming staircases. "
           "Derived channels such as R-R interval and BPM are computed, not measured.")
L.source_note("cebs_rest")
L.chapter_nav(PATH)
