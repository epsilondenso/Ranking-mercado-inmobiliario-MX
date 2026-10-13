import html 
import pandas as pd
import geopandas as gpd
import folium
import branca.colormap as cm
import shapely
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from config.paths import SCORED_DATA, GEOJSON_CP

test = pd.read_csv(SCORED_DATA / "global_norm_cp.csv")[
["estado",
"municipio",
"colonia",
"codigo_postal",
"conteo",
"proporcion",
"qs_score",
"precio_m2"]
].rename(columns={"proporcion":"proporcion_cp_colonia", 
                  "conteo": "conteo_cp"})
test_filter = test[test["conteo_cp"]>=3]

geojson_dir = GEOJSON_CP

files = list(geojson_dir.glob("*.geojson"))

gdfs = [gpd.read_file(file) for file in files]

poligonos = gpd.GeoDataFrame(
    pd.concat(gdfs, ignore_index=True),
    crs=gdfs[0].crs
)


poligonos["d_codigo"] = (
    poligonos["d_codigo"]
    .astype("string")
    .str.strip()
    .str.zfill(5)
)

metricas = test_filter[
    ["codigo_postal", "colonia", "precio_m2", "qs_score"]
].copy()

metricas["codigo_postal"] = (
    metricas["codigo_postal"]
    .astype("string")
    .str.strip()
    .str.zfill(5)
)

cp_con_score = metricas.loc[
    metricas["qs_score"].notna(), "codigo_postal"
].unique()

# Solo se dibujan los CP con score: los ~36k polígonos del país
# (~10.7M vértices) generan un HTML de ~300 MB que el navegador no soporta
poligonos = poligonos[
    poligonos["d_codigo"].isin(cp_con_score)
].copy()

# Conservar solo las métricas de CP con polígono, para que tooltips y escala coincidan
metricas = metricas[metricas["codigo_postal"].isin(poligonos["d_codigo"])]

#VALIDAR GEOMETRÍAS

def extraer_poligonos(geom):
    """Extrae componentes Polygon de geometrías simples o colecciones."""
    if geom is None or geom.is_empty:
        return []

    if isinstance(geom, Polygon):
        return [geom]

    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        resultado = []
        for parte in geom.geoms:
            resultado.extend(extraer_poligonos(parte))
        return resultado

    return []


def reparar_geometria(geom):
    if geom is None or geom.is_empty:
        return None

    try:
        reparada = shapely.make_valid(
            geom,
            method="structure",
            keep_collapsed=False
        )
    except Exception:
        # Alternativa para geometrías que GEOS no logra reparar
        try:
            reparada = geom.buffer(0)
        except Exception:
            return None

    partes = extraer_poligonos(reparada)

    if not partes:
        return None

    try:
        resultado = unary_union(partes)
        return resultado if not resultado.is_empty else None
    except Exception:
        return None


# Reparar individualmente, evitando que un solo registro interrumpa todo
poligonos["geometry"] = poligonos.geometry.apply(
    reparar_geometria
)

# Retirar únicamente las geometrías que no pudieron recuperarse
poligonos = poligonos[
    poligonos.geometry.notna()
    & ~poligonos.geometry.is_empty
    & poligonos.geometry.is_valid
].copy()

print("Polígonos recuperados:", len(poligonos))
print(
    "Geometrías inválidas restantes:",
    (~poligonos.geometry.is_valid).sum()
)
###################

def crear_tooltip(grupo):
    filas = []

    for _, row in grupo.iterrows():
        colonia = html.escape(str(row["colonia"]))

        score = (
            f'{row["qs_score"]:.3f}'
            if pd.notna(row["qs_score"]) else "N/D"
        )

        precio = (
            f'${row["precio_m2"]:,.0f}'
            if pd.notna(row["precio_m2"]) else "N/D"
        )

        filas.append(
            f"<tr>"
            f"<td>{colonia}</td>"
            f"<td>{score}</td>"
            f"<td>{precio}</td>"
            f"</tr>"
        )

    return (
        "<div style='max-height:300px; overflow-y:auto;'>"
        "<table style='border-collapse:collapse; font-size:12px;'>"
        "<thead><tr>"
        "<th style='padding:4px;'>Colonia</th>"
        "<th style='padding:4px;'>Score</th>"
        "<th style='padding:4px;'>Precio/m²</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(filas) +
        "</tbody></table></div>"
    )


# Una fila por CP con su contenido emergente
tooltips = (
    metricas.groupby("codigo_postal", sort=False)
    .apply(crear_tooltip, include_groups=False)
    .rename("tooltip_html")
    .reset_index()
)

# Métrica resumida para colorear cada CP
resumen = (
    metricas.groupby("codigo_postal", as_index=False)
    .agg(score_cp=("qs_score", "mean"))
)

# Una geometría por CP, sin métricas previas
cp_base = (
    poligonos[["d_codigo", "geometry"]]
    .dissolve(by="d_codigo", as_index=False)
    .to_crs(epsg=4326)
)
print("CP con score:", len(cp_con_score))
print("Polígonos postales resultantes:", len(cp_base))

# Evitar inconsistencias de tipo o formato
cp_base["d_codigo"] = (
    cp_base["d_codigo"].astype("string").str.strip().str.zfill(5)
)

resumen["codigo_postal"] = (
    resumen["codigo_postal"].astype("string").str.strip().str.zfill(5)
)

tooltips["codigo_postal"] = (
    tooltips["codigo_postal"].astype("string").str.strip().str.zfill(5)
)

# Unir el resumen de scores
cp_gdf = cp_base.merge(
    resumen,
    left_on="d_codigo",
    right_on="codigo_postal",
    how="left",
    validate="one_to_one"
)

# Eliminar la clave redundante del resumen
cp_gdf = cp_gdf.drop(columns=["codigo_postal"])

# Unir los tooltips directamente con la clave geográfica
cp_gdf = cp_gdf.merge(
    tooltips,
    left_on="d_codigo",
    right_on="codigo_postal",
    how="left",
    validate="one_to_one"
)

valores = cp_gdf["score_cp"].dropna()
vmin, vmax = valores.min(), valores.max()

if vmin == vmax:
    vmax = vmin + 1

colormap = cm.linear.YlOrRd_09.scale(vmin, vmax)
colormap.caption = "Score promedio por código postal"

m = folium.Map(
    location=[23.6, -102.5],
    zoom_start=5,
    tiles="CartoDB positron"
)

def estilo(feature):
    valor = feature["properties"]["score_cp"]

    if valor is None or pd.isna(valor):
        return {
            "fillColor": "#bdbdbd",
            "color": "#777777",
            "weight": 0.3,
            "fillOpacity": 0.5,
        }

    return {
        "fillColor": colormap(valor),
        "color": "#555555",
        "weight": 0.5,
        "fillOpacity": 0.75,
    }
tooltip = folium.GeoJsonTooltip(
    fields=["d_codigo", "tooltip_html"],
    aliases=["Código postal:", ""],
    labels=True,
    sticky=True,
    parse_html=True,
    style=(
        "background-color: white; color: #333333; "
        "font-family: Arial; font-size: 12px; padding: 8px;"
    ),
)

folium.GeoJson(
    cp_gdf,
    name="Códigos postales con score",
    style_function=estilo,
    tooltip=tooltip,
).add_to(m)

colormap.add_to(m)
folium.LayerControl().add_to(m)

m.fit_bounds([
    [cp_gdf.total_bounds[1], cp_gdf.total_bounds[0]],
    [cp_gdf.total_bounds[3], cp_gdf.total_bounds[2]],
])

m.save("mapa_scores_cp.html")