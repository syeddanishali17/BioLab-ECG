import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.signal import hilbert

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, ecg_grid, is_dark, is_mobile, overline, tokens
from ui.terms import CATEGORIES, DOMAIN_BADGE, MAP_DOMAINS, MAP_EDGES, MAP_NODES, MAP_STORY, TERMS

overline("Learn · reference", "gl")
st.title("Glossary")
st.markdown("Every term from the class, plus the electrical background behind it: electrodes, current through the "
            "body, grounding and safety. **Pick a term** on the map or in the list to see what it means, where you "
            "see it in a real signal, and how it connects to the rest.")

# ------------------------------------------------------------------ focus state (map, list, buttons, URL)
# A ?term= link opens that term, also when the glossary was already open in this session. The URL is
# rewritten at the end of every run; "gl_qp_last" remembers what we wrote, so only *new* links take over.
_q = st.query_params.get("term")
if "gl_focus" not in st.session_state:
    st.session_state.gl_focus = _q if _q in TERMS else "ecg"
elif _q in TERMS and _q != st.session_state.get("gl_qp_last"):
    st.session_state.gl_focus = _q


def set_focus(key: str) -> None:
    st.session_state.gl_focus = key


def _matches(q: str, cats) -> list:
    q = q.strip().lower()
    return [t for t in TERMS.values()
            if (not cats or t.cat in cats) and (not q or q in " ".join((t.name, t.aka, t.short, t.body)).lower())]


def _open_first_match() -> None:
    """After a new search or filter, open the best match so the detail card is never off-topic."""
    found = _matches(st.session_state.get("gl_q", ""), st.session_state.get("gl_cats"))
    if found and st.session_state.gl_focus not in {t.key for t in found}:
        q = st.session_state.get("gl_q", "").strip().lower()
        by_name = [t for t in found if q and q in t.name.lower()]
        st.session_state.gl_focus = (by_name or found)[0].key


def _from_map() -> None:
    ev = st.session_state.get("gl_map")
    pts = ev.selection.points if ev else []
    if pts:
        cd = pts[0].get("customdata")
        cd = cd[0] if isinstance(cd, (list, tuple)) and cd else cd
        if cd in TERMS:
            st.session_state.gl_focus = cd


# keep the detail card in view while the term index scrolls (keyed element only)
st.html("<style>@media (min-width: 640px) { .st-key-gl_detail { position: sticky; top: 4.2rem; } }</style>")

tk = tokens()
dark = is_dark()
DOMAIN_DARK = {"Electrical": "#8FA2FF", "Mechanical": "#4FC2B3", "Acoustic": "#F0874B",
               "Vascular / optical": "#F06A5E", "Derived": "#A39D92", "Breathing": "#B9C6FF", "Motion": "#D39BD6"}
dcol = DOMAIN_DARK if dark else MAP_DOMAINS

