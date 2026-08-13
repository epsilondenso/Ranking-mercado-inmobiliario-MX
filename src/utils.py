from pathlib import Path

def extraer_sufijo_csv(ruta: str) -> str:
    return Path(ruta).stem.rsplit("_", 1)[-1]