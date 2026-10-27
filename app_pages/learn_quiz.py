import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.signal import find_peaks

from ui import learn as L
from ui.style import PLOT_CONFIG, base_layout, tokens

PATH = "app_pages/learn_quiz.py"
L.chapter_header(PATH, "Exam practice",
                 "A one-page summary, a self-check, and a real synchronized recording to interpret, the way exam "
                 "questions usually ask: *what happens first, which sensor measures what, and how do you read the graph?*")
tk = tokens()

# ------------------------------------------------------------ cheat sheet
st.header("Cheat sheet", anchor=False)
st.table(pd.DataFrame([
    ("ECG", "Electrical", "Voltage difference between two electrodes", "P, QRS, T; R-R interval → HR"),
    ("Heart sounds", "Mechanical / acoustic", "Valves closing", "S1 = AV valves close, S2 = semilunar valves close"),
    ("PPG", "Optical", "Blood-volume pulse in the tissue", "Foot, upstroke, systolic peak, dicrotic notch, runoff"),
    ("Respiration", "Mechanical", "Chest expansion (stretch band)", "Inspiration ↑, expiration ↓, much slower than ECG"),
    ("Accelerometer", "Motion", "Acceleration along X, Y, Z", "Flags movement → suspect motion artefacts"),
    ("BIOPAC MP36", "Acquisition", "Amplify, filter, sample, display", "Sampling rate, calculation channels (R-R, BPM)"),
], columns=["Signal", "Domain", "What it measures", "Remember"]).set_index("Signal"))
st.markdown("**The sequence:** electrical activation (QRS) → ventricles contract → **S1** → aortic valve opens, blood "
            "ejected → pressure wave travels → **PPG pulse** at the finger → ventricles relax → **S2**.")

# ------------------------------------------------------------ quiz
st.header("Self-check", anchor=False)
QUIZ = [
    ("Which signal records the heart's electrical activity?",
     ["PPG", "ECG", "Phonocardiogram", "Respiration band"], 1,
     "The ECG measures a voltage difference between electrodes. PPG is optical, heart sounds are acoustic."),
    ("The P wave corresponds to…",
     ["ventricular depolarization", "atrial depolarization", "ventricular repolarization", "closure of the AV valves"], 1,
     "P = atria depolarize. QRS = ventricles depolarize. T = ventricles repolarize."),
    ("The R-R interval is 0.75 s. The heart rate is…", ["45 bpm", "75 bpm", "80 bpm", "133 bpm"], 2,
     "HR = 60 / RR = 60 / 0.75 = 80 bpm."),
    ("If the R-R interval gets longer, the heart rate…", ["increases", "decreases", "stays the same"], 1,
     "Longer interval between beats = fewer beats per minute."),
    ("S1 (“lub”) is caused mainly by…",
     ["the aortic and pulmonary valves closing", "the mitral and tricuspid valves closing",
      "blood hitting the aorta", "the atria contracting"], 1,
     "S1 = AV valves (mitral, tricuspid) close as the ventricles start to contract, just after the QRS."),
    ("Which comes first in one heartbeat?",
     ["PPG pulse at the finger", "S2", "ECG R peak", "S1"], 2,
     "Electrical activation (R peak) comes first. Then S1, ejection, the PPG pulse, and S2."),
    ("Blood leaving the right ventricle goes…",
     ["through the aortic valve to the body", "through the pulmonary valve to the lungs",
      "back into the right atrium", "into the left ventricle"], 1,
     "Right ventricle → pulmonary valve → lungs: the pulmonary circulation."),
    ("During inspiration, heart rate usually…", ["increases", "decreases", "does not change"], 0,
     "Respiratory sinus arrhythmia: HR rises when you breathe in and falls when you breathe out."),
    ("A large spike appears in the PPG at the same moment as a spike in the accelerometer. Most likely…",
     ["an extra heartbeat", "a motion artefact", "a dicrotic notch", "a change in breathing"], 1,
     "Disturbances that coincide with movement are most likely motion artefacts, not physiology."),
    ("Why does the PPG pulse appear after the ECG R peak?",
     ["The PPG sensor samples more slowly", "The ventricles must contract and the pressure wave must travel to the finger",
      "The ECG is filtered", "Light travels slower than electricity"], 1,
     "ECG is electrical (instant); PPG sees the mechanical pulse that arrives a few hundred ms later."),
]
with st.form("quiz", border=True):
    answers = []
    for i, (q, opts, _, _) in enumerate(QUIZ):
        answers.append(st.radio(f"**{i + 1}.** {q}", opts, index=None, key=f"qz_{i}"))
    done = st.form_submit_button("Check my answers", icon=":material/check:", type="primary")
