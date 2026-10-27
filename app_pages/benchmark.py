import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bench.detectors import DETECTORS
from bench.filters import PREFILTER_LABELS
from ui import data, glossary
from ui.charts import METRIC_LABEL, snr_curves
from ui.style import PLOT_CONFIG, base_layout, det_style, overline

overline(f"Results · {data.meta().get('n_runs', 0):,} precomputed runs", "bm")
st.title("Detector benchmark")
st.markdown("Sensitivity and positive predictivity against expert reference beats, per SNR, **on noisy "
            "segments only**, with 95% block-bootstrap confidence intervals.")

if not data.results_available():
    st.warning("No precomputed results. Run `python scripts/run_benchmark.py`.", icon=":material/hourglass_empty:")
    st.stop()

S = data.summary()
NOISE_LABEL = {"em": "Electrode motion", "ma": "Muscle artefact", "bw": "Baseline wander"}

with st.container(border=True):
    c1, c2, c3 = st.columns([1.3, 1.6, 1.4], vertical_alignment="bottom")
    dataset = c1.segmented_control(
        "Dataset", ["mixed", "nstdb"], default="mixed", required=True, wrap=True, key="bm_ds",
        format_func={"mixed": "Our mixer (15)", "nstdb": "NSTDB (2)"}.get,
        help="Our mixer adds all three noise types to 15 MIT-BIH records with the nst method. "
             "The official NSTDB records exist for electrode motion only.")
    noises = ["em", "ma", "bw"] if dataset == "mixed" else ["em"]
    noise = c2.segmented_control("Noise type", noises, default="em", required=True, wrap=True, key=f"bm_noise_{dataset}",
                                 format_func=NOISE_LABEL.get)
    pf = c3.segmented_control("Pre-filter", list(PREFILTER_LABELS), default="none", required=True, wrap=True, key="bm_pf",
                              format_func={"none": "None", "hp_notch": "HP 0.5 Hz + notch"}.get,
                              help=glossary.PREFILTER)
    c4, c5 = st.columns([3, 1.4], vertical_alignment="bottom")
    dets = c4.pills("Detectors", list(DETECTORS), default=list(DETECTORS), selection_mode="multi",
                    format_func=lambda k: DETECTORS[k].name, wrap=True, key="bm_dets")
    metric = c5.segmented_control("Second panel", ["f1", "hr_within5"], default="f1", required=True, wrap=True, key="bm_m",
                                  format_func={"f1": "F1", "hr_within5": "HR ±5 bpm"}.get,
                                  help=glossary.HR5)

sel = S[(S.dataset == dataset) & (S.noise == noise) & (S.prefilter == pf)]
noisy = sel[sel.segment == "noisy"]
# clean baseline from the 24 dB runs: after strong noise, adaptive thresholds
# take a while to recover, which would contaminate the "clean" minutes
clean = sel[(sel.segment == "clean") & (sel.snr == 24)]

if not dets:
    st.info("Pick at least one detector.", icon=":material/touch_app:")
    st.stop()

with st.container(border=True):
    st.subheader(f"{NOISE_LABEL[noise]} · {PREFILTER_LABELS[pf]}", anchor=False)
    st.caption("Shaded: 95% CI. Dotted: same detector on the clean segments of the 24 dB runs. SNR falls left to right.")
    st.plotly_chart(snr_curves(noisy, ["se", "ppv"], dets, clean_baseline=clean, height=380),
                    alt="Se and +P versus SNR", config=PLOT_CONFIG)
    st.plotly_chart(snr_curves(noisy, [metric], dets, clean_baseline=clean, height=300,
                               ci=metric != "hr_within5"),
                    alt=f"{METRIC_LABEL[metric]} versus SNR", config=PLOT_CONFIG)


# Breaking point: highest SNR at which a metric falls below a threshold
def breaking_snr(d: pd.DataFrame, col: str, thr: float) -> float | None:
    d = d.sort_values("snr", ascending=False)
    prev = None
    for _, r in d.iterrows():
        if r[col] < thr:
            if prev is None:
                return float(r.snr)
            # linear interpolation between neighbouring SNR points
            s0, v0, s1, v1 = prev.snr, prev[col], r.snr, r[col]
            return float(s0 + (thr - v0) * (s1 - s0) / (v1 - v0))
        prev = r
    return None


st.subheader("Where each detector breaks", anchor=False)
thr = st.select_slider("Acceptance threshold", options=[0.90, 0.95, 0.97, 0.99], value=0.95, key="bm_thr",
                       format_func=lambda v: f"{v:.0%}",
                       help="The SNR at which Se or +P first drops below this level (interpolated). "
                            "Lower SNR = more robust.")
rows = []
for det in dets:
    d = noisy[noisy.detector == det]
    if d.empty:
        continue
    bs, bp = breaking_snr(d, "se", thr), breaking_snr(d, "ppv", thr)
    rows.append({
        "Detector": DETECTORS[det].name,
        "Se breaks below (dB)": bs,
        "+P breaks below (dB)": bp,
        "Se at 6 dB": float(d[d.snr == 6].se.iloc[0]) if (d.snr == 6).any() else np.nan,
        "+P at 6 dB": float(d[d.snr == 6].ppv.iloc[0]) if (d.snr == 6).any() else np.nan,
        "F1 at 0 dB": float(d[d.snr == 0].f1.iloc[0]) if (d.snr == 0).any() else np.nan,
        "Clean F1": float(clean[clean.detector == det].f1.mean()),
    })
