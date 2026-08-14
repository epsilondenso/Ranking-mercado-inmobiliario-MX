import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from config.config import paleta


color_letras = paleta["oscuro"]


def bar_plot(data: pd.DataFrame, criterion: str, title:str, barplot_args: dict):

    labels = [f"{data["colonia"].iloc[i]} ({data["municipio"].iloc[i]})"for i in range(data.shape[0])]
    plt.title(title)
    ax = sns.barplot(data = data, y = "colonia", x = criterion, orient = "y", **barplot_args)
    plt.xlabel(criterion)
    plt.ylabel("Colonia (municipio)")
    plt.yticks([])

    ax.bar_label(ax.containers[0],
    labels = labels,
    label_type = "center", color = color_letras)
    plt.show()

    return None