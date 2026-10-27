import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, tokens

PATH = "app_pages/learn_ecg.py"
L.chapter_header(PATH, "The ECG: the heart's electricity",
                 "An ECG electrode does not measure “the heart”. It measures a **voltage difference** between two "
                 "points on the skin. That difference comes from electrical waves spreading through the heart muscle.")

tk = tokens()

# ------------------------------------------------------------ 1. leads and axis
st.header("Two electrodes, one voltage", anchor=False)
st.markdown("At any instant the heart's electrical activity can be drawn as one arrow, the **electrical vector**. "
            "A pair of electrodes defines a line, the **lead axis**. The ECG shows how much of the vector points "
            "along that line (its projection). Same heart, different electrode positions → different-looking ECG.")

LEADS = {"Lead I": (0, "right arm → left arm"), "Lead II": (60, "right arm → left leg"),
         "aVF": (90, "straight down, toward the feet"), "Lead III": (120, "left arm → left leg"),
         "aVR": (-150, "looking from the right shoulder")}
with st.container(border=True):
    c1, c2 = st.columns([1.2, 1], gap="large", vertical_alignment="bottom")
    axis = c1.slider("Heart's electrical axis (QRS direction)", -90, 180, 60, step=5, key="le_axis",
                     format="%d°", help="In most healthy adults the QRS vector points down and to the left, "
                                        "roughly between −30° and +90°.")
    lead_name = c2.segmented_control("Electrode pair (lead)", list(LEADS), default="Lead II", required=True,
                                     wrap=True, key="le_lead")
    lead, lead_desc = LEADS[lead_name]
    st.caption(f"{lead_name}: {lead_desc}. 0° points to the person's left, +90° straight down.")


def xy(deg, r=1.0):
    """Angle in ECG convention (0° = person's left, +90° = down) to plot coordinates."""
    return r * np.cos(np.radians(deg)), -r * np.sin(np.radians(deg))


proj = float(np.cos(np.radians(axis - lead)))
c1, c2 = st.columns(2, gap="large")
with c1:
    f = go.Figure()
    lx, ly = xy(lead, 1.25)
    f.add_trace(go.Scatter(x=[-lx, lx], y=[-ly, ly], mode="lines+markers",
                           line=dict(color=tk["muted"], width=2, dash="dot"),
                           marker=dict(size=[10, 14], color=[tk["muted"], tk["noise"]]), hoverinfo="skip"))
    hx, hy = xy(axis, 1.0)
    px, py = xy(lead, proj)
    f.add_trace(go.Scatter(x=[0, px], y=[0, py], mode="lines", line=dict(color=tk["noise"], width=8), opacity=0.5,
                           hoverinfo="skip"))
    f.add_annotation(x=hx, y=hy, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                     arrowwidth=3, arrowcolor=tk["trace"])
    f.add_annotation(x=lx, y=ly, text="+ electrode", showarrow=False, yshift=14, font=dict(color=tk["noise"], size=11))
    f.add_annotation(x=-lx, y=-ly, text="− electrode", showarrow=False, yshift=14, font=dict(color=tk["muted"], size=11))
    f.add_annotation(x=hx * 0.5, y=hy * 0.5, text="heart vector", showarrow=False, xanchor="right", xshift=-10,
                     font=dict(color=tk["trace"], size=11))
    f.add_annotation(x=0, y=1.42, text="head ↑", showarrow=False, font=dict(color=tk["muted"], size=11))
    f.add_annotation(x=1.5, y=-1.42, text="person's left →", showarrow=False, xanchor="right",
                     font=dict(color=tk["muted"], size=11))
    base_layout(f, height=340, showlegend=False, margin=dict(l=0, r=0, t=36, b=0),
                title=dict(text="Heart vector, lead axis and projection", font=dict(size=13)))
    f.update_xaxes(range=[-1.6, 1.6], visible=False)
    f.update_yaxes(range=[-1.5, 1.5], visible=False, scaleanchor="x")
    st.plotly_chart(f, config={"displayModeBar": False}, alt="Heart vector and lead axis")

with c2:
    # each wave has its own direction: P (atria) ~ +50°, QRS = slider, T roughly follows QRS
    t = np.linspace(-0.3, 0.6, 900)
    g = lambda mu, sd: np.exp(-0.5 * ((t - mu) / sd) ** 2)  # noqa: E731
    p_w = 0.15 * g(-0.16, 0.025) * np.cos(np.radians(50 - lead))
    q_w = -0.12 * g(-0.025, 0.008) * np.cos(np.radians(axis + 40 - lead))
    r_w = 1.2 * g(0, 0.011) * proj
    s_w = -0.3 * g(0.03, 0.01) * np.cos(np.radians(axis - 40 - lead))
    t_w = 0.32 * g(0.28, 0.05) * np.cos(np.radians(0.7 * axis + 12 - lead))
    y = p_w + q_w + r_w + s_w + t_w
    fig = go.Figure(go.Scatter(x=t, y=y, line=dict(color=tk["trace"], width=2.4), hoverinfo="skip"))
    base_layout(fig, height=340, showlegend=False, margin=dict(l=8, r=8, t=36, b=8),
                title=dict(text=f"What {lead_name} records (simulated)", font=dict(size=13)))
    ecg_grid(fig)
    fig.update_yaxes(range=[-1.4, 1.4], title_text="mV")
    fig.update_xaxes(title_text="Time (s)", dtick=0.2)
    st.plotly_chart(fig, config={"displayModeBar": False}, alt="Simulated ECG beat seen by the chosen lead")

word = ("tall and upright" if proj > 0.7 else "upright but smaller" if proj > 0.25 else
        "tiny or two-sided (biphasic)" if proj > -0.25 else "inverted (pointing down)")
