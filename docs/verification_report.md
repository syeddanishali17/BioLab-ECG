# Verification report: QRS detector robustness under recorded ECG noise

**Document:** VR-ECGNB-001 · **Version:** 1.0 · **Date:** 2026-10-27 · **Author:** Syed Danish Ali

> Research and education tool. Not a medical device. Not for diagnosis or patient monitoring. This report describes algorithm robustness and agreement with reference annotations only.

## 1. Purpose
Find out at which noise level, and why, five open-source QRS detectors stop agreeing with expert reference beat annotations, and whether a simple pre-filter changes that. The protocol follows the idea of the MIT-BIH noise stress test (Moody et al., 1984). The beat matching is EC57-style. **No compliance with ANSI/AAMI EC57 is claimed.**

## 2. Items under test
| ID | Detector | Library | Reference |
|---|---|---|---|
| `neurokit` | NeuroKit2 | neurokit2 0.2.13 | Makowski et al. 2021 (default method) |
| `pantompkins` | Pan-Tompkins | neurokit2 0.2.13 | Pan & Tompkins 1985 |
| `hamilton` | Hamilton | neurokit2 0.2.13 | Hamilton 2002 |
| `elgendi` | Elgendi | neurokit2 0.2.13 | Elgendi et al. 2010 |
| `xqrs` | XQRS | wfdb 4.3.1 | PhysioNet WFDB XQRS |

All detectors run with library default settings, including each method's own pre-processing. Pre-filter settings: **none**, and **HP+notch** (0.5 Hz Butterworth high-pass, order 2, plus 60 Hz notch with Q = 30, applied zero-phase).

## 3. Test setup
- **Signals.** MIT-BIH Arrhythmia DB records 118 and 119 plus 13 extension records chosen by a stated rule (100, 101, 103, 109, 111, 112, 113, 115, 116, 117, 121, 122, 123); channel 0 (MLII), 360 Hz, 30 min each.
- **Noise.** NSTDB recordings `em`, `ma`, `bw`, added with a reimplementation of PhysioNet `nst` (same S and N estimators, schedule and continuity offsets) at 24, 18, 12, 6, 0 and −6 dB. The 12 official NSTDB records (`em` only) are also tested directly.
- **Schedule.** 5 min clean, then alternating 2 min noisy / 2 min clean. **Metrics come from noisy segments only.** Clean segments are reported as the baseline.
- **Matching.** ±150 ms, one-to-one. Se = TP/(TP+FN), +P = TP/(TP+FP).
- **Uncertainty.** 95% block-bootstrap CI (1,000 resamples of 10 s windows), pooled over records.
- **Scale.** 2,820 detector runs over 282 test signals.

### 3.1 Mixer validation
Remixing 118 and 119 with `em` reproduces the official NSTDB records: noise gain within **0.06 dB** of the gain nst used, waveform difference **7–48 µV RMS** (1 ADC step = 5 µV). A plain-variance noise estimate would have been off by **7.3 dB**.

## 4. Acceptance criteria
These thresholds were defined for this bench. They are not regulatory limits. A criterion is **PASS** when the lower 95% CI bound of every listed metric meets the threshold for every noise type. It is **MARGINAL** when every point estimate meets it but a CI crosses it, and **FAIL** otherwise. Dataset: our mixer, no pre-filter.

| ID | Condition | Metric | Threshold |
|---|---|---|---|
| AC-1 | Clean segments (24 dB runs) | Se, +P | ≥ 99% |
| AC-2 | 24 dB, every noise type | Se, +P | ≥ 99% |
| AC-3 | 12 dB, every noise type | Se, +P | ≥ 95% |
| AC-4 | 6 dB, every noise type | Se, +P | ≥ 90% |
| AC-5 | 12 dB, heart rate | HR within ±5 bpm | ≥ 95% |

## 5. Results
### 5.1 Verdicts
| Detector | AC-1 | AC-2 | AC-3 | AC-4 | AC-5 |
|---|---|---|---|---|---|
| NeuroKit2 | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL |
| Pan-Tompkins | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL |
| Hamilton | ❌ FAIL | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL |
| Elgendi | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL |
| XQRS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL |

Details of non-passing cells:

