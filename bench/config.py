"""Shared constants for the bench."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

FS = 360  # Hz, confirmed from the .hea headers in the data audit
MATCH_TOL_S = 0.150  # EC57-style beat-matching tolerance
WINDOW_S = 10.0  # window length for HR error and block bootstrap

# Annotation symbols counted as beats (PhysioNet/WFDB beat codes).
BEAT_SYMBOLS = frozenset("NLRBAaJSVrFejnE/fQ?")

NSTDB_SNRS = [24, 18, 12, 6, 0, -6]
NOISE_TYPES = {"em": "Electrode motion", "ma": "Muscle artefact", "bw": "Baseline wander"}

# Slice 3 extension records: output of scripts/select_records.py (rule in README).
EXTENSION_RECORDS = ["100", "101", "103", "109", "111", "112", "113", "115", "116", "117", "121", "122", "123"]
NSTDB_SOURCES = ["118", "119"]
MIXED_RECORDS = NSTDB_SOURCES + EXTENSION_RECORDS
CHANNEL = 0  # MLII in every benchmarked record
