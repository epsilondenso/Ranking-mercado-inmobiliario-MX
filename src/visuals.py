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
    #ax.set_yticks(range(1, data.shape[0]+1, 1))
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(range(1, len(labels)+1, 1))

    for bar, label in zip(ax.containers[0], labels):
        if bar is not None:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + bar.get_height() / 2,
                label,
                ha="center",
                va="center",
                color=color_letras,
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