#!/usr/bin/env python3

"""
Regional annual time series (GCMs, RegCM5, and CRU) with a map of the
AR7 regions. EAS-12 version of Graziela's script:
  - regions and names come from regions_EAS-12.txt (select_regions.py)
  - map uses 0–360 longitudes, since EAS-12 crosses 180°E
  - each panel can have its own y-axis (SHARED_Y_AXIS in config.py)
  - optional year range on the x-axis (PLOT_YEARS in config.py)
"""

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from math import ceil
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

from config import (
    DOMAIN,
    GCM_MODELS,
    GCM_REGIONAL_DIR,
    REGCM_REGIONAL_DIR,
    CRU_REGIONAL_DIR,
    REGION_NAMES,
    PERIODS,
    REGCM_PERIODS,
    MASK_DIR,
    PLOT_YEARS,
    SHARED_Y_AXIS,
    MAP_LON_0_360,
    TIMESERIES_FIGURE_DIR,
    get_regions,
    mask_grid_lonlat,
    create_output_directories,
)

# ============================================================
# SETTINGS
# ============================================================

PLOT_VARIABLES = ["tas"]  # Change to ["tas", "pr"] later

PANEL_WIDTH = 4.0
PANEL_HEIGHT = 2.8

COLORS = {
    "EC-Earth3-Veg": "#0072B2",
    "MPI-ESM1-2-HR": "#009E73",
    "NorESM2-MM": "#D55E00",}

GCM_STYLE = "--"
REGCM_STYLE = "-"
CRU_STYLE = "-"
LINEWIDTH = 1.25
CRU_LINEWIDTH = 1.8

SIDEBAR_HEIGHTS = [0.85, 1.0]

MAP_DOWNSAMPLE = 3
MAP_MARGIN = 3

VARIABLES = {
    "tas": ("TAS", "Temperature (°C)"),
    "pr": ("PR", "Annual precipitation (mm/year)"),}

# ============================================================
# INPUT FILES AND DATA
# ============================================================

def input_file(dataset, model, experiment, variable, region):
    if dataset == "GCM":
        base = GCM_REGIONAL_DIR
        start, end = PERIODS[experiment]
    else:
        base = REGCM_REGIONAL_DIR
        start, end = REGCM_PERIODS[experiment]

    return base / variable / region / f"{variable}_{model}_{experiment}_{region}_year_{start}-{end}.nc"

def read_series(path, variable):
    with xr.open_dataset(path) as ds:
        values = ds[variable].squeeze(drop=True).load().values.ravel()
        years = ds.time.dt.year.values.astype(int)

    # Keep only the years shown on the x-axis
    if PLOT_YEARS is not None:
        keep = (years >= PLOT_YEARS[0]) & (years <= PLOT_YEARS[1])
        years, values = years[keep], values[keep]

    return years, values

def load_data(variable, regions):
    data = {}

    for region in regions:
        # Load GCM and RegCM5 model data
        for dataset in ("GCM", "RegCM5"):
            for model in GCM_MODELS:
                for experiment in ("historical", "ssp370"):
                    path = input_file(dataset, model, experiment, variable, region)

                    if path.exists():
                        data[(region, dataset, model, experiment)] = read_series(path, variable)
                    else:
                        print(f"Missing: {path}")

        # Load CRU observations for temperature only
        if variable == "tas":
            path = CRU_REGIONAL_DIR / "tas" / f"tas_CRU_{region}_year_1970-2024.nc"

            if path.exists():
                data[(region, "CRU", "CRU", "historical")] = read_series(path, "tmp")
            else:
                print(f"Missing CRU file: {path}")

    return data

def value_limits(series):
    """Padded min/max of all finite values in a list of (years, values)."""

    finite = [values[np.isfinite(values)] for _, values in series if np.isfinite(values).any()]

    if not finite:
        return None

    all_values = np.concatenate(finite)
    low, high = all_values.min(), all_values.max()
    pad = 0.05 * (high - low) if high > low else 1

    return low - pad, high + pad

# ============================================================
# MAP
# ============================================================

