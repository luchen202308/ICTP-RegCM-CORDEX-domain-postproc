#!/usr/bin/env python3

"""
Calculate annual regional means for the selected AR7 regions.

Inputs:
    GCM annual files in GCM_INPUT_DIR
    RegCM5 annual files in annual/RegCM5/<variable>/
    CRU annual file in annual/OBS/
    AR7 masks in MASK_DIR

Outputs:
    regional/GCM/
    regional/RegCM5/
    regional/OBS/

EAS-12 changes from Graziela's AFR-12 version:
  - mask_grid.txt is read from the script folder (no copy to BASE_DIR)
  - each mask is regridded once per grid and reused for every
    experiment and variable (same results, much faster)
  - CRU uses the same regional-mean routine as the models
"""

import shutil
import subprocess

from config import (
    BASE_DIR,
    GCM_INPUT_DIR,
    GCM_MODELS,
    GCM_REGIONAL_DIR,
    REGCM_ANNUAL_DIR,
    REGCM_REGIONAL_DIR,
    EXPERIMENTS,
    VARIABLES,
    PERIODS,
    REGCM_PERIODS,
    MASK_DIR,
    MASK_GRID,
    CRU_ANNUAL_DIR,
    CRU_REGIONAL_DIR,
    get_regions,
    create_output_directories,)

# Temporary folder for regridded masks (removed at the end).
TMP_DIR = BASE_DIR / "tmp_regional"

# ============================================================
# HELPERS
# ============================================================

def run_command(command, **kwargs):
    """Run a command and raise an error if it fails."""
    print("  Running:", " ".join(map(str, command)))
    subprocess.run(command, check=True, **kwargs)


def find_annual_file(model, experiment, variable, dataset):
    """Find the annual file for one model, experiment and variable."""

    if dataset == "GCM":
        search_dir = GCM_INPUT_DIR
        start_year, end_year = PERIODS[experiment]
    else:
        search_dir = REGCM_ANNUAL_DIR / variable
        start_year, end_year = REGCM_PERIODS[experiment]

    filename = (
        f"{variable}_{model}_{experiment}_year_"
        f"{start_year}-{end_year}.nc")

    path = search_dir / filename

    if not path.exists():
        print(f"  Missing input: {path}")
        return None

    return path


def fixed_mask_file(region):
    """AR7 mask with the correct geographic grid (made once per region)."""

    output = TMP_DIR / "masks" / "fixed" / f"{region}_mask.nc"

    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        run_command([
            "cdo", "-O",
            f"setgrid,{MASK_GRID}",
            str(MASK_DIR / f"{region}_mask.nc"),
            str(output),])

    return output


def remapped_mask_file(region, input_file, grid_key):
    """
    AR7 mask on the grid of input_file (made once per grid).
    Nearest-neighbour remapping preserves categorical mask values.
    """

    output = TMP_DIR / "masks" / grid_key / f"{region}_mask.nc"

    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        grid_file = output.parent / "target_grid.txt"

        if not grid_file.exists():
            with open(grid_file, "w") as handle:
                run_command(
                    ["cdo", "griddes", str(input_file)],
                    stdout=handle,)

        run_command([
            "cdo", "-O",
            f"remapnn,{grid_file}",
            str(fixed_mask_file(region)),
            str(output),])

    return output


def calculate_region(input_file, region, grid_key, output_file):
    """Apply the regional mask and calculate the spatial mean per year."""

    mask = remapped_mask_file(region, input_file, grid_key)

    run_command([
        "cdo", "-O",
        "fldmean",
        "-ifthen",
        str(mask),
        str(input_file),
        str(output_file),])

# ============================================================
# PROCESS DATASETS
# ============================================================

def process_dataset(dataset, models, output_dir):
    """Process every selected region for one dataset."""

    regions = get_regions()

    for model in models:

        # All RegCM5 runs share one grid; each GCM has its own.
        grid_key = "RegCM5" if dataset == "RegCM5" else f"GCM_{model}"

        for experiment in EXPERIMENTS:
            for variable in VARIABLES:

                input_file = find_annual_file(
                    model, experiment, variable, dataset)

                if input_file is None:
                    continue

                if dataset == "GCM":
                    start_year, end_year = PERIODS[experiment]
                else:
                    start_year, end_year = REGCM_PERIODS[experiment]

                for region in regions:

                    region_dir = output_dir / variable / region
                    region_dir.mkdir(parents=True, exist_ok=True)

                    output_file = region_dir / (
                        f"{variable}_{model}_{experiment}_"
                        f"{region}_year_{start_year}-{end_year}.nc")

                    if output_file.exists():
                        print(f"Already exists: {output_file}")
                        continue

                    print(
                        f"\n{dataset} | {model} | {experiment} | "
                        f"{variable} | {region}")

                    calculate_region(
                        input_file,
                        region,
                        grid_key,
                        output_file,)


def process_cru():
    """Calculate annual regional temperature means from CRU."""

    annual_file = (
        CRU_ANNUAL_DIR / "tas_CRU_year_1970-2024.nc")

    if not annual_file.is_file():
        raise FileNotFoundError(
            f"CRU annual file not found: {annual_file}")

    region_dir = CRU_REGIONAL_DIR / "tas"
    region_dir.mkdir(parents=True, exist_ok=True)

    for region in get_regions():

        output_file = region_dir / (
            f"tas_CRU_{region}_year_1970-2024.nc")

        if output_file.exists():
            print(f"Already exists: {output_file}")
            continue

        print(f"\nCRU | tas | {region}")

        calculate_region(
            annual_file,
            region,
            "CRU",
            output_file,)

    print(f"\nCRU regional outputs saved in: {CRU_REGIONAL_DIR}")

# ============================================================
# MAIN
# ============================================================

def main():
    create_output_directories()

    if not MASK_GRID.is_file():
        raise FileNotFoundError(
            f"Mask grid description not found: {MASK_GRID}")

    print("Selected AR7 regions:", ", ".join(get_regions()))

    # GCMs: annual files are already prepared.
    process_dataset(
        dataset="GCM",
        models=GCM_MODELS,
        output_dir=GCM_REGIONAL_DIR,)

    # RegCM5: annual files were generated from daily inputs.
    process_dataset(
        dataset="RegCM5",
        models=GCM_MODELS,
        output_dir=REGCM_REGIONAL_DIR,)

    process_cru()

    # Remove the regridded masks.
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print("\nRegional processing finished.")


if __name__ == "__main__":
    main()
