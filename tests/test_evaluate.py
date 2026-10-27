import numpy as np
import pandas as pd
import pytest

from bench.evaluate import bootstrap_ci, match_beats, metrics, summarize, window_table

FS = 360
TOL = 54  # 150 ms at 360 Hz


def test_perfect_detection():
    ref = np.arange(100, 10_000, 300)
    m = match_beats(ref, ref.copy(), TOL)
    assert len(m.tp_ref) == len(ref) and len(m.fp) == 0 and len(m.fn) == 0


def test_known_counts():
    ref = np.array([1000, 2000, 3000, 4000, 5000])
    # 1000 matched exactly, 2000 matched at edge (+54), 3000 missed (+55 is outside),
    # 4000 matched, 5000 missed; 7000 is a pure false positive.
    det = np.array([1000, 2054, 3055, 3990, 7000])
    m = match_beats(ref, det, TOL)
    assert len(m.tp_ref) == 3
    assert set(ref[m.fn]) == {3000, 5000}
    assert set(det[m.fp]) == {3055, 7000}


def test_one_to_one_two_detections_one_beat():
    ref = np.array([1000])
    det = np.array([990, 1005])
    m = match_beats(ref, det, TOL)
    assert len(m.tp_ref) == 1 and len(m.fp) == 1
    assert det[m.tp_det][0] == 1005  # the closer detection wins


def test_one_to_one_one_detection_between_two_beats():
    ref = np.array([1000, 1080])
    det = np.array([1045])
    m = match_beats(ref, det, TOL)
    assert len(m.tp_ref) == 1 and len(m.fn) == 1 and len(m.fp) == 0


def test_greedy_does_not_steal_better_match():
    ref = np.array([1000, 1060])
    det = np.array([1030, 1061])
    m = match_beats(ref, det, TOL)
    assert len(m.tp_ref) == 2 and len(m.fp) == 0


def test_empty_inputs():
    m = match_beats(np.array([], int), np.array([5, 6]), TOL)
    assert len(m.fp) == 2 and len(m.tp_ref) == 0
    m = match_beats(np.array([5, 6]), np.array([], int), TOL)
    assert len(m.fn) == 2


def test_metrics_values():
    out = metrics(tp=90, fp=10, fn=10)
    assert out["se"] == pytest.approx(0.9)
    assert out["ppv"] == pytest.approx(0.9)
    assert out["f1"] == pytest.approx(0.9)
    assert np.isnan(metrics(0, 0, 0)["se"])


def test_window_table_assigns_events_and_noisy_flag():
    n = 60 * FS  # 60 s -> six 10 s windows
    mask = np.zeros(n, bool)
    mask[20 * FS:40 * FS] = True  # windows 2 and 3 noisy
    ref = np.arange(FS // 2, n, FS)  # 60 bpm
    det = ref.copy()
    det = np.delete(det, [25])  # miss one beat in window 2
    det = np.sort(np.r_[det, 35 * FS + 180])  # extra detection in window 3
    wt = window_table(ref, det, mask, FS)
    assert list(wt["noisy"]) == [False, False, True, True, False, False]
    noisy = summarize(wt[wt.noisy])
    clean = summarize(wt[~wt.noisy])
    assert (noisy["tp"], noisy["fp"], noisy["fn"]) == (19, 1, 1)
    assert (clean["tp"], clean["fp"], clean["fn"]) == (40, 0, 0)
    assert clean["hr_mae"] == pytest.approx(0, abs=1e-9)
    assert wt.loc[0, "hr_ref"] == pytest.approx(60)


def test_bootstrap_ci_brackets_point_estimate():
    rng = np.random.default_rng(1)
    wt = pd.DataFrame({"tp": rng.integers(8, 13, 200), "fp": rng.integers(0, 3, 200),
                       "fn": rng.integers(0, 3, 200)})
    point = metrics(wt.tp.sum(), wt.fp.sum(), wt.fn.sum())
    ci = bootstrap_ci(wt, n_boot=500)
    for k in ("se", "ppv", "f1"):
        lo, hi = ci[k]
        assert lo < point[k] < hi
        assert hi - lo < 0.05
