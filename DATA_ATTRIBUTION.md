# Data attribution

This repository redistributes, unmodified, a subset of two PhysioNet databases.
Both are published under the **Open Data Commons Attribution License v1.0**
(https://opendatacommons.org/licenses/by/1-0/), which permits redistribution
with attribution.

## MIT-BIH Noise Stress Test Database v1.0.0 (`data/nstdb/`)

- Source: https://physionet.org/content/nstdb/1.0.0/
- DOI: https://doi.org/10.13026/C2HS3T
- Files included: records 118e24, 118e18, 118e12, 118e06, 118e00, 118e_6,
  119e24, 119e18, 119e12, 119e06, 119e00, 119e_6 (`.hea`, `.dat`, `.atr`)
  and noise records `bw`, `ma`, `em` (`.hea`, `.dat`).
- Original publication: Moody GB, Muldrow WE, Mark RG. A noise stress test for
  arrhythmia detectors. Computers in Cardiology 1984; 11:381-384.

## MIT-BIH Arrhythmia Database v1.0.0 (`data/mitdb/`)

- Source: https://physionet.org/content/mitdb/1.0.0/
- DOI: https://doi.org/10.13026/C2F305
- Files included: records 100, 101, 103, 109, 111, 112, 113, 115, 116, 117,
  118, 119, 121, 122, 123 (`.hea`, `.dat`, `.atr`).
- Citation: Moody G, Mark R. MIT-BIH Arrhythmia Database (version 1.0.0).
  PhysioNet. https://doi.org/10.13026/C2F305
- Original publication: Moody GB, Mark RG. The impact of the MIT-BIH
  Arrhythmia Database. IEEE Eng in Med and Biol 20(3):45-50 (May-June 2001).

## PhysioNet

Please also cite the PhysioNet platform reference shown on each dataset page
(copy the current citation from the page).

## Changes

None. The files are byte-identical to the PhysioNet originals. The NSTDB
header baseline quirk (see README, "Data audit findings") is corrected at load
time in `bench/data.py`, not in the files.

---

# Learn chapters (`data/learn/`)

The Learn chapters use short **excerpts** extracted by `scripts/build_learning_data.py`
(resampled, trimmed, PPG inverted so pulses point up, accelerometer converted from m/s² to g,
stored as float16). These are modified derivatives of the following PhysioNet databases.

## CEBS: Combined measurement of ECG, Breathing and Seismocardiograms v1.0.0

- Source: https://physionet.org/content/cebsdb/1.0.0/ · Licence: ODC-By 1.0
- Used: record b001 (ECG leads I and II, respiration band, SCG; recorded with a BIOPAC MP36), resampled 5 kHz → 500 Hz.
- García-González MA, Argelagós-Palau A, Fernández-Chimeno M, Ramos-Castro J. A comparison of heartbeat
  detectors for the seismocardiogram. Computing in Cardiology 2013; 40:461-464.

## Pulse Transit Time PPG Dataset v1.1.0

- Source: https://physionet.org/content/pulse-transit-time-ppg/1.1.0/
- **Licence: Open Data Commons Open Database License (ODbL) v1.0.** The excerpts `data/learn/ptt_*.npz`
  are a derivative database and are therefore also made available under ODbL v1.0 (share-alike).
- Used: subject 1, sitting / walking / running; 120 s excerpts of ECG, PPG (red, IR, green) and accelerometer.
- Data note: the headers label the accelerometer in g, but the resting magnitude is ~9.6, i.e. m/s²;
  the excerpts are converted to g.
- Mehrgardt P, Khushi M, Poon S, Withana A. Pulse Transit Time PPG Dataset (version 1.1.0). PhysioNet.

## PhysioNet/Computing in Cardiology Challenge 2016

- Source: https://physionet.org/content/challenge-2016/1.0.0/ · Licence: ODC-By 1.0
- Used: training-a record a0012 (labelled normal): 20 s of heart sounds (PCG) with simultaneous ECG.
- Liu C, Springer D, Li Q, et al. An open access database for the evaluation of heart sound algorithms.
  Physiol Meas 2016; 37(12):2181-2213.
