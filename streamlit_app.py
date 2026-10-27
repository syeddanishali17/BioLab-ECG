"""ECG Noise Stress-Test Bench: Streamlit entry point."""
import streamlit as st

from ui.learn import CHAPTERS
from ui.style import page_css

st.set_page_config(
    page_title="ECG Noise Stress-Test Bench",
    page_icon="assets/icon.svg",
    layout="wide",
)
st.logo("assets/logo.svg", icon_image="assets/icon.svg", size="large")
page_css()

pages = {
    "": [st.Page("app_pages/home.py", title="Overview", icon=":material/monitor_heart:", default=True)],
    "Bench": [
        st.Page("app_pages/noise_lab.py", title="Noise lab", icon=":material/graphic_eq:"),
        st.Page("app_pages/filter_designer.py", title="Filter designer", icon=":material/tune:"),
        st.Page("app_pages/benchmark.py", title="Detector benchmark", icon=":material/query_stats:"),
        st.Page("app_pages/failure_gallery.py", title="Failure gallery", icon=":material/report:"),
        st.Page("app_pages/report.py", title="Verification report", icon=":material/fact_check:"),
        st.Page("app_pages/methods.py", title="Methods & limitations", icon=":material/menu_book:"),
    ],
    "Learn": [st.Page(path, title=title, icon=icon) for path, title, icon in CHAPTERS]
    + [st.Page("app_pages/learn_glossary.py", title="Glossary", icon=":material/dictionary:")],
}
page = st.navigation(pages, position="top")
# per-page browser-tab title, so tabs, bookmarks and shared links say where they point
st.set_page_config(page_title="ECG Noise Stress-Test Bench" if page.title == "Overview"
                   else f"{page.title} · ECG Noise Bench")
page.run()

st.space("large")
with st.container(border=True, key="footer"):
    st.caption(
        ":material/info: **Research and education tool. Not a medical device. "
        "Not for diagnosis or patient monitoring.** "
        "Data: open PhysioNet databases (MIT-BIH NSTDB and Arrhythmia, CEBS, Pulse Transit Time PPG, "
        "CinC Challenge 2016), credited in Methods → Citations. Bench results describe algorithm "
        "robustness against reference annotations; Learn chapters are for education only."
    )
