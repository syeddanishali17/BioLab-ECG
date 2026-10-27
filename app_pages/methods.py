import pandas as pd
import streamlit as st

from bench.config import BEAT_SYMBOLS, EXTENSION_RECORDS
from bench.detectors import DETECTORS
from ui import data
from ui.style import overline

overline("Documentation", "mt")
st.title("Methods & limitations")
st.markdown("How the bench works, what was checked, and what the results do **not** show.")

audit = data.json_result("audit.json")
meta = data.meta()

tab_data, tab_snr, tab_eval, tab_audit, tab_lim, tab_cite = st.tabs(
    ["Data", "SNR & mixing", "Evaluation", "Data audit", "Limitations", "Citations"])

with tab_data:
    st.markdown(f"""
#### Records
- **MIT-BIH Noise Stress Test Database (NSTDB) v1.0.0**: 12 ready-made records (MIT-BIH 118 and 119 with
  electrode-motion noise at 24, 18, 12, 6, 0 and −6 dB) plus the three noise recordings: `bw` (baseline
  wander), `ma` (muscle artefact) and `em` (electrode motion).
- **MIT-BIH Arrhythmia Database v1.0.0**: the clean sources 118 and 119, plus {len(EXTENSION_RECORDS)}
  extension records so results are not limited to two subjects.
- All records: 360 Hz, 11-bit, 30 min 5 s, two leads. The bench scores **channel 0 (MLII)**.

#### Extension-record selection rule
A record is included if **all** hold: channel 0 is MLII · no paced beats · the only rhythm annotation is
normal sinus rhythm · one beat label among N / L / R covers ≥ 95% of beats · at most 15 signal-quality (`~`)
annotations · not 118 or 119. Result: **{", ".join(EXTENSION_RECORDS)}**. The rule keeps failures about
noise, not about arrhythmia. Script: `scripts/select_records.py`.

#### Reference beats
Annotation symbols counted as beats: `{"".join(sorted(BEAT_SYMBOLS))}`. Rhythm changes, signal-quality
markers and other non-beat annotations are excluded.
""")

with tab_snr:
    st.markdown("#### SNR definition (as PhysioNet's `nst`)")
    st.latex(r"\mathrm{SNR} = 10\log_{10}\frac{S}{N},\qquad S=\frac{pp^2}{8},\qquad N = \mathrm{rms}^2")
    st.latex(r"a = 10^{-\mathrm{SNR}/20}\,\frac{\sqrt{2}}{4}\,\frac{pp}{\mathrm{rms}}")
    st.markdown("""
- **pp**: peak-to-peak amplitude within ±50 ms of each of the first 300 normal beats, 5%-trimmed mean
  (`sigamp -a`). S = pp²/8 is the power of a sine wave with that peak-to-peak amplitude.
- **rms**: RMS of each of the first 300 one-second windows of the noise record, **each window mean-removed**,
  5%-trimmed mean (`sigamp -r`). The per-second mean removal acts as a high-pass filter. This is the
  "frequency weighting" in nst's SNR, and it is why baseline wander needs a large gain to reach a given SNR.
- **Schedule**: 5 minutes clean, then 2-minute noisy and clean segments alternating to the end.
- **Continuity offset**: whenever the gain changes, nst adds a constant so the output has no step. Our mixer
  does the same.

The estimators were read from the WFDB source (`app/nst.c`, `app/sigamp.c`) and reimplemented in
`bench/mixer.py`. The validation against the official records is in the *Data audit* tab.
""")

