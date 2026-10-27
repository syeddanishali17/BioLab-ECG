import numpy as np
import streamlit as st

from bench.detectors import DETECTORS
from bench.mixer import signal_power
from ui import data, glossary
from ui.charts import ecg_window
from ui.style import PLOT_CONFIG, overline

overline("Root-cause analysis", "fg")
st.title("Failure gallery")
st.markdown("The worst 10-second windows for each detector, with the reference beats, what the detector "
            "did, and a short explanation of the failure mode. Root-cause analysis, applied to an algorithm.")

if not data.results_available():
    st.warning("No precomputed results. Run `python scripts/run_benchmark.py`.", icon=":material/hourglass_empty:")
    st.stop()

NOISE_LABEL = {"em": "Electrode motion", "ma": "Muscle artefact", "bw": "Baseline wander"}

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([3.2, 1.7, 1.2, 1.2], vertical_alignment="bottom")
    det = c1.segmented_control("Detector", list(DETECTORS), default="neurokit", required=True, wrap=True, key="fg_det",
                               format_func=lambda k: DETECTORS[k].name)
    noise = c2.segmented_control("Noise type", ["all", "em", "ma", "bw"], default="all", required=True, wrap=True, key="fg_noise",
                                 format_func=lambda k: "All" if k == "all" else k.upper())
    min_snr = c3.select_slider("Only SNR ≥", options=[-6, 0, 6, 12], value=6, key="fg_snr",
                               format_func=lambda v: f"{v} dB",
                               help="At −6 dB everything fails. Failures at moderate SNR are the instructive ones.")
    pf = c4.toggle("HP + notch pre-filter", key="fg_pf", help=glossary.PREFILTER)
pf_key = "hp_notch" if pf else "none"

W = data.worst_windows()  # already one (the worst) window per run
w = W[(W.detector == det) & (W.prefilter == pf_key) & (W.snr >= min_snr)]
if noise != "all":
    w = w[w.noise == noise]
picked = w.sort_values(["errors", "snr"], ascending=[False, False]).head(5)

if picked.empty or picked.errors.max() == 0:
    st.success(f"{DETECTORS[det].name} made no errors in this selection.", icon=":material/check_circle:")
    st.stop()


P = data.per_record()
CLEAN_PPV = (P[~P.noisy].set_index(["dataset", "record", "noise", "snr", "detector", "prefilter"]).ppv)


def explain(row, local_snr: float, n_fp: int, n_fn: int, nominal: int) -> str:
    kind = row.noise
    clean_ppv = CLEAN_PPV.get((row.dataset, row.record, row.noise, row.snr, row.detector, row.prefilter), 1.0)
    if n_fp >= n_fn and clean_ppv < 0.98:
        return (f"**Not caused by the noise.** This detector also over-counts on the *clean* segments of record "
                f"{row.record} (+P {clean_ppv:.1%} with no noise). The extra detections sit about 300–450 ms after "
                "each R peak, which is where the T wave is: tall T waves at a slow heart rate are counted as "
                "beats. The fix belongs in the decision logic (refractory period / T-wave discrimination), "
                "not in filtering.")
    lead = f"Local SNR in this window: **{local_snr:.1f} dB** (record nominal {nominal} dB). "
    if local_snr < nominal - 3:
        lead += "The noise is bursty, so this stretch is much worse than the record average. "
    if n_fp >= n_fn:
        why = {
            "em": "Electrode motion produces sharp, QRS-like deflections and the detector fires on them. "
                  "The NSTDB documentation notes this artefact can mimic ectopic beats and is hard to remove "
                  "with simple filters.",
            "ma": "Muscle noise is broadband and overlaps the 5–15 Hz QRS band. Bursts cross the detection "
                  "threshold and are counted as beats.",
            "bw": "Large, fast baseline swings leak into the detector's band and create extra peaks.",
        }[kind]
        return lead + f"**Mostly false detections ({n_fp} FP).** " + why
    why = {
        "em": "Large motion artefacts raise the detector's adaptive threshold, so the real QRS complexes that "
              "follow fall below it and are skipped.",
        "ma": "The noise envelope is as large as the QRS, so peaks cannot be separated from the background and "
              "real beats are missed.",
        "bw": "The baseline swing pushes the signal outside the range the detector expects, and beats on the "
              "steep slope are missed.",
    }[kind]
    return lead + f"**Mostly missed beats ({n_fn} FN).** " + why


for i, row in enumerate(picked.itertuples(), 1):
    x, ref, mask, fs = data.signal(row.dataset, str(row.record), row.noise, float(row.snr))
    peaks = data.live_detections(row.dataset, str(row.record), row.noise, float(row.snr), det, pf_key)
    clean, clean_rec = data.clean(str(row.record))
    a = int(row.t0_s * fs)
    b = a + int(10 * fs)
    a0, b0 = max(0, a - int(fs)), min(x.size, b + int(fs))
    o = data.outcome(ref, peaks, fs)
    outcome = {k: (v[(v >= a0) & (v < b0)] / fs, x[v[(v >= a0) & (v < b0)]]) for k, v in o.items()}
    in_win = (ref >= a0) & (ref < b0)
    noise_seg = (x - clean)[a:b].astype(float)
    S = signal_power(clean.astype(float), clean_rec.beats, fs, clean_rec.beat_symbols)
    local_snr = 10 * np.log10(S / max(np.var(noise_seg), 1e-12))

    with st.container(border=True):
        h1, h2 = st.columns([4, 1.4], vertical_alignment="center")
        src = "official NSTDB" if row.dataset == "nstdb" else "our mixer"
        h1.markdown(f"##### #{i} · record {row.record} · {NOISE_LABEL[row.noise]} · {row.snr} dB "
                    f"· {int(row.t0_s // 60)}:{int(row.t0_s % 60):02d} ({src})")
        with h2.container(horizontal=True, horizontal_alignment="right"):
            st.badge(f"{row.fp} FP", color="red", icon=":material/close:")
            st.badge(f"{row.fn} FN", color="orange", icon=":material/arrow_downward:")
        fig = ecg_window(np.arange(a0, b0) / fs, x[a0:b0], clean=clean[a0:b0], ref_t=ref[in_win] / fs,
                         outcome=outcome, mask_spans=[(a / fs, b / fs)], height=330)
        st.plotly_chart(fig, alt=f"Failure window {i} for {DETECTORS[det].name}", key=f"fg_plot_{i}",
                        config=PLOT_CONFIG)
        st.markdown(explain(row, local_snr, int(row.fp), int(row.fn), int(row.snr)))

st.caption("Shaded: the scored 10-second window (±1 s context shown). Grey ▼: reference beats. "
           "Green ●: correct detections. Red ✕: false detections. Red ▽: missed beats.")
