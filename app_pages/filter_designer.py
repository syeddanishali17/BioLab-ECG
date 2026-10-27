import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from bench.config import MIXED_RECORDS
from bench.filters import FilterSpec, apply, design, response
from ui import data
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, overline, tokens

tk = tokens()
overline("Signal processing · IIR and FIR", "fd")
st.title("Filter designer")
st.markdown("Design a pre-filter, see its frequency, phase and group-delay response, and what it does to "
            "a noisy ECG. Key point: **a causal filter delays every beat**, and that delay eats into the "
            "150 ms matching window.")

KINDS = {"highpass": "High-pass", "notch": "Notch", "bandpass": "Band-pass", "lowpass": "Low-pass"}
DEFAULTS = {"highpass": (0.5, None), "lowpass": (40.0, None), "bandpass": (5.0, 15.0), "notch": (60.0, None)}

with st.container(border=True):
    c1, c2, c3 = st.columns([1.6, 1.2, 1.2], vertical_alignment="bottom")
    kind = c1.segmented_control("Filter type", list(KINDS), default="highpass", required=True,
                                format_func=KINDS.get, wrap=True, key="fd_kind")
    family = c2.segmented_control("Family", ["iir", "fir"], default="iir", required=True, wrap=True, key="fd_family",
                                  format_func={"iir": "IIR Butterworth", "fir": "FIR (Hamming)"}.get,
                                  disabled=kind == "notch",
                                  help="IIR: few coefficients, non-linear phase. FIR: many coefficients, "
                                       "exactly linear phase (constant delay).")
    mode = c3.segmented_control("Application", ["zero", "causal"], default="causal", required=True,
                                wrap=True, key="fd_mode",
                                format_func={"zero": "Zero-phase (filtfilt)", "causal": "Causal (real-time)"}.get,
                                help="Zero-phase filters forward then backward: no delay, but needs the "
                                     "whole signal, so it is offline only. Causal is what a device can run live.")
    if kind == "notch":
        family = "iir"

    f1_def, f2_def = DEFAULTS[kind]
    d1, d2, d3 = st.columns(3, vertical_alignment="bottom")
    if kind == "bandpass":
        f1, f2 = d1.slider("Pass band (Hz)", 0.5, 60.0, (f1_def, f2_def), step=0.5, key="fd_band")
    else:
        lim = {"highpass": (0.1, 10.0), "lowpass": (5.0, 150.0), "notch": (45.0, 65.0)}[kind]
        f1 = d1.slider("Cut-off (Hz)" if kind != "notch" else "Notch frequency (Hz)", lim[0], lim[1], f1_def,
                       step=0.1 if kind == "highpass" else 0.5, key=f"fd_f1_{kind}")
        f2 = None
    if kind == "notch":
        q = d2.slider("Quality factor Q", 5.0, 60.0, 30.0, step=1.0, key="fd_q",
                      help="Higher Q: narrower notch, longer ringing.")
        order = 2
    elif family == "iir":
        order = d2.slider("Order", 1, 8, 2, key="fd_order")
        q = 30.0
    else:
        order = d2.slider("Taps", 31, 1501, 181 if kind != "highpass" else 721, step=10, key="fd_taps",
                          help="Low cut-offs need very long FIR filters. Delay = (taps − 1) / 2 samples.")
        q = 30.0
    rec = d3.selectbox("Test signal", [f"{r} + {n.upper()} @ 6 dB" for r in MIXED_RECORDS[:4] for n in ("bw", "ma", "em")],
                       key="fd_sig", help="Clean record plus a noise type at 6 dB SNR, from our mixer.")

spec = FilterSpec(kind=kind, family=family, f1=f1, f2=f2, order=order, q=q)
fs = 360.0
try:
    d = design(spec, fs)
except ValueError as e:
    st.error(f"Cannot design this filter: {e}", icon=":material/error:")
    st.stop()
r = response(d, zero_phase=(mode == "zero"))

fig = make_subplots(rows=1, cols=3, subplot_titles=["Magnitude (dB)", "Phase (degrees)", "Group delay (ms)"],
                    horizontal_spacing=0.07)
fig.add_trace(go.Scatter(x=r.f, y=r.mag_db, line=dict(color=tk["trace"], width=2), name="Magnitude"), 1, 1)
fig.add_trace(go.Scatter(x=r.f, y=r.phase_deg, line=dict(color=tk["tp"], width=2), name="Phase"), 1, 2)
fig.add_trace(go.Scatter(x=r.f, y=r.group_delay_ms, line=dict(color=tk["noise"], width=2), name="Group delay"), 1, 3)
for c in (1, 2, 3):
    fig.add_vrect(x0=5, x1=15, fillcolor=tk["band"], line_width=0, row=1, col=c)
    fig.update_xaxes(type="log", range=[np.log10(0.1), np.log10(180)], title_text="Hz", row=1, col=c)
