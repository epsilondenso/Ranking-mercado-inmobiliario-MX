import argparse
import json
import re
import statistics
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


def redondear_coordenadas(coordenadas: Any, decimales: int) -> Any:
    """
    Redondea recursivamente las coordenadas de una geometría.

    Parameters
    ----------
    coordenadas : Any
        Lista (anidada) de coordenadas.
    decimales : int
        Número de decimales a conservar.

    Returns
    -------
    Any
        Coordenadas redondeadas con la misma estructura.
    """
    if isinstance(coordenadas, (int, float)):
        return round(coordenadas, decimales)

    return [redondear_coordenadas(c, decimales) for c in coordenadas]


def actualizar_feature(
    feature: dict[str, Any],
    metricas: dict[tuple[str, str], dict[str, Any]],
    decimales: int | None = None,
) -> tuple[dict[str, Any], int, int]:
    """
    Construye el feature de salida con las métricas de sus colonias.

    En la entrada, ``properties.colonias`` es una lista de nombres y
    ``properties.tipo_asenta`` una lista paralela con su tipo. En la
    salida cada colonia lleva su propio ``tipo_asenta`` (None para las
    añadidas desde los anuncios) y el feature tiene propiedades escalares
    (``score_cp``, ``precio_m2_cp``, ``n_colonias_score``) para colorear
    el polígono directamente en el mapa.

    Parameters
    ----------
    feature : dict
        Feature GeoJSON correspondiente a un código postal.
    metricas : dict
        Índice de métricas por código postal y colonia.
    decimales : int or None
        Decimales de las coordenadas; None conserva la precisión original.

    Returns
    -------
    tuple
        Feature de salida, colonias actualizadas y colonias añadidas.
    """
    propiedades = feature.get("properties") or {}

    codigo_postal = normalizar_codigo_postal(
        propiedades.get("d_codigo")
    )

    nombres = propiedades.get("colonias")
    tipos = propiedades.get("tipo_asenta")

    if not isinstance(nombres, list):
        nombres = []

    if not isinstance(tipos, list):
        tipos = []

    colonias: list[dict[str, Any]] = []
    actualizadas = 0
    nombres_existentes: set[str] = set()

    # Colonias ya presentes en el GeoJSON.
    for i, nombre_original in enumerate(nombres):
        nombre = normalizar_colonia(nombre_original)
        datos = None

        if nombre is not None:
            nombres_existentes.add(nombre)
            datos = metricas.get((codigo_postal, nombre))

        colonias.append(
            {
                "colonia": nombre_original,
                "tipo_asenta": tipos[i] if i < len(tipos) else None,
                "precio_m2": datos["precio_m2"] if datos else None,
                "score": datos["score"] if datos else None,
            }
        )

        if datos is not None:
            actualizadas += 1

    # Añadir colonias con score que no existan en el GeoJSON.
    nuevas = 0

    for (cp, nombre), datos in metricas.items():
        if codigo_postal is None or cp != codigo_postal:
            continue

        if nombre in nombres_existentes:
            continue

        # Solo añadir nuevas colonias que tengan score.
        if datos["score"] is None:
            continue

        colonias.append(
            {
                "colonia": datos["colonia"],
                "tipo_asenta": None,
                "precio_m2": datos["precio_m2"],
                "score": datos["score"],
            }
        )

        nombres_existentes.add(nombre)
        nuevas += 1

    scores = [c["score"] for c in colonias if c["score"] is not None]
    precios = [
        c["precio_m2"] for c in colonias if c["precio_m2"] is not None
    ]

    geometria = feature.get("geometry")

    if decimales is not None and geometria:
        geometria = {
            **geometria,
            "coordinates": redondear_coordenadas(
                geometria["coordinates"],
                decimales,
            ),
        }

    salida = {
        "type": "Feature",
        "properties": {
            "d_codigo": codigo_postal,
            "estado": propiedades.get("estado"),
            "municipio": propiedades.get("municipio"),
            "score_cp": statistics.fmean(scores) if scores else None,
            "precio_m2_cp": (
                statistics.median(precios) if precios else None
            ),
            "n_colonias_score": len(scores),
            "colonias": colonias,
        },
        "geometry": geometria,
    }

    return salida, actualizadas, nuevas


def escribir_geojson(geojson: dict[str, Any], ruta: Path) -> None:
    """
    Guarda un FeatureCollection con indentación legible y tamaño contenido.

    La estructura (features y propiedades) se indenta, pero cada geometría
    y cada colonia se escriben en una sola línea: indentar las coordenadas
    multiplicaría el tamaño del archivo.

    Parameters
    ----------
    geojson : dict
        FeatureCollection a guardar.
    ruta : Path
        Archivo de destino.
    """
    compactos: list[Any] = []

    def marcar(valor: Any) -> str:
        compactos.append(valor)
        return f"@@COMPACTO_{len(compactos) - 1}@@"

    features = []

    for feature in geojson["features"]:
        propiedades = feature["properties"]
        features.append(
            {
                **feature,
                "properties": {
                    **propiedades,
                    "colonias": [
                        marcar(c) for c in propiedades["colonias"]
                    ],
                },
                "geometry": marcar(feature["geometry"]),
            }
        )

    texto = json.dumps(
        {**geojson, "features": features},
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )

    texto = re.sub(
        r'"@@COMPACTO_(\d+)@@"',
        lambda m: json.dumps(
            compactos[int(m.group(1))],
            ensure_ascii=False,
            allow_nan=False,
            separators=(", ", ": "),
        ),
        texto,
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def actualizar_archivo(
    ruta_entrada: Path,
    ruta_salida: Path,
    metricas: dict[tuple[str, str], dict[str, Any]],
    decimales: int | None = None,
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
    decimales : int or None
        Decimales de las coordenadas; None conserva la precisión original.

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
    features_salida = []

    for feature in features:
        salida, actualizadas, nuevas = actualizar_feature(
            feature,
            metricas,
            decimales,
        )
        features_salida.append(salida)
        total_actualizadas += actualizadas
        total_nuevas += nuevas

    if geojson["type"] == "FeatureCollection":
        geojson["features"] = features_salida
    else:
        geojson = {
            "type": "FeatureCollection",
            "features": features_salida,
        }

    escribir_geojson(geojson, ruta_salida)

    return len(features), total_actualizadas, total_nuevas


def main() -> None:
    """
    Procesa los GeoJSON postales y guarda sus métricas actualizadas.
    """
    parser = argparse.ArgumentParser(
        description="Asigna score y precio a las colonias de los GeoJSON."
    )
    parser.add_argument(
        "--decimales",
        type=int,
        default=None,
        help=(
            "Redondear coordenadas a N decimales (6 ≈ 0.1 m, 5 ≈ 1 m). "
            "Por defecto conserva la precisión original."
        ),
    )
    args = parser.parse_args()

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
            args.decimales,
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