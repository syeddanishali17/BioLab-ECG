"""Apply the Slice 3 record-selection rule to MIT-BIH and print the result.

Rule (stated in README and Methods):
  1. channel 0 is MLII (same lead as the NSTDB sources);
  2. no paced beats;
  3. the only rhythm annotation is normal sinus rhythm "(N";
  4. one beat label among N / L / R covers >= 95% of beats
     (a single dominant conduction pattern, so failures are about noise,
     not about arrhythmia);
  5. at most 15 "~" (signal-quality) annotations, so the clean source is clean;
  6. not 118 or 119 (already in the NSTDB set).
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np
import wfdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.config import BEAT_SYMBOLS  # noqa: E402


def evaluate(rec: str) -> tuple[bool, str]:
    p = ROOT / "data" / "mitdb" / rec
    h = wfdb.rdheader(str(p))
    a = wfdb.rdann(str(p), "atr")
    sym = np.asarray(a.symbol)
    beats = sym[np.isin(sym, list(BEAT_SYMBOLS))]
    c = collections.Counter(beats)
    rhythms = {x.strip("\x00") for x in a.aux_note if x.startswith("(")}
    dom, share = max(((k, c[k] / len(beats)) for k in "NLR"), key=lambda t: t[1])
    checks = {
        "MLII": h.sig_name[0] == "MLII",
        "not paced": c["/"] == 0,
        "sinus only": rhythms == {"(N"},
        f"dominant {dom} {share:.1%}": share >= 0.95,
        f"~ count {int((sym == '~').sum())}": (sym == "~").sum() <= 15,
        "not NSTDB source": rec not in {"118", "119"},
    }
    ok = all(checks.values())
    failed = [k for k, v in checks.items() if not v]
    return ok, ("selected" if ok else "rejected: " + ", ".join(failed)) + f" | {dom}={share:.1%}"


def main() -> None:
    recs = sorted({p.stem for p in (ROOT / "data" / "mitdb").glob("*.hea")})
    chosen = []
    for r in recs:
        ok, msg = evaluate(r)
        print(r, msg)
        if ok:
            chosen.append(r)
    print("\nEXTENSION_RECORDS =", chosen)


if __name__ == "__main__":
    main()
