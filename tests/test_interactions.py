"""Logic tests: drive every page's controls through realistic combinations and check the results,
not only that nothing crashes. Needs data/ and results/ (skipped otherwise)."""
import itertools

import pytest

from bench.config import RESULTS_DIR

pytestmark = pytest.mark.skipif(not (RESULTS_DIR / "summary.parquet").exists(), reason="results not computed")


def page(name: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../streamlit_app.py", default_timeout=180)
    at.run()
    at.switch_page(f"app_pages/{name}.py").run()
    assert not at.exception, at.exception
    return at


def ok(at):
    at.run()
    assert not at.exception, at.exception
    return at


def texts(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [f"{m.label} {m.value}" for m in at.metric]
    parts += [e.value for e in at.success] + [e.value for e in at.warning] + [e.value for e in at.info]
    return "\n".join(str(p) for p in parts)


# ------------------------------------------------------------------ bench pages
def test_noise_lab_all_sources_noises_detectors():
    at = page("noise_lab")
    for noise in ("em", "ma", "bw"):
        at.segmented_control(key="nl_noise").set_value(noise)
        at.slider(key="nl_snr").set_value(-6)
        ok(at)
    assert "Noisy" in texts(at)  # default view at 302 s is inside the first noisy segment
    for i in range(1, 6):  # every detector overlay, including a live (non-precomputed) SNR
        at.selectbox(key="nl_det").select_index(i)
        at.slider(key="nl_snr").set_value(5)
        ok(at)
        assert "correct" in texts(at)
    at.toggle(key="nl_pf").set_value(True)
    at.toggle(key="nl_spec").set_value(True)
    at.segmented_control(key="nl_span").set_value(30)
    at.slider(key="nl_t0").set_value(1790)
    ok(at)
    at.segmented_control(key="nl_source").set_value("nstdb")
    ok(at)
    at.select_slider(key="nl_snr_off").set_value(-6)
    ok(at)
    at.slider(key="nl_t0").set_value(0)
    ok(at)
    assert "Clean" in texts(at)  # the first 5 minutes are always clean


def test_filter_designer_every_design_and_delay_logic():
    at = page("filter_designer")
    for kind, family, mode in itertools.product(("highpass", "notch", "bandpass", "lowpass"), ("iir", "fir"),
                                                ("zero", "causal")):
        at.segmented_control(key="fd_kind").set_value(kind)
        ok(at)
        if kind != "notch":
            at.segmented_control(key="fd_family").set_value(family)
        at.segmented_control(key="fd_mode").set_value(mode)
        ok(at)
        if mode == "zero":
            assert "Measured QRS delay 0 ms" in texts(at), (kind, family)
    # FIR band-pass, 181 taps, causal: delay must be (181 - 1) / 2 samples = 250 ms at 360 Hz
    at.segmented_control(key="fd_kind").set_value("bandpass")
    ok(at)
    at.segmented_control(key="fd_family").set_value("fir")
    at.segmented_control(key="fd_mode").set_value("causal")
    ok(at)
    at.slider(key="fd_taps").set_value(181)
    ok(at)
    t = texts(at)
    assert "Measured QRS delay 250 ms" in t and "Group delay in 5–15 Hz 250 ms" in t
    for i in range(len(at.selectbox(key="fd_sig").options)):
        at.selectbox(key="fd_sig").select_index(i)
        ok(at)


def test_benchmark_all_views():
    at = page("benchmark")
    for ds in ("mixed", "nstdb"):
        at.segmented_control(key="bm_ds").set_value(ds)
        ok(at)
        for noise in (("em", "ma", "bw") if ds == "mixed" else ("em",)):
            at.segmented_control(key=f"bm_noise_{ds}").set_value(noise)
            for pf, m in itertools.product(("none", "hp_notch"), ("f1", "hr_within5")):
                at.segmented_control(key="bm_pf").set_value(pf)
                at.segmented_control(key="bm_m").set_value(m)
                ok(at)
    for thr in (0.9, 0.99):
        at.select_slider(key="bm_thr").set_value(thr)
        ok(at)
    at.toggle(key="bm_per_rec").set_value(True)
    ok(at)
    at.select_slider(key="bm_rec_snr").set_value(-6)
    ok(at)
    at.pills(key="bm_dets").set_value([])
    ok(at)
    assert "Pick at least one detector" in texts(at)


def test_failure_gallery_every_detector_and_noise():
    at = page("failure_gallery")
    for det, noise in itertools.product(("neurokit", "pantompkins", "hamilton", "elgendi", "xqrs"),
                                        ("all", "em", "ma", "bw")):
        at.segmented_control(key="fg_det").set_value(det)
        at.segmented_control(key="fg_noise").set_value(noise)
        ok(at)
    at.select_slider(key="fg_snr").set_value(12)
    at.toggle(key="fg_pf").set_value(True)
    ok(at)
    # neurokit on record 113 is a known noise-free failure (T-wave oversensing): explained as such
    at.segmented_control(key="fg_det").set_value("neurokit")
    at.segmented_control(key="fg_noise").set_value("all")
    at.select_slider(key="fg_snr").set_value(12)
    at.toggle(key="fg_pf").set_value(False)
    ok(at)
    t = texts(at)
    assert "record 113" in t and "Not caused by the noise" in t


def test_methods_and_report_render():
    at = page("methods")
    assert len(at.tabs) == 6
    at = page("report")
    assert any("Verification report" in m.value for m in at.markdown)


# ------------------------------------------------------------------ learn pages
def test_learn_start_every_event():
    at = page("learn_start")
    opts = at.select_slider(key="ls_event").options
    for o in opts:
        at.select_slider(key="ls_event").set_value(o)
        ok(at)
    assert "S2" in texts(at)


def test_learn_ecg_projection_logic():
    at = page("learn_ecg")
    at.slider(key="le_axis").set_value(60)
    at.segmented_control(key="le_lead").set_value("Lead II")
    ok(at)
    assert "+1.00" in texts(at) and "tall and upright" in texts(at)
    at.segmented_control(key="le_lead").set_value("aVR")  # -150°: 150° away from +60° vector... inverted
    ok(at)
    assert "inverted" in texts(at)
    at.slider(key="le_axis").set_value(-30)
    at.segmented_control(key="le_lead").set_value("Lead II")  # perpendicular: cos(90°) = 0
    ok(at)
    assert "+0.00" in texts(at) or "-0.00" in texts(at)
    at.segmented_control(key="le_real").set_value("lead_II")
    at.pills(key="le_waves").set_value([])
    ok(at)


def test_learn_heart_rate_formula():
    at = page("learn_heart_rate")
    at.number_input(key="hr_rr").set_value(750)
    ok(at)
    assert "Heart rate 80 bpm" in texts(at)  # 60 / 0.75 s
    at.slider(key="hr_sim").set_value(180)
    at.slider(key="hr_start").set_value(int(at.slider(key="hr_start").proto.max))
    at.slider(key="hr_rsa").set_value(int(at.slider(key="hr_rsa").proto.max))
    ok(at)
    assert "333 ms" in texts(at)  # 60 / 180


def test_learn_cardiac_cycle_valves_follow_pressure():
    at = page("learn_cardiac_cycle")
    for i in range(6):
        at.radio(key="cc_flow").set_value(at.radio(key="cc_flow").options[i])
        ok(at)
    for hr in (50, 150):
        at.slider(key="cc_hr").set_value(hr)
        ok(at)
        cur = at.slider(key=f"cc_t_{hr}")
        for t in (0, int(cur.proto.max)):
            cur.set_value(t)
            ok(at)
    # in the middle of systole the aortic valve is open and the mitral valve closed
    at.slider(key="cc_hr").set_value(70)
    ok(at)
    at.slider(key="cc_t_70").set_value(330)
    ok(at)
    t = texts(at)
    assert "Aortic valve Open" in t and "Mitral valve Closed" in t and "Ejection" in t
    at.slider(key="cc_snd").set_value(float(at.slider(key="cc_snd").proto.max))
    ok(at)


def test_learn_ppg_features_and_windows():
    at = page("learn_ppg")
    for f in ("Pulse arrival (foot)", "Systolic upstroke", "Systolic peak", "Dicrotic notch", "Diastolic runoff"):
        at.pills(key="pp_feat").set_value(f)
        ok(at)
    at.slider(key="pp_win").set_value(110)
    ok(at)


def test_learn_motion_interference_and_filters():
    import re

    at = page("learn_motion")
    ppg_err = {}
    for act in ("sit", "walk", "run"):
        at.segmented_control(key="mo_act").set_value(act)
        at.slider(key="mo_win").set_value(110)
        ok(at)
        ppg_err[act] = float(re.search(r"PPG heart-rate error vs ECG ([\d.]+) bpm", texts(at)).group(1))
    # movement must make the PPG heart rate worse: the point of the chapter
    assert ppg_err["sit"] < ppg_err["walk"] < ppg_err["run"], ppg_err
    at.segmented_control(key="mo_mf").set_value(60)
    for k, v in (("mo_mains", 0.5), ("mo_bw", 1.5), ("mo_emg", 0.3), ("mo_em", 0.8)):
        at.slider(key=k).set_value(v)
    ok(at)
    noisy = texts(at)
    for k in ("mo_hp", "mo_notch", "mo_lp"):
        at.toggle(key=k).set_value(True)
    ok(at)
    err = lambda s: int(re.search(r"Remaining error vs the clean ECG (\d+) µV", s).group(1))  # noqa: E731
    assert err(texts(at)) < err(noisy)  # filtering must reduce the error


def test_learn_acquisition_aliasing_logic():
    at = page("learn_acquisition")
    at.select_slider(key="aq_fs").set_value(60)
    at.toggle(key="aq_aa").set_value(False)
    at.toggle(key="aq_hum").set_value(True)
    ok(at)
    assert "fake **10 Hz** wave" in texts(at) or "fake 10 Hz wave" in texts(at)
    at.select_slider(key="aq_fs").set_value(25)
    ok(at)
    assert "constant offset" in texts(at)
    for fs in (40, 75, 100, 150, 250, 500):
        at.select_slider(key="aq_fs").set_value(fs)
        ok(at)
    for b in (3, 16):
        at.slider(key="aq_bits").set_value(b)
        ok(at)


def test_learn_quiz_all_correct_scores_full_marks():
    at = page("learn_quiz")
    correct = ["ECG", "atrial depolarization", "80 bpm", "decreases", "the mitral and tricuspid valves closing",
               "ECG R peak", "through the pulmonary valve to the lungs", "increases", "a motion artefact",
               "The ventricles must contract and the pressure wave must travel to the finger"]
    for i, a in enumerate(correct):
        at.radio(key=f"qz_{i}").set_value(a)
    at.form_submit_button[0].click()
    ok(at)
    assert "10 / 10 correct" in texts(at)
    at.number_input(key="rg_beats").set_value(13)
    at.number_input(key="rg_hr").set_value(66)
    at.button(key="rg_check").click()
    ok(at)


def test_glossary_every_topic_and_empty_search():
    at = page("learn_glossary")
    from ui.terms import CATEGORIES

    for c in CATEGORIES:
        at.pills(key="gl_cats").set_value([c])
        ok(at)
    at.pills(key="gl_cats").set_value([])
    at.text_input(key="gl_q").input("zzzz-no-such-term")
    ok(at)
    assert "No term matches" in texts(at)
