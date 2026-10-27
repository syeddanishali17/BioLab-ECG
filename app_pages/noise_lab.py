import numpy as np
import plotly.graph_objects as go
import streamlit as st

from bench.config import MIXED_RECORDS, NOISE_TYPES, NSTDB_SNRS, NSTDB_SOURCES
from bench.detectors import DETECTORS
from bench.mixer import qrs_peak_to_peak
from bench.segments import runs
from ui import data, glossary
from ui.charts import ecg_window
from ui.style import PLOT_CONFIG, PLOT_CONFIG_STATIC, base_layout, noise_style, overline, tokens

overline("Interactive · real recorded noise", "nl")
st.title("Noise lab")
st.markdown("Add real recorded noise to clean ECG at any SNR and watch what a detector does with it.")

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.3, 1, 1.4, 1.6], vertical_alignment="bottom")
    source = c1.segmented_control(
        "Noise source", ["mixed", "nstdb"], default="mixed", required=True, wrap=True, key="nl_source",
        format_func={"mixed": "Our mixer", "nstdb": "Official NSTDB"}.get,
        help="Our mixer: any of 15 records, any noise type, any SNR. Official NSTDB: the 12 ready-made "
             "records (118 and 119 with electrode-motion noise only).")
    records = MIXED_RECORDS if source == "mixed" else NSTDB_SOURCES
    record = c2.selectbox("Clean record", records, key=f"nl_record_{source}",
                          help="MIT-BIH Arrhythmia Database record number. 118 and 119 are the NSTDB sources.")
    noise = c3.segmented_control(
        "Noise type", list(NOISE_TYPES), default="em", required=True, wrap=True, key="nl_noise",
        format_func=lambda k: k.upper(), disabled=source == "nstdb",
        help="EM: electrode motion. MA: muscle artefact. BW: baseline wander. All three are real "
             "recordings from the NSTDB.")
    if source == "nstdb":
        noise = "em"
        snr = c4.select_slider("SNR (dB)", options=sorted(NSTDB_SNRS, reverse=True), value=6,
                               key="nl_snr_off", help=glossary.SNR)
    else:
        snr = c4.slider("SNR (dB)", -6, 24, 6, step=1, key="nl_snr", help=glossary.SNR)

    c5, c6, c7, c8 = st.columns([2.6, 1, 1.4, 1.2], vertical_alignment="bottom")
    t0 = c5.slider("View start (s)", 0, 1790, 302, step=1, key="nl_t0",
                   help="Noise is added from 5:00, in 2-minute bursts alternating with 2 clean minutes.")
    span = c6.segmented_control("Window", [5, 10, 30], default=10, required=True, wrap=True, key="nl_span",
                                format_func=lambda s: f"{s} s")
    det = c7.selectbox("Overlay detector", ["(none)", *DETECTORS], key="nl_det",
                       format_func=lambda k: k if k == "(none)" else DETECTORS[k].name)
    pf = c8.toggle("HP + notch pre-filter", key="nl_pf", help=glossary.PREFILTER)

pf_key = "hp_notch" if pf else "none"
with st.spinner("Building test signal…"):
    x, ref, mask, fs = data.signal(source, record, noise, float(snr))
clean, clean_rec = data.clean(record)

a, b = int(t0 * fs), int(min((t0 + span) * fs, x.size))
t = np.arange(a, b) / fs
in_win = (ref >= a) & (ref < b)

outcome = None
if det != "(none)":
    with st.spinner(f"Running {DETECTORS[det].name} on the full 30-minute record…"):
        peaks = data.live_detections(source, record, noise, float(snr), det, pf_key)
    o = data.outcome(ref, peaks, fs)
    outcome = {k: (v[(v >= a) & (v < b)] / fs, x[v[(v >= a) & (v < b)]]) for k, v in o.items()}

spans = [(max(s.start, a) / fs, min(s.stop, b) / fs) for s in runs(mask) if s.noisy and s.stop > a and s.start < b]

