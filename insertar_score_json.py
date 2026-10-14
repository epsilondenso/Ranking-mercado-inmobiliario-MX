import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from config.paths import SCORED_DATA, GEOJSON_CP


# Configuración
INPUT_CSV = SCORED_DATA / "global_norm_cp.csv"
OUTPUT_DIR = GEOJSON_CP.parent / "geojson_with_scores"
MIN_ANUNCIOS = 3


def normalizar_codigo_postal(codigo: Any) -> str | None:
    """
    Normaliza un código postal a cinco dígitos.

    Parameters
    ----------
    codigo : Any
        Código postal de origen.

    Returns
    -------
    str or None
        Código postal normalizado o None si es inválido.
    """
    if pd.isna(codigo):
        return None

    codigo = str(codigo).strip()

    # Evitar convertir valores numéricos como 3100.0 en códigos inválidos.
    if re.fullmatch(r"\d+\.0", codigo):
        codigo = codigo[:-2]

    if not codigo.isdigit() or len(codigo) > 5:
        return None

    return codigo.zfill(5)


def normalizar_colonia(nombre: Any) -> str | None:
    """
    Normaliza nombres para comparar colonias sin alterar su texto original.

    Parameters
    ----------
    nombre : Any
        Nombre de la colonia.

    Returns
    -------
    str or None
        Nombre normalizado o None si está vacío.
    """
    if not isinstance(nombre, str) or not nombre.strip():
        return None

    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(
        caracter
        for caracter in nombre
        if not unicodedata.combining(caracter)
    )

    return " ".join(nombre.casefold().split())


def cargar_metricas(
    ruta_csv: Path,
    min_anuncios: int,
) -> dict[tuple[str, str], dict[str, Any]]:
    
    """
    Construye un índice de métricas por código postal y colonia.

    Parameters
    ----------
    ruta_csv : Path
        Ruta al archivo CSV de scores.
    min_anuncios : int
        Número mínimo de anuncios para incluir una colonia.

    Returns
    -------
    dict
        Métricas indexadas por (código postal, colonia normalizada).
    """
    columnas = [
        "codigo_postal",
        "colonia",
        "conteo_cp",
        "qs_score",
        "precio_m2",
    ]

    df = pd.read_csv(
        ruta_csv,
        usecols=columnas,
        dtype={"codigo_postal": "string"},
    )

    df["codigo_postal"] = df["codigo_postal"].map(
        normalizar_codigo_postal
    )
    df["colonia_key"] = df["colonia"].map(normalizar_colonia)

    df = df[
        df["codigo_postal"].notna()
        & df["colonia_key"].notna()
        & (df["conteo_cp"] >= min_anuncios)
    ].copy()

    # Una única entrada por código postal y colonia.
    # Si hay duplicados, se promedian las métricas disponibles.
    df = (
        df.groupby(
            ["codigo_postal", "colonia_key"],
            as_index=False,
            dropna=False,
        )
        .agg(
            colonia=("colonia", "first"),
            qs_score=("qs_score", "mean"),
            precio_m2=("precio_m2", "mean"),
        )
    )

    metricas: dict[tuple[str, str], dict[str, Any]] = {}

    for fila in df.itertuples(index=False):
        clave = (fila.codigo_postal, fila.colonia_key)

        metricas[clave] = {
            "colonia": fila.colonia,
            "score": (
                float(fila.qs_score)
                if pd.notna(fila.qs_score)
                else None
            ),
            "precio_m2": (
                float(fila.precio_m2)
                if pd.notna(fila.precio_m2)
                else None
            ),
        }

    return metricas


