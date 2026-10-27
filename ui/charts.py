"""Reusable Plotly figures."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bench.detectors import DETECTORS

from .style import base_layout, det_style, ecg_grid, hex_to_rgba, is_mobile, outcome_markers, ref_marker, tokens

METRIC_LABEL = {"se": "Sensitivity (Se)", "ppv": "Positive predictivity (+P)", "f1": "F1",
                "hr_within5": "HR within ±5 bpm"}


def snr_curves(df: pd.DataFrame, metrics: list[str], detectors: list[str], height: int = 400,
               clean_baseline: pd.DataFrame | None = None, ci: bool = True) -> go.Figure:
    """Metric vs SNR, one line per detector, optional CI bands, one panel per metric."""
    stack = is_mobile() and len(metrics) > 1  # phones: one panel per row
    if stack:
        fig = make_subplots(rows=len(metrics), cols=1, shared_xaxes=True, vertical_spacing=0.12,
                            subplot_titles=[METRIC_LABEL[m] for m in metrics])
        height = int(height * 1.6)
    else:
        fig = make_subplots(rows=1, cols=len(metrics), shared_yaxes=True, horizontal_spacing=0.04,
                            subplot_titles=[METRIC_LABEL[m] for m in metrics])
    for c, m in enumerate(metrics, start=1):
        rc = dict(row=c, col=1) if stack else dict(row=1, col=c)
        for det in detectors:
            d = df[df.detector == det].sort_values("snr")
            if d.empty:
                continue
            s = det_style(det)
            name = DETECTORS[det].name
            x = d.snr.to_numpy()
            if ci and f"{m}_lo" in d:
                lo, hi = d[f"{m}_lo"].to_numpy() * 100, d[f"{m}_hi"].to_numpy() * 100
                fig.add_trace(go.Scatter(
                    x=np.r_[x, x[::-1]], y=np.r_[hi, lo[::-1]], fill="toself", mode="lines",
                    fillcolor=hex_to_rgba(s["color"], 0.12), line=dict(width=0),
                    hoverinfo="skip", showlegend=False, legendgroup=det), **rc)
            fig.add_trace(go.Scatter(
                x=x, y=d[m].to_numpy() * 100, name=name, legendgroup=det, showlegend=(c == 1),
                mode="lines+markers",
                line=dict(color=s["color"], dash=s["dash"], width=2.2),
                marker=dict(symbol=s["symbol"], size=7, color=s["color"]),
                hovertemplate=f"{name}: %{{y:.1f}}%<extra></extra>"), **rc)
            if clean_baseline is not None:
                b = clean_baseline[clean_baseline.detector == det][m]
                if len(b):
                    fig.add_hline(y=float(b.mean()) * 100, line=dict(color=s["color"], width=1, dash="dot"),
                                  opacity=0.45, **rc)
        fig.update_xaxes(title_text="SNR (dB) · noisier →", autorange="reversed",
                         tickvals=[24, 18, 12, 6, 0, -6], **rc)
        if stack or c == 1:
            fig.update_yaxes(title_text="%", **rc)
    # legend above the subplot titles, so the two never overlap
    base_layout(fig, height=height, margin=dict(l=8, r=8, t=78, b=8),
                legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="left", x=0, title_text="",
                            font=dict(size=12)))
    return fig


def ecg_window(t: np.ndarray, noisy: np.ndarray, clean: np.ndarray | None = None,
               ref_t: np.ndarray | None = None, outcome: dict | None = None,
               mask_spans: list[tuple[float, float]] | None = None, height: int = 340,
               title: str | None = None, noise: np.ndarray | None = None) -> go.Figure:
    """ECG trace on ECG paper with reference beats and (optionally) TP / FP / FN markers."""
    tk = tokens()
    mk = outcome_markers()
    fig = go.Figure()
    for a, b in mask_spans or []:
        fig.add_vrect(x0=a, x1=b, fillcolor=tk["noisy_shade"], line_width=0, layer="below")
    if clean is not None:
        fig.add_trace(go.Scattergl(x=t, y=clean, name="Clean ECG", line=dict(color=tk["clean"], width=1.2),
                                   hoverinfo="skip"))
    if noise is not None:
        fig.add_trace(go.Scattergl(x=t, y=noise, name="Added noise", line=dict(color=tk["noise"], width=1),
                                   hoverinfo="skip", visible="legendonly"))
    fig.add_trace(go.Scattergl(x=t, y=noisy, name="Test signal", line=dict(color=tk["trace"], width=1.5),
                               hovertemplate="%{y:.2f} mV<extra></extra>"))
    top = float(np.nanmax(noisy)) if noisy.size else 1.0
    span = float(np.nanmax(noisy) - np.nanmin(noisy)) if noisy.size else 1.0
    y_ref = top + 0.12 * span
    if ref_t is not None and ref_t.size:
        fig.add_trace(go.Scatter(x=ref_t, y=np.full(ref_t.size, y_ref), mode="markers",
                                 name="Reference beat", marker=ref_marker(),
                                 hovertemplate="reference beat %{x:.2f} s<extra></extra>"))
    if outcome:
        for key, label in (("tp", "Correct"), ("fp", "False detection"), ("fn", "Missed beat")):
            tt, yy = outcome.get(key, (np.array([]), np.array([])))
            if key == "fn":
                yy = np.full(tt.size, y_ref)
            fig.add_trace(go.Scatter(x=tt, y=yy, mode="markers", name=f"{label} ({tt.size})", marker=mk[key],
                                     hovertemplate=f"{label} %{{x:.2f}} s<extra></extra>"))
    base_layout(fig, height=height, title=dict(text=title, font=dict(size=14)) if title else None)
    ecg_grid(fig, span_mv=span)
    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="mV")
    fig.update_layout(hovermode="closest")
    return fig
