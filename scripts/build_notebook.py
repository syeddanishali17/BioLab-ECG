"""Build (and execute) notebooks/00_data_audit.ipynb from code cells kept here.

Usage:  python scripts/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

cells = [
    ("md", "# 00 · Data audit (Checkpoint 0)\n\nConfirms sampling rate, channels, gains, annotation symbols, "
           "the noisy-segment schedule and the mixer, before anything is benchmarked. Every finding here is "
           "also summarised in the app (*Methods & limitations → Data audit*)."),
    ("code", "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path.cwd().parent))\n"
             "import numpy as np, pandas as pd, matplotlib.pyplot as plt\n"
             "from bench import audit\nfrom bench.data import load_record, nstdb_name\n"
             "from bench.signals import nstdb_mask\nfrom bench.segments import runs\n"
             "pd.set_option('display.width', 160)"),
    ("md", "## 1 · Headers: sampling rate, channels, gain, duration"),
    ("code", "h = pd.DataFrame(audit.headers()); h"),
    ("code", "assert set(h.fs) == {360.0}, 'expected 360 Hz everywhere'\nprint('All records: 360 Hz')"),
    ("md", "## 2 · Annotation symbols"),
    ("code", "pd.DataFrame({k: audit.symbol_counts(*k.split('/')) for k in "
             "['mitdb/118', 'mitdb/119', 'nstdb/118e24']}).fillna(0).astype(int)"),
    ("md", "## 3 · Noisy-segment mask by subtraction\n\n**Surprise 1:** the residual (noisy − clean) is *not* "
           "zero in the clean segments: nst adds a continuity offset at every gain change. So the mask marks "
           "where the residual *changes*."),
    ("code", "n, c = load_record('nstdb', '118e24'), load_record('mitdb', '118')\n"
             "r = n.signal[:, 0].astype(float) - c.signal[:, 0].astype(float)\n"
             "for a, b in [(0, 300), (300, 420), (420, 540), (540, 660)]:\n"
             "    s = r[a*360:b*360]\n"
             "    print(f'{a:4d}-{b:4d} s  mean {s.mean()*1000:7.1f} µV  std {s.std()*1000:6.1f} µV')"),
    ("code", "pd.DataFrame(audit.mask_report())"),
    ("md", "**Surprise 2:** NSTDB headers keep `baseline = 1024` although nst removed the ADC zero. "
           "`bench.data.load_record` uses the ADC zero instead; without that, official records sit 5.12 mV low."),
    ("code", "import wfdb\nhd = wfdb.rdheader('../data/nstdb/118e24')\nprint('baseline', hd.baseline, ' adc_zero', hd.adc_zero)"),
    ("md", "## 4 · Mains frequency"),
    ("code", "audit.mains_check()"),
    ("md", "## 5 · Noise on both channels?"),
    ("code", "audit.both_channels_noisy()"),
    ("md", "## 6 · Mixer validation\n\n**Surprise 3:** a plain-variance SNR is ~7.25 dB away from nst's. "
           "With nst's own estimators (read from `nst.c` / `sigamp.c`) our gains match within 0.06 dB."),
    ("code", "mv = pd.DataFrame(audit.mixer_validation()); mv.round(3)"),
    ("md", "## 7 · One noisy segment at each SNR"),
    ("code", "fig, axes = plt.subplots(6, 1, figsize=(11, 11), sharex=True)\n"
             "for ax, snr in zip(axes, [24, 18, 12, 6, 0, -6]):\n"
             "    rec = load_record('nstdb', nstdb_name('118', snr))\n"
             "    t = np.arange(298*360, 306*360)\n"
             "    ax.plot(t/360, rec.signal[t, 0], lw=.8, color='#1F3A93')\n"
             "    ax.axvspan(300, 306, color='#D2602A', alpha=.08)\n"
             "    ax.set_ylabel(f'{snr} dB')\n"
             "axes[-1].set_xlabel('time (s): noise starts at 300 s')\nplt.tight_layout()"),
]

nb = nbf.v4.new_notebook()
nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in cells]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = ROOT / "notebooks" / "00_data_audit.ipynb"
NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(out.parent)}}).execute()
nbf.write(nb, out)
print(f"wrote {out}")
