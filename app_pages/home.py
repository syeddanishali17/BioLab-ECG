import numpy as np
import plotly.graph_objects as go
import streamlit as st

from bench.config import MIXED_RECORDS
from ui import data, glossary
from ui.charts import snr_curves
from ui.style import PLOT_CONFIG, PLOT_CONFIG_STATIC, base_layout, ecg_grid, is_mobile, overline, tokens


@st.cache_data(show_spinner=False)
def hero_strip(dark: bool) -> go.Figure:
    """Record 118 at the moment electrode-motion noise switches on (5:00), official 6 dB record."""
    x, ref, mask, fs = data.signal("nstdb", "118", "em", 6.0)
    a, b = int(294 * fs), int(306 * fs)
    t = np.arange(a, b) / fs
    tk = tokens()
    fig = go.Figure(go.Scattergl(x=t, y=x[a:b], line=dict(color=tk["trace"], width=1.6), hoverinfo="skip"))
    fig.add_vrect(x0=300, x1=306, fillcolor=tk["noisy_shade"], line_width=0, layer="below")
    fig.add_annotation(x=300.1, y=1, yref="paper", text="noise on · 5:00", showarrow=False, xanchor="left",
                       font=dict(size=11, color=tk["noise"]))
    base_layout(fig, height=170, margin=dict(l=0, r=0, t=4, b=0), showlegend=False)
    ecg_grid(fig)
    fig.update_xaxes(showticklabels=False, title_text=None, range=[294, 306])
    fig.update_yaxes(showticklabels=False, title_text=None)
    return fig


overline("Algorithm verification · open data · reproducible", "home")
st.title("When do heartbeat detectors break?")
st.markdown(
    "<span style='font-size:1.12rem'>Every ECG device has to keep finding heartbeats while electrodes "
    "move, muscles fire and the baseline drifts. This bench adds <b>real recorded noise</b> to expert-"
    "annotated ECG, from 24 dB down to −6 dB SNR, and measures where and why five open-source QRS "
    "detectors fail. It works the way device makers test their algorithms.</span>",
    unsafe_allow_html=True)

if not data.results_available():
    st.warning("No precomputed results found. Run `python scripts/run_benchmark.py` first.",
               icon=":material/hourglass_empty:")
    st.stop()

st.plotly_chart(hero_strip(st.context.theme.type == "dark"), config=PLOT_CONFIG_STATIC,
                alt="ECG strip: clean, then electrode-motion noise switches on at 5 minutes")

summary = data.summary()
meta = data.meta()
noisy = summary[summary.segment == "noisy"]
official = noisy[(noisy.dataset == "nstdb") & (noisy.prefilter == "none")]
dets = list(meta.get("detectors", {}))

mw = 158 if is_mobile() else "stretch"  # two cards per row on phones
with st.container(horizontal=True, gap="small" if is_mobile() else "medium"):
    n_cfg = max(len(meta.get("detectors", {})) * len(meta.get("prefilters", [])), 1)
    hours = noisy.n_windows.sum() * 10 / 3600 / n_cfg  # each signal is scored by every configuration
    st.metric("Detector runs", f"{meta.get('n_runs', 0):,}", border=True, width=mw,
              help="Signal × noise type × SNR × detector × pre-filter, all precomputed offline.")
    st.metric("Noisy ECG", f"{hours:,.0f} h", border=True, width=mw,
              help=f"{meta.get('n_signals', 0)} test signals × 13 noisy minutes, each scored by {n_cfg} "
                   "detector configurations. " + glossary.NOISY_ONLY)
    st.metric("ECG records", f"{len(MIXED_RECORDS)}", border=True, width=mw,
              help="MIT-BIH 118 and 119 (the NSTDB sources) plus 13 records chosen by a stated rule.")
    st.metric("Mixer error", "±0.06 dB", border=True, width=mw,
              help="Our reimplementation of PhysioNet's nst reproduces the noise gain of all 12 official "
                   "records within 0.06 dB.")

st.space("small")
overline("Headline result", "headline")
st.header("Electrode motion makes detectors see beats that are not there", anchor=False)
st.caption("Official NSTDB records 118 and 119, noisy segments only, no extra pre-filter. Bands: 95% "
           "block-bootstrap CI. Dotted: the same detector on clean segments.")
st.plotly_chart(
    snr_curves(official, ["se", "ppv"], dets,
               clean_baseline=summary[(summary.segment == "clean") & (summary.dataset == "nstdb") & (summary.snr == 24)
                                      & (summary.prefilter == "none")]),
    config=PLOT_CONFIG, alt="Sensitivity and positive predictivity versus SNR for each detector")

em = noisy[(noisy.dataset == "nstdb") & (noisy.prefilter == "none")]
at0 = em[em.snr == 0].set_index("detector")
at6 = em[em.snr == 6].set_index("detector")
clean_f1 = summary[(summary.segment == "clean") & (summary.dataset == "nstdb") & (summary.snr == 24)
                   & (summary.prefilter == "none")].groupby("detector").f1.mean()
# same ranking as the verification report: mean F1 at 6 dB over the three noise types (our mixer)
mix6 = noisy[(noisy.dataset == "mixed") & (noisy.prefilter == "none") & (noisy.snr == 6)]
rank = mix6.groupby("detector").f1.mean().sort_values(ascending=False)
best = rank.index[0]

c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.markdown("##### On clean ECG")
    st.markdown(f"On records 118 and 119 all five detectors agree with the reference on **≥ {clean_f1.min():.1%}** "
                "of beats (F1). Some other records trip detectors even without noise (see the report).")
with c2:
    st.markdown("##### At 6 dB and 0 dB")
    st.markdown(f"Positive predictivity falls to **{at6.ppv.min():.0%}–{at6.ppv.max():.0%}** at 6 dB and "
                f"**{at0.ppv.min():.0%}–{at0.ppv.max():.0%}** at 0 dB. Sensitivity drops much less: the errors "
                f"are mostly false beats.")
with c3:
    st.markdown("##### Most robust overall")
    st.markdown(f"**{data.detector_name(best)}**: mean F1 {rank.iloc[0]:.1%} at 6 dB across electrode motion, muscle "
                f"artefact and baseline wander (15 records). Runner-up: {data.detector_name(rank.index[1])} "
                f"{rank.iloc[1]:.1%}.")

st.space("small")
overline("Explore", "explore")
with st.container(horizontal=True, gap="small"):
    st.page_link("app_pages/noise_lab.py", label="Mix noise into ECG", icon=":material/graphic_eq:")
    st.page_link("app_pages/benchmark.py", label="Compare detectors", icon=":material/query_stats:")
    st.page_link("app_pages/failure_gallery.py", label="Worst failures", icon=":material/report:")
    st.page_link("app_pages/report.py", label="Verification report", icon=":material/fact_check:")

with st.container(border=True):
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown("**New to biosignals?** The *Learn* track explains ECG, heart sounds, PPG, breathing and motion "
                "with real recordings, starting from one heartbeat seen by five sensors.")
    with c2:
        st.page_link("app_pages/learn_start.py", label="Start learning", icon=":material/school:")

with st.expander("What is being measured, in plain words", icon=":material/school:"):
    st.markdown(
        f"- **QRS detector**: {glossary.QRS}\n"
        f"- **SNR**: {glossary.SNR}\n"
        f"- **Sensitivity (Se)**: {glossary.SE}\n"
        f"- **Positive predictivity (+P)**: {glossary.PPV}\n"
        f"- **Matching rule**: {glossary.TOLERANCE}\n"
        f"- **Noisy segments only**: {glossary.NOISY_ONLY}"
    )