- **NeuroKit2, AC-1:** worst +P 96.77% (muscle artefact).
- **NeuroKit2, AC-2:** worst +P 96.43% (electrode motion).
- **NeuroKit2, AC-3:** worst +P 81.85% (electrode motion).
- **NeuroKit2, AC-4:** worst +P 69.13% (electrode motion).
- **NeuroKit2, AC-5:** worst HR±5 34.79% (electrode motion).
- **Pan-Tompkins, AC-3:** worst +P 88.57% (muscle artefact).
- **Pan-Tompkins, AC-4:** worst +P 66.88% (electrode motion).
- **Pan-Tompkins, AC-5:** worst HR±5 40.60% (muscle artefact).
- **Hamilton, AC-1:** worst +P 99.00% (baseline wander).
- **Hamilton, AC-3:** worst +P 90.69% (electrode motion).
- **Hamilton, AC-4:** worst +P 67.47% (electrode motion).
- **Hamilton, AC-5:** worst HR±5 57.44% (muscle artefact).
- **Elgendi, AC-2:** worst +P 93.59% (electrode motion).
- **Elgendi, AC-3:** worst +P 77.16% (electrode motion).
- **Elgendi, AC-4:** worst +P 65.59% (electrode motion).
- **Elgendi, AC-5:** worst HR±5 34.79% (electrode motion).
- **XQRS, AC-3:** worst +P 91.78% (muscle artefact).
- **XQRS, AC-4:** worst +P 71.04% (muscle artefact).
- **XQRS, AC-5:** worst HR±5 51.28% (muscle artefact).

### 5.2 Positive predictivity by noise type (noisy segments, no pre-filter)
**Electrode motion**

| Detector | 24 dB | 18 dB | 12 dB | 6 dB | 0 dB | −6 dB |
|---|---|---|---|---|---|---|
| NeuroKit2 | 96.4% / 100.0% | 91.7% / 99.7% | 81.8% / 96.7% | 69.1% / 89.4% | 53.8% / 71.3% | 42.2% / 53.5% |
| Pan-Tompkins | 100.0% / 99.9% | 99.9% / 99.8% | 91.9% / 99.2% | 66.9% / 97.1% | 53.5% / 89.1% | 41.6% / 65.4% |
| Hamilton | 99.9% / 99.9% | 99.7% / 99.8% | 90.7% / 98.3% | 67.5% / 93.6% | 54.2% / 86.8% | 43.2% / 66.8% |
| Elgendi | 93.6% / 97.6% | 87.8% / 95.4% | 77.2% / 92.1% | 65.6% / 88.3% | 53.7% / 77.4% | 41.1% / 59.1% |
| XQRS | 100.0% / 99.9% | 99.8% / 99.9% | 94.6% / 99.4% | 72.9% / 96.9% | 55.7% / 91.1% | 45.0% / 75.1% |

**Muscle artefact**

| Detector | 24 dB | 18 dB | 12 dB | 6 dB | 0 dB | −6 dB |
|---|---|---|---|---|---|---|
| NeuroKit2 | 97.9% / 99.9% | 97.0% / 99.9% | 94.8% / 99.2% | 89.0% / 91.6% | 78.2% / 72.7% | 66.1% / 54.6% |
| Pan-Tompkins | 100.0% / 99.8% | 99.9% / 99.8% | 88.6% / 99.0% | 68.3% / 97.8% | 58.4% / 85.8% | 37.8% / 35.6% |
| Hamilton | 100.0% / 99.8% | 99.7% / 99.8% | 92.0% / 98.7% | 71.5% / 95.3% | 60.8% / 87.0% | 41.4% / 37.7% |
| Elgendi | 97.0% / 98.8% | 93.8% / 97.6% | 88.3% / 96.1% | 78.8% / 91.3% | 67.5% / 79.4% | 56.8% / 65.1% |
| XQRS | 100.0% / 99.9% | 99.6% / 99.8% | 91.8% / 99.1% | 71.0% / 97.1% | 58.4% / 90.6% | 45.9% / 62.7% |

**Baseline wander**

| Detector | 24 dB | 18 dB | 12 dB | 6 dB | 0 dB | −6 dB |
|---|---|---|---|---|---|---|
| NeuroKit2 | 96.9% / 99.9% | 97.2% / 99.9% | 97.8% / 99.9% | 98.1% / 99.8% | 96.9% / 99.4% | 93.6% / 96.6% |
| Pan-Tompkins | 100.0% / 99.9% | 100.0% / 99.9% | 100.0% / 99.9% | 99.3% / 99.8% | 96.2% / 99.5% | 84.7% / 98.8% |
| Hamilton | 99.5% / 99.7% | 99.9% / 99.8% | 99.9% / 99.8% | 99.3% / 99.7% | 97.1% / 99.4% | 87.6% / 97.9% |
| Elgendi | 99.7% / 99.9% | 99.3% / 99.7% | 98.0% / 99.3% | 94.3% / 97.7% | 87.8% / 94.7% | 79.8% / 91.2% |
| XQRS | 100.0% / 99.9% | 100.0% / 99.9% | 99.9% / 99.9% | 99.4% / 99.8% | 97.1% / 99.5% | 87.6% / 98.7% |

Cells: +P / Se.

