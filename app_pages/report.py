import streamlit as st

from bench.config import ROOT
from ui.style import overline

REPORT = ROOT / "docs" / "verification_report.md"

if not REPORT.exists():
    st.title("Verification report")
    st.info("Run `python scripts/make_report.py` to generate the report.", icon=":material/hourglass_empty:")
    st.stop()

text = REPORT.read_text(encoding="utf-8")
overline("Test protocol · VR-ECGNB-001", "vr")
with st.container(horizontal=True, horizontal_alignment="right"):
    st.download_button("Download report (Markdown)", text.encode("utf-8"), "verification_report.md",
                       "text/markdown", icon=":material/download:")
st.markdown(text)
