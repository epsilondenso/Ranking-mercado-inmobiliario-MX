
import pandas as pd

from config.paths import GROUPED_DATA, SCORED_DATA
from src.score import minmax_columns, pavc_score, qs_score


def build_global_ranking() -> pd.DataFrame:
    """Concatena los CSV agrupados, normaliza sobre el conjunto global y guarda el resultado."""
    files = sorted(GROUPED_DATA.glob("grouped_*.csv"))
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos grouped_*.csv en {GROUPED_DATA}")

    frames = []
    for file in files:
        frame = pd.read_csv(file)
        frame.insert(0, "estado", file.stem.removeprefix("grouped_"))
        frames.append(frame)

    grouped = pd.concat(frames, ignore_index=True)
    normalized = minmax_columns(
        grouped,
        {
            "precio_m2_mediana": (0, 1),
            "precio_m2_cv": (1, 0),
            "edad_dias_promedio": (1, 0),
            "ln(1+n)": (0, 1),
        },
    )
    normalized = qs_score(pavc_score(normalized))

    SCORED_DATA.mkdir(parents=True, exist_ok=True)
    output_path = SCORED_DATA / "global_norm.csv"
    normalized.to_csv(output_path, index=False)
    print(f"Ranking global guardado en {output_path} ({len(normalized)} colonias)")
    return normalized


if __name__ == "__main__":
    build_global_ranking()