### 5.3 Official NSTDB records (electrode motion, records 118 and 119)
| Detector | 24 dB | 18 dB | 12 dB | 6 dB | 0 dB | -6 dB |
|---|---|---|---|---|---|---|
| NeuroKit2 | 98.1% / 100.0% | 95.1% / 99.9% | 84.8% / 97.1% | 71.3% / 89.9% | 55.1% / 70.2% | 42.8% / 52.4% |
| Pan-Tompkins | 100.0% / 100.0% | 99.9% / 100.0% | 93.8% / 99.7% | 67.8% / 97.7% | 55.6% / 90.0% | 42.1% / 65.4% |
| Hamilton | 100.0% / 100.0% | 99.8% / 100.0% | 90.4% / 98.4% | 68.6% / 94.8% | 56.2% / 88.2% | 44.6% / 66.8% |
| Elgendi | 96.4% / 99.4% | 92.8% / 97.9% | 82.7% / 93.6% | 68.8% / 88.7% | 55.9% / 78.0% | 41.6% / 58.3% |
| XQRS | 100.0% / 100.0% | 100.0% / 100.0% | 93.7% / 99.4% | 71.3% / 96.5% | 55.3% / 89.6% | 45.4% / 74.4% |

Cells: +P / Se.

### 5.4 Effect of the HP+notch pre-filter (F1, percentage points, noisy segments)
| Detector | electrode motion @ 6 dB | muscle artefact @ 6 dB | baseline wander @ 6 dB |
|---|---|---|---|
| NeuroKit2 | -0.11 | -0.02 | -0.02 |
| Pan-Tompkins | +0.13 | -0.00 | -0.03 |
| Hamilton | -0.11 | -0.03 | -0.01 |
| Elgendi | +0.02 | -0.00 | -0.03 |
| XQRS | +0.00 | +0.00 | +0.00 |

Largest single effect: **Pan-Tompkins**, baseline wander at -6 dB, F1 91.2% → 91.6% (+0.4 pp).

## 6. Failure modes observed
1. **Electrode motion → false beats.** Electrode-motion artefact is the hardest noise. At 6 dB, +P ranges 65.6%–72.9% while Se stays at 88.3%–97.1%. The artefact has QRS-like slopes inside the QRS band, so detectors add beats rather than lose them. Filtering cannot separate it from the QRS.
2. **Muscle artefact → mixed errors.** At 6 dB, +P 68.3%–89.0% and Se 91.3%–97.8%. Broadband bursts both trigger false detections and raise adaptive thresholds so that real beats are skipped.
3. **Baseline wander is mostly harmless to these detectors.** Even at 0 dB, +P 87.8%–97.1%, because every pipeline already high-passes the signal. Note that nst's per-second mean removal makes the bw gain very large for a given SNR.
4. **Bursty noise.** Errors cluster in short stretches where the local SNR is several dB below the record's nominal SNR (see the Failure Gallery in the app).
5. **Slow hearts score worst.** At the same nominal SNR, F1 per record follows the number of true beats (Spearman ρ = 0.96 at 6 dB electrode motion; worst: records 117, 123). The noise adds about the same number of false detections per minute everywhere, so a slow heart, with fewer true beats, loses more +P.
6. **T-wave oversensing, with no noise at all.** Some failures happen on clean segments: NeuroKit2 on record 113: +P 63.5%, false detections a median 328 ms after the R peak (RR 1014 ms); Hamilton on record 117: +P 93.1%, false detections a median 428 ms after the R peak (RR 1181 ms); Hamilton on record 115: +P 95.8%, false detections a median 454 ms after the R peak (RR 911 ms). A delay of 300–450 ms after the R peak is where the T wave sits, so these detectors count tall T waves as extra beats, mostly at slow heart rates. Noise did not cause this. It is a weakness in the decision logic, and it fails AC-1 for those detectors.
7. **Noise hangover into the clean minutes.** At −6 dB, sensitivity on the *clean* segments that follow each noise burst falls to Pan-Tompkins 64%, Hamilton 74%, XQRS 87% (vs ≥ 99.6% at 24 dB). Adaptive thresholds learnt on the noise stay too high after the noise stops, so real beats are missed for a while. This is why AC-1 uses the clean segments of the 24 dB runs as the baseline.

## 7. Limitations
Fifteen 1970s Holter recordings, one lead, default detector settings, digitally added noise and the same noise segments for every record. The results describe how the algorithms behave under noise, not how well they would perform across a population. See *Methods & limitations* in the app.

## 8. Conclusion
No detector meets AC-3: at 12 dB electrode motion every detector's +P is below 95% (77.2%–94.6%), so **electrode motion is the limiting failure cause**, and it shows up as false detections, not misses. Ranked by mean F1 at 6 dB across the three noise types: **NeuroKit2** 89.1%, **XQRS** 88.3%, **Hamilton** 86.5%, **Pan-Tompkins** 86.4%, **Elgendi** 85.3%. Two failure modes have nothing to do with SNR: T-wave oversensing on some clean records, and threshold hangover after strong noise. The HP+notch pre-filter changes F1 by less than half a percentage point, because every detector already band-limits its input. Noise inside the QRS band cannot be filtered away; the decision logic has to cope with it.

---
*Generated by `scripts/make_report.py` from `results/`. Re-run after re-running the benchmark.*