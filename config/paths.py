from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
RAW_DATA = DATA / "raw"
PREPRO_DATA = DATA / "preprocessed"
CLEAN_DATA = DATA / "clean"
GROUPED_DATA = DATA / "grouped"