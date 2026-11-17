#!/usr/bin/env python3

"""
Regional annual time series (GCMs, RegCM5, and CRU), one panel per AR7
region. EAS-12 version of Graziela's script: regions come from
regions_EAS-12.txt, and PLOT_YEARS and SHARED_Y_AXIS are set in config.py.
"""

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from matplotlib.lines import Line2D

from config import (
    DOMAIN,
    GCM_MODELS,
    GCM_REGIONAL_DIR,
    REGCM_REGIONAL_DIR,
    CRU_REGIONAL_DIR,
    PERIODS,
    REGCM_PERIODS,
    PLOT_YEARS,
    SHARED_Y_AXIS,
    TIMESERIES_FIGURE_DIR,
    get_regions,
    create_output_directories,
)

# ============================================================
# SETTINGS
# ============================================================

PLOT_VARIABLES = ["tas"]

#NROWS = 3
#NCOLS = 5

#FIGSIZE = (20, 11)

from math import ceil

REGIONS = get_regions()

NCOLS = min(5, len(REGIONS))
NROWS = ceil(len(REGIONS) / NCOLS)

PANEL_WIDTH = 4.0
PANEL_HEIGHT = 2.8

FIGSIZE = (
    PANEL_WIDTH * NCOLS,
    PANEL_HEIGHT * NROWS + 1.5,)

DPI = 300

# SHARED_Y_AXIS is set in config.py
SAVE_FIGURES = True
SHOW_FIGURES = False

GCM_LINESTYLE = "--"
REGCM_LINESTYLE = "-"
CRU_LINESTYLE = "-"

LINEWIDTH = 1.4
CRU_LINEWIDTH = 1.8

COLORS = {
    "EC-Earth3-Veg": "#0072B2",
    "MPI-ESM1-2-HR": "#009E73",
    "NorESM2-MM": "#D55E00",
}

VARIABLE_INFO = {
    "tas": {
        "label": "TAS",
        "units": "°C",
        "description": "near-surface air temperature",
    },
    "pr": {
        "label": "PR",
        "units": "mm/year",
        "description": "annual precipitation",},}

# ============================================================
# INPUT FILES
# ============================================================

def get_input_file(dataset, model, experiment, variable, region):
    if dataset == "GCM":
        base_dir = GCM_REGIONAL_DIR
        start, end = PERIODS[experiment]
    else:
        base_dir = REGCM_REGIONAL_DIR
        start, end = REGCM_PERIODS[experiment]

    return (
        base_dir / variable / region /
        f"{variable}_{model}_{experiment}_{region}_year_{start}-{end}.nc")

# ============================================================
# READ DATA
# ============================================================

def load_series(path, variable):
    with xr.open_dataset(path) as ds:
        if variable not in ds:
            raise KeyError(
                f"Variable '{variable}' not found in {path}. "
                f"Available variables: {list(ds.data_vars)}")

        if "time" not in ds:
            raise KeyError(f"No time coordinate found in {path}")

        values = (
            ds[variable]
            .squeeze(drop=True)
            .load()
            .values
            .ravel())

        years = ds.time.dt.year.values.astype(int)

    if len(years) != len(values):
        raise ValueError(
            f"Time/value length mismatch in {path}: "
            f"{len(years)} years and {len(values)} values")

    # Keep only the years shown on the x-axis
    if PLOT_YEARS is not None:
        keep = (years >= PLOT_YEARS[0]) & (years <= PLOT_YEARS[1])
        years, values = years[keep], values[keep]

    return years, values

def collect_data(variable):
    data = {}

    for region in REGIONS:

        # GCM and RegCM5 model data
        for dataset in ("GCM", "RegCM5"):
            for model in GCM_MODELS:
                for experiment in ("historical", "ssp370"):
                    path = get_input_file(
                        dataset,
                        model,
                        experiment,
                        variable,
                        region,)

                    if path.exists():
                        key = (region, dataset, model, experiment)
                        data[key] = load_series(path, variable)
                    else:
                        print(f"Missing: {path}")

        # CRU observations: temperature only
        if variable == "tas":
            path = (
                CRU_REGIONAL_DIR / "tas" /
                f"tas_CRU_{region}_year_1970-2024.nc")

            if path.exists():
                key = (region, "CRU", "CRU", "historical")
                data[key] = load_series(path, "tmp")
            else:
                print(f"Missing CRU file: {path}")

    return data

# ============================================================
# SHARED Y-AXIS LIMITS
# ============================================================

def calculate_shared_limits(series):
    finite_values = [
        values[np.isfinite(values)]
        for _, values in series
        if np.isfinite(values).any()]

    if not finite_values:
        return None, None

    all_values = np.concatenate(finite_values)

    low = all_values.min()
    high = all_values.max()

    pad = 0.05 * (high - low) if high > low else 1.0

    return low - pad, high + pad


# ============================================================
# PLOTTING
# ============================================================