with tab_eval:
    st.markdown("""
#### Beat matching
A detection matches a reference beat if it lies within **±150 ms**, one-to-one, closest pairs first.
Unmatched detections are false positives (FP), unmatched reference beats false negatives (FN). The 150 ms
tolerance follows EC57-style evaluation as cited by Gupta et al. (arXiv 2107.05469). **This is not a claim
of compliance with ANSI/AAMI EC57.**

#### Metrics
- Se = TP / (TP + FN), +P = TP / (TP + FP), F1 = 2TP / (2TP + FP + FN).
- **Noisy segments only.** Each record is cut into 10-second windows. A window is noisy if most of its
  samples carry added noise. Clean windows are reported separately as a baseline.
- **Heart rate**: per 10 s window, from mean RR of the detections vs the reference. A window where the
  detector yields no heart rate counts as outside ±5 bpm.
- **Uncertainty**: 95% percentile CI from a block bootstrap with 1,000 resamples of whole 10-second windows
  (beats inside a window share noise and are correlated).

#### Detectors
Each detector is its library's published pipeline, including that method's own pre-processing.
""")
    st.dataframe(pd.DataFrame([{"Detector": d.name, "Library": d.library, "Reference": d.reference}
                               for d in DETECTORS.values()]), hide_index=True, alt="Detectors")
    st.markdown("""
The optional **bench pre-filter** (0.5 Hz Butterworth high-pass, order 2, plus 60 Hz notch, Q = 30) runs
forward-backward before the detector, so it adds no delay.
""")
    if meta:
        st.caption(f"Benchmark created {meta.get('created')} · {meta.get('n_runs'):,} runs · "
                   + " · ".join(f"{k} {v}" for k, v in meta.get("versions", {}).items()))

with tab_audit:
    if not audit:
        st.info("Run `python scripts/data_audit.py` to populate this tab.")
    else:
        fs = sorted({h["fs"] for h in audit["headers"]})
        mv = pd.DataFrame(audit["mixer_validation"])
        st.markdown(f"""
#### What the audit confirmed
- **Sampling rate** from every header: {", ".join(f"{f:g} Hz" for f in fs)}.
- **Noise schedule.** Recovered by subtracting the clean MIT-BIH record from each NSTDB record. It agrees with
  the documented protocol on **≥ {min(m["agreement_with_protocol"] for m in audit["masks"]) * 100:.3f}%** of
  samples in all 12 records (7 noisy segments, 13.1 noisy minutes each).
- **Both channels** carry noise (residual step size MLII
  {audit["noise_per_channel"]["MLII"] * 1000:.1f} µV, V1 {audit["noise_per_channel"]["V1"] * 1000:.1f} µV).
- **Mains frequency**: spectral peak {audit["mains"]["peak_60Hz_dB_above_floor"]:.1f} dB above the floor at
  60 Hz vs {audit["mains"]["peak_50Hz_dB_above_floor"]:.1f} dB at 50 Hz, as expected for US recordings.

#### Surprises (written down, as the spec asked)
1. **Clean segments are not identical to the clean record.** After each noisy segment, the NSTDB signal
   carries a constant DC offset (for example −44 ADC units = −0.22 mV in 118e24). The cause is nst's
   continuity offset. A plain "residual ≠ 0" mask marks the whole record as noisy, so the bench marks
   noise where the residual *changes* from sample to sample.
2. **NSTDB headers declare the wrong baseline.** nst removed the ADC zero (1024) from the samples but the
   headers still say baseline 1024, so a naive reader shifts every official record by −5.12 mV. The loader
   corrects this.
3. **A plain-variance SNR is about 7.25 dB off.** Measuring noise as the plain variance of the added noise,
   as an earlier draft of the spec suggested, makes the official "0 dB" records equivalent to about −7 dB.
   Using nst's estimators instead removes the gap.
""")
        st.markdown("#### Mixer validation: remixing 118 / 119 + em and comparing with the official records")
        show = mv[["record", "nominal_snr_db", "nst_gain_fitted", "our_gain", "gain_error_db",
                   "variance_estimator_gain_error_db", "rms_diff_uV", "within_5lsb_pct", "fit_r"]]
        st.dataframe(show, hide_index=True, alt="Mixer validation against official NSTDB records",
                     column_config={
                         "nominal_snr_db": st.column_config.NumberColumn("SNR (dB)"),
                         "nst_gain_fitted": st.column_config.NumberColumn("nst gain (fitted)", format="%.4f"),
                         "our_gain": st.column_config.NumberColumn("Our gain", format="%.4f"),
                         "gain_error_db": st.column_config.NumberColumn("Gain error (dB)", format="%+.3f"),
                         "variance_estimator_gain_error_db": st.column_config.NumberColumn(
                             "Plain-variance error (dB)", format="%+.2f"),
                         "rms_diff_uV": st.column_config.NumberColumn("Waveform RMS diff (µV)", format="%.1f"),
                         "within_5lsb_pct": st.column_config.NumberColumn("Samples within 5 LSB", format="%.2f%%"),
                         "fit_r": st.column_config.NumberColumn("Fit r", format="%.4f"),
                     })
        st.caption(f"Our gains are within {mv.gain_error_db.abs().max():.2f} dB of the gains nst used. The "
                   f"remixed waveforms differ from the official files by {mv.rms_diff_uV.min():.0f}–"
                   f"{mv.rms_diff_uV.max():.0f} µV RMS, mostly 1-LSB rounding of the continuity offset "
                   "(nst works in integers). For scale: one ADC step is 5 µV.")