# ------------------------------------------------------------------ concept map
with st.container(border=True):
    st.subheader("How it all connects", anchor=False)
    st.caption("The sequence from class: electrical activation → contraction → valve sounds → ejection → pressure "
               "pulse → PPG at the finger, with heart rate derived from the R peaks. Breathing and movement modulate "
               "what you measure. " + ("**Tap a step** to open the term." if is_mobile() else
                                       "**Click a node** to open the term."))
    if is_mobile():  # a graph is unreadable at phone width: tell the same story as steps
        node = {k: (lab.replace("<br>", " "), dom) for k, lab, _, _, dom in MAP_NODES}
        for title, keys in MAP_STORY:
            st.markdown(f"**{title}**")
            for n, k in enumerate(keys, 1):
                lab, dom = node[k]
                with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                    st.badge(dom, color=DOMAIN_BADGE[dom])
                    st.button(f"{n}. {lab}" if title == "One heartbeat" else lab, key=f"gl_story_{k}",
                              on_click=set_focus, args=(k,), type="primary" if k == st.session_state.gl_focus
                              else "tertiary")
    else:
        pos = {k: (x, y) for k, _, x, y, _ in MAP_NODES}
        fig = go.Figure()
        for a, b, lab in MAP_EDGES:
            (x0, y0), (x1, y1) = pos[a], pos[b]
            fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=2, arrowsize=1, arrowwidth=1.4, arrowcolor=tk["muted"], standoff=26, startstandoff=24,
                               opacity=0.75)
            if lab:  # beside vertical arrows, just above the others, so labels never sit on a node label
                vertical = abs(x1 - x0) < 1e-6
                fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=f"<i>{lab}</i>", showarrow=False,
                                   font=dict(size=10, color=tk["muted"]), xanchor="left" if vertical else "center",
                                   xshift=8 if vertical else 0, yshift=0 if vertical else 9)
        focus = st.session_state.gl_focus
        for dom, col in dcol.items():
            nodes = [n for n in MAP_NODES if n[4] == dom]
            fig.add_trace(go.Scatter(
                x=[n[2] for n in nodes], y=[n[3] for n in nodes], mode="markers+text", name=dom,
                text=[n[1] for n in nodes], textposition="bottom center", customdata=[n[0] for n in nodes],
                textfont=dict(size=11 if not is_mobile() else 9),
                marker=dict(size=[30 if n[0] == focus else 20 for n in nodes], color=col,
                            line=dict(width=[4 if n[0] == focus else 1.5 for n in nodes],
                                      color=[tk["noise"] if n[0] == focus else ("#11131C" if dark else "#FFFFFF")
                                             for n in nodes])),
                hovertemplate="%{text}<extra>click to open</extra>"))
        base_layout(fig, height=470, margin=dict(l=4, r=4, t=36, b=4), hovermode="closest", dragmode=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title_text="", font=dict(size=11)))
        fig.update_xaxes(visible=False, range=[-0.8, 9.6])  # no fixedrange: it disables click-to-select
        fig.update_yaxes(visible=False, range=[-0.5, 6.7])
        st.plotly_chart(fig, key="gl_map", on_select=_from_map, selection_mode="points", config=PLOT_CONFIG,
                        alt="Concept map of how ECG, heart sounds, PPG, breathing and motion are connected")

# ------------------------------------------------------------------ search
st.subheader("Find a term", anchor=False)
query = st.text_input("Search", placeholder="Search 128 terms, e.g. dicrotic notch, ground, aliasing", key="gl_q",
                      icon=":material/search:", label_visibility="collapsed", on_change=_open_first_match)
cats = st.pills("Topics", list(CATEGORIES), selection_mode="multi", key="gl_cats", wrap=True,
                format_func=lambda k: CATEGORIES[k][0], label_visibility="collapsed",
                on_change=_open_first_match)
shown = _matches(query, cats)


# ------------------------------------------------------------------ visuals for the detail card
@st.cache_data(show_spinner=False)
def _ecg_beat():
    d = L.load("cebs_rest")
    fs = d["fs"]
    pre, post = int(0.3 * fs), int(0.55 * fs)
    return L.ensemble(L.bandpass(d["lead_I"], 0.5, 40, fs), d["beats"], pre, post), fs, pre


@st.cache_data(show_spinner=False)
def _ppg_pulse():
    d = L.load("ptt_sit")
    fs = d["fs"]
    avg = L.ensemble(L.bandpass(d["ppg_ir"], 0.4, 10, fs), d["beats"], 0, int(0.85 * fs))
    return (avg - avg.min()) / np.ptp(avg), fs, L.ppg_landmarks(avg, fs)


@st.cache_data(show_spinner=False)
def _pcg_beat():
    h = L.load("pcg")
    fs = h["fs"]
    rp = L.r_peaks(h["ecg"], fs)
    pre, post = int(0.15 * fs), int(0.6 * fs)
    snd = L.ensemble(h["pcg"].astype(float), rp, pre, post)
    env = L.ensemble(np.abs(hilbert(h["pcg"].astype(float))), rp, pre, post)
    ecg = L.ensemble(h["ecg"].astype(float), rp, pre, post)
    s1 = pre + int(np.argmax(env[pre:pre + int(0.15 * fs)]))
    s2 = pre + int(0.22 * fs) + int(np.argmax(env[pre + int(0.22 * fs):pre + int(0.5 * fs)]))
    return snd / np.abs(snd).max(), ecg / np.abs(ecg).max(), fs, pre, s1, s2


