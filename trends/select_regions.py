#!/usr/bin/env python3

"""
Choose the AR7 regions that lie inside the EAS-12 domain.

For every <REGION>_mask.nc in MASK_DIR, measure how much of the region's
area falls inside the RegCM grid, print a table, and write the regions
with coverage >= REGION_MIN_COVERAGE to REGION_FILE (regions_EAS-12.txt).
The other scripts read their region list from that file.

It also checks that the GCM annual files in GCM_INPUT_DIR cover EAS-12.

Run once on the login node (takes about a minute):
    python3 select_regions.py               # writes regions_EAS-12.txt
    python3 select_regions.py --overwrite   # replace an existing list
"""

import argparse

import numpy as np
import xarray as xr

from config import (
    DOMAIN,
    REGCM_INPUT_DIR,
    GCM_INPUT_DIR,
    GCM_MODELS,
    PERIODS,
    MASK_DIR,
    mask_grid_lonlat,
    REGION_FILE,
    REGION_MIN_COVERAGE,
    REGION_BUFFER_POINTS,)

# Width of the EAS-12 relaxation zone (nspgx in the namelist). Only used
# for the extra "interior" column of the table.
RELAXATION_POINTS = 40

# ============================================================
# GRIDS
# ============================================================

def find_regcm_sample():
    """Any daily tas file of EAS-12 (all runs share one grid)."""

    for pattern in (
        "*/*/*/*/*/day/tas/*.nc",
        "*/*/*/*/*/day/tas/v*/*.nc",):
        files = sorted(REGCM_INPUT_DIR.glob(pattern))
        if files:
            return files[0]

    raise FileNotFoundError(
        f"No daily tas file found under {REGCM_INPUT_DIR}")


def neighbour_distance(lat, lon, axis):
    """Great-circle distance (radians) to the next point along one axis."""

    lat = np.deg2rad(lat)
    lon = np.deg2rad(lon)

    lat2 = np.roll(lat, -1, axis=axis)
    lon2 = np.roll(lon, -1, axis=axis)

    a = (np.sin((lat2 - lat) / 2) ** 2
         + np.cos(lat) * np.cos(lat2) * np.sin((lon2 - lon) / 2) ** 2)
    dist = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    # The last row/column has no next point: copy the one before it.
    index = [slice(None)] * dist.ndim
    index[axis] = -1
    previous = [slice(None)] * dist.ndim
    previous[axis] = -2
    dist[tuple(index)] = dist[tuple(previous)]

    return dist


def latlon(ds):
    """Latitude and longitude arrays, whatever they are called."""

    for lat_name, lon_name in (
        ("lat", "lon"),
        ("latitude", "longitude"),
        ("nav_lat", "nav_lon"),):
        if lat_name in ds.variables and lon_name in ds.variables:
            return ds[lat_name].values, ds[lon_name].values

    raise KeyError(f"No latitude/longitude found in {ds.encoding.get('source')}")


def read_regcm_grid(path):
    """2D lat, lon (0–360) and cell areas (unit sphere) of the RegCM grid."""

    with xr.open_dataset(path, decode_times=False) as ds:
        lat, lon = latlon(ds)

    if lat.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)

    area = (neighbour_distance(lat, lon, axis=0)
            * neighbour_distance(lat, lon, axis=1))

    return lat, lon % 360, area


def trim(array, points):
    """Drop `points` rows and columns along each edge."""
    return array[points:-points, points:-points] if points > 0 else array

# ============================================================
# MASKS
# ============================================================

def read_mask(path):
    """Mask values and, if the file has one, the region's full name."""

    with xr.open_dataset(path) as ds:
        if "mask" in ds.data_vars:
            name = "mask"
        else:
            name = next(
                var for var in ds.data_vars
                if var != "region" and ds[var].dtype.kind in "fiub")

        values = ds[name].squeeze(drop=True).values.astype(float)

        long_name = None
        for attrs in (ds.attrs, ds[name].attrs):
            for key in ("region_name", "name", "long_name", "title"):
                text = str(attrs.get(key, "")).strip()
                if text and "mask" not in text.lower():
                    long_name = text
                    break
            if long_name:
                break

    return values, long_name


def coverage(inside, mask_lat, mask_lon, regcm_lat, regcm_lon, regcm_area):
    """Share of the region's area that lies on the RegCM grid."""

    # Region area on the global mask grid
    weight = np.cos(np.deg2rad(mask_lat))[:, None]
    dlat = np.deg2rad(abs(mask_lat[1] - mask_lat[0]))
    dlon = np.deg2rad(abs(mask_lon[1] - mask_lon[0]))
    area_global = (inside * weight).sum() * dlat * dlon

    if area_global == 0:
        return 0.0

    # Nearest mask point for every RegCM point (as CDO remapnn does)
    i = np.rint((regcm_lat - mask_lat[0]) / (mask_lat[1] - mask_lat[0]))
    i = np.clip(i.astype(int), 0, len(mask_lat) - 1)
    j = np.rint(((regcm_lon - mask_lon[0]) % 360) / (mask_lon[1] - mask_lon[0]))
    j = j.astype(int) % len(mask_lon)

    area_regcm = (inside[i, j] * regcm_area).sum()

    return float(area_regcm / area_global)

