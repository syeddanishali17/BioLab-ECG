# ECG Noise Stress-Test Bench

**A test bench that stresses heartbeat-detection algorithms with real recorded noise and reports where
they break, the way device makers test their algorithms.**

> **Research and education tool. Not a medical device. Not for diagnosis or patient monitoring.**

[**Live app**](https://biolab-ecg.streamlit.app) · [Verification report](docs/verification_report.md) ·
[Methods](#methods) · [Learn track](#learn-track-for-newcomers-to-biosignals)

Two parts in one app: a **verification bench** for QRS detectors under recorded noise, and a **Learn track**
that teaches ECG, heart sounds, PPG, breathing and motion with real recordings (made for a biosignals class
using a BIOPAC MP36).

---

## What it does

Every ECG device has to keep finding heartbeats while electrodes move, muscles fire and the baseline drifts.
This bench takes clean ECG with expert-annotated beat locations from PhysioNet, adds **real recorded
noise** (electrode motion, muscle artefact, baseline wander) at controlled signal-to-noise ratios from
**24 dB down to −6 dB**, and measures when and why five open-source QRS detectors start to fail.

| Page | What you can do |
|---|---|
| **Overview** | The headline result: Se and +P vs SNR on the official NSTDB records |
| **Noise lab** | Mix any noise into any of 15 records at any SNR, overlay a detector live, inspect spectra |
| **Filter designer** | Design IIR/FIR filters, see magnitude, phase and group delay, measure the beat delay a causal filter adds |
| **Detector benchmark** | Se, +P, F1 and heart-rate agreement vs SNR with bootstrap CIs, breaking-point table, pre-filter effect, per-record breakdown, CSV export |
| **Failure gallery** | The worst 10-second windows per detector, annotated, with an explanation of each failure mode |
| **Verification report** | A test-protocol-style report with acceptance criteria and PASS / MARGINAL / FAIL verdicts |
| **Methods & limitations** | SNR definition, matching rule, data-audit findings, mixer validation, citations |

### Learn track (for newcomers to biosignals)

Eight short chapters and a glossary, built on real open recordings, following a typical biosignals lab (BIOPAC MP36):

| Chapter | Interactive centrepiece |
|---|---|
| Start here | One averaged heartbeat seen by ECG, heart sound, PPG and accelerometer; step through the event sequence |
| The ECG | Rotate the heart's electrical vector and see what each lead records; a real beat with P, QRS and T labelled |
| Heart rate & breathing | R-R interval → HR with a BIOPAC-style calculation channel; rest vs activity; respiratory sinus arrhythmia |
| Heart, valves & sounds | Circulation step-through; a pressure-driven cardiac-cycle model with valve states; real heart sounds to play |
| PPG: the pulse | Pulse landmarks, pulse arrival time after the R peak, HR from PPG vs ECG, breathing in the PPG |
| Motion & interference | Accelerometer vs motion artefacts while walking and running; 50/60 Hz, baseline wander, EMG and filters |
| How signals are recorded | Sampling rate and aliasing, ADC resolution, calculation channels |
| Exam practice | Cheat sheet, 10-question self-check, read-the-graph exercise, drawing checklist |
| Glossary | 128 terms in 11 topics (incl. electrodes, current through the body, earth vs isolated ground, safety), a clickable concept map of how they connect, search, real-signal illustrations, study-sheet download, shareable `?term=` links |

Data for the Learn track: CEBS (BIOPAC MP36 recordings), Pulse Transit Time PPG and PhysioNet/CinC 2016
heart sounds. Rebuild with `python scripts/fetch_learning_data.py` then `python scripts/build_learning_data.py`.

## Key results

2,820 detector runs (282 test signals × 5 detectors × 2 pre-filter settings): 61 hours of noisy test ECG, each scored by all 10 detector configurations.
Full tables, acceptance criteria and verdicts: [docs/verification_report.md](docs/verification_report.md).

1. **Electrode motion is the limiting noise, and it causes false beats, not misses.** At 6 dB, +P drops to
   66–73% while Se stays at 88–97%. At 12 dB no detector reaches 95% +P. The artefact sits inside the QRS
   band, so filtering cannot remove it.
2. **Our nst reimplementation matches the official NSTDB.** Noise gains match within 0.06 dB and waveforms
   within < 50 µV RMS on all 12 records, and the benchmark curves for official and remixed records agree to
   within about 1–2 points.
3. **A pre-filter does not help.** A 0.5 Hz high-pass plus 60 Hz notch changes F1 by less than 0.5 percentage
   points, because every detector already band-limits its input.
4. **Two failure modes do not depend on SNR.**
   - *T-wave oversensing:* NeuroKit2 reaches only 63.5% +P on the **clean** segments of record 113, with false
     beats ~330 ms after each R peak (tall T waves at ~59 bpm). Hamilton does the same on records 115 and 117.
   - *Threshold hangover:* after −6 dB noise, Pan-Tompkins finds only 64% of beats in the following
     **clean** minutes, because its adaptive threshold stays inflated.
5. **Slow hearts score worst.** Per-record F1 follows the beat count (Spearman ρ = 0.96), because the noise
   adds a similar number of false beats per minute everywhere.
6. **Ranking** by mean F1 at 6 dB across the three noise types: NeuroKit2 89.1%, XQRS 88.3%, Hamilton 86.5%,
   Pan-Tompkins 86.4%, Elgendi 85.3%. Each detector ran with its default settings.

## Methods

- **Data.** MIT-BIH Noise Stress Test Database (12 ready-made records + `bw`, `ma`, `em` noise) and
  MIT-BIH Arrhythmia Database records 118, 119 plus 13 extension records chosen by a stated rule
  (MLII lead, no pacing, sinus rhythm only, one dominant beat type ≥ 95%, ≤ 15 signal-quality annotations).
  Reference beats: annotation symbols `NLRBAaJSVrFejnE/fQ?`.
- **Noise mixing.** A reimplementation of PhysioNet `nst`, with the estimators read from the WFDB source
  (`app/nst.c`, `app/sigamp.c`). S = pp²/8, where pp is the 5%-trimmed mean of the peak-to-peak amplitude
  within ±50 ms of the first 300 normal beats. N = rms², where rms is the 5%-trimmed mean of per-second,
  mean-removed RMS over the first 300 s of the noise record. Schedule: 5 min clean, then 2 min noisy /
  2 min clean. Continuity offsets at gain changes, as in nst.
- **Detectors.** NeuroKit2 (default), Pan-Tompkins, Hamilton, Elgendi (all via NeuroKit2 0.2.13, each with
  its own cleaning step) and PhysioNet's XQRS (wfdb 4.3.1). Each is run with and without an extra
  zero-phase 0.5 Hz high-pass + 60 Hz notch.
- **Evaluation.** ±150 ms one-to-one beat matching (EC57-style; **no EC57 compliance is claimed**). Se,
  +P, F1 and heart-rate error per 10 s window. **Noisy segments only**, with clean segments as the baseline.
  95% CIs from a block bootstrap over 10 s windows.

### Data audit findings

Checkpoint 0 found three things the documentation does not say:

1. **"Clean" NSTDB segments are offset.** After each noisy segment the signal carries a constant DC
   offset (e.g. −0.22 mV in 118e24), because nst adds a continuity offset whenever the gain changes.
   Masking "residual ≠ 0" marks the whole record noisy. The bench masks where the residual *changes*
   instead, which agrees with the documented schedule on ≥ 99.997% of samples.
2. **NSTDB headers declare the wrong baseline.** nst subtracted the ADC zero (1024) but left baseline 1024
   in the header, so naive readers shift every official record by −5.12 mV. Corrected at load time.
3. **SNR definitions matter.** A plain-variance noise estimate is ~7.25 dB off nst's. With nst's own
   estimators our gains are within 0.06 dB.

Also confirmed: 360 Hz in every header, noise on both channels, 60 Hz mains.

## Run it locally

```bash
git clone https://github.com/syeddanishali17/BioLab-ECG.git
```

```bash
cd BioLab-ECG
```

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
```

```bash
.venv/Scripts/python -m streamlit run streamlit_app.py
```

(On macOS/Linux use `.venv/bin/python`.) The data and precomputed results are in the repository, so the
app starts without downloads.

### Reproduce everything from scratch

```bash
python scripts/fetch_data.py
```

```bash
python scripts/data_audit.py
```

```bash
python scripts/run_benchmark.py
```

```bash
python scripts/make_report.py
```

```bash
python scripts/build_notebook.py
```

```bash
python -m pytest
```

`fetch_data.py` downloads MIT-BIH from PhysioNet's AWS Open Data mirror and NSTDB from physionet.org in
parallel (single connections to physionet.org can be very slow). The benchmark takes about 15 minutes on 12
cores and writes `results/`.

## Deploy (Streamlit Community Cloud)

1. Push this repository to GitHub (public).
2. On https://share.streamlit.io choose **Create app → From existing repo**. Main file: `streamlit_app.py`.
   In *Advanced settings* choose Python 3.12.
3. No secrets are needed.

Free-tier apps sleep after 12 hours without traffic. Open the link before interviews or before sending
applications.

## Repository layout

```
streamlit_app.py       entry point: navigation, page config, disclaimer footer
app_pages/             one file per page
ui/                    shared UI: styles, charts, cached data access, glossary tooltips
bench/                 the test bench (no Streamlit imports)
  data.py              load records and reference beats
  segments.py          noisy/clean masks
  mixer.py             nst reimplementation
  filters.py           filter designs and responses
  detectors.py         five detectors behind one interface
  evaluate.py          beat matching, Se, +P, F1, HR error, block bootstrap
  signals.py           test-signal builders shared by benchmark and app
  audit.py             checkpoint 0 data audit
  report.py            aggregation helpers
scripts/               fetch data, select records, audit, benchmark, derive tables, report, notebook
notebooks/             00_data_audit.ipynb
results/               precomputed tables (parquet, npz, json)
docs/                  verification report
tests/                 unit tests (synthetic cases with known TP/FP/FN) + a render test for every page
data/                  PhysioNet records (ODC-By 1.0, see DATA_ATTRIBUTION.md)
```

## Wording

The bench reports *detection performance*, *signal quality*, *algorithm robustness* and *agreement with
reference annotations*. It does not detect arrhythmia, diagnose or monitor anyone.

## Citations

- Moody GB, Muldrow WE, Mark RG. A noise stress test for arrhythmia detectors. *Computers in Cardiology*
  1984; 11:381–384.
- MIT-BIH Noise Stress Test Database v1.0.0. PhysioNet. https://doi.org/10.13026/C2HS3T
- Moody G, Mark R. MIT-BIH Arrhythmia Database v1.0.0. PhysioNet. https://doi.org/10.13026/C2F305
- PhysioNet platform: cite the current reference listed on the dataset pages.
- Makowski D, et al. NeuroKit2: A Python toolbox for neurophysiological signal processing.
  *Behavior Research Methods* 2021.
- Gupta et al. (150 ms tolerance): https://arxiv.org/abs/2107.05469

## Licence

Code: MIT (see `LICENSE`). Data: Open Data Commons Attribution License v1.0 (see `DATA_ATTRIBUTION.md`).