with tab_lim:
    st.markdown("""
- **Few subjects.** NSTDB has two underlying subjects. The 13 extension records help, but 15 Holter records
  are not a population. Results show how the algorithms behave under noise, not how well they would perform
  across a population.
- **Default settings.** Every detector runs with its library defaults. Tuning could change the ranking.
- **Old recordings.** MIT-BIH data comes from 1975–1979 Holter recordings. Modern wearables differ in
  electrodes, sampling rate and noise.
- **Synthetic mixing.** Noise is recorded but added digitally to separate recordings. Real artefacts can
  correlate with the ECG (for example motion during exercise raises heart rate). Additive mixing cannot show
  that.
- **One lead.** Only channel 0 (MLII) is scored. Multi-lead detectors could do better.
- **Same noise segments.** Every record gets the same stretches of the three noise recordings, aligned in time,
  as nst does. The noise sample is small.
- **Reference annotations are not perfect truth**, although MIT-BIH annotations are widely used as reference.
- **Not EC57 compliance.** The evaluation follows EC57-style beat matching. No compliance is claimed.
""")
    st.info("Research and education tool. Not a medical device. Not for diagnosis or patient monitoring. "
            "The bench measures algorithm robustness and agreement with reference annotations.",
            icon=":material/gavel:")

with tab_cite:
    st.markdown("""
- Moody GB, Muldrow WE, Mark RG. *A noise stress test for arrhythmia detectors.* Computers in Cardiology
  1984; 11:381–384.
- MIT-BIH Noise Stress Test Database v1.0.0. PhysioNet. https://doi.org/10.13026/C2HS3T
- Moody G, Mark R. MIT-BIH Arrhythmia Database (version 1.0.0). PhysioNet. https://doi.org/10.13026/C2F305
- PhysioNet: cite the current platform reference listed on the dataset pages.
- `nst` and `sigamp`, WFDB Software Package: https://physionet.org/physiotools/wag/nst-1.htm
- Gupta et al., beat-matching tolerance: https://arxiv.org/abs/2107.05469
- Makowski D. et al. *NeuroKit2: A Python toolbox for neurophysiological signal processing.*
  Behavior Research Methods 2021.
- Pan J, Tompkins WJ. *A real-time QRS detection algorithm.* IEEE TBME 1985.
- Hamilton P. *Open source ECG analysis.* Computers in Cardiology 2002.
- Elgendi M, Jonkman M, De Boer F. *Frequency bands effects on QRS detection.* BIOSIGNALS 2010.
- Data licence (bench): Open Data Commons Attribution License v1.0.

**Learn chapters**
- CEBS database (ECG, breathing, seismocardiogram; BIOPAC MP36), PhysioNet, ODC-By 1.0. García-González MA et
  al., Computing in Cardiology 2013.
- Pulse Transit Time PPG Dataset v1.1.0, PhysioNet, ODbL 1.0. Mehrgardt P et al. Excerpts in this app are
  shared under ODbL 1.0.
- PhysioNet/CinC Challenge 2016 heart-sound database, ODC-By 1.0. Liu C et al., Physiol Meas 2016.
- The cardiac-cycle (Wiggers) diagram in chapter 3 is a simplified model written for this app, not a
  recording.
""")