fig.update_yaxes(range=[-60, 5], row=1, col=1)
fig.update_yaxes(tickformat=".0f", rangemode="tozero", row=1, col=3)
fig.update_yaxes(tickformat=".0f", row=1, col=2)
base_layout(fig, height=320, showlegend=False)
st.plotly_chart(fig, alt="Filter magnitude, phase and group delay", config=PLOT_CONFIG)
st.caption(f"{spec.label}. Shaded band: 5–15 Hz, where most QRS energy is."
           + (" Zero-phase: magnitude is squared, phase and delay are zero." if mode == "zero" else ""))

# Before / after on a real noisy ECG. Only a 62 s slice is filtered (fast even for long FIRs):
# 250-312 s covers a clean stretch for the delay measurement and the noise onset at 300 s.
rid, rest = rec.split(" + ")
noise = rest.split(" ")[0].lower()
x, ref, mask, _ = data.signal("mixed", rid, noise, 6.0)
s0, s1 = int(250 * fs), int(312 * fs)
xs = x[s0:s1].astype(np.float64)
cs = data.clean(rid)[0][s0:s1].astype(np.float64)
y = apply(d, xs, zero_phase=(mode == "zero"))
yc = apply(d, cs, zero_phase=(mode == "zero"))
# Measured beat delay: lag that best aligns filtered and original clean ECG (262-298 s, past transients)
m0, m1_ = int(12 * fs), int(48 * fs)
lags = np.arange(-int(0.3 * fs), int(0.3 * fs) + 1)
ref_seg = cs[m0:m1_] - cs[m0:m1_].mean()
scores = [np.dot(yc[m0 + k:m1_ + k] - yc[m0 + k:m1_ + k].mean(), ref_seg) for k in lags]
lag = lags[int(np.argmax(scores))]
delay_ms = lag / fs * 1000
gd_band = np.nanmedian(r.group_delay_ms[(r.f > 5) & (r.f < 15)]) if mode == "causal" else 0.0
m1, m2, m3 = st.columns(3)
m1.metric("Measured QRS delay", f"{delay_ms:.0f} ms", border=True,
          help="Lag that best aligns the filtered ECG with the original, from cross-correlation.")
m2.metric("Group delay in 5–15 Hz", f"{gd_band:.0f} ms", border=True)
m3.metric("Share of 150 ms tolerance used", f"{abs(delay_ms) / 150:.0%}", border=True,
          delta="beats will be mis-matched" if abs(delay_ms) > 150 else ("tight" if abs(delay_ms) > 75 else "OK"),
          delta_color="inverse" if abs(delay_ms) > 75 else "off", delta_arrow="off")

a, b = int(302 * fs), int(308 * fs)
t = np.arange(a, b) / fs
ff = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                   subplot_titles=["Before: test signal", "After: filtered"])
ff.add_trace(go.Scatter(x=t, y=cs[a - s0:b - s0], line=dict(color=tk["clean"], width=1.2), name="Clean ECG"), 1, 1)
ff.add_trace(go.Scatter(x=t, y=xs[a - s0:b - s0], line=dict(color=tk["trace"], width=1.4), name="Noisy input"), 1, 1)
ff.add_trace(go.Scatter(x=t, y=y[a - s0:b - s0], line=dict(color=tk["tp"], width=1.5), name="Filtered output"), 2, 1)
rw = ref[(ref >= a) & (ref < b)]
for rr in rw:
    for row in (1, 2):
        ff.add_vline(x=rr / fs, line=dict(color=tk["muted"], width=1, dash="dot"), row=row, col=1)
base_layout(ff, height=440)
ecg_grid(ff, row=1, col=1, span_mv=float(np.ptp(np.r_[xs[a - s0:b - s0], cs[a - s0:b - s0]])))
ecg_grid(ff, row=2, col=1, span_mv=float(np.ptp(y[a - s0:b - s0])))
ff.update_xaxes(title_text="Time (s); dotted lines = reference beat times", row=2, col=1)
st.plotly_chart(ff, alt="ECG before and after filtering", config=PLOT_CONFIG)

mains = data.json_result("audit.json").get("mains", {})
if mains:
    st.caption(f"Mains check on clean record 118: spectral peak {mains['peak_60Hz_dB_above_floor']:.1f} dB above "
               f"the floor at 60 Hz vs {mains['peak_50Hz_dB_above_floor']:.1f} dB at 50 Hz, so the notch "
               f"defaults to 60 Hz (US recordings).")