bt = pd.DataFrame(rows)
for c in ("Se at 6 dB", "+P at 6 dB", "F1 at 0 dB", "Clean F1"):
    bt[c] = bt[c] * 100
st.dataframe(
    bt, hide_index=True, alt="Breaking-point SNR per detector",
    column_config={
        "Se breaks below (dB)": st.column_config.NumberColumn(format="%.1f", help="Blank: never below threshold in 24 to −6 dB."),
        "+P breaks below (dB)": st.column_config.NumberColumn(format="%.1f"),
        **{c: st.column_config.ProgressColumn(c, min_value=0.0, max_value=100.0, format="%.1f%%")
           for c in ("Se at 6 dB", "+P at 6 dB", "F1 at 0 dB", "Clean F1")},
    })

if dataset == "mixed":
    st.subheader("Does the pre-filter help?", anchor=False)
    st.caption("Change in F1 when the 0.5 Hz high-pass + 60 Hz notch runs before each detector "
               "(percentage points, noisy segments). Positive = better with the filter.")
    both = S[(S.dataset == "mixed") & (S.noise == noise) & (S.segment == "noisy")]
    piv = both.pivot_table(index=["detector", "snr"], columns="prefilter", values="f1").reset_index()
    piv["delta"] = (piv["hp_notch"] - piv["none"]) * 100
    fig = go.Figure()
    for det in dets:
        d = piv[piv.detector == det].sort_values("snr", ascending=False)
        fig.add_trace(go.Bar(x=d.snr.astype(str) + " dB", y=d.delta, name=DETECTORS[det].name,
                             marker_color=det_style(det)["color"],
                             marker_pattern_shape={"solid": "", "dash": "/", "dot": ".", "dashdot": "x",
                                                   "longdash": "-"}[det_style(det)["dash"]],
                             hovertemplate="%{y:+.2f} pp<extra>" + DETECTORS[det].name + "</extra>"))
    base_layout(fig, height=300, barmode="group")
    fig.update_yaxes(title_text="Δ F1 (pp)", zeroline=True, zerolinecolor="rgba(128,128,128,0.6)")
    st.plotly_chart(fig, alt="Change in F1 from pre-filtering", config=PLOT_CONFIG)

if st.toggle("Per-record breakdown: what the pooled numbers hide", key="bm_per_rec"):
    P = data.per_record()
    snr_pick = st.select_slider("SNR", options=[24, 18, 12, 6, 0, -6], value=6, key="bm_rec_snr")
    per = P[(P.dataset == dataset) & (P.noise == noise) & (P.prefilter == pf) & P.noisy & (P.snr == snr_pick)
            & P.detector.isin(dets)]
    grid = per.pivot_table(index="record", columns="detector", values="f1", observed=True)
    hm = go.Figure(go.Heatmap(
        z=grid.to_numpy() * 100, x=[DETECTORS[c].name for c in grid.columns], y=[f"rec {r}" for r in grid.index],
        zmin=50, zmax=100, colorscale=[[0, "#B8322A"], [0.5, "#E9C46A"], [0.8, "#EFE9DF"], [1, "#2A8C82"]],
        text=np.round(grid.to_numpy() * 100, 1), texttemplate="%{text}", hovertemplate="%{y} · %{x}: F1 %{z:.1f}%<extra></extra>",
        colorbar=dict(title="F1 %", thickness=10)))
    base_layout(hm, height=max(260, 28 * len(grid) + 60))
    hm.update_yaxes(autorange="reversed", showgrid=False)
    hm.update_xaxes(showgrid=False, side="top")
    st.plotly_chart(hm, alt="F1 per record and detector", config=PLOT_CONFIG)
    st.caption("Slow hearts score worst. The noise adds roughly the same number of false detections per minute "
               "to every record, so a record with fewer true beats (117 and 123, about 50 bpm) loses more "
               "+P. Rank correlation between beat count and F1 at 6 dB electrode motion: 0.96.")
with st.expander("Full results table and download", icon=":material/download:"):
    show = sel[sel.detector.isin(dets)].copy()
    show["detector"] = show.detector.map(lambda k: DETECTORS[k].name)
    cols = ["detector", "segment", "snr", "tp", "fp", "fn", "se", "se_lo", "se_hi", "ppv", "ppv_lo", "ppv_hi",
            "f1", "hr_mae", "hr_within5", "n_windows", "n_records"]
    show = show[cols].sort_values(["segment", "detector", "snr"], ascending=[False, True, False])
    st.dataframe(show, hide_index=True, alt="Full benchmark results",
                 column_config={c: st.column_config.NumberColumn(format="%.4f") for c in cols if c[:2] in ("se", "pp", "f1", "hr")})
    st.download_button("Download CSV", show.to_csv(index=False).encode(), f"benchmark_{dataset}_{noise}_{pf}.csv",
                       "text/csv", icon=":material/download:")