# ============================================================
# GCM CHECK
# ============================================================

def check_gcm_files(regcm_lat, regcm_lon):
    """Print whether each GCM annual file covers the EAS-12 domain."""

    print("\nGCM annual files:")

    start, end = PERIODS["historical"]

    for model in GCM_MODELS:
        path = GCM_INPUT_DIR / f"tas_{model}_historical_year_{start}-{end}.nc"

        if not path.exists():
            print(f"  {model:15s} MISSING: {path}")
            continue

        with xr.open_dataset(path, decode_times=False) as ds:
            lat, lon = latlon(ds)
            lon = lon % 360

        lat_ok = lat.min() <= regcm_lat.min() and lat.max() >= regcm_lat.max()
        lon_ok = (lon.max() - lon.min() > 350
                  or (lon.min() <= regcm_lon.min()
                      and lon.max() >= regcm_lon.max()))

        status = "OK" if (lat_ok and lon_ok) else "does NOT cover EAS-12"

        print(
            f"  {model:15s} lon {lon.min():6.1f} to {lon.max():6.1f}, "
            f"lat {lat.min():6.1f} to {lat.max():6.1f}  -> {status}")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=f"replace an existing {REGION_FILE.name}")
    args = parser.parse_args()

    sample = find_regcm_sample()
    regcm_lat, regcm_lon, regcm_area = read_regcm_grid(sample)

    print(f"RegCM grid from: {sample}")
    print(
        f"  {regcm_lat.shape[0]} x {regcm_lat.shape[1]} points, "
        f"lon {regcm_lon.min():.1f} to {regcm_lon.max():.1f} (0–360), "
        f"lat {regcm_lat.min():.1f} to {regcm_lat.max():.1f}")

    # Grid used for the selection (full domain unless a buffer is set)
    sel_lat = trim(regcm_lat, REGION_BUFFER_POINTS)
    sel_lon = trim(regcm_lon, REGION_BUFFER_POINTS)
    sel_area = trim(regcm_area, REGION_BUFFER_POINTS)

    # Interior only, for information
    int_lat = trim(regcm_lat, RELAXATION_POINTS)
    int_lon = trim(regcm_lon, RELAXATION_POINTS)
    int_area = trim(regcm_area, RELAXATION_POINTS)

    mask_lon, mask_lat = mask_grid_lonlat()

    mask_files = sorted(MASK_DIR.glob("*_mask.nc"))

    if not mask_files:
        raise FileNotFoundError(f"No *_mask.nc files in {MASK_DIR}")

    rows = []

    for path in mask_files:
        code = path.name[:-len("_mask.nc")]
        values, long_name = read_mask(path)

        if values.shape != (len(mask_lat), len(mask_lon)):
            print(f"  Skipping {code}: shape {values.shape} does not match mask_grid.txt")
            continue

        inside = np.isfinite(values) & (values > 0)

        full = coverage(inside, mask_lat, mask_lon, sel_lat, sel_lon, sel_area)

        if full < 0.01:
            continue

        interior = coverage(inside, mask_lat, mask_lon, int_lat, int_lon, int_area)
        rows.append((code, full, interior, long_name or code))

    rows.sort(key=lambda row: -row[1])
    selected = [row for row in rows if row[1] >= REGION_MIN_COVERAGE]

    label = (f"buffer {REGION_BUFFER_POINTS}" if REGION_BUFFER_POINTS
             else "full domain")

    print(
        f"\nAR7 regions touching {DOMAIN} "
        f"(share of region area inside the domain):")
    print(f"  {'region':8s} {label:>12s} {'w/o ' + str(RELAXATION_POINTS) + '-pt buffer':>18s}  keep  name")

    for code, full, interior, name in rows:
        keep = "yes" if full >= REGION_MIN_COVERAGE else ""
        print(f"  {code:8s} {full:12.0%} {interior:18.0%}  {keep:4s}  {name}")

    print(
        f"\n{len(selected)} region(s) with coverage >= "
        f"{REGION_MIN_COVERAGE:.0%}: {', '.join(row[0] for row in selected)}")

    check_gcm_files(regcm_lat, regcm_lon)

    # Write the region list
    if REGION_FILE.exists() and not args.overwrite:
        print(
            f"\n{REGION_FILE.name} already exists, not changed. "
            f"Use --overwrite to replace it.")
        return

    lines = [
        f"# AR7 regions used for {DOMAIN} (written by select_regions.py)",
        f"# Kept: coverage >= {REGION_MIN_COVERAGE:.0%} ({label}).",
        "# One region per line: CODE  Full name. Edit names or delete lines freely.",
    ]
    lines += [f"{code:8s} {name}" for code, _, _, name in selected]

    REGION_FILE.write_text("\n".join(lines) + "\n")
    print(f"\nWritten: {REGION_FILE}")

    if any(code == name for code, _, _, name in selected):
        print("  Some regions have no full name in their mask file:")
        print("  add names in that file if you want them on the map legend.")


if __name__ == "__main__":
    main()
