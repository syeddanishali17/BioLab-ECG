import numpy as np
import pytest

from bench.filters import FilterSpec, apply, design, response
from bench.mixer import gain_for_snr, qrs_peak_to_peak, snr_for_gain
from bench.segments import protocol_mask, runs, subtraction_mask

FS = 360


def test_protocol_mask_schedule():
    n = 30 * 60 * FS
    m = protocol_mask(n, FS)
    segs = runs(m)
    assert segs[0].noisy is False and segs[0].stop == 300 * FS
    assert segs[1].noisy is True and segs[1].stop - segs[1].start == 120 * FS
    assert segs[2].noisy is False and segs[2].stop - segs[2].start == 120 * FS


def test_subtraction_mask_closes_zero_crossings():
    rng = np.random.default_rng(0)
    clean = rng.integers(-200, 200, 20 * FS)
    noise = np.zeros_like(clean)
    noise[5 * FS:15 * FS] = rng.integers(-3, 4, 10 * FS)  # contains many exact zeros
    m = subtraction_mask(clean + noise, clean, FS)
    assert m[5 * FS + 10:15 * FS - 10].all()
    assert not m[: 5 * FS - 1].any() and not m[15 * FS + 1:].any()


def test_gain_snr_roundtrip():
    S, N = 0.5, 0.01
    for snr in (24, 6, -6):
        assert snr_for_gain(S, N, gain_for_snr(S, N, snr)) == pytest.approx(snr)


def test_qrs_peak_to_peak_on_synthetic_spikes():
    x = np.zeros(10 * FS)
    beats = np.arange(FS, 9 * FS, FS)
    x[beats] = 1.5
    x[beats + 5] = -0.5
    assert qrs_peak_to_peak(x, beats, FS) == pytest.approx(2.0)


def test_highpass_removes_drift_and_keeps_qrs_band():
    t = np.arange(60 * FS) / FS
    drift = np.sin(2 * np.pi * 0.1 * t)
    qrs = 0.5 * np.sin(2 * np.pi * 10 * t)
    y = apply(design(FilterSpec("highpass", "iir", 0.5, order=2), FS), drift + qrs)
    core = slice(5 * FS, -5 * FS)
    assert np.std(y[core] - qrs[core]) < 0.02


def test_notch_attenuates_60hz():
    d = design(FilterSpec("notch", f1=60.0, q=30), FS)
    r = response(d)
    i60 = np.argmin(np.abs(r.f - 60))
    i10 = np.argmin(np.abs(r.f - 10))
    assert r.mag_db[i60] < -30 and abs(r.mag_db[i10]) < 0.5


def test_fir_bandpass_group_delay_is_constant():
    d = design(FilterSpec("bandpass", "fir", 5, 15, order=101), FS)
    r = response(d)
    gd = r.group_delay_ms[(r.f > 6) & (r.f < 14)]
    assert np.nanstd(gd) < 0.01
    assert np.nanmean(gd) == pytest.approx(50 / FS * 1000, rel=1e-3)


def test_noise_rms_removes_per_second_mean():
    from bench.mixer import noise_rms

    rng = np.random.default_rng(3)
    white = rng.normal(0, 0.2, 400 * FS)
    assert noise_rms(white, FS) == pytest.approx(0.2, rel=0.02)
    # a DC offset is removed by the per-second mean subtraction
    assert noise_rms(white + 5.0, FS) == pytest.approx(0.2, rel=0.02)


def test_nst_gain_formula_matches_snr_definition():
    from bench.mixer import gain_for_snr

    pp, rms, snr = 1.6, 0.05, 6.0
    a_nst = 10 ** (-snr / 20) * np.sqrt(2) / 4 * pp / rms  # as in nst.c
    assert gain_for_snr(pp ** 2 / 8, rms ** 2, snr) == pytest.approx(a_nst)


def test_mix_continuity_has_no_steps_at_boundaries():
    from bench.data import Record
    from bench.mixer import mix

    n = 30 * 60 * FS
    rng = np.random.default_rng(4)
    beats = np.arange(FS, n - FS, FS)
    ecg = np.zeros(n, np.float32)
    ecg[beats] = 1.0
    noise = (rng.normal(0, 0.1, n) + 2.0).astype(np.float32)  # noise with a large DC part
    mk = lambda sig, b: Record("t", "t", FS, sig[:, None], np.zeros((n, 1), np.int16), ("c",), (200.0,),  # noqa: E731
                               (0,), ("mV",), b, np.array(["N"] * b.size))
    m = mix(mk(ecg, beats), mk(noise, np.array([], int)), 0.0)
    jumps = np.abs(np.diff(m.signal - ecg))
    k = 300 * FS  # first switch on
    assert jumps[k - 1] < 5 * m.gain * 0.1  # no jump from the DC part of the noise
    assert np.allclose(m.signal[: k], ecg[: k])
