"""Visual constants shared by every page: "ink on ECG paper".

One colour + dash + marker per detector (distinguishable in greyscale), one fixed
marker style for reference beats and for each match outcome, and a light/dark
aware palette (navy ink on warm paper, periwinkle on ink)."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

_DET = {  # light, dark, dash, marker
    "neurokit": ("#1F3A93", "#8FA2FF", "solid", "circle"),
    "pantompkins": ("#D2602A", "#F0874B", "dash", "square"),
    "hamilton": ("#2A8C82", "#4FC2B3", "dot", "diamond"),
    "elgendi": ("#9B4F96", "#D39BD6", "dashdot", "triangle-up"),
    "xqrs": ("#B8901C", "#E2BE4F", "longdash", "x"),
}
_NOISE = {
    "em": ("#D2602A", "#F0874B", "Electrode motion"),
    "ma": ("#1F3A93", "#8FA2FF", "Muscle artefact"),
    "bw": ("#2A8C82", "#4FC2B3", "Baseline wander"),
}

FONT = "Geist, Inter, system-ui, sans-serif"
MONO = "Geist Mono, ui-monospace, monospace"


def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001 - outside a Streamlit run
        return False


def _pick(pair: tuple[str, str]) -> str:
    return pair[1] if is_dark() else pair[0]


def det_style(key: str) -> dict:
    light, dark, dash, symbol = _DET[key]
    return {"color": dark if is_dark() else light, "dash": dash, "symbol": symbol}


def noise_style(key: str) -> dict:
    light, dark, label = _NOISE[key]
    return {"color": dark if is_dark() else light, "label": label}


def tokens() -> dict:
    """Plot colours for the active theme."""
    dark = is_dark()
    return {
        "trace": "#A9B7FF" if dark else "#1F3A93",  # the ECG "ink"
        "clean": "rgba(236,231,222,0.35)" if dark else "rgba(36,34,30,0.28)",
        "clean_strong": "rgba(236,231,222,0.85)" if dark else "rgba(36,34,30,0.80)",
        "noisy_shade_strong": "rgba(240,135,75,0.28)" if dark else "rgba(210,96,42,0.25)",
        "ref": "#ECE7DE" if dark else "#24221E",
        "noise": "#F0874B" if dark else "#D2602A",
        "noisy_shade": "rgba(240,135,75,0.10)" if dark else "rgba(210,96,42,0.08)",
        "grid_major": "rgba(240,135,75,0.16)" if dark else "rgba(210,96,42,0.20)",
        "grid_minor": "rgba(240,135,75,0.06)" if dark else "rgba(210,96,42,0.08)",
        "grid": "rgba(236,231,222,0.08)" if dark else "rgba(36,34,30,0.08)",
        "tp": "#4FC2B3" if dark else "#2A8C82",
        "fp": "#F06A5E" if dark else "#B8322A",
        "muted": "#A39D92" if dark else "#7A746A",
        "band": "rgba(143,162,255,0.08)" if dark else "rgba(31,58,147,0.06)",
    }


def ref_marker() -> dict:
    """Reference beats always use this one marker style."""
    return dict(symbol="triangle-down", size=9, color=tokens()["ref"], line=dict(width=0))


def outcome_markers() -> dict:
    t = tokens()
    return {
        "tp": dict(symbol="circle", size=8, color=t["tp"], line=dict(width=1.2, color="white")),
        "fp": dict(symbol="x-thin", size=12, color=t["fp"], line=dict(width=3, color=t["fp"])),
        "fn": dict(symbol="triangle-down-open", size=13, color=t["fp"], line=dict(width=2.4)),
    }


def base_layout(fig: go.Figure, height: int = 380, **kw) -> go.Figure:
    t = tokens()
    layout = dict(
        height=height,
        margin=dict(l=8, r=8, t=40, b=8),
        font=dict(family=FONT, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                    font=dict(size=12)),
        hoverlabel=dict(font=dict(family=MONO, size=12)),
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(**{**layout, **kw})
    # stacked (single-column) subplot titles: left-aligned, editorial style, never under a cursor label
    for a in fig.layout.annotations:
        if a.xref == "paper" and a.x == 0.5 and a.yanchor == "bottom" and a.showarrow is False:
            a.update(x=0, xanchor="left")
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], zeroline=False, linecolor=t["grid"],
                     tickfont=dict(family=MONO, size=11))
    fig.update_yaxes(showgrid=True, gridcolor=t["grid"], zeroline=False, linecolor=t["grid"],
                     tickfont=dict(family=MONO, size=11))
    fig.update_annotations(font=dict(family=FONT, size=13))
    return fig


def ecg_grid(fig: go.Figure, row=None, col=None, span_mv: float | None = None) -> go.Figure:
    """ECG-paper grid: 1 s / 0.5 mV major lines, 0.2 s / 0.1 mV minor. The voltage grid
    coarsens for large signal spans (e.g. strong baseline wander) so labels stay readable."""
    t = tokens()
    kw = dict(row=row, col=col) if row else {}
    ydt = 0.5 if span_mv is None or span_mv <= 5 else (1.0 if span_mv <= 10 else 2.0)
    fig.update_xaxes(dtick=1.0, gridcolor=t["grid_major"],
                     minor=dict(dtick=0.2, showgrid=True, gridcolor=t["grid_minor"]), **kw)
    fig.update_yaxes(dtick=ydt, gridcolor=t["grid_major"],
                     minor=dict(dtick=ydt / 5, showgrid=True, gridcolor=t["grid_minor"]), **kw)
    return fig


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# No mode bar: cleaner, and it overlaps legends on phones. Drag to zoom, double-click to reset still work.
PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False}
PLOT_CONFIG_STATIC = {"displayModeBar": False}


def is_mobile() -> bool:
    """Phone-sized client, from the user agent (Streamlit does not expose the viewport width)."""
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:  # noqa: BLE001 - outside a Streamlit run
        return False
    return any(k in ua for k in ("Mobile", "Android", "iPhone"))


def overline(text: str, key: str) -> None:
    """Small uppercase, letter-spaced section label (keyed so CSS can target it)."""
    with st.container(key=f"overline_{key}"):
        st.caption(text)


def page_css() -> None:
    """Minimal CSS, only on keyed elements: uppercase overlines."""
    st.html("""<style>
    [class*="st-key-overline_"] p { text-transform: uppercase; letter-spacing: .14em;
        font-size: .72rem; font-weight: 600; margin-bottom: -.4rem; }
    @media (max-width: 640px) {
        h1 { font-size: 2.05rem !important; line-height: 1.12 !important; }
        h2 { font-size: 1.45rem !important; }
    }
    </style>""")