def visual(spec) -> go.Figure | None:
    kind = spec[0]
    fig = go.Figure()
    if kind == "ecg":
        avg, fs, pre = _ecg_beat()
        t = (np.arange(avg.size) - pre) / fs * 1000
        fig.add_vrect(x0=spec[1], x1=spec[2], fillcolor=tk["noisy_shade_strong"], line_width=0, layer="below")
        fig.add_trace(go.Scatter(x=t, y=avg, line=dict(color=tk["trace"], width=2.4), hoverinfo="skip"))
        ecg_grid(fig, span_mv=float(np.ptp(avg)))
        fig.update_xaxes(dtick=200, minor=dict(dtick=40, showgrid=True), title_text="ms from the R peak")
        fig.update_yaxes(title_text="mV")
    elif kind == "ppg":
        avg, fs, lm = _ppg_pulse()
        t = np.arange(avg.size) / fs * 1000
        i = getattr(lm, spec[1])
        fig.add_trace(go.Scatter(x=t, y=avg, line=dict(color=tk["fp"], width=2.6), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[t[i]], y=[avg[i]], mode="markers", marker=dict(size=14, color=tk["noise"],
                                                                                    line=dict(width=2, color="white")),
                                 hoverinfo="skip"))
        fig.add_vline(x=0, line=dict(color=tk["trace"], dash="dot"), annotation_text="R peak")
        fig.update_xaxes(title_text="ms after the ECG R peak")
        fig.update_yaxes(showticklabels=False)
    elif kind == "pcg":
        snd, ecg, fs, pre, s1, s2 = _pcg_beat()
        t = (np.arange(snd.size) - pre) / fs * 1000
        fig.add_trace(go.Scatter(x=t, y=ecg * 0.6 + 1.6, line=dict(color=tk["trace"], width=1.6), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=t, y=snd, line=dict(color=tk["muted"], width=1), hoverinfo="skip"))
        k = s1 if spec[1] == "s1" else s2
        fig.add_vrect(x0=t[k] - 40, x1=t[k] + 40, fillcolor=tk["noisy_shade_strong"], line_width=0, layer="below")
        fig.add_annotation(x=t[k], y=1.1, text=spec[1].upper(), showarrow=False, font=dict(color=tk["noise"], size=13))
        fig.update_xaxes(title_text="ms from the R peak (top: ECG, bottom: heart sound)")
        fig.update_yaxes(showticklabels=False)
    elif kind == "rr":
        d = L.load("cebs_rest")
        fs = d["fs"]
        a, b = 20 * fs, 24 * fs
        x = L.bandpass(d["lead_I"], 0.5, 40, fs)[a:b]
        bb = d["beats"][(d["beats"] >= a) & (d["beats"] < b)]
        fig.add_trace(go.Scatter(x=np.arange(x.size) / fs, y=x, line=dict(color=tk["trace"], width=1.6), hoverinfo="skip"))
        top = float(x.max())
        for r0, r1 in zip(bb[:-1], bb[1:]):
            rr = (r1 - r0) / fs
            fig.add_annotation(x=(r0 + r1) / 2 / fs - a / fs, y=top * 1.25, showarrow=False,
                               text=f"RR {rr * 1000:.0f} ms → {60 / rr:.0f} bpm", font=dict(size=11, color=tk["noise"]))
            fig.add_shape(type="line", x0=r0 / fs - a / fs, x1=r1 / fs - a / fs, y0=top * 1.1, y1=top * 1.1,
                          line=dict(color=tk["noise"], width=1.5))
        fig.update_yaxes(range=[float(x.min()) - 0.1, top * 1.45], showticklabels=False)
        fig.update_xaxes(title_text="Time (s)")
    elif kind == "resp":
        d = L.load("cebs_rest")
        fs = d["fs"]
        a, b = 40 * fs, 70 * fs
        bb = d["beats"]
        hr = 60 * fs / np.diff(bb)
        m = (bb[1:] >= a) & (bb[1:] < b)
        fig.add_trace(go.Scatter(x=np.arange(b - a)[::10] / fs, y=d["resp"][a:b:10], name="Breathing",
                                 line=dict(color=tk["tp"], width=2), yaxis="y"))
        fig.add_trace(go.Scatter(x=(bb[1:][m] - a) / fs, y=hr[m], name="Heart rate (bpm)", mode="lines+markers",
                                 line=dict(color=tk["noise"], width=2), marker=dict(size=4), yaxis="y2"))
        fig.update_layout(yaxis=dict(showticklabels=False), yaxis2=dict(overlaying="y", side="right", showgrid=False))
        fig.update_xaxes(title_text="Time (s): heart rate rises with each breath in")
    else:
        return None
    base_layout(fig, height=230, showlegend=(kind == "resp"), margin=dict(l=8, r=8, t=26, b=8), hovermode=False)
    return fig


