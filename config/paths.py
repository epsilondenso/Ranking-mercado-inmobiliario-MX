from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
RAW_DATA = DATA / "raw"
SCORED_DATA = DATA / "scored"
CLEAN_DATA = DATA / "clean"
GROUPED_DATA = DATA / "grouped"