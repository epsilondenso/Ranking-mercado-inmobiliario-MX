import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from config.config import paleta


color_letras = paleta["oscuro"]

def bar_plot(
    data: pd.DataFrame,
    criterion: str,
    title: str,
    barplot_args: dict | None = None,
    ax=None,
):
    if barplot_args is None:
        barplot_args = {}

    if ax is None:
        _, ax = plt.subplots()

    labels = [
    f"{data['colonia'].iloc[i].replace('Fraccionamiento ', '')} "
    f"({data['municipio'].iloc[i]})"
    for i in range(data.shape[0])
]

    sns.barplot(
        data=data,
        y="colonia",
        x=criterion,
        orient="y",
        ax=ax,
        **barplot_args
    )

    ax.set_title(title)
    ax.set_xlabel(criterion)
    ax.set_ylabel("Colonia (municipio)")
    ax.set_yticks([])

    ax.bar_label(
        ax.containers[0],
        labels=labels,
        label_type="center",
        color=color_letras
    )

    return ax

def hist_plot(
    data: pd.DataFrame,
    column: str,
    title: str,
    histplot_args: dict | None = None,
    ax=None,
):
    if histplot_args is None:
        histplot_args = {}

    if ax is None:
        _, ax = plt.subplots()

    sns.histplot(
        data=data,
        x=column,
        ax=ax,
        **histplot_args
    )
    y_label = histplot_args["stat"] if "stat" in histplot_args.keys() else "stat"
    ax.set_title(title)
    ax.set_xlabel(column)
    ax.set_ylabel(y_label)

    return ax