if done:
    score = sum(a == opts[c] for a, (_, opts, c, _) in zip(answers, QUIZ))
    (st.success if score >= 8 else st.warning)(f"{score} / {len(QUIZ)} correct.", icon=":material/grading:")
    for i, (a, (q, opts, c, why)) in enumerate(zip(answers, QUIZ)):
        ok = a == opts[c]
        with st.expander(f"{'✓' if ok else '✗'} {i + 1}. {q}", expanded=not ok):
            if not ok:
                st.markdown(f"Your answer: *{a or 'none'}* · Correct: **{opts[c]}**")
            st.markdown(why)

# ------------------------------------------------------------ read the graph
st.header("Read the graph", anchor=False)
st.markdown("A real synchronized recording: chest band and ECG from the BIOPAC MP36. Work out the answers from the "
            "picture, then check.")
cebs = L.load("cebs_rest")
fs = cebs["fs"]
a, b = 100 * fs, 112 * fs
t = np.arange(b - a) / fs
ecg = L.bandpass(cebs["lead_I"], 0.5, 40, fs)[a:b]
resp = cebs["resp"][a:b]
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=["Respiration (chest band)", "ECG lead I"])
fig.add_trace(go.Scatter(x=t, y=resp, line=dict(color=tk["tp"], width=2), hoverinfo="skip"), 1, 1)
fig.add_trace(go.Scatter(x=t, y=ecg, line=dict(color=tk["trace"], width=1.3), hoverinfo="skip"), 2, 1)
base_layout(fig, height=400, showlegend=False)
fig.update_xaxes(dtick=1, title_text="Time (s)", row=2, col=1)
fig.update_yaxes(showticklabels=False)
st.plotly_chart(fig, config=PLOT_CONFIG, alt="Exercise: respiration and ECG over 12 seconds")
bt = cebs["beats"]
true_beats = int(((bt >= a) & (bt < b)).sum())
true_hr = 60 * fs / float(np.median(np.diff(bt[(bt >= a) & (bt < b)])))
pk, _ = find_peaks(resp.astype(float), distance=int(1.5 * fs), prominence=0.5)
c1, c2, c3 = st.columns(3, vertical_alignment="bottom")
g_beats = c1.number_input("How many R peaks in these 12 s?", 0, 40, 0, key="rg_beats")
g_hr = c2.number_input("Heart rate (bpm)?", 0, 200, 0, key="rg_hr")
g_br = c3.number_input("How many breaths start (peaks) in 12 s?", 0, 10, 0, key="rg_br")
if st.button("Check", icon=":material/check:", key="rg_check"):
    st.markdown(f"- R peaks: **{true_beats}** {'✓' if abs(g_beats - true_beats) <= 1 else '✗'}\n"
                f"- Heart rate: **{true_hr:.0f} bpm** (from the median R-R interval) "
                f"{'✓' if abs(g_hr - true_hr) <= 5 else '✗'}. Quick estimate: beats in 12 s × 5.\n"
                f"- Breathing peaks: **{len(pk)}** {'✓' if abs(g_br - len(pk)) <= 1 else '✗'}, so roughly "
                f"{len(pk) * 5} breaths per minute. Notice how many heartbeats fit into one breath.")

# ------------------------------------------------------------ drawing checklist
st.header("Drawing a signal in the exam", anchor=False)
c1, c2 = st.columns(2, gap="large")
with c1:
    for i, item in enumerate([
        "Label both axes with quantity and unit: time (s), voltage (mV) or a.u.",
        "Draw at least two beats so the R-R interval is visible, and mark it.",
        "Label P, Q, R, S, T, with QRS clearly the sharpest and tallest.",
        "Synchronized plots: one shared time axis, signals stacked, events lined up vertically.",
        "PPG pulse starts after the R peak; S1 just after QRS; S2 near the end of T.",
        "Respiration: one slow wave spanning several heartbeats; mark inspiration / expiration.",
    ]):
        st.checkbox(item, key=f"draw_{i}")
with c2:
    st.markdown("**Typical numbers to quote**")
    st.markdown("- Resting HR 60–100 bpm → R-R 0.6–1.0 s\n- QRS about 0.08–0.10 s\n- R peak → S1 ≈ 0.03–0.06 s\n"
                "- R peak → PPG at the finger ≈ 0.2–0.3 s\n- R peak → S2 ≈ 0.3–0.4 s\n- Breathing 12–20 per minute at "
                "rest\n- ECG amplitude ≈ 1 mV")

L.key_idea("Always ask three questions of a synchronized graph: which signal is which (electrical, mechanical, optical, "
           "motion)? What happens first? And does anything coincide with movement?")
L.source_note("cebs_rest")
L.chapter_nav(PATH)
