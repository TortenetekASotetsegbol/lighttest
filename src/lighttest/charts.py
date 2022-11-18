from enum import Enum

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
from pandas import DataFrame
from os import makedirs
from pathlib import Path
from functools import wraps


class Orientation(Enum):
    HORIZONTAL = "h"
    VERTICAL = "v"


class Palette(Enum):
    DARK = "dark",
    PASTEL = "pastel"


class Localisations(Enum):
    LOWER_LEFT = "lower left"
    LOWER_RIGHT = "lower right"
    UPPER_RIGHT = "upper right"
    UPPER_LEFT = "upper left"
    RIGHT = "right"
    CENTER = "center"
    CENTER_LEFT = "center left"
    CENTER_RIGHT = "center right"
    LOWER_CENTER = "lower center"
    UPPER_CENTER = "upper center"


def plot_config(generate_plot):
    @wraps(generate_plot)
    def plot(save_fig: bool = False, show_fig: bool = False, fig_directory: str = "", *args, **kwargs):
        if type(kwargs["data"]) == dict:
            if (len(kwargs["data"]) == 0 or sum(kwargs["data"].values()) == 0):
                return
        if type(kwargs["data"]) == DataFrame:
            if len(kwargs["data"]) == 0:
                return

        plt.title(kwargs["title"])
        plt.rc('legend', fontsize=20)

        generate_plot(*args, **kwargs)

        plt.tight_layout()

        if save_fig:
            plt.savefig(fig_directory,
                        bbox_inches="tight",
                        pad_inches=1)
        if show_fig:
            plt.show()

        plt.clf()
        plt.close()

    return plot


def generate_figure_from_array(data: DataFrame, x_axis_column: str, y_axis_column: str, y_label: str, x_label: str,
                               title: str,
                               size_height: float = 10, size_width: float = 15,
                               orientation: str = Orientation.HORIZONTAL.value,
                               grouping_column: str = None, palette=Palette.PASTEL.value, save_fig: bool = False,
                               show_fig: bool = False, fig_directory: Path = "") -> None:
    if len(data) == 0:
        return
    chart = sns.catplot(data=data, kind="bar", palette=palette, hue=grouping_column, x=x_axis_column, y=y_axis_column,
                        orient=orientation, legend_out=False, legend=Localisations.UPPER_RIGHT.value)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.margins(y=0.25, x=0.25)
    chart.fig.set_figheight(size_height)
    chart.fig.set_figwidth(size_width)
    plt.tight_layout()

    if save_fig:
        plt.savefig(fig_directory,
                    bbox_inches="tight",
                    pad_inches=1)
    if show_fig:
        plt.show()
    plt.clf()


@plot_config
def generate_pie_chart_from_simple_dict(title: str, data: dict, size_height: float = 10, size_width: float = 10):
    values: list[int] = [value for value in data.values()]
    labels: list[str] = [f'{key} ({value} element)' for key, value in data.items()]
    color_palette = sns.color_palette(Palette.PASTEL.value)
    plt.pie(x=values, colors=color_palette, autopct='%.0f%%')
    plt.legend(labels)


@plot_config
def generate_bar_chart_from_simple_dict(title: str, data: dict, size_height: float = 10, size_width: float = 10):
    values: list[int] = [value for value in data.values()]
    x_axis_elements: list[str] = [key for key, value in data.items()]

    plt.barh(y=x_axis_elements, width=values)


@plot_config
def generate_bar_chart_from_dataframe(y_label: str, x_label: str, title: str, data: DataFrame, key_collumn: str,
                                      value_collumn: str,
                                      size_height: float = 10, size_width: float = 10):
    data = data.to_dict("list")
    values: list[int] = list(data[value_collumn])
    x_axis_elements: list[str] = list(data[key_collumn])
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    plt.barh(y=x_axis_elements, width=values)