st.markdown(f"The heart vector makes an angle of **{abs((axis - lead + 180) % 360 - 180)}°** with {lead_name}, so the "
            f"projection is cos(angle) = **{proj:+.2f}** and the R wave looks **{word}**.")

with st.expander("Try this", icon=":material/science:"):
    st.markdown("- Set the axis to **+60°** and pick Lead II: the biggest R wave, which is why Lead II is a common "
                "rhythm lead (BIOPAC's default ECG lead is Lead II).\n"
                "- Keep the axis and pick **aVR**: everything flips upside down.\n"
                "- Find the lead where the QRS nearly disappears: it is perpendicular (90°) to the heart vector.")


# ------------------------------------------------------------ 2. real beat, labelled
st.header("Anatomy of one beat", anchor=False)
st.markdown("Below is a **real** heartbeat recorded with a BIOPAC MP36, the system from your class: the average of "
            "about 300 beats from a healthy volunteer lying still. Averaging removes noise but keeps the shape.")


@st.cache_data(show_spinner=False)
def real_beat(lead: str):
    d = L.load("cebs_rest")
    fs = d["fs"]
    pre, post = int(0.3 * fs), int(0.55 * fs)
    avg = L.ensemble(L.bandpass(d[lead], 0.5, 40, fs), d["beats"], pre, post)
    return avg, fs, pre, L.ecg_landmarks(avg, pre, fs)


lead_pick = st.segmented_control("Lead", ["lead_I", "lead_II"], default="lead_I", required=True, wrap=True, key="le_real",
                                 format_func={"lead_I": "Lead I", "lead_II": "Lead II"}.get,
                                 help="Same heartbeats, two electrode pairs. Notice how different they look.")
avg, fs, pre, lm = real_beat(lead_pick)
tt = (np.arange(avg.size) - pre) / fs
WAVES = {
    "P wave": (lm.p, -0.06, 0.05, "Atrial depolarization: the electrical wave spreads through the atria, which "
               "then contract and top up the ventricles.", "~80–110 ms"),
    "QRS complex": (lm.r, -0.05, 0.05, "Ventricular depolarization: the wave races through the ventricles. Big "
                    "muscle mass, fast spread → sharp, tall complex. Q = first dip, R = peak, S = dip after.",
                    "~70–110 ms"),
    "T wave": (lm.t, -0.09, 0.1, "Ventricular repolarization: the ventricles electrically reset, ready for the "
               "next beat.", "~150–250 ms"),
}
show = st.pills("Highlight", list(WAVES), default=list(WAVES), selection_mode="multi", wrap=True, key="le_waves")
fig = go.Figure()
shade = {"P wave": tk["band"], "QRS complex": tk["noisy_shade"], "T wave": tk["band"]}
for w in show or []:
    i, a, b, *_ = WAVES[w]
    fig.add_vrect(x0=tt[i] + a, x1=tt[i] + b, fillcolor=shade[w], line_width=0, layer="below",
                  annotation_text=w, annotation_position="top left", annotation_font_size=12)
fig.add_trace(go.Scatter(x=tt, y=avg, line=dict(color=tk["trace"], width=2.4), name="ECG",
                         hovertemplate="%{x:.3f} s · %{y:.2f} mV<extra></extra>"))
for lab, i in (("P", lm.p), ("Q", lm.q), ("R", lm.r), ("S", lm.s), ("T", lm.t)):
    fig.add_annotation(x=tt[i], y=avg[i], text=f"<b>{lab}</b>", showarrow=True, arrowhead=0, ay=-26 if avg[i] >= 0 else 26,
                       font=dict(size=13, color=tk["noise"]), arrowcolor=tk["muted"])
base_layout(fig, height=380, showlegend=False)
ecg_grid(fig, span_mv=float(np.ptp(avg)))
fig.update_xaxes(title_text="Time relative to the R peak (s)", dtick=0.2)
pad = 0.12 * float(np.ptp(avg))
fig.update_yaxes(title_text="mV", range=[float(avg.min()) - 2 * pad, float(avg.max()) + 3 * pad])
st.plotly_chart(fig, config=PLOT_CONFIG, alt="Averaged real ECG beat with P, Q, R, S and T labelled")

cols = st.columns(3)
for col, (w, (_, _, _, what, dur)) in zip(cols, WAVES.items()):
    with col.container(border=True, height="stretch"):
        st.markdown(f"**{w}**")
        st.caption(f"Typical duration {dur}")
        st.markdown(what)

m1, m2, m3 = st.columns(3)
m1.metric("P peak → R peak", f"{(lm.r - lm.p) / fs * 1000:.0f} ms", border=True,
          help="Time for the activation to travel from the atria through the AV node to the ventricles "
               "(related to the PR interval, which is measured from P onset).")
m2.metric("Q → S", f"{(lm.s - lm.q) / fs * 1000:.0f} ms", border=True,
          help="An approximation of the QRS duration (true QRS onset/offset is slightly wider).")
m3.metric("R peak → T peak", f"{(lm.t - lm.r) / fs * 1000:.0f} ms", border=True,
          help="How long the ventricles stay electrically active before resetting.")

with st.expander("Exam corner: where is atrial repolarization?", icon=":material/school:"):
    st.markdown("The atria also repolarize, but it happens **at the same time as the QRS complex**, and the much "
                "bigger ventricular signal hides it. That is why there is no visible “atrial T wave”.")

L.key_idea("ECG = electrical. P = atria activate, QRS = ventricles activate, T = ventricles reset. What a lead shows "
           "depends on where the two electrodes are: it is the projection of the heart's electrical vector.")
L.source_note("cebs_rest")
L.chapter_nav(PATH)