# ------------------------------------------------------------------ list + detail
left, right = st.columns([1.25, 1], gap="large")
with left:
    st.caption(f"{len(shown)} of {len(TERMS)} terms · hover for a one-line definition, click to open")
    if shown:
        focus = st.session_state.gl_focus
        with st.container(height=640 if len(shown) > 14 else "content", border=True):
            for ck, (clab, cicon, _) in CATEGORIES.items():
                group = [t for t in shown if t.cat == ck]
                if not group:
                    continue
                st.markdown(f"**{cicon} {clab}**")
                with st.container(gap=None):
                    for t in group:
                        st.button(t.name, key=f"gl_item_{t.key}", on_click=set_focus, args=(t.key,), help=t.short,
                                  type="primary" if t.key == focus else "tertiary")
    else:
        st.info("No term matches. Try a shorter word, or clear the topic filter.", icon=":material/search_off:")

with right:
    t = TERMS[st.session_state.gl_focus]
    label, icon, color = CATEGORIES[t.cat]
    with st.container(border=True, key="gl_detail"):
        st.badge(label, icon=icon, color=color)
        st.subheader(t.name, anchor=False)
        if t.aka:
            st.caption(f"Also called: {t.aka}")
        st.markdown(f"**{t.short}**")
        st.markdown(t.body)
        if t.visual:
            fig = visual(t.visual)
            if fig is not None:
                st.plotly_chart(fig, config={"displayModeBar": False}, key="gl_vis",
                                alt=f"Where {t.name} appears in a real recording")
        if t.see:
            st.markdown(f":material/visibility: **Where you see it:** {t.see}")
        if t.related:
            st.markdown("**Related**")
            with st.container(horizontal=True, gap="small"):
                for r in t.related:
                    st.button(TERMS[r].name, key=f"gl_rel_{t.key}_{r}", on_click=set_focus, args=(r,),
                              type="secondary", icon=CATEGORIES[TERMS[r].cat][1])
        if t.chapter:
            title = next(c[1] for c in L.CHAPTERS if c[0] == t.chapter)
            st.page_link(t.chapter, label=f"Explore it in “{title}”", icon=":material/arrow_forward:")

st.query_params["term"] = st.session_state.gl_focus  # shareable link to the open term
st.session_state.gl_qp_last = st.session_state.gl_focus

# ------------------------------------------------------------------ study sheet
st.space("small")
with st.container(border=True):
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown("**Revising for the exam?** Download all terms grouped by topic as one study sheet.")
    lines = ["# Biosignals glossary", "", "From the ECG Noise Stress-Test Bench · Learn track", ""]
    for ck, (clab, _, _) in CATEGORIES.items():
        lines += [f"## {clab}", ""]
        for tt in (x for x in TERMS.values() if x.cat == ck):
            lines.append(f"- **{tt.name}**: {tt.short} {tt.body}")
        lines.append("")
    c2.download_button("Study sheet (.md)", "\n".join(lines).encode("utf-8"), "biosignals_glossary.md",
                       "text/markdown", icon=":material/download:", width="stretch")

L.key_idea("ECG = electrical, heart sounds = valves closing, PPG = blood volume seen with light, respiration = "
           "breathing, accelerometer = movement. Electrodes turn ionic currents into a voltage *difference*; a "
           "properly isolated, differential setup keeps the measurement clean and the person safe.")
