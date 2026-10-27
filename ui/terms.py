"""Glossary content for the Learn track: every term from the class, plus the electrical background
(electrodes, current through the body, grounding, safety) needed to understand it.

Each term: name, category, one-line definition, explanation (markdown), optional "where you see it",
related term keys, the chapter that covers it, and an optional visual (drawn by the glossary page).
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = {
    "signals": ("Signals & sensors", ":material/sensors:", "blue"),
    "electric": ("The heart's electricity", ":material/electric_bolt:", "violet"),
    "ecg": ("ECG waveform", ":material/ecg:", "blue"),
    "electrodes": ("Electrodes & leads", ":material/cable:", "violet"),
    "safety": ("Current, ground & safety", ":material/electrical_services:", "red"),
    "heart": ("Heart & circulation", ":material/cardiology:", "red"),
    "valves": ("Valves & heart sounds", ":material/hearing:", "orange"),
    "rate": ("Heart rate & breathing", ":material/pulmonology:", "green"),
    "ppg": ("PPG & pulse", ":material/water_drop:", "red"),
    "noise": ("Motion, noise & filters", ":material/tune:", "orange"),
    "acq": ("Recording & processing", ":material/settings_input_component:", "gray"),
}

CH = {  # chapter pages
    "start": "app_pages/learn_start.py", "ecg": "app_pages/learn_ecg.py", "hr": "app_pages/learn_heart_rate.py",
    "cycle": "app_pages/learn_cardiac_cycle.py", "ppg": "app_pages/learn_ppg.py", "motion": "app_pages/learn_motion.py",
    "acq": "app_pages/learn_acquisition.py", "quiz": "app_pages/learn_quiz.py",
}


@dataclass(frozen=True)
class Term:
    key: str
    name: str
    cat: str
    short: str
    body: str
    see: str = ""
    related: tuple[str, ...] = ()
    chapter: str | None = None
    aka: str = ""
    visual: tuple | None = None  # ("ecg", t0_ms, t1_ms) | ("ppg", landmark) | ("pcg", "s1"|"s2") | ("rr",) | ("resp",)


_T: list[Term] = [
    # ------------------------------------------------------------------ signals & sensors
    Term("biosignal", "Biosignal", "signals", "Any measurable signal produced by the body.",
         "Electrical (ECG, EMG), mechanical (breathing, heart sounds), optical (PPG) or thermal signals that change "
         "over time. Each needs its own **sensor** to turn the body's activity into a voltage a computer can record.",
         related=("sensor", "ecg", "ppg", "pcg", "respiration_signal"), chapter=CH["start"]),
    Term("sensor", "Sensor (transducer)", "signals", "A device that converts a physical quantity into an electrical signal.",
         "An ECG electrode converts ionic currents into an electronic voltage, a PPG converts light into current, a "
         "respiration band converts stretch into resistance, an accelerometer converts acceleration into voltage.",
         related=("electrode", "ppg", "respiration_signal", "accelerometer"), chapter=CH["start"], aka="transducer"),
    Term("ecg", "ECG (electrocardiogram)", "signals", "Recording of the heart's electrical activity from the skin.",
         "The heart's muscle cells change their voltage as they activate and recover. Because body tissue conducts, "
         "these changes create tiny voltages (about 1 mV) on the skin. An ECG measures the **voltage difference** "
         "between two electrodes over time. It is **electrical**: it shows *when* the heart is told to contract, "
         "not the contraction itself.",
         see="P wave, QRS complex and T wave repeating every beat.",
         related=("potential_difference", "lead", "p_wave", "qrs", "t_wave", "r_peak"), chapter=CH["ecg"],
         aka="EKG", visual=("ecg", -300, 550)),
    Term("ppg", "PPG (photoplethysmogram)", "signals", "Optical recording of blood-volume changes in tissue.",
         "An LED shines light into the skin (finger, wrist, ear) and a photodiode measures how much comes back. Each "
         "heartbeat pushes a pulse of blood into the tissue, which absorbs more light. The PPG is a **mechanical / "
         "vascular** consequence of the heartbeat, measured **optically**, so it lags the ECG.",
         see="A smooth pulse per beat: upstroke, systolic peak, dicrotic notch, runoff.",
         related=("pulse_arrival_time", "systolic_peak", "dicrotic_notch", "ppg_wavelength", "ecg"), chapter=CH["ppg"],
         aka="pulse wave, pleth", visual=("ppg", "peak")),
    Term("pcg", "Phonocardiogram (heart sounds)", "signals", "Recording of the sounds made by the heart.",
         "A microphone or stethoscope on the chest picks up vibrations, mostly from **valves snapping shut**. The two "
         "main sounds are **S1** (“lub”) and **S2** (“dub”). Mechanical / acoustic, not electrical.",
         see="Two short bursts per beat: S1 just after the QRS, S2 near the end of the T wave.",
         related=("s1", "s2", "heart_valve"), chapter=CH["cycle"], aka="PCG", visual=("pcg", "s1")),
    Term("respiration_signal", "Respiration signal", "signals", "Recording of breathing, e.g. from a chest band.",
         "A stretch-sensitive belt around the chest (in class, a BIOPAC respiration transducer) changes its "
         "resistance as the chest expands and contracts. The signal rises during **inspiration** and falls during "
         "**expiration**, and is much slower than the ECG: one breath spans several heartbeats.",
         related=("inspiration", "expiration", "respiration_rate", "rsa"), chapter=CH["hr"], visual=("resp",)),
    Term("accelerometer", "Accelerometer", "signals", "Sensor that measures acceleration along X, Y and Z.",
         "At rest it measures only gravity (1 g, constant). When the body or the sensor moves, all three axes change. "
         "Used to **detect movement**, so that disturbances in ECG or PPG can be recognised as motion artefacts. "
         "Placed on the chest it can even feel the heartbeat (seismocardiogram).",
         related=("motion_artefact", "gyroscope", "scg"), chapter=CH["motion"]),
    Term("gyroscope", "Gyroscope", "signals", "Sensor that measures rotation speed around X, Y and Z.",
         "Complements the accelerometer in watches and phones: it tells how fast the device is turning. Together they "
         "describe movement well enough to reject motion-corrupted stretches of a PPG.",
         related=("accelerometer", "smartwatch"), chapter=CH["motion"]),
    Term("scg", "Seismocardiogram (SCG)", "signals", "Chest vibrations from the heartbeat, measured by an accelerometer.",
         "Each contraction gives the chest a tiny mechanical kick. It is another *mechanical* view of the heartbeat, "
         "and the CEBS recordings used in this app include it alongside ECG and breathing.",
         related=("accelerometer", "pcg"), chapter=CH["start"]),
    Term("synchronization", "Synchronized signals", "signals", "Several signals recorded on one shared time axis.",
         "BIOPAC shows respiration, ECG, PPG and accelerometer stacked with the same time axis. Only then can you say "
         "**what happens first** (the R peak), what follows (S1, PPG pulse, S2) and what coincides with movement.",
         related=("ecg", "ppg", "pulse_arrival_time", "motion_artefact"), chapter=CH["start"]),

    # ------------------------------------------------------------------ heart's electricity
    Term("action_potential", "Action potential", "electric", "The brief voltage swing of a single heart-muscle cell.",
         "At rest the inside of a cell is about −90 mV relative to the outside. When triggered, ion channels open, "
         "sodium and calcium rush in (**depolarization**), the cell contracts, then potassium flows out and the cell "
         "resets (**repolarization**). The ECG is the sum of millions of these, seen from the skin.",
         related=("depolarization", "repolarization", "ion_current"), chapter=CH["ecg"]),
    Term("depolarization", "Depolarization", "electric", "Cells becoming electrically activated (inside turns positive).",
         "A wave of depolarization spreading through heart muscle triggers contraction. **Atrial** depolarization "
         "makes the P wave; **ventricular** depolarization makes the QRS complex.",
         related=("atrial_depolarization", "ventricular_depolarization", "repolarization", "action_potential"),
         chapter=CH["ecg"]),
    Term("repolarization", "Repolarization", "electric", "Cells resetting to their resting voltage after activation.",
         "Needed before the next beat. **Ventricular** repolarization makes the T wave. Atrial repolarization happens "
         "too, but is hidden inside the much larger QRS complex.",
         related=("ventricular_repolarization", "t_wave", "depolarization"), chapter=CH["ecg"]),
    Term("atrial_depolarization", "Atrial depolarization", "electric", "Activation of the atria → the P wave.",
         "Starts at the SA node and spreads across both atria, which then contract and top up the ventricles.",
         related=("p_wave", "sa_node", "right_atrium", "left_atrium"), chapter=CH["ecg"], visual=("ecg", -240, -80)),
    Term("ventricular_depolarization", "Ventricular depolarization", "electric", "Activation of the ventricles → the QRS complex.",
         "Spreads very fast through the conduction system and the thick ventricular walls, so it produces the "
         "sharpest, largest deflection of the ECG. Contraction (systole) follows a few tens of milliseconds later.",
         related=("qrs", "r_peak", "conduction_system", "systole"), chapter=CH["ecg"], visual=("ecg", -50, 50)),
    Term("ventricular_repolarization", "Ventricular repolarization", "electric", "Recovery of the ventricles → the T wave.",
         "Slower and more spread out than depolarization, so the T wave is broad and rounded. The ventricles relax "
         "around its end, which is when S2 is heard.",
         related=("t_wave", "repolarization", "diastole", "s2"), chapter=CH["ecg"], visual=("ecg", 150, 420)),
    Term("sa_node", "SA node (sinoatrial node)", "electric", "The heart's natural pacemaker, in the right atrium.",
         "A cluster of cells that fire on their own, setting the heart rate. The nervous system speeds it up "
         "(sympathetic) or slows it down (vagus nerve). Each firing starts one heartbeat.",
         related=("atrial_depolarization", "heart_rate", "vagus_nerve", "conduction_system"), chapter=CH["ecg"],
         aka="sinus node, pacemaker"),
    Term("av_node", "AV node (atrioventricular node)", "electric", "The electrical gate between atria and ventricles.",
         "Delays the impulse by about 0.1 s so the atria finish emptying before the ventricles contract. This delay is "
         "the flat stretch between the P wave and the QRS.",
         related=("pr_interval", "conduction_system", "sa_node"), chapter=CH["ecg"]),
    Term("conduction_system", "Conduction system", "electric", "Specialised pathway that carries the impulse through the heart.",
         "SA node → atria → AV node → bundle of His → bundle branches → Purkinje fibres → ventricular muscle. Fast "
         "conduction in the ventricles is why the QRS is short (about 0.1 s).",
         related=("sa_node", "av_node", "ventricular_depolarization"), chapter=CH["ecg"], aka="His–Purkinje system"),
    Term("ion_current", "Ionic current", "electric", "Electric current in the body, carried by ions such as Na⁺, K⁺, Cl⁻.",
         "In wires, electrons carry current; in the body, dissolved ions do. Heart cells create ionic currents that "
         "spread through the surrounding tissue. The electrode is where ionic current becomes electronic current.",
         related=("volume_conductor", "electrode", "action_potential"), chapter=CH["ecg"]),
    Term("volume_conductor", "Volume conductor", "electric", "The body as a 3D conductor of the heart's currents.",
         "Tissue and body fluids conduct, so the heart's electrical activity produces a voltage pattern over the "
         "whole body surface. That is why you can measure an ECG from the chest, the arms or even two fingers (a "
         "watch), just with different shapes and sizes.",
         related=("ion_current", "lead", "electrical_axis"), chapter=CH["ecg"]),
    Term("electrical_axis", "Electrical axis (cardiac vector)", "electric", "The main direction of the heart's electrical activity.",
         "At each instant the heart's activity can be drawn as one arrow. The average QRS direction is the "
         "electrical axis, usually pointing down and to the left. Each lead sees the **projection** of this arrow "
         "onto its own direction, which is why leads look different.",
         related=("lead", "lead_axis", "einthoven"), chapter=CH["ecg"], aka="heart vector"),

    # ------------------------------------------------------------------ ECG waveform
    Term("p_wave", "P wave", "ecg", "Small rounded bump before the QRS: atrial depolarization.",
         "The first deflection of each beat. About 80–110 ms long and small, because the atria are thin.",
         see="Small hump ~0.15 s before the tall R peak.",
         related=("atrial_depolarization", "pr_interval", "qrs"), chapter=CH["ecg"], visual=("ecg", -240, -80)),
    Term("q_wave", "Q wave", "ecg", "First downward dip of the QRS complex.",
         "The first part of ventricular depolarization, travelling across the septum. Often small, or absent in "
         "some leads.",
         related=("qrs", "r_peak", "s_wave"), chapter=CH["ecg"], visual=("ecg", -45, -5)),
    Term("r_peak", "R peak (R wave)", "ecg", "The tall, sharp upward spike: the landmark of each heartbeat.",
         "The main ventricular depolarization seen by the lead. Because it is the sharpest, largest feature, QRS "
         "detectors look for it, and heart rate is calculated from the time between R peaks.",
         see="The tallest point of every beat.",
         related=("qrs", "rr_interval", "heart_rate", "qrs_detector"), chapter=CH["ecg"], visual=("ecg", -12, 12)),
    Term("s_wave", "S wave", "ecg", "Downward dip right after the R peak.",
         "The last part of ventricular depolarization, as activation reaches the upper parts of the ventricles.",
         related=("qrs", "r_peak", "q_wave"), chapter=CH["ecg"], visual=("ecg", 5, 50)),
    Term("qrs", "QRS complex", "ecg", "The sharp Q–R–S deflection: ventricular depolarization.",
         "Short (about 70–110 ms) and large because the impulse spreads fast through a big muscle mass. It is the "
         "electrical trigger for ventricular contraction.",
         see="Spiky complex in the middle of each beat.",
         related=("ventricular_depolarization", "q_wave", "r_peak", "s_wave", "systole"), chapter=CH["ecg"],
         visual=("ecg", -50, 50)),
    Term("t_wave", "T wave", "ecg", "Broad rounded wave after the QRS: ventricular repolarization.",
         "Comes about 0.2–0.4 s after the R peak. Its end roughly marks the end of ventricular contraction, close to "
         "the second heart sound (S2).",
         see="Wide hump in the second half of each beat.",
         related=("ventricular_repolarization", "qt_interval", "s2"), chapter=CH["ecg"], visual=("ecg", 150, 420)),
    Term("pr_interval", "PR interval", "ecg", "From the start of the P wave to the start of the QRS.",
         "Time for the impulse to cross the atria and the AV node: normally about 0.12–0.20 s.",
         related=("p_wave", "av_node", "qrs"), chapter=CH["ecg"], visual=("ecg", -200, -40)),
    Term("qt_interval", "QT interval", "ecg", "From the start of the QRS to the end of the T wave.",
         "How long the ventricles stay electrically active. It gets shorter as heart rate rises.",
         related=("qrs", "t_wave", "heart_rate"), chapter=CH["ecg"], visual=("ecg", -40, 400)),
    Term("baseline", "Isoelectric line (baseline)", "ecg", "The flat 0 mV level between waves.",
         "Where no net electrical activity is seen, e.g. between the T wave and the next P wave. Baseline wander "
         "makes this line drift up and down.",
         related=("baseline_wander", "p_wave", "t_wave"), chapter=CH["ecg"]),

    # ------------------------------------------------------------------ electrodes & leads
    Term("electrode", "Electrode", "electrodes", "The skin contact that picks up the body's voltage.",
         "Converts **ionic** current in the body into **electronic** current in the wire. A good ECG electrode makes "
         "a stable, low-resistance contact. Movement disturbs that contact and creates electrode-motion artefacts.",
         related=("ag_agcl", "electrode_gel", "skin_impedance", "lead", "electrode_motion"), chapter=CH["ecg"]),
    Term("ag_agcl", "Ag/AgCl electrode", "electrodes", "Silver / silver-chloride electrode, the standard for ECG.",
         "The silver-chloride layer exchanges chloride ions with the gel, so ionic current turns into electron flow "
         "smoothly and with a stable, low offset voltage. Disposable stick-on ECG electrodes (as in class) are usually "
         "Ag/AgCl with gel.",
         related=("electrode", "electrode_gel", "half_cell"), chapter=CH["ecg"]),
    Term("electrode_gel", "Electrolyte gel", "electrodes", "Conductive gel between skin and electrode.",
         "Fills the gaps in the skin surface and provides ions, lowering the contact impedance and stabilising the "
         "signal. Dry electrodes (as in a watch) work without gel but are noisier.",
         related=("ag_agcl", "skin_impedance", "dry_electrode"), chapter=CH["ecg"]),
    Term("skin_impedance", "Skin–electrode impedance", "electrodes", "The electrical 'resistance' of the skin contact.",
         "Mostly from the dry outer skin layer. Typically kΩ to MΩ. High or changing impedance makes the ECG pick up "
         "more mains hum and motion noise; skin preparation and gel lower it.",
         related=("electrode_gel", "input_impedance", "mains_interference", "electrode_motion"), chapter=CH["motion"]),
    Term("half_cell", "Half-cell potential", "electrodes", "A small DC voltage that forms where metal meets electrolyte.",
         "Every electrode has one (hundreds of mV for some metals). If the two electrodes differ, or the contact "
         "changes with movement, this DC voltage shifts, which shows up as baseline drift or motion artefact. "
         "Ag/AgCl keeps it small and stable.",
         related=("ag_agcl", "baseline_wander", "electrode_motion"), chapter=CH["motion"]),
    Term("dry_electrode", "Dry electrode", "electrodes", "Electrode without gel, e.g. the metal back of a watch.",
         "Convenient for wearables, but higher and less stable skin impedance means more noise, especially with "
         "movement.",
         related=("electrode_gel", "smartwatch", "skin_impedance"), chapter=CH["motion"]),
    Term("potential_difference", "Potential difference (voltage)", "electrodes", "What an ECG actually measures: V₊ − V₋.",
         "A voltage only exists *between* two points. The ECG amplifier subtracts the potential at one electrode from "
         "the other. Swap the electrodes and the ECG turns upside down.",
         related=("lead", "differential_amplifier", "ecg"), chapter=CH["ecg"], aka="voltage"),
    Term("lead", "Lead", "electrodes", "One specific electrode pair (or combination) and the voltage between them.",
         "Not the cable! A *lead* is a viewing direction on the heart. Lead I is left arm minus right arm, Lead II "
         "is left leg minus right arm, and so on. Your class setup with two chest electrodes was one lead.",
         related=("lead_axis", "einthoven", "potential_difference", "electrical_axis"), chapter=CH["ecg"]),
    Term("lead_axis", "Lead axis", "electrodes", "The line from the negative to the positive electrode.",
         "If the heart's electrical activity points along the lead axis, the wave is tall and upright; perpendicular, "
         "it nearly vanishes; opposite, it is inverted.",
         related=("lead", "electrical_axis"), chapter=CH["ecg"]),
    Term("einthoven", "Einthoven's triangle (Leads I, II, III)", "electrodes", "The three classic limb leads.",
         "Right arm, left arm and left leg form a triangle around the heart. Lead I = LA − RA (0°), Lead II = LL − RA "
         "(+60°), Lead III = LL − LA (+120°). Lead II often shows the clearest P waves and R peaks.",
         related=("lead", "lead_axis", "electrical_axis"), chapter=CH["ecg"]),
    Term("reference_electrode", "Reference / ground electrode", "electrodes", "Third electrode that ties the body to the amplifier's reference.",
         "Often placed on the right leg or a bony spot. It is not part of the measured voltage; it keeps the body near "
         "the amplifier's reference level so the common-mode voltage stays small. It is **not** connected to the "
         "building's earth in safe equipment.",
         related=("common_mode", "right_leg_drive", "signal_ground", "earth_ground"), chapter=CH["motion"],
         aka="RL electrode, ground electrode"),
    Term("differential_amplifier", "Differential amplifier", "electrodes", "Amplifies the difference between two inputs and rejects what they share.",
         "ECG voltages are about 1 mV, while mains hum couples tens of mV or more onto the whole body. Because the hum "
         "is almost the same at both electrodes, subtracting them cancels most of it while the ECG difference "
         "remains. In practice an *instrumentation amplifier*.",
         related=("common_mode", "cmrr", "potential_difference", "mains_interference"), chapter=CH["acq"],
         aka="instrumentation amplifier"),
    Term("common_mode", "Common-mode signal", "electrodes", "The part of the voltage that is the same on both electrodes.",
         "Mains hum picked up by the whole body is mostly common-mode. An ideal differential amplifier ignores it "
         "completely; a real one lets a tiny fraction through.",
         related=("differential_amplifier", "cmrr", "mains_interference", "right_leg_drive")),
    Term("cmrr", "CMRR (common-mode rejection ratio)", "electrodes", "How well an amplifier ignores common-mode signals.",
         "Expressed in dB; ECG amplifiers aim for 100 dB or more (a 100 000× suppression). Unequal electrode "
         "impedances turn common-mode hum into a difference signal, which is one reason good skin contact matters.",
         related=("common_mode", "differential_amplifier", "skin_impedance")),
    Term("right_leg_drive", "Right-leg drive", "electrodes", "Active circuit that feeds the inverted common-mode back to the body.",
         "Measures the common-mode voltage and drives the reference electrode with its opposite, actively cancelling "
         "hum. Common in ECG front-ends (e.g. the AD8232 chip used in the PPG dataset).",
         related=("reference_electrode", "common_mode", "mains_interference"), aka="RLD, driven right leg"),
    Term("input_impedance", "Input impedance", "electrodes", "How little current the amplifier draws from the electrodes.",
         "Must be very high (MΩ to GΩ) so the skin–electrode impedance does not shrink the signal or unbalance the two "
         "inputs.",
         related=("skin_impedance", "differential_amplifier")),

    # ------------------------------------------------------------------ current, ground & safety
    Term("current_body", "Current through the body", "safety", "How electric current flows through tissue, and why it matters.",
         "Current follows the lowest-resistance path between contact points. Skin is the main resistance (roughly "
         "1 kΩ wet to 100 kΩ dry); inside, tissue and blood conduct well. A path from **hand to hand** or **hand to "
         "foot** crosses the chest and heart, which is why such currents are dangerous. The ECG itself only *senses* "
         "tiny voltages; the equipment must make sure no harmful current can flow.",
         related=("macroshock", "microshock", "leakage_current", "isolation", "skin_impedance"), chapter=CH["motion"]),
    Term("earth_ground", "Earth ground (protective earth)", "safety", "The building's connection to the earth, via the plug's earth pin.",
         "Mains-powered devices connect their metal case to earth so that a fault current flows to earth instead of "
         "through a person. But a **patient** must not be connected to earth: then any stray voltage could drive "
         "current through the body to earth.",
         related=("signal_ground", "isolation", "leakage_current", "ground_loop"), chapter=CH["motion"], aka="PE, mains earth"),
    Term("signal_ground", "Signal ground (reference)", "safety", "The 0 V reference of the measuring circuit.",
         "All amplifier voltages are measured relative to it, and the reference electrode connects the body to it. In "
         "medical equipment this ground is **isolated** (floating) from the mains earth.",
         related=("earth_ground", "isolation", "reference_electrode"), aka="circuit ground, isolated ground"),
    Term("isolation", "Patient isolation", "safety", "Electrical separation between the patient circuit and the mains.",
         "Isolation transformers or optical / capacitive barriers carry the signal across without a conductive path. "
         "Even if the PC or mains side fails, no dangerous current can reach the person. Teaching systems such as "
         "BIOPAC's are built so students can be wired up safely; battery-powered devices (a watch) are isolated "
         "by design.",
         related=("earth_ground", "leakage_current", "signal_ground", "biopac"), aka="galvanic isolation"),
    Term("leakage_current", "Leakage current", "safety", "Small unintended current that can flow from equipment through a person.",
         "Comes from capacitance between mains wiring and the case or patient leads. Medical equipment standards "
         "(IEC 60601-1) limit it to microamps, because currents directly through the heart are dangerous at very "
         "low levels.",
         related=("microshock", "isolation", "earth_ground"), chapter=CH["motion"]),
    Term("macroshock", "Macroshock", "safety", "Current entering and leaving through the skin.",
         "Most of it spreads through the body, so only a fraction reaches the heart. Roughly 1 mA is perceptible, "
         "~10 mA can make muscles lock, and ~100 mA through the chest can cause ventricular fibrillation (mains "
         "frequency, about 1 s).",
         related=("microshock", "current_body", "isolation")),
    Term("microshock", "Microshock", "safety", "Current delivered directly to the heart, e.g. via a catheter.",
         "Bypasses the skin's resistance and the spreading through the body, so tens of microamps can be dangerous. "
         "This is why medical leakage-current limits are so strict.",
         related=("macroshock", "leakage_current")),
    Term("mains_interference", "Mains interference (50 / 60 Hz hum)", "safety", "Pickup from the electricity grid at 50 Hz (Europe) or 60 Hz (USA).",
         "Power cables and lights create electric fields that couple onto the body and the lead wires (capacitive "
         "coupling). It shows up as a fine regular ripple. Reduced by good electrodes, short twisted leads, a "
         "differential amplifier, right-leg drive and finally a notch filter. MIT-BIH data (USA) has 60 Hz; a lab "
         "in Vienna sees 50 Hz.",
         see="Fine, regular fuzz on the trace; a sharp spectral peak at 50 or 60 Hz.",
         related=("capacitive_coupling", "notch_filter", "differential_amplifier", "common_mode"), chapter=CH["motion"],
         aka="powerline noise, hum"),
    Term("capacitive_coupling", "Capacitive coupling", "safety", "Interference passing through the air between a cable and the body.",
         "The body and nearby mains wiring act like the two plates of a capacitor. An alternating mains voltage "
         "pushes a small current through this “capacitor” into the body, which becomes hum on the ECG.",
         related=("mains_interference", "shielding")),
    Term("ground_loop", "Ground loop", "safety", "Two ground paths at different potentials, letting current circulate.",
         "If a measurement is grounded in two places (say the amplifier and a separately earthed device), small "
         "voltage differences drive current around the loop, adding hum and, in the worst case, a safety risk.",
         related=("earth_ground", "isolation", "mains_interference")),
    Term("shielding", "Shielding", "safety", "A conductive layer around cables that intercepts electric fields.",
         "Shielded or twisted lead wires pick up less hum. Labs sometimes use a Faraday cage for very small signals.",
         related=("capacitive_coupling", "mains_interference")),

    # ------------------------------------------------------------------ heart & circulation
    Term("right_atrium", "Right atrium", "heart", "Receives oxygen-poor blood from the body.",
         "Blood returns through the venae cavae. Contains the SA node. Passes blood to the right ventricle through "
         "the tricuspid valve.",
         related=("right_ventricle", "tricuspid_valve", "systemic_circulation", "sa_node"), chapter=CH["cycle"]),
    Term("right_ventricle", "Right ventricle", "heart", "Pumps oxygen-poor blood to the lungs.",
         "Thinner-walled than the left ventricle because the lungs need only low pressure (about 25 mmHg). Ejects "
         "through the pulmonary valve.",
         related=("pulmonary_valve", "pulmonary_circulation", "right_atrium"), chapter=CH["cycle"]),
    Term("left_atrium", "Left atrium", "heart", "Receives oxygen-rich blood from the lungs.",
         "Blood arrives through the pulmonary veins and passes to the left ventricle through the mitral valve.",
         related=("left_ventricle", "mitral_valve", "pulmonary_circulation"), chapter=CH["cycle"]),
    Term("left_ventricle", "Left ventricle", "heart", "The main pump: sends oxygen-rich blood to the whole body.",
         "The thickest, strongest chamber; reaches about 120 mmHg each beat. Ejects through the aortic valve.",
         related=("aortic_valve", "systemic_circulation", "stroke_volume", "systole"), chapter=CH["cycle"]),
    Term("pulmonary_circulation", "Pulmonary circulation", "heart", "Right heart → lungs → left heart.",
         "Short, low-pressure loop where blood picks up oxygen and releases CO₂.",
         related=("right_ventricle", "left_atrium", "systemic_circulation"), chapter=CH["cycle"]),
    Term("systemic_circulation", "Systemic circulation", "heart", "Left heart → body → right heart.",
         "Long, high-pressure loop that supplies every organ, then returns oxygen-poor blood to the right atrium.",
         related=("left_ventricle", "right_atrium", "aorta", "pulmonary_circulation"), chapter=CH["cycle"]),
    Term("aorta", "Aorta", "heart", "The large artery leaving the left ventricle.",
         "Elastic: it stretches during ejection and recoils afterwards, keeping blood flowing between beats. The "
         "pressure wave that starts here is what the PPG eventually feels at the finger.",
         related=("aortic_valve", "pulse_wave", "systemic_circulation"), chapter=CH["cycle"]),
    Term("systole", "Systole", "heart", "The contraction phase of the ventricles.",
         "Starts just after the QRS: pressure rises, the AV valves close (S1), the semilunar valves open and blood is "
         "ejected. Ends when the ventricles relax and the semilunar valves close (S2).",
         related=("diastole", "s1", "s2", "ejection", "qrs"), chapter=CH["cycle"]),
    Term("diastole", "Diastole", "heart", "The relaxation and filling phase of the ventricles.",
         "The AV valves are open and the ventricles fill, first passively, then with a final push from the atria. "
         "Shrinks most when heart rate goes up.",
         related=("systole", "s2", "mitral_valve"), chapter=CH["cycle"]),
    Term("venous_return", "Venous return", "heart", "Blood flowing back to the right heart through the veins.",
         "Increases during inspiration (lower pressure in the chest draws blood in). More filling means a bigger "
         "next beat, which is one link between breathing, heart rate and the PPG.",
         related=("inspiration", "rsa", "stroke_volume", "respiratory_ppg"), chapter=CH["hr"]),
    Term("stroke_volume", "Stroke volume", "heart", "Blood ejected by one ventricle in one beat (about 70 mL).",
         "End-diastolic volume minus end-systolic volume. Cardiac output = stroke volume × heart rate.",
         related=("cardiac_output", "ejection", "venous_return"), chapter=CH["cycle"]),
    Term("cardiac_output", "Cardiac output", "heart", "Blood pumped per minute: stroke volume × heart rate.",
         "About 5 L/min at rest. Rises during exercise mainly through a higher heart rate.",
         related=("stroke_volume", "heart_rate"), chapter=CH["cycle"]),

    # ------------------------------------------------------------------ valves & heart sounds
    Term("heart_valve", "Heart valve", "valves", "A passive one-way door, opened and closed by pressure.",
         "A valve opens when the pressure behind it is higher than in front, and snaps shut when that reverses. No "
         "muscle opens it. Four valves: tricuspid and mitral (AV valves), pulmonary and aortic (semilunar valves).",
         related=("av_valves", "semilunar_valves", "s1", "s2"), chapter=CH["cycle"]),
    Term("av_valves", "AV valves (atrioventricular)", "valves", "Tricuspid (right) and mitral (left): between atria and ventricles.",
         "Open during filling; close at the start of ventricular contraction, making **S1**.",
         related=("tricuspid_valve", "mitral_valve", "s1"), chapter=CH["cycle"]),
    Term("semilunar_valves", "Semilunar valves", "valves", "Pulmonary (right) and aortic (left): between ventricles and arteries.",
         "Open during ejection; close when the ventricles relax, making **S2**.",
         related=("pulmonary_valve", "aortic_valve", "s2"), chapter=CH["cycle"]),
    Term("tricuspid_valve", "Tricuspid valve", "valves", "Right atrium → right ventricle.",
         "Three leaflets. One of the two AV valves whose closure makes S1.",
         related=("av_valves", "right_atrium", "right_ventricle", "s1"), chapter=CH["cycle"]),
    Term("mitral_valve", "Mitral valve", "valves", "Left atrium → left ventricle.",
         "Two leaflets (also called bicuspid). Its closure is the main contributor to S1.",
         related=("av_valves", "left_atrium", "left_ventricle", "s1"), chapter=CH["cycle"], aka="bicuspid valve"),
    Term("pulmonary_valve", "Pulmonary valve", "valves", "Right ventricle → pulmonary artery (to the lungs).",
         "A semilunar valve; its closure contributes to S2.",
         related=("semilunar_valves", "right_ventricle", "s2"), chapter=CH["cycle"]),
    Term("aortic_valve", "Aortic valve", "valves", "Left ventricle → aorta (to the body).",
         "A semilunar valve. Opens when left-ventricular pressure exceeds aortic pressure (ejection starts) and closes "
         "when it falls below again (S2, and the dicrotic notch in arterial pressure).",
         related=("semilunar_valves", "ejection", "s2", "dicrotic_notch"), chapter=CH["cycle"]),
    Term("s1", "S1 (“lub”)", "valves", "First heart sound: the AV valves (mitral, tricuspid) closing.",
         "Heard at the start of ventricular contraction, about 30–60 ms after the R peak. Lower-pitched and longer "
         "than S2.",
         see="First burst in the phonocardiogram, just after the QRS.",
         related=("av_valves", "systole", "qrs", "s2"), chapter=CH["cycle"], visual=("pcg", "s1")),
    Term("s2", "S2 (“dub”)", "valves", "Second heart sound: the semilunar valves (aortic, pulmonary) closing.",
         "Heard as the ventricles relax, about 0.3–0.4 s after the R peak, near the end of the T wave. Shorter and "
         "higher-pitched than S1.",
         see="Second burst in the phonocardiogram, near the end of the T wave.",
         related=("semilunar_valves", "t_wave", "diastole", "s1"), chapter=CH["cycle"], visual=("pcg", "s2")),
    Term("isovolumic", "Isovolumic contraction / relaxation", "valves", "Phases when all valves are shut and volume cannot change.",
         "Contraction: pressure rises after S1 until the aortic valve opens. Relaxation: pressure falls after S2 until "
         "the mitral valve opens.",
         related=("s1", "s2", "wiggers"), chapter=CH["cycle"]),
    Term("ejection", "Ejection", "valves", "Blood leaving the ventricle while the semilunar valve is open.",
         "Begins when ventricular pressure exceeds arterial pressure and launches the pressure pulse into the arteries.",
         related=("aortic_valve", "pulse_wave", "stroke_volume", "pre_ejection_period"), chapter=CH["cycle"]),
    Term("wiggers", "Wiggers diagram", "valves", "Classic chart of pressures, volume, ECG and sounds over one beat.",
         "Shows on one time axis how electrical events lead to pressure changes, valve movements and heart sounds. "
         "Chapter 3 has an interactive simplified version.",
         related=("systole", "diastole", "s1", "s2", "isovolumic"), chapter=CH["cycle"]),

    # ------------------------------------------------------------------ heart rate & breathing
    Term("heart_rate", "Heart rate (HR)", "rate", "Beats per minute: HR = 60 / RR (RR in seconds).",
         "Calculated from the time between beats, not measured directly. Higher HR means shorter R-R intervals. "
         "ECG and PPG should give approximately the same heart rate.",
         see="Count R peaks in 10 s and multiply by 6, or divide 60 by the R-R interval.",
         related=("rr_interval", "r_peak", "ppg", "rsa"), chapter=CH["hr"], aka="pulse rate, BPM", visual=("rr",)),
    Term("rr_interval", "R-R interval", "rate", "Time between two consecutive R peaks.",
         "The beat-to-beat interval. 0.8 s → 75 bpm; 0.5 s → 120 bpm. BIOPAC's “ECG R-R Interval” calculation "
         "channel computes it automatically.",
         related=("heart_rate", "r_peak", "beat_interval", "calculation_channel"), chapter=CH["hr"], visual=("rr",)),
    Term("beat_interval", "Beat-to-beat interval", "rate", "The time between consecutive heartbeats, from any signal.",
         "From the ECG it is the R-R interval; from a PPG it is the peak-to-peak interval. Varies slightly from beat "
         "to beat even at rest.",
         related=("rr_interval", "hrv", "ppg"), chapter=CH["hr"], aka="inter-beat interval, IBI"),
    Term("hrv", "Heart-rate variability", "rate", "The natural beat-to-beat variation of the R-R interval.",
         "A healthy heart does not tick like a metronome. Breathing (RSA), blood-pressure regulation and the nervous "
         "system all modulate the intervals.",
         related=("rsa", "rr_interval", "vagus_nerve"), chapter=CH["hr"], aka="HRV"),
    Term("rest_vs_excited", "Resting vs excited state", "rate", "Low HR with long intervals vs high HR with short intervals.",
         "At rest the vagus nerve slows the SA node; exercise, stress or excitement add sympathetic drive and "
         "adrenaline, so the heart beats faster and diastole (filling time) shortens most.",
         related=("heart_rate", "rr_interval", "diastole", "vagus_nerve"), chapter=CH["hr"]),
    Term("inspiration", "Inspiration", "rate", "Breathing in.",
         "The diaphragm moves down and the chest expands; pressure inside the chest drops, drawing air into the lungs "
         "and more blood back to the heart. Heart rate tends to rise.",
         related=("expiration", "rsa", "venous_return", "respiration_signal"), chapter=CH["hr"], aka="inhalation"),
    Term("expiration", "Expiration", "rate", "Breathing out.",
         "The chest relaxes and pressure inside it rises. Heart rate tends to fall.",
         related=("inspiration", "rsa", "respiration_signal"), chapter=CH["hr"], aka="exhalation"),
    Term("respiration_rate", "Respiration rate", "rate", "Breaths per minute (about 12–20 at rest).",
         "Counted from the peaks of the respiration signal, or estimated from how breathing modulates the ECG or PPG.",
         related=("respiration_signal", "respiratory_ppg"), chapter=CH["hr"]),
    Term("rsa", "Respiratory sinus arrhythmia (RSA)", "rate", "Heart rate rising with inspiration and falling with expiration.",
         "Normal, and strongest in young, relaxed people. Two mechanisms: breathing in reduces the vagal brake on the "
         "SA node, and changes chest pressure and venous return. Despite the name it is not a disease.",
         see="R-R intervals shorten during each breath in and lengthen during each breath out.",
         related=("inspiration", "expiration", "vagus_nerve", "hrv", "venous_return"), chapter=CH["hr"], visual=("resp",)),
    Term("vagus_nerve", "Vagus nerve", "rate", "The main parasympathetic nerve: the heart's brake.",
         "Slows the SA node. Its activity drops during inspiration and rises during expiration, which drives RSA.",
         related=("sa_node", "rsa", "rest_vs_excited")),

    # ------------------------------------------------------------------ PPG & pulse
    Term("pulse_arrival", "Pulse arrival (foot)", "ppg", "The moment the pulse reaches the sensor: the start of the PPG upstroke.",
         "Often found with the *intersecting tangent* method: where the steepest rise, extended backwards, meets "
         "the minimum before the pulse.",
         related=("pulse_arrival_time", "systolic_upstroke", "ppg"), chapter=CH["ppg"], aka="pulse foot",
         visual=("ppg", "foot")),
    Term("systolic_upstroke", "Systolic upstroke", "ppg", "The steep rise of the PPG as blood rushes in.",
         "Corresponds to the arrival of the pressure wave generated by ventricular ejection.",
         related=("pulse_arrival", "systolic_peak", "ejection"), chapter=CH["ppg"], visual=("ppg", "upstroke")),
    Term("systolic_peak", "Systolic peak", "ppg", "Maximum blood volume of the PPG pulse.",
         "Used for heart rate from PPG (peak-to-peak intervals). Its height (pulse amplitude) varies with breathing "
         "and with how tightly the sensor is pressed.",
         related=("systolic_upstroke", "dicrotic_notch", "heart_rate"), chapter=CH["ppg"], visual=("ppg", "peak")),
    Term("dicrotic_notch", "Dicrotic notch", "ppg", "Small dip or kink on the PPG's falling slope.",
         "Linked to aortic-valve closure (the incisura in aortic pressure) and to pressure waves reflected from the "
         "periphery. Clearer in young people and at some measurement sites; may be only a shoulder.",
         related=("aortic_valve", "s2", "diastolic_runoff"), chapter=CH["ppg"], visual=("ppg", "notch")),
    Term("diastolic_runoff", "Diastolic runoff", "ppg", "The slow decay of the PPG until the next pulse.",
         "Blood drains out of the tissue while the heart refills.",
         related=("dicrotic_notch", "diastole"), chapter=CH["ppg"], visual=("ppg", "diastolic")),
    Term("pulse_wave", "Pressure pulse (pulse wave)", "ppg", "The pressure wave travelling from the heart through the arteries.",
         "Launched by ejection into the elastic aorta; travels at several metres per second (much slower than blood "
         "flow itself and far slower than electricity). Faster in stiffer arteries and at higher blood pressure.",
         related=("ejection", "aorta", "pulse_transit_time", "ppg"), chapter=CH["ppg"]),
    Term("pulse_arrival_time", "Pulse arrival time (PAT)", "ppg", "Time from the ECG R peak to the PPG pulse arrival.",
         "About 200–300 ms at the finger at rest. PAT = pre-ejection period + pulse transit time. Shortens during "
         "exercise. It is the core example of *ECG first, PPG later*.",
         see="The gap between each R peak and the next PPG upstroke.",
         related=("pre_ejection_period", "pulse_transit_time", "r_peak", "pulse_arrival"), chapter=CH["ppg"],
         aka="PAT, pulse arrival delay"),
    Term("pulse_transit_time", "Pulse transit time (PTT)", "ppg", "Travel time of the pressure pulse between two sites.",
         "E.g. from the heart (aortic valve opening) to the finger, or between two points on the same finger. Studied "
         "for cuff-less blood-pressure estimation.",
         related=("pulse_arrival_time", "pulse_wave", "pre_ejection_period"), chapter=CH["ppg"], aka="PTT"),
    Term("pre_ejection_period", "Pre-ejection period (PEP)", "ppg", "From electrical activation (QRS) to the opening of the aortic valve.",
         "The time the ventricle needs to build up pressure (includes isovolumic contraction). Part of PAT that is "
         "not travel time.",
         related=("pulse_arrival_time", "isovolumic", "ejection"), chapter=CH["ppg"], aka="PEP"),
    Term("ppg_wavelength", "PPG wavelengths (green, red, infrared)", "ppg", "Different light colours probe different depths.",
         "Green (~530 nm) stays shallow and copes better with motion, used by watches for heart rate. Red (~660 nm) "
         "and infrared (~880–940 nm) go deeper; their ratio gives blood-oxygen saturation (SpO₂) in pulse oximeters.",
         related=("ppg", "spo2", "smartwatch"), chapter=CH["ppg"]),
    Term("spo2", "SpO₂ (pulse oximetry)", "ppg", "Blood-oxygen saturation estimated from red and infrared PPG.",
         "Oxygen-rich and oxygen-poor haemoglobin absorb red and infrared light differently; comparing the pulsatile "
         "parts of both signals gives the saturation.",
         related=("ppg_wavelength", "ppg"), aka="oxygen saturation"),
    Term("respiratory_ppg", "Respiratory modulation of the PPG", "ppg", "Breathing makes the PPG's amplitude and baseline rise and fall.",
         "Breathing changes chest pressure, venous return, stroke volume and the blood volume in the periphery, so "
         "the PPG 'breathes' along with you. Respiration rate can be estimated from it.",
         related=("venous_return", "stroke_volume", "respiration_rate", "inspiration"), chapter=CH["ppg"]),

    # ------------------------------------------------------------------ motion, noise & filters
    Term("noise", "Noise", "noise", "Any part of the recorded signal that is not the physiology you want.",
         "Sources include movement, muscles, mains hum, electrode contact and the electronics themselves. How much "
         "noise there is relative to the signal is the SNR.",
         related=("snr", "motion_artefact", "mains_interference", "emg_noise", "baseline_wander"), chapter=CH["motion"]),
    Term("motion_artefact", "Motion artefact", "noise", "A disturbance caused by movement, not by the body's physiology.",
         "Movement changes electrode contact (ECG) or presses on tissue and lets in ambient light (PPG). If a "
         "disturbance in ECG or PPG coincides with accelerometer activity, suspect motion.",
         see="Irregular spikes or drifts that line up with accelerometer movement.",
         related=("accelerometer", "electrode_motion", "ppg", "noise"), chapter=CH["motion"], aka="movement artefact"),
    Term("electrode_motion", "Electrode-motion artefact", "noise", "ECG disturbance from the electrode moving on the skin.",
         "Stretching the skin changes the electrode's half-cell potential and contact impedance. It overlaps the "
         "ECG's own frequencies, can mimic heartbeats, and cannot be removed by simple filters: the main subject of "
         "the stress-test bench.",
         related=("motion_artefact", "half_cell", "skin_impedance", "qrs_detector"), chapter=CH["motion"]),
    Term("baseline_wander", "Baseline wander", "noise", "Slow drift of the ECG baseline.",
         "Caused by breathing, sweat and slowly changing electrode contact (below about 1 Hz). Removed with a "
         "high-pass filter around 0.5 Hz.",
         related=("high_pass", "baseline", "half_cell"), chapter=CH["motion"]),
    Term("emg_noise", "Muscle noise (EMG)", "noise", "Electrical activity of skeletal muscles picked up by the ECG electrodes.",
         "Shivering, tensing or moving the arms add broadband, high-frequency fuzz. Partly reduced by a low-pass "
         "filter, but it overlaps the QRS band.",
         related=("low_pass", "noise", "motion_artefact"), chapter=CH["motion"], aka="muscle artefact"),
    Term("snr", "SNR (signal-to-noise ratio)", "noise", "How strong the signal is compared with the noise, in dB.",
         "SNR = 10·log₁₀(signal power / noise power). +24 dB: noise barely visible. 0 dB: equal power. −6 dB: noise "
         "four times the signal power. The bench tests detectors from 24 dB down to −6 dB.",
         related=("noise", "qrs_detector"), chapter=CH["motion"]),
    Term("filter", "Filter", "noise", "Signal processing that keeps some frequencies and removes others.",
         "Works only when the noise sits at different frequencies from the signal. Types: high-pass, low-pass, "
         "band-pass, notch.",
         related=("high_pass", "low_pass", "band_pass", "notch_filter"), chapter=CH["motion"]),
    Term("high_pass", "High-pass filter", "noise", "Removes slow components below a cut-off frequency.",
         "At about 0.5 Hz it removes baseline wander while keeping the ECG shape.",
         related=("baseline_wander", "filter"), chapter=CH["motion"]),
    Term("low_pass", "Low-pass filter", "noise", "Removes fast components above a cut-off frequency.",
         "At about 40 Hz it smooths muscle noise; it is also the anti-aliasing filter before sampling.",
         related=("emg_noise", "anti_aliasing", "filter"), chapter=CH["motion"]),
    Term("band_pass", "Band-pass filter", "noise", "Keeps only a band of frequencies.",
         "QRS detectors often use about 5–15 Hz, where the QRS has most of its energy and P/T waves and baseline wander "
         "have little.",
         related=("filter", "qrs_detector"), chapter=CH["motion"]),
    Term("notch_filter", "Notch filter", "noise", "Removes one narrow frequency, e.g. 50 Hz mains hum.",
         "Very selective, so the ECG around it is barely touched.",
         related=("mains_interference", "filter"), chapter=CH["motion"]),
    Term("qrs_detector", "QRS detector", "noise", "An algorithm that finds the R peak of each heartbeat in an ECG.",
         "Filters the ECG, emphasises steep slopes and applies an adaptive threshold. Every heart-rate number depends "
         "on it, and noise makes it miss beats or invent false ones: that is what the stress-test bench measures.",
         related=("r_peak", "heart_rate", "electrode_motion", "snr"), chapter=CH["start"], aka="beat detector"),

    # ------------------------------------------------------------------ recording & processing
    Term("daq", "Data acquisition", "acq", "Turning sensor voltages into numbers a computer can store.",
         "Chain: electrodes / sensor → amplifier → analogue filters → ADC → software. The BIOPAC MP36 is a data "
         "acquisition unit.",
         related=("adc", "sampling_rate", "differential_amplifier", "biopac"), chapter=CH["acq"], aka="DAQ"),
    Term("adc", "ADC (analogue-to-digital converter)", "acq", "Samples a voltage and rounds it to a number.",
         "Defined by its sampling rate (how often) and resolution (how finely).",
         related=("sampling_rate", "resolution", "daq"), chapter=CH["acq"]),
    Term("sampling_rate", "Sampling rate", "acq", "How many samples per second are taken (Hz).",
         "The class setup used 2 kHz; MIT-BIH uses 360 Hz. Too low and short events such as the QRS are missed or "
         "distorted.",
         related=("nyquist", "aliasing", "adc"), chapter=CH["acq"], aka="sampling frequency, fs"),
    Term("nyquist", "Nyquist frequency", "acq", "Half the sampling rate: the highest frequency that can be represented.",
         "To capture a signal correctly you must sample at more than twice its highest frequency.",
         related=("sampling_rate", "aliasing", "anti_aliasing"), chapter=CH["acq"]),
    Term("aliasing", "Aliasing", "acq", "High frequencies masquerading as low ones after sampling.",
         "A 50 Hz hum sampled at 60 Hz shows up as a fake 10 Hz wave. Prevented by low-pass filtering below Nyquist "
         "before sampling.",
         related=("nyquist", "anti_aliasing", "sampling_rate"), chapter=CH["acq"]),
    Term("anti_aliasing", "Anti-aliasing filter", "acq", "Low-pass filter applied before the ADC.",
         "Removes everything above the Nyquist frequency so it cannot fold back into the recording.",
         related=("aliasing", "low_pass", "nyquist"), chapter=CH["acq"]),
    Term("resolution", "Resolution (bits)", "acq", "How finely the ADC divides its input range.",
         "N bits give 2ᴺ levels; the smallest step is range / 2ᴺ (1 LSB). MIT-BIH: 11 bits over 10 mV ≈ 5 µV. Too few "
         "bits turn small P and T waves into staircases (quantization).",
         related=("adc", "quantization"), chapter=CH["acq"]),
    Term("quantization", "Quantization", "acq", "Rounding each sample to the nearest ADC level.",
         "Adds a small error (quantization noise), about LSB/√12 RMS.",
         related=("resolution", "adc")),
    Term("calculation_channel", "Calculation channel", "acq", "A derived channel computed by software from recorded ones.",
         "In BIOPAC Student Lab, e.g. “ECG R-R Interval” or BPM: the software detects each R peak and writes the "
         "interval as a new channel. Computed, not measured.",
         related=("rr_interval", "heart_rate", "biopac"), chapter=CH["acq"]),
    Term("biopac", "BIOPAC MP36 / Student Lab", "acq", "The teaching data-acquisition system used in class.",
         "MP36 hardware (4 analogue input channels) records ECG, respiration, PPG and accelerometer; BIOPAC Student "
         "Lab software displays them, filters them and computes calculation channels. The CEBS recordings in this app "
         "were made with an MP36.",
         related=("daq", "calculation_channel", "isolation", "synchronization"), chapter=CH["acq"]),
    Term("smartwatch", "Smartwatch sensors (e.g. Apple Watch)", "acq", "PPG, accelerometer, gyroscope and a single-lead ECG in one device.",
         "Green PPG for routine heart rate; accelerometer and gyroscope for movement; an on-demand ECG between the "
         "back electrode and a finger on the crown. Two contact points → one voltage difference → a single-lead ECG "
         "similar to Lead I.",
         related=("single_lead", "ppg_wavelength", "accelerometer", "dry_electrode"), chapter=CH["motion"]),
    Term("single_lead", "Single-lead ECG", "acq", "An ECG from just one electrode pair.",
         "Enough for heart rate and rhythm timing (R peaks); a clinical 12-lead ECG looks at the heart from 12 "
         "directions. Your class setup was single-lead.",
         related=("lead", "smartwatch", "einthoven"), chapter=CH["ecg"]),
]

TERMS: dict[str, Term] = {t.key: t for t in _T}

# Concept map: the causal chain taught in class, plus breathing and motion as modulators.
MAP_DOMAINS = {
    "Electrical": "#1F3A93", "Mechanical": "#2A8C82", "Acoustic": "#D2602A", "Vascular / optical": "#B8322A",
    "Derived": "#7A746A", "Breathing": "#5B7BD5", "Motion": "#9B4F96",
}
MAP_NODES = [  # key, label, x, y, domain   (laid out so that no edge crosses a node)
    ("sa_node", "SA node fires", 0.0, 5.0, "Electrical"),
    ("p_wave", "P wave<br>(atria activate)", 1.3, 5.0, "Electrical"),
    ("qrs", "QRS complex<br>(ventricles activate)", 1.3, 3.4, "Electrical"),
    ("t_wave", "T wave<br>(ventricles reset)", 1.3, 1.6, "Electrical"),
    ("systole", "Ventricles contract<br>(systole)", 2.8, 3.4, "Mechanical"),
    ("s1", "S1 “lub”<br>AV valves close", 4.3, 4.6, "Acoustic"),
    ("ejection", "Aortic valve opens<br>blood ejected", 4.3, 3.4, "Mechanical"),
    ("pulse_wave", "Pressure pulse<br>travels", 5.8, 3.4, "Vascular / optical"),
    ("ppg", "PPG pulse<br>at the finger", 7.3, 3.4, "Vascular / optical"),
    ("diastole", "Ventricles relax<br>(diastole)", 2.8, 1.6, "Mechanical"),
    ("s2", "S2 “dub”<br>semilunar valves close", 4.3, 1.6, "Acoustic"),
    ("rr_interval", "R-R interval", 0.0, 2.5, "Derived"),
    ("heart_rate", "Heart rate<br>= 60 / RR", 0.0, 0.7, "Derived"),
    ("pulse_arrival_time", "Pulse arrival time<br>(R peak → PPG)", 4.3, 6.1, "Derived"),
    ("respiration_signal", "Breathing", 5.8, 0.3, "Breathing"),
    ("rsa", "RSA", 2.8, 0.3, "Breathing"),
    ("accelerometer", "Accelerometer<br>(movement)", 8.7, 6.1, "Motion"),
    ("motion_artefact", "Motion artefact", 8.7, 4.6, "Motion"),
]
MAP_EDGES = [  # from, to, label
    ("sa_node", "p_wave", ""), ("p_wave", "qrs", "AV-node delay"), ("qrs", "systole", "triggers"),
    ("systole", "s1", ""), ("systole", "ejection", ""), ("ejection", "pulse_wave", ""), ("pulse_wave", "ppg", ""),
    ("qrs", "t_wave", ""), ("t_wave", "diastole", ""), ("diastole", "s2", ""),
    ("qrs", "rr_interval", ""), ("rr_interval", "heart_rate", ""), ("qrs", "pulse_arrival_time", ""),
    ("ppg", "pulse_arrival_time", ""), ("respiration_signal", "rsa", ""), ("rsa", "heart_rate", "modulates"),
    ("respiration_signal", "ppg", "modulates"), ("accelerometer", "motion_artefact", "detects"),
    ("motion_artefact", "ppg", "distorts"),
]

# The same relationships as a linear story, for narrow screens where a graph cannot be read.
MAP_STORY = [
    ("One heartbeat", ["sa_node", "p_wave", "qrs", "systole", "s1", "ejection", "pulse_wave", "ppg", "t_wave",
                       "diastole", "s2"]),
    ("What is calculated from it", ["rr_interval", "heart_rate", "pulse_arrival_time"]),
    ("What changes what you measure", ["respiration_signal", "rsa", "accelerometer", "motion_artefact"]),
]
DOMAIN_BADGE = {"Electrical": "blue", "Mechanical": "green", "Acoustic": "orange", "Vascular / optical": "red",
                "Derived": "gray", "Breathing": "violet", "Motion": "violet"}