with st.container(horizontal=True, gap="medium"):
    pp = qrs_peak_to_peak(clean.astype(float), clean_rec.beats, fs, clean_rec.beat_symbols)
    if source == "mixed":
        info = data.mix_info(record, noise, float(snr))
        st.metric("Noise gain a", f"{info['gain']:.3f}", help=glossary.GAIN, border=True)
        st.metric("Noise RMS (nst estimate)", f"{np.sqrt(info['N']) * info['gain'] * 1000:.0f} µV", border=True,
                  help="Per-second, mean-removed RMS of the scaled noise, as nst measures it.")
    else:
        resid = (x - clean)[mask]
        st.metric("Noise gain a", "set by nst", help="Official record, mixed by PhysioNet's nst tool.", border=True)
        st.metric("Added noise RMS", f"{np.std(resid) * 1000:.0f} µV", border=True,
                  help="Residual (noisy minus clean) in the noisy segments.")
    st.metric("QRS peak-to-peak", f"{pp:.2f} mV", border=True,
              help="Trimmed mean of normal-beat amplitudes. Signal power S = pp² / 8, as in nst.")
    in_noisy = bool(mask[min(a + (b - a) // 2, mask.size - 1)])
    st.metric("This window", "Noisy" if in_noisy else "Clean", border=True,
              help="Shading marks samples where noise was added.")

fig = ecg_window(t, x[a:b], clean=clean[a:b], ref_t=ref[in_win] / fs, outcome=outcome, mask_spans=spans,
                 height=430, noise=(x - clean)[a:b])
st.plotly_chart(fig, alt="ECG test signal with reference beats", config=PLOT_CONFIG)
if outcome:
    n_tp, n_fp, n_fn = (len(outcome[k][0]) for k in ("tp", "fp", "fn"))
    st.caption(f"In this window: {n_tp} correct, {n_fp} false, {n_fn} missed. ▼ = reference beat from the "
               f"expert annotations; detections are matched within 150 ms.")

# Whole-record timeline (min/max envelope, ~1,800 points)
tk = tokens()
tl = go.Figure()
for s in runs(mask):
    if s.noisy:
        tl.add_vrect(x0=s.start / fs / 60, x1=s.stop / fs / 60, fillcolor=tk["noisy_shade_strong"], line_width=0)
tl.add_vrect(x0=a / fs / 60, x1=b / fs / 60, fillcolor=tk["trace"], opacity=0.55, line_width=0)
blk = int(fs)
n_blk = x.size // blk
env = x[: n_blk * blk].reshape(n_blk, blk)
tm = np.arange(n_blk) / 60
tl.add_trace(go.Scatter(x=np.r_[tm, tm[::-1]], y=np.r_[env.max(1), env.min(1)[::-1]], fill="toself",
                        line=dict(width=0), fillcolor=tk["trace"], opacity=0.5, hoverinfo="skip", showlegend=False))
base_layout(tl, height=120, margin=dict(l=0, r=0, t=26, b=0),
            title=dict(text="Whole record, minutes · shaded: noisy segments · solid: current view",
                       font=dict(size=12)))
tl.update_yaxes(visible=False)
tl.update_xaxes(dtick=5)
st.plotly_chart(tl, alt="Timeline of the whole record with noisy segments", config=PLOT_CONFIG_STATIC)

if st.toggle("Show spectra: why the three noise types behave differently", key="nl_spec"):
    sp = data.spectra(record)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sp["f"], y=sp["ecg"], name=f"Clean ECG {record}",
                              line=dict(color=tk["clean_strong"], width=2)))
    for k in NOISE_TYPES:
        ns = noise_style(k)
        fig2.add_trace(go.Scatter(x=sp["f"], y=sp[k], name=ns["label"],
                                  line=dict(color=ns["color"], width=1.8, dash="solid" if k == noise else "dot")))
    fig2.add_vrect(x0=5, x1=15, fillcolor=tk["band"], line_width=0,
                   annotation_text="QRS band", annotation_position="top left")
    base_layout(fig2, height=320)
    fig2.update_xaxes(type="log", title_text="Frequency (Hz)", range=[np.log10(0.1), np.log10(180)])
    fig2.update_yaxes(title_text="Power (dB/Hz, unscaled)")
    st.plotly_chart(fig2, alt="Power spectra of clean ECG and the three noise recordings", config=PLOT_CONFIG)
    st.markdown(
        "Baseline wander sits almost entirely below 1 Hz, so a high-pass filter removes most of it. "
        "Muscle artefact and electrode motion overlap the 5–15 Hz band where the QRS complex lives, so "
        "filtering cannot separate them from the heartbeat. The NSTDB documentation notes that electrode "
        "motion artefact can mimic ectopic beats and is hard to remove with simple filters."
    )
