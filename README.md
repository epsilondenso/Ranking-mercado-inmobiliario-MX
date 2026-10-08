# Ranking de colonias del mercado inmobiliario en México

Este proyecto procesa anuncios de inmuebles en venta y compara colonias dentro de cada estado. Resume los anuncios por municipio y colonia, calcula indicadores de precio, antigüedad y variabilidad, y genera dos puntajes para ordenar las colonias. Incluye datos crudos por estado, resultados procesados y un notebook para ejecutar el análisis y visualizar los principales resultados.

## Qué hace

Para cada archivo `data/raw/properties_<Estado>.csv`, el pipeline:

1. Conserva las columnas necesarias, elimina filas duplicadas y descarta registros sin colonia, precio o superficie construida.
2. Convierte los precios en USD a MXN usando el tipo de cambio configurado y estandariza los nombres de columnas.
3. Calcula el precio por metro cuadrado (`precio_m2`), elimina valores atípicos con el criterio de rango intercuartílico (IQR) y calcula la edad del anuncio en días.
4. Agrupa los registros por municipio y colonia. Para cada grupo calcula el número de anuncios, mediana y promedio del precio por m², desviación estándar, coeficiente de variación y edad promedio.
5. Descarta grupos con pocos anuncios y normaliza los indicadores entre 0 y 1 dentro del estado analizado.
6. Calcula `pavc_score` y `qs_score`, y guarda los datos limpios, agrupados y puntuados.

El puntaje PAVC combina mediana de precio por m² (50 %), antigüedad promedio (25 %) y coeficiente de variación del precio (25 %). El puntaje QS combina calidad (75 %: precio 75 % y antigüedad 25 %) y tamaño del mercado (25 %: logaritmo de uno más el número de anuncios). En los indicadores de antigüedad y variabilidad, valores menores reciben una puntuación normalizada mayor.

## Cómo funciona

El flujo principal está en `src/pipeline.py`; las transformaciones se reparten entre `src/preprocessing.py`, `src/clean.py` y `src/score.py`. Las rutas de entrada y salida se definen en `config/paths.py`, y los parámetros del análisis, pesos y valores de referencia están en `config/config.py`.

Los resultados se escriben en:

- `data/clean/clean_<Estado>.csv`: registros válidos con precio por m² y edad del anuncio.
- `data/grouped/grouped_<Estado>.csv`: métricas agregadas por municipio y colonia.
- `data/scored/scored_<Estado>.csv`: métricas normalizadas y puntajes.

El notebook `notebooks/test.ipynb` aplica el pipeline a los archivos de `data/raw/`, obtiene los primeros lugares por puntaje o por mediana de precio, y muestra gráficas de barras e histogramas.

## Requisitos y ejecución

Se requiere Python y las dependencias listadas en `requirements.txt` (Pandas, NumPy, Matplotlib, Seaborn y scikit-learn). Desde la raíz del repositorio, instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

Para procesar un estado directamente desde Python:

```python
from src.pipeline import full_treatment, get_top

resultado = full_treatment("data/raw/properties_Sonora.csv")
top_colonias = get_top(resultado, top=10, criterion="pavc_score")
print(top_colonias[["municipio", "colonia", "pavc_score"]])
```

`full_treatment` guarda automáticamente los tres CSV de salida. También puede ejecutarse `notebooks/test.ipynb` en Jupyter Notebook o JupyterLab para procesar los estados disponibles y ver las gráficas. No hay actualmente un comando de consola dedicado.

## Alcances y limitaciones

- El análisis se basa en los anuncios presentes en los CSV y en los campos de precio y superficie construida.
- El ranking compara colonias dentro del estado procesado: la normalización min-max se calcula para cada archivo por separado. Los puntajes de distintos estados no son directamente comparables.
- El filtro de anuncios usa como umbral el menor valor entre `min_ads` (10 por defecto) y la mediana de anuncios por grupo. Por ello, el mínimo efectivo puede ser inferior a 10.
- El tipo de cambio (`tipo_cambio`) y la fecha de referencia (`fecha_scrap`) son constantes en `config/config.py`; hay que actualizarlos para reflejar otra fecha o conversión.
- Aunque `filter_date` recibe un año mínimo, actualmente no aplica el filtro al DataFrame que devuelve. Por tanto, el procesamiento no excluye efectivamente anuncios por año de publicación.
- El cálculo de precio por m² usa división entera y requiere una superficie construida válida y distinta de cero. La calidad y cobertura de los datos de entrada afectan los resultados.
- Los pesos de los puntajes y el tratamiento de atípicos son decisiones configurables.

## Estructura del proyecto

```text
config/       Rutas y parámetros del análisis
data/raw/     Anuncios originales por estado
data/clean/   Registros limpios generados
data/grouped/ Métricas agregadas por colonia generadas
data/scored/  Métricas normalizadas y puntajes generados
notebooks/    Ejecución por estados y visualización
src/          Preprocesamiento, limpieza, puntuación y gráficas
```