def plot_variable(variable):
    data = collect_data(variable)

    if not data:
        print(f"No data available for {variable}.")
        return

    info = VARIABLE_INFO[variable]

    fig, axes = plt.subplots(
        NROWS,
        NCOLS,
        figsize=FIGSIZE,
        sharex=True,
        sharey=SHARED_Y_AXIS,
        squeeze=False,)

    axes = np.asarray(axes).flatten()

    for i, region in enumerate(REGIONS):
        ax = axes[i]

        # Plot GCM and RegCM5 series
        for dataset, linestyle in (
            ("GCM", GCM_LINESTYLE),
            ("RegCM5", REGCM_LINESTYLE),):
            for model in GCM_MODELS:
                color = COLORS[model]

                for experiment in ("historical", "ssp370"):
                    key = (region, dataset, model, experiment)

                    if key not in data:
                        continue

                    years, values = data[key]

                    ax.plot(
                        years,
                        values,
                        color=color,
                        linestyle=linestyle,
                        linewidth=LINEWIDTH,)

        # Plot CRU observations on top of model lines
        cru_key = (region, "CRU", "CRU", "historical")

        if cru_key in data:
            years, values = data[cru_key]

            ax.plot(
                years,
                values,
                color="black",
                linestyle=CRU_LINESTYLE,
                linewidth=CRU_LINEWIDTH,
                zorder=10,)

        # Historical / projection boundary
        ax.axvline(
            2015,
            color="black",
            linestyle=":",
            linewidth=0.8,)

        ax.set_title(
            region,
            loc="left",
            fontsize=10,
            fontweight="bold",)

        ax.grid(True, alpha=0.25, linewidth=0.5)
        ax.tick_params(axis="both", labelsize=8)

        if PLOT_YEARS is not None:
            ax.set_xlim(PLOT_YEARS[0] - 1, PLOT_YEARS[1] + 1)

        # With separate y-axes, every panel keeps its own tick labels
        if not SHARED_Y_AXIS:
            ax.tick_params(labelleft=True)

        row = i // NCOLS
        col = i % NCOLS

        if i + NCOLS >= len(REGIONS):
            # No panel below this one
            ax.set_xlabel("Year", fontsize=9)
            ax.tick_params(labelbottom=True)

        if col == 0:
            ax.set_ylabel(f"Temperature ({info['units']})", fontsize=9)

    # Hide unused panels if the number of regions is below 15
    for i in range(len(REGIONS), len(axes)):
        axes[i].set_visible(False)

    # Y limits, including CRU observations: shared or one per region
    for i, region in enumerate(REGIONS):
        if SHARED_Y_AXIS:
            series = data.values()
        else:
            series = [s for key, s in data.items() if key[0] == region]

        low, high = calculate_shared_limits(series)

        if low is not None:
            axes[i].set_ylim(low, high)

    # Figure title
    fig.suptitle(
        f"{DOMAIN}: regional annual mean {info['label']} - GCMs, RegCM5 and CRU",
        fontsize=14,
        fontweight="bold",
        y=0.98,)

    # Model colour legend
    model_handles = [
        Line2D(
            [0], [0],
            color=COLORS[model],
            linewidth=2,
            label=model,)
        for model in GCM_MODELS]

    # Dataset line-style legend (grey for model styles, so CRU stands out)
    dataset_handles = [
        Line2D(
            [0], [0],
            color="0.45",
            linewidth=1.8,
            linestyle=GCM_LINESTYLE,
            label="GCM",
        ),
        Line2D(
            [0], [0],
            color="0.45",
            linewidth=1.8,
            linestyle=REGCM_LINESTYLE,
            label="RegCM5",
        ),
        Line2D(
            [0], [0],
            color="black",
            linewidth=CRU_LINEWIDTH,
            linestyle=CRU_LINESTYLE,
            label="CRU observations",
        ),
    ]

    fig.legend(
        handles=model_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.055),
        ncol=3,
        frameon=False,
        fontsize=9,)

    fig.legend(
        handles=dataset_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.018),
        ncol=3,
        frameon=False,
        fontsize=9,)

    fig.tight_layout(rect=[0.025, 0.09, 0.99, 0.95])

    if SAVE_FIGURES:
        TIMESERIES_FIGURE_DIR.mkdir(parents=True, exist_ok=True)

        output = (
            TIMESERIES_FIGURE_DIR /
            f"regional_timeseries_{variable}_{DOMAIN}_regions.png")

        fig.savefig(
            output,
            dpi=DPI,
            bbox_inches="tight",)

        print(f"Saved: {output}")

    if SHOW_FIGURES:
        plt.show()

    plt.close(fig)

# ============================================================
# MAIN
# ============================================================

def main():
    create_output_directories()

    for variable in PLOT_VARIABLES:
        if variable not in VARIABLE_INFO:
            raise ValueError(f"Unknown variable: {variable}")

        plot_variable(variable)

if __name__ == "__main__":
    main()

