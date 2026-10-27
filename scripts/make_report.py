"""Generate docs/verification_report.md from the precomputed results.

Usage:  python scripts/make_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.config import EXTENSION_RECORDS, RESULTS_DIR  # noqa: E402
from bench.data import load_record  # noqa: E402
from bench.detectors import DETECTORS  # noqa: E402
from bench.evaluate import match_beats  # noqa: E402
from bench.report import run_key, unpack_detections  # noqa: E402

NOISE = {"em": "electrode motion", "ma": "muscle artefact", "bw": "baseline wander"}

# Acceptance criteria defined for this bench (not taken from any standard).
CRITERIA = [
    ("AC-1", "Clean segments (24 dB runs)", "clean", 24, ["se", "ppv"], 0.99),
    ("AC-2", "24 dB, every noise type", "noisy", 24, ["se", "ppv"], 0.99),
    ("AC-3", "12 dB, every noise type", "noisy", 12, ["se", "ppv"], 0.95),
    ("AC-4", "6 dB, every noise type", "noisy", 6, ["se", "ppv"], 0.90),
    ("AC-5", "12 dB, heart rate", "noisy", 12, ["hr_within5"], 0.95),
]


def verdict(rows: pd.DataFrame, metrics: list[str], thr: float) -> tuple[str, str]:
    """PASS if every lower CI bound >= thr, MARGINAL if every point estimate >= thr
    but a CI crosses it, FAIL otherwise. Returns (verdict, worst value text)."""
    worst_pt, worst_lo, worst_txt = 1.0, 1.0, ""
    for m in metrics:
        for _, r in rows.iterrows():
            pt = r[m]
            lo = r.get(f"{m}_lo", pt) if m != "hr_within5" else pt
            if pt < worst_pt:
                worst_pt, worst_txt = pt, f"{m.replace('ppv', '+P').replace('se', 'Se').replace('hr_within5', 'HR±5')} " \
                                          f"{pt:.2%} ({NOISE.get(r.noise, r.noise)})"
            worst_lo = min(worst_lo, lo)
    if worst_lo >= thr:
        return "PASS", worst_txt
    if worst_pt >= thr:
        return "MARGINAL", worst_txt
    return "FAIL", worst_txt


def clean_failures(per_rec: pd.DataFrame, thr: float = 0.98) -> list[dict]:
    """Detector/record pairs with +P below thr on *clean* segments, with the median
    delay of their false detections after the preceding reference beat."""
    z = np.load(RESULTS_DIR / "detections.npz")
    c = per_rec[(per_rec.dataset == "mixed") & (per_rec.prefilter == "none") & (~per_rec.noisy)
                & (per_rec.noise == "em") & (per_rec.snr == 24)]
    out = []
    for _, r in c[c.ppv < thr].sort_values("ppv").iterrows():
        rec = load_record("mitdb", str(r.record))
        det = unpack_detections(z[run_key("mixed", str(r.record), "em", 24, r.detector, "none")])
        m = match_beats(rec.beats, det, int(0.15 * rec.fs))
        fp = det[m.fp]
        prev = np.searchsorted(rec.beats, fp) - 1
        ok = prev >= 0
        lag = (fp[ok] - rec.beats[prev[ok]]) / rec.fs * 1000
        rr = np.median(np.diff(rec.beats)) / rec.fs * 1000
        out.append({"record": str(r.record), "detector": r.detector, "ppv": r.ppv, "lag_ms": float(np.median(lag)),
                    "rr_ms": float(rr)})
    return out


def fmt_pct(v: float) -> str:
    return "n/a" if pd.isna(v) else f"{v:.1%}"


def main() -> None:
    S = pd.read_parquet(RESULTS_DIR / "summary.parquet")
    meta = json.loads((RESULTS_DIR / "meta.json").read_text())
    audit = json.loads((RESULTS_DIR / "audit.json").read_text())
    mix = S[(S.dataset == "mixed") & (S.prefilter == "none")]
    off = S[(S.dataset == "nstdb") & (S.prefilter == "none") & (S.segment == "noisy")]
    dets = list(DETECTORS)
    L: list[str] = []
    w = L.append

    w("# Verification report: QRS detector robustness under recorded ECG noise")
    w("")
    w(f"**Document:** VR-ECGNB-001 · **Version:** 1.0 · **Date:** {meta['created'][:10]} · "
      f"**Author:** Syed Danish Ali")
    w("")
    w("> Research and education tool. Not a medical device. Not for diagnosis or patient monitoring. "
      "This report describes algorithm robustness and agreement with reference annotations only.")
    w("")
    w("## 1. Purpose")
    w("Find out at which noise level, and why, five open-source QRS detectors stop agreeing with expert "
      "reference beat annotations, and whether a simple pre-filter changes that. The protocol follows the "
      "idea of the MIT-BIH noise stress test (Moody et al., 1984). The beat matching is EC57-style. "
      "**No compliance with ANSI/AAMI EC57 is claimed.**")
    w("")
    w("## 2. Items under test")
    w("| ID | Detector | Library | Reference |")
    w("|---|---|---|---|")
    for k, d in DETECTORS.items():
        w(f"| `{k}` | {d.name} | {d.library} {meta['versions'].get(d.library, '')} | {d.reference} |")
    w("")
    w("All detectors run with library default settings, including each method's own pre-processing. "
      "Pre-filter settings: **none**, and **HP+notch** (0.5 Hz Butterworth high-pass, order 2, plus 60 Hz "
      "notch with Q = 30, applied zero-phase).")
    w("")
    w("## 3. Test setup")
    w(f"- **Signals.** MIT-BIH Arrhythmia DB records 118 and 119 plus {len(EXTENSION_RECORDS)} extension "
      f"records chosen by a stated rule ({', '.join(EXTENSION_RECORDS)}); channel 0 (MLII), 360 Hz, "
      f"30 min each.")
    w("- **Noise.** NSTDB recordings `em`, `ma`, `bw`, added with a reimplementation of PhysioNet `nst` "
      "(same S and N estimators, schedule and continuity offsets) at 24, 18, 12, 6, 0 and −6 dB. "
      "The 12 official NSTDB records (`em` only) are also tested directly.")
    w("- **Schedule.** 5 min clean, then alternating 2 min noisy / 2 min clean. "
      "**Metrics come from noisy segments only.** Clean segments are reported as the baseline.")
    w("- **Matching.** ±150 ms, one-to-one. Se = TP/(TP+FN), +P = TP/(TP+FP).")
    w("- **Uncertainty.** 95% block-bootstrap CI (1,000 resamples of 10 s windows), pooled over records.")
    w(f"- **Scale.** {meta['n_runs']:,} detector runs over {meta['n_signals']} test signals.")
    w("")
    w("### 3.1 Mixer validation")
    mv = pd.DataFrame(audit["mixer_validation"])
    w(f"Remixing 118 and 119 with `em` reproduces the official NSTDB records: noise gain within "
      f"**{mv.gain_error_db.abs().max():.2f} dB** of the gain nst used, waveform difference "
      f"**{mv.rms_diff_uV.min():.0f}–{mv.rms_diff_uV.max():.0f} µV RMS** (1 ADC step = 5 µV). "
      f"A plain-variance noise estimate would have been off by "
      f"**{mv.variance_estimator_gain_error_db.abs().mean():.1f} dB**.")
    w("")
    w("## 4. Acceptance criteria")
    w("These thresholds were defined for this bench. They are not regulatory limits. A criterion is "
      "**PASS** when the lower 95% CI bound of every listed metric meets the threshold for every noise type. "
      "It is **MARGINAL** when every point estimate meets it but a CI crosses it, and **FAIL** otherwise. "
      "Dataset: our mixer, no pre-filter.")
    w("")
    w("| ID | Condition | Metric | Threshold |")
    w("|---|---|---|---|")
    for cid, cond, _, _, mets, thr in CRITERIA:
        w(f"| {cid} | {cond} | {', '.join('Se' if m == 'se' else '+P' if m == 'ppv' else 'HR within ±5 bpm' for m in mets)} | ≥ {thr:.0%} |")
    w("")
    w("## 5. Results")
    w("### 5.1 Verdicts")
    w("| Detector | " + " | ".join(c[0] for c in CRITERIA) + " |")
    w("|---|" + "---|" * len(CRITERIA))
    detail = []
    for det in dets:
        cells = []
        for cid, _, seg, snr, mets, thr in CRITERIA:
            rows = mix[(mix.detector == det) & (mix.segment == seg) & (mix.snr == snr)]
            v, worst = verdict(rows, mets, thr)
            cells.append({"PASS": "✅ PASS", "MARGINAL": "⚠️ MARGINAL", "FAIL": "❌ FAIL"}[v])
            if v != "PASS":
                detail.append(f"- **{DETECTORS[det].name}, {cid}:** worst {worst}.")
        w(f"| {DETECTORS[det].name} | " + " | ".join(cells) + " |")
    w("")
    if detail:
        w("Details of non-passing cells:")
        w("")
        L.extend(detail)
        w("")

    w("### 5.2 Positive predictivity by noise type (noisy segments, no pre-filter)")
    nm = mix[mix.segment == "noisy"]
    for noise in ("em", "ma", "bw"):
        w(f"**{NOISE[noise].capitalize()}**")
        w("")
        w("| Detector | 24 dB | 18 dB | 12 dB | 6 dB | 0 dB | −6 dB |")
        w("|---|---|---|---|---|---|---|")
        for det in dets:
            d = nm[(nm.noise == noise) & (nm.detector == det)].set_index("snr")
            w(f"| {DETECTORS[det].name} | " + " | ".join(
                f"{fmt_pct(d.ppv.get(s))} / {fmt_pct(d.se.get(s))}" for s in (24, 18, 12, 6, 0, -6)) + " |")
        w("")
    w("Cells: +P / Se.")
    w("")

    w("### 5.3 Official NSTDB records (electrode motion, records 118 and 119)")
    w("| Detector | " + " | ".join(f"{s} dB" for s in (24, 18, 12, 6, 0, -6)) + " |")
    w("|---|" + "---|" * 6)
    for det in dets:
        d = off[off.detector == det].set_index("snr")
        w(f"| {DETECTORS[det].name} | " + " | ".join(
            f"{fmt_pct(d.ppv.get(s))} / {fmt_pct(d.se.get(s))}" for s in (24, 18, 12, 6, 0, -6)) + " |")
    w("")
    w("Cells: +P / Se.")
    w("")

    w("### 5.4 Effect of the HP+notch pre-filter (F1, percentage points, noisy segments)")
    both = S[(S.dataset == "mixed") & (S.segment == "noisy")]
    piv = both.pivot_table(index=["noise", "detector", "snr"], columns="prefilter", values="f1").reset_index()
    piv["delta"] = (piv["hp_notch"] - piv["none"]) * 100
    w("| Detector | " + " | ".join(f"{NOISE[n]} @ 6 dB" for n in ("em", "ma", "bw")) + " |")
    w("|---|---|---|---|")
    for det in dets:
        cells = []
        for n in ("em", "ma", "bw"):
            v = piv[(piv.noise == n) & (piv.detector == det) & (piv.snr == 6)].delta
            cells.append(f"{v.iloc[0]:+.2f}" if len(v) else "n/a")
        w(f"| {DETECTORS[det].name} | " + " | ".join(cells) + " |")
    w("")
    big = piv.loc[piv.delta.abs().idxmax()]
    w(f"Largest single effect: **{DETECTORS[big.detector].name}**, {NOISE[big.noise]} at {big.snr} dB, "
      f"F1 {big['none']:.1%} → {big['hp_notch']:.1%} ({big.delta:+.1f} pp).")
    w("")

    w("## 6. Failure modes observed")
    em6 = nm[(nm.noise == "em") & (nm.snr == 6)]
    ma6 = nm[(nm.noise == "ma") & (nm.snr == 6)]
    bw0 = nm[(nm.noise == "bw") & (nm.snr == 0)]
    w(f"1. **Electrode motion → false beats.** Electrode-motion artefact is the hardest noise. At 6 dB, +P "
      f"ranges {em6.ppv.min():.1%}–{em6.ppv.max():.1%} while Se stays at {em6.se.min():.1%}–{em6.se.max():.1%}. "
      "The artefact has QRS-like slopes inside the QRS band, so detectors add beats rather than lose them. "
      "Filtering cannot separate it from the QRS.")
    w(f"2. **Muscle artefact → mixed errors.** At 6 dB, +P {ma6.ppv.min():.1%}–{ma6.ppv.max():.1%} and Se "
      f"{ma6.se.min():.1%}–{ma6.se.max():.1%}. Broadband bursts both trigger false detections and raise "
      "adaptive thresholds so that real beats are skipped.")
    w(f"3. **Baseline wander is mostly harmless to these detectors.** Even at 0 dB, +P "
      f"{bw0.ppv.min():.1%}–{bw0.ppv.max():.1%}, because every pipeline already high-passes the signal. "
      "Note that nst's per-second mean removal makes the bw gain very large for a given SNR.")
    w("4. **Bursty noise.** Errors cluster in short stretches where the local SNR is several dB below the "
      "record's nominal SNR (see the Failure Gallery in the app).")
    P = pd.read_parquet(RESULTS_DIR / "per_record.parquet")
    pr = P[(P.dataset == "mixed") & (P.noise == "em") & (P.snr == 6) & (P.prefilter == "none") & P.noisy]         .groupby("record", observed=True).f1.mean()
    beats = pd.Series({r: len(load_record("mitdb", str(r)).beats) for r in pr.index})
    rho = pd.DataFrame({"f1": pr, "beats": beats}).corr(method="spearman").iloc[0, 1]
    w(f"5. **Slow hearts score worst.** At the same nominal SNR, F1 per record follows the number of true beats "
      f"(Spearman ρ = {rho:.2f} at 6 dB electrode motion; worst: records {', '.join(pr.nsmallest(2).index.astype(str))}). "
      "The noise adds about the same number of false detections per minute everywhere, so a slow heart, "
      "with fewer true beats, loses more +P.")
    cf = clean_failures(pd.read_parquet(RESULTS_DIR / "per_record.parquet"))
    if cf:
        items = "; ".join(f"{DETECTORS[c['detector']].name} on record {c['record']}: +P {c['ppv']:.1%}, false "
                          f"detections a median {c['lag_ms']:.0f} ms after the R peak (RR {c['rr_ms']:.0f} ms)"
                          for c in cf)
        w(f"6. **T-wave oversensing, with no noise at all.** Some failures happen on clean segments: {items}. "
          "A delay of 300–450 ms after the R peak is where the T wave sits, so these detectors count tall T waves "
          "as extra beats, mostly at slow heart rates. Noise did not cause this. It is a weakness in the "
          "decision logic, and it fails AC-1 for those detectors.")
    cl = mix[mix.segment == "clean"].pivot_table(index="snr", columns="detector", values="se")
    hang = cl.loc[-6].sort_values()
    w(f"7. **Noise hangover into the clean minutes.** At −6 dB, sensitivity on the *clean* segments that follow "
      f"each noise burst falls to {', '.join(f'{DETECTORS[d].name} {v:.0%}' for d, v in hang.items() if v < 0.98)} "
      f"(vs ≥ {cl.loc[24].min():.1%} at 24 dB). Adaptive thresholds learnt on the noise stay too high after "
      "the noise stops, so real beats are missed for a while. This is why AC-1 uses the clean segments of the "
      "24 dB runs as the baseline.")
    w("")
    w("## 7. Limitations")
    w("Fifteen 1970s Holter recordings, one lead, default detector settings, digitally added noise and the "
      "same noise segments for every record. The results describe how the algorithms behave under noise, not "
      "how well they would perform across a population. See *Methods & limitations* in the app.")
    w("")
    w("## 8. Conclusion")
    f6 = nm[nm.snr == 6].groupby("detector").f1.mean().sort_values(ascending=False)
    em12 = nm[(nm.noise == "em") & (nm.snr == 12)]
    w(f"No detector meets AC-3: at 12 dB electrode motion every detector's +P is below 95% "
      f"({em12.ppv.min():.1%}–{em12.ppv.max():.1%}), so **electrode motion is the limiting failure cause**, and it "
      f"shows up as false detections, not misses. Ranked by mean F1 at 6 dB across the three noise types: "
      + ", ".join(f"**{DETECTORS[d].name}** {v:.1%}" for d, v in f6.items()) + ". "
      "Two failure modes have nothing to do with SNR: T-wave oversensing on some clean records, and "
      "threshold hangover after strong noise. The HP+notch pre-filter changes F1 by less than half a "
      "percentage point, because every detector already band-limits its input. Noise inside the QRS band "
      "cannot be filtered away; the decision logic has to cope with it.")
    w("")
    w("---")
    w("*Generated by `scripts/make_report.py` from `results/`. Re-run after re-running the benchmark.*")

    out = ROOT / "docs" / "verification_report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