def draw_map(ax, regions):
    bounds = []

    # Geographic coordinates of the masks (same grid CDO uses)
    grid_lon, grid_lat = mask_grid_lonlat()

    order = np.arange(len(grid_lon))
    if MAP_LON_0_360:
        grid_lon = grid_lon % 360
        order = np.argsort(grid_lon)
        grid_lon = grid_lon[order]

    for region in regions:
        path = MASK_DIR / f"{region}_mask.nc"

        if not path.exists():
            print(f"Missing mask: {path}")
            continue

        with xr.open_dataset(path) as ds:
            mask_name = "mask" if "mask" in ds.data_vars else next(name for name in ds.data_vars if name != "region")
            mask = ds[mask_name].squeeze(drop=True).values

        mask = mask[:, order]

        step = MAP_DOWNSAMPLE
        mask = mask[::step, ::step]
        lon = grid_lon[::step]
        lat = grid_lat[::step]

        inside = np.isfinite(mask) & (mask > 0)

        if not inside.any():
            continue

        ax.contour(lon, lat, inside.astype(float), levels=[0.5], colors="black", linewidths=0.6)

        lon2d, lat2d = np.meshgrid(lon, lat)
        x = float(np.median(lon2d[inside]))
        y = float(np.median(lat2d[inside]))

        ax.text(x, y, region, ha="center", va="center", fontsize=7, fontweight="bold")

        bounds.append((
            float(lon[inside.any(axis=0)].min()),
            float(lon[inside.any(axis=0)].max()),
            float(lat[inside.any(axis=1)].min()),
            float(lat[inside.any(axis=1)].max()),
        ))

    if bounds:
        ax.set_xlim(min(b[0] for b in bounds) - MAP_MARGIN, max(b[1] for b in bounds) + MAP_MARGIN)
        ax.set_ylim(min(b[2] for b in bounds) - MAP_MARGIN, max(b[3] for b in bounds) + MAP_MARGIN)

    ax.set_aspect("equal")
    ax.set_title(f"AR7 regions ({len(regions)})", fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_color("0.7")
        spine.set_linewidth(0.6)

def draw_region_names(ax, regions):
    ax.axis("off")

    for i, region in enumerate(regions):
        y = 1 - i / len(regions)
        ax.text(0.02, y, region, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
        ax.text(0.25, y, REGION_NAMES.get(region, region), transform=ax.transAxes, fontsize=8, va="top")

# ============================================================
# PLOTTING
# ============================================================

def plot_variable(variable):
    regions = get_regions()
    data = load_data(variable, regions)

    if not data:
        print(f"No data available for {variable}.")
        return

    ncols = min(5, len(regions))
    nrows = ceil(len(regions) / ncols)

    if nrows == 1:
        figsize = (PANEL_WIDTH * ncols, 7.5)
    else:
        figsize = (PANEL_WIDTH * ncols + 5.5, PANEL_HEIGHT * nrows + 2.5)

    # Panels need more room when each has its own y tick labels
    wspace = 0.08 if SHARED_Y_AXIS else 0.22

    fig = plt.figure(figsize=figsize)

    if nrows == 1:
        # One row: plots on top, map and region names below
        outer = GridSpec(2, 1, figure=fig, height_ratios=[3.2, 1.2], hspace=0.30, left=0.055, right=0.985, top=0.90, bottom=0.20)
        panels = GridSpecFromSubplotSpec(nrows, ncols, subplot_spec=outer[0], hspace=0.12, wspace=wspace)
        sidebar = GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[1], width_ratios=[1.1, 1.0], wspace=0.12)
        map_ax = fig.add_subplot(sidebar[0])
        names_ax = fig.add_subplot(sidebar[1])
    else:
        # Multiple rows: plots on the left, map and names on the right
        # Keep about 1 inch above the panels for the title
        outer = GridSpec(1, 2, figure=fig, width_ratios=[5.2, 1.1], wspace=0.055, left=0.055, right=0.985, top=1 - 1.0 / figsize[1], bottom=0.16)
        panels = GridSpecFromSubplotSpec(nrows, ncols, subplot_spec=outer[0], hspace=0.12 if SHARED_Y_AXIS else 0.18, wspace=wspace)
        sidebar = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[1], height_ratios=SIDEBAR_HEIGHTS, hspace=0.08)
        map_ax = fig.add_subplot(sidebar[0])
        names_ax = fig.add_subplot(sidebar[1])

    axes = []

    for i, region in enumerate(regions):
        ax = fig.add_subplot(panels[i // ncols, i % ncols])
        axes.append(ax)

        # Plot GCM and RegCM5 data
        for dataset, style in (("GCM", GCM_STYLE), ("RegCM5", REGCM_STYLE)):
            for model in GCM_MODELS:
                color = COLORS[model]

                for experiment in ("historical", "ssp370"):
                    key = (region, dataset, model, experiment)

                    if key in data:
                        years, values = data[key]
                        ax.plot(years, values, color=color, linestyle=style, linewidth=LINEWIDTH)

        # Plot CRU observations on top of model lines
        cru_key = (region, "CRU", "CRU", "historical")

        if cru_key in data:
            years, values = data[cru_key]
            ax.plot(years, values, color="black", linestyle=CRU_STYLE, linewidth=CRU_LINEWIDTH, zorder=10)

        ax.axvline(2015, color="black", linestyle=":", linewidth=0.7)
        ax.set_title(region, loc="left", fontsize=9, fontweight="bold")
        ax.grid(True, alpha=0.22, linewidth=0.5)
        ax.tick_params(labelsize=7)

        if PLOT_YEARS is not None:
            ax.set_xlim(PLOT_YEARS[0] - 1, PLOT_YEARS[1] + 1)

        if i + ncols < len(regions):
            # Another panel sits below this one
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Year", fontsize=9)

        if SHARED_Y_AXIS and i % ncols != 0:
            ax.tick_params(labelleft=False)

    # Y-axis limits: one range for all regions, or one per region
    if SHARED_Y_AXIS:
        limits = value_limits(data.values())
        if limits:
            for ax in axes:
                ax.set_ylim(*limits)
    else:
        for ax, region in zip(axes, regions):
            limits = value_limits([series for key, series in data.items() if key[0] == region])
            if limits:
                ax.set_ylim(*limits)

    # Same x-axis for all panels
    if PLOT_YEARS is None:
        x_low = min(ax.get_xlim()[0] for ax in axes)
        x_high = max(ax.get_xlim()[1] for ax in axes)
        for ax in axes:
            ax.set_xlim(x_low, x_high)

    label, ylabel = VARIABLES[variable]
    fig.supylabel(ylabel, fontsize=10, x=0.018)
    fig.suptitle(f"{DOMAIN}: regional annual mean {label} - GCMs, RegCM5 and CRU", fontsize=14, fontweight="bold", y=1 - 0.3 / figsize[1])

    draw_map(map_ax, regions)
    draw_region_names(names_ax, regions)

    # Model colour legend
    model_handles = [Line2D([0], [0], color=COLORS[model], lw=2, label=model) for model in GCM_MODELS]

    # Dataset line-style legend (grey for model styles, so CRU stands out)
    dataset_handles = [
        Line2D([0], [0], color="0.45", lw=1.8, linestyle=GCM_STYLE, label="GCM"),
        Line2D([0], [0], color="0.45", lw=1.8, linestyle=REGCM_STYLE, label="RegCM5"),
        Line2D([0], [0], color="black", lw=CRU_LINEWIDTH, linestyle=CRU_STYLE, label="CRU observations"),
    ]

    if nrows == 1:
        model_y = 0.105
        dataset_y = 0.045
        legend_x = 0.5
    else:
        model_y = 0.090
        dataset_y = 0.060
        legend_x = 0.39

    fig.legend(handles=model_handles, loc="lower center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(legend_x, model_y))
    fig.legend(handles=dataset_handles, loc="lower center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(legend_x, dataset_y))

    TIMESERIES_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = TIMESERIES_FIGURE_DIR / f"regional_timeseries_{variable}_{DOMAIN}_{len(regions)}regions_with_map.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved: {output}")

    plt.close(fig)


# ============================================================
# MAIN
# ============================================================

def main():
    create_output_directories()

    for variable in PLOT_VARIABLES:
        if variable not in VARIABLES:
            raise ValueError(f"Unknown variable: {variable}")

        plot_variable(variable)


if __name__ == "__main__":
    main()
