"""Extract the small excerpts used by the Learn chapters into data/learn/*.npz.

Inputs: data/learn_raw/ (run scripts/fetch_learning_data.py first).
Every choice made here (record, segment, polarity) is printed and stored in
data/learn/manifest.json, so the pages can say exactly what they show.

Usage:  python scripts/build_learning_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import wfdb
from scipy import signal as sps

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "learn_raw"
OUT = ROOT / "data" / "learn"
FS = 500


def f16(x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float32).astype(np.float16)


def standardize(x: np.ndarray) -> np.ndarray:
    return (x - np.median(x)) / (np.std(x) + 1e-12)


def ensemble(x: np.ndarray, beats: np.ndarray, pre: int, post: int) -> np.ndarray:
    beats = beats[(beats - pre >= 0) & (beats + post < x.size)]
    return np.mean([x[b - pre:b + post] for b in beats], axis=0)


def cebs(record: str = "b001") -> dict:
    """Leads I and II, respiration band and SCG at rest (BIOPAC MP36, 5 kHz -> 500 Hz)."""
    rec = wfdb.rdrecord(str(RAW / "cebsdb" / record))
    ann = wfdb.rdann(str(RAW / "cebsdb" / record), "atr")
    q = int(rec.fs // FS)
    sig = {n: sps.resample_poly(rec.p_signal[:, i], 1, q) for i, n in enumerate(rec.sig_name)}
    # the database annotates every beat once per lead (chan 0 = lead I); keep lead I
    beats = np.asarray(ann.sample)[np.asarray(ann.chan) == 0] // q
    resp = sps.filtfilt(*sps.butter(2, [0.05, 1.0], btype="band", fs=FS), sig["RESP"])
    # polarity: inspiration is the shorter phase of each breath; make it the rising one
    peaks, _ = sps.find_peaks(resp, distance=int(1.5 * FS), prominence=np.std(resp) * 0.5)
    troughs, _ = sps.find_peaks(-resp, distance=int(1.5 * FS), prominence=np.std(resp) * 0.5)
    rise = np.median([p - troughs[troughs < p][-1] for p in peaks if (troughs < p).any()])
    fall = np.median([t - peaks[peaks < t][-1] for t in troughs if (peaks < t).any()])
    flipped = bool(rise > fall)
    if flipped:
        resp = -resp
    print(f"CEBS {record}: rise {rise / FS:.2f}s fall {fall / FS:.2f}s -> respiration flipped={flipped}")
    scg = sps.filtfilt(*sps.butter(2, [1, 40], btype="band", fs=FS), sig["SCG"])
    return {"lead_I": f16(sig["I"]), "lead_II": f16(sig["II"]), "resp": f16(standardize(resp)),
            "scg": f16(standardize(scg)), "beats": beats.astype(np.int32), "fs": FS,
            "_meta": {"record": record, "resp_flipped": flipped, "seconds": round(sig["I"].size / FS, 1)}}


def ptt(record: str, seconds: int = 120) -> dict:
    """ECG, finger PPG (red, IR, green) and 3-axis accelerometer, 500 Hz."""
    rec = wfdb.rdrecord(str(RAW / "pulse-transit-time-ppg" / record))
    ann = wfdb.rdann(str(RAW / "pulse-transit-time-ppg" / record), "atr")
    n = rec.sig_name
    x = {k: rec.p_signal[:, n.index(k)] for k in ("ecg", "pleth_1", "pleth_2", "pleth_3", "a_x", "a_y", "a_z")}
    # a centred segment (activity well under way)
    mid = rec.sig_len // 2
    a, b = mid - seconds * FS // 2, mid + seconds * FS // 2
    beats = np.asarray(ann.sample)
    beats = beats[(beats >= a) & (beats < b)] - a
    out = {"ecg": f16(x["ecg"][a:b]), "beats": beats.astype(np.int32), "fs": FS}
    flips = {}
    for key, name in (("pleth_1", "ppg_red"), ("pleth_2", "ppg_ir"), ("pleth_3", "ppg_green")):
        p = x[key][a:b]
        pf = sps.filtfilt(*sps.butter(2, [0.4, 10], btype="band", fs=FS), p)
        # more blood absorbs more light, so raw counts fall with each pulse; flip so
        # the systolic upstroke points up (the usual clinical display)
        slope = np.diff(ensemble(pf, beats, 0, int(0.6 * FS)))
        flip = bool(slope[np.argmax(np.abs(slope))] < 0)  # steepest change after R is the upstroke
        flips[name] = flip
        out[name] = f16(standardize(-p if flip else p))
    # The header says the accelerometer is in g, but at rest the magnitude is ~9.6 (gravity in m/s^2),
    # so the stored values are m/s^2. Convert to g.
    mag_rest = float(np.median(np.linalg.norm(np.c_[x["a_x"], x["a_y"], x["a_z"]], axis=1)))
    to_g = 1 / 9.80665 if mag_rest > 5 else 1.0
    for k in ("a_x", "a_y", "a_z"):
        out[k] = f16(x[k][a:b] * to_g)
    hdr = " ".join(rec.comments)
    out["_meta"] = {"record": record, "segment_s": [a / FS, b / FS], "ppg_flipped": flips, "header": hdr,
                    "accel_units_fix": f"median |a| = {mag_rest:.2f} -> stored as m/s^2, converted to g" if to_g != 1 else "g"}
    print(f"PTT {record}: segment {a / FS:.0f}-{b / FS:.0f}s, {beats.size} beats, flips {flips}")
    return out


def pcg_score(rec: str) -> float:
    """How clearly S1 and S2 stand out: envelope energy in the S1/S2 windows vs the rest."""
    r = wfdb.rdrecord(str(RAW / "challenge-2016" / rec))
    fs = r.fs
    pcg, ecg = r.p_signal[:, 0], r.p_signal[:, 1]
    ecg_f = sps.filtfilt(*sps.butter(2, [5, 25], btype="band", fs=fs), ecg)
    rp, _ = sps.find_peaks(np.abs(ecg_f), distance=int(0.4 * fs), height=np.percentile(np.abs(ecg_f), 98) * 0.4)
    env = np.abs(sps.hilbert(sps.filtfilt(*sps.butter(2, [25, 400], btype="band", fs=fs), pcg)))
    avg = ensemble(env, rp, 0, int(0.7 * fs))
    s1 = avg[: int(0.15 * fs)].max()
    s2 = avg[int(0.25 * fs): int(0.45 * fs)].max()
    floor = np.median(avg[int(0.5 * fs):])
    return float(min(s1, s2) / (floor + 1e-12))


def pcg(rec: str, seconds: int = 20) -> dict:
    r = wfdb.rdrecord(str(RAW / "challenge-2016" / rec))
    fs = int(r.fs)
    n = min(r.sig_len, seconds * fs)
    p = r.p_signal[:n, 0]
    p = sps.filtfilt(*sps.butter(2, [25, 400], btype="band", fs=fs), p)
    e = sps.filtfilt(*sps.butter(2, [0.5, 40], btype="band", fs=fs), r.p_signal[:n, 1])
    return {"pcg": f16(p / np.max(np.abs(p))), "ecg": f16(standardize(e)), "fs": fs,
            "_meta": {"record": rec, "seconds": n / fs}}


def save(name: str, d: dict, manifest: dict) -> None:
    meta = d.pop("_meta")
    np.savez_compressed(OUT / f"{name}.npz", **d)
    manifest[name] = meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    save("cebs_rest", cebs("b001"), manifest)
    for act in ("sit", "walk", "run"):
        save(f"ptt_{act}", ptt(f"s1_{act}"), manifest)
    cands = sorted(p.stem for p in (RAW / "challenge-2016").glob("*.hea"))
    scores = {c: float(np.nan_to_num(pcg_score(c))) for c in cands}
    best = max(scores, key=scores.get)
    print("PCG clarity scores:", {k: round(v, 1) for k, v in scores.items()}, "->", best)
    save("pcg", pcg(best), manifest)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(p.stat().st_size for p in OUT.glob("*.npz"))
    print(f"wrote {len(manifest)} excerpts, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
