"""Smoke test: every page renders without an exception (needs data/ and results/)."""
import pytest

from bench.config import RESULTS_DIR

PAGES = ["home", "noise_lab", "filter_designer", "benchmark", "failure_gallery", "report", "methods",
         "learn_start", "learn_ecg", "learn_heart_rate", "learn_cardiac_cycle", "learn_ppg", "learn_motion",
         "learn_acquisition", "learn_quiz", "learn_glossary"]

pytestmark = pytest.mark.skipif(not (RESULTS_DIR / "summary.parquet").exists(), reason="results not computed")


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../streamlit_app.py", default_timeout=120)
    at.run()
    at.switch_page(f"app_pages/{page}.py").run()
    assert not at.exception, at.exception


def _glossary():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../streamlit_app.py", default_timeout=120)
    at.run()
    at.switch_page("app_pages/learn_glossary.py").run()
    return at


def test_glossary_search_and_related_navigation():
    at = _glossary()
    assert at.session_state.gl_focus == "ecg"
    at.text_input(key="gl_q").input("dicrotic").run()
    assert not at.exception
    assert any("1 of" in c.value or "2 of" in c.value for c in at.caption)
    assert at.session_state.gl_focus == "dicrotic_notch"  # a new search opens its best match
    # clicking a related-term button opens that term
    btn = next(b for b in at.button if b.key and b.key.startswith("gl_rel_dicrotic_notch_"))
    target = btn.key.split("gl_rel_dicrotic_notch_")[1]
    btn.click().run()
    assert at.session_state.gl_focus == target
    assert at.query_params["term"] in (target, [target])


def test_glossary_deep_link():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("../streamlit_app.py", default_timeout=120)
    at.query_params["term"] = "s2"
    at.run()
    at.switch_page("app_pages/learn_glossary.py").run()
    assert not at.exception
    assert at.session_state.gl_focus == "s2"