def actualizar_feature(
    feature: dict[str, Any],
    metricas: dict[tuple[str, str], dict[str, Any]],
) -> tuple[int, int]:
    """
    Actualiza las métricas de las colonias de un código postal.

    Parameters
    ----------
    feature : dict
        Feature GeoJSON correspondiente a un código postal.
    metricas : dict
        Índice de métricas por código postal y colonia.

    Returns
    -------
    tuple of int
        Número de colonias actualizadas y añadidas.
    """
    propiedades = feature.setdefault("properties", {})

    codigo_postal = normalizar_codigo_postal(
        propiedades.get("d_codigo")
    )

    if codigo_postal is None:
        return 0, 0

    colonias = propiedades.get("colonias")

    if not isinstance(colonias, list):
        colonias = []
        propiedades["colonias"] = colonias

    actualizadas = 0
    nombres_existentes: set[str] = set()

    # Actualizar las colonias ya presentes en el GeoJSON.
    for i, colonia in enumerate(colonias):
        if isinstance(colonia, str):
            colonia = {
                "colonia": colonia,
                "tipo_asenta": "colonia",
            }
            colonias[i] = colonia
    
        if not isinstance(colonia, dict):
            continue
        
        nombre = normalizar_colonia(colonia.get("colonia"))
    
        if nombre is None:
            colonia["precio_m2"] = None
            colonia["score"] = None
            continue
        nombres_existentes.add(nombre)
    
        datos = metricas.get((codigo_postal, nombre))
    
        colonia["precio_m2"] = (
            datos["precio_m2"] if datos else None
        )
        colonia["score"] = (
            datos["score"] if datos else None
        )
    
        if datos is not None:
            actualizadas += 1

    # Añadir colonias con score que no existan en el GeoJSON.
    nuevas = 0

    for (cp, nombre), datos in metricas.items():
        if cp != codigo_postal:
            continue

        if nombre in nombres_existentes:
            continue

        # Solo añadir nuevas colonias que tengan score.
        if datos["score"] is None:
            continue

        colonias.append(
            {
                "colonia": datos["colonia"],
                "tipo_asenta": "colonia",
                "precio_m2": datos["precio_m2"],
                "score": datos["score"],
            }
        )

        nombres_existentes.add(nombre)
        nuevas += 1

    return actualizadas, nuevas


def actualizar_archivo(
    ruta_entrada: Path,
    ruta_salida: Path,
    metricas: dict[tuple[str, str], dict[str, Any]],
) -> tuple[int, int, int]:
    """
    Actualiza y guarda las métricas de un archivo GeoJSON.

    Parameters
    ----------
    ruta_entrada : Path
        Archivo GeoJSON original.
    ruta_salida : Path
        Destino del GeoJSON actualizado.
    metricas : dict
        Índice de métricas por código postal y colonia.

    Returns
    -------
    tuple of int
        Features procesadas, colonias actualizadas y añadidas.
    """
    with ruta_entrada.open("r", encoding="utf-8") as archivo:
        geojson = json.load(archivo)

    if geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
    elif geojson.get("type") == "Feature":
        features = [geojson]
    else:
        raise ValueError(
            f"Tipo GeoJSON no soportado: {ruta_entrada}"
        )

    total_actualizadas = 0
    total_nuevas = 0

    for feature in features:
        actualizadas, nuevas = actualizar_feature(feature, metricas)
        total_actualizadas += actualizadas
        total_nuevas += nuevas

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    with ruta_salida.open("w", encoding="utf-8") as archivo:
        json.dump(
            geojson,
            archivo,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )

    return len(features), total_actualizadas, total_nuevas


def main() -> None:
    """
    Procesa los GeoJSON postales y guarda sus métricas actualizadas.
    """
    metricas = cargar_metricas(INPUT_CSV, MIN_ANUNCIOS)

    archivos = sorted(GEOJSON_CP.glob("*.geojson"))

    if not archivos:
        print(f"No se encontraron GeoJSON en {GEOJSON_CP}")
        return

    total_features = 0
    total_actualizadas = 0
    total_nuevas = 0

    for entrada in archivos:
        salida = OUTPUT_DIR / entrada.name

        features, actualizadas, nuevas = actualizar_archivo(
            entrada,
            salida,
            metricas,
        )

        total_features += features
        total_actualizadas += actualizadas
        total_nuevas += nuevas

        print(
            f"{entrada.name}: "
            f"{features} códigos postales, "
            f"{actualizadas} colonias actualizadas, "
            f"{nuevas} colonias añadidas"
        )

    print("\nProceso terminado.")
    print(f"Features procesadas: {total_features}")
    print(f"Colonias actualizadas: {total_actualizadas}")
    print(f"Colonias añadidas: {total_nuevas}")
    print(f"Directorio de salida: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()