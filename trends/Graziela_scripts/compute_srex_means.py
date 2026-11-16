#!/usr/bin/env python3

"""
Calculate annual regional means for the selected AR7 regions.

Inputs:
    GCM annual files in GCM_INPUT_DIR
    RegCM5 annual files in annual/RegCM5/<variable>/
    AR7 masks in MASK_DIR

Outputs:
    regional/GCM/
    regional/RegCM5/
"""

import subprocess
from pathlib import Path

from config import (
    BASE_DIR,
    GCM_INPUT_DIR,
    GCM_MODELS,
    GCM_REGIONAL_DIR,
    REGCM_NAME,
    REGCM_ANNUAL_DIR,
    REGCM_REGIONAL_DIR,
    EXPERIMENTS,
    VARIABLES,
    PERIODS,
    REGCM_PERIODS,
    MASK_DIR,
    CRU_ANNUAL_DIR,
    CRU_REGIONAL_DIR,
    get_regions,
    create_output_directories,)

# Grid description for the original AR7 masks.
# This allows CDO to recognize their generic grids as geographic grids.
MASK_GRID = BASE_DIR / "mask_grid.txt"

# ============================================================
# HELPERS
# ============================================================

def run_command(command):
    """Run a command and raise an error if it fails."""
    print("  Running:", " ".join(map(str, command)))
    subprocess.run(command, check=True)

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

def get_grid_description(input_file, output_file):
    """Write a CDO grid description for the input model grid."""

    with open(output_file, "w") as handle:
        subprocess.run(
            ["cdo", "griddes", str(input_file)],
            stdout=handle,
            check=True,)

def calculate_region(input_file, mask_file, output_file, work_dir):
    """
    Correct the AR7 mask grid, remap the mask to the model grid,
    apply the mask, and calculate the regional mean time series.
    """

    work_dir.mkdir(parents=True, exist_ok=True)

    grid_file = work_dir / "target_grid.txt"
    fixed_mask = work_dir / "fixed_mask.nc"
    remapped_mask = work_dir / "remapped_mask.nc"
    selected_data = work_dir / "selected_region.nc"

    # Describe the target model grid.
    get_grid_description(input_file, grid_file)

    # Assign the correct geographic grid to the original AR7 mask.
    run_command([
        "cdo", "-O",
        f"setgrid,{MASK_GRID}",
        str(mask_file),
        str(fixed_mask),])

    # Remap the corrected mask to the model grid.
    # Nearest-neighbour remapping preserves categorical mask values.
    run_command([
        "cdo", "-O",
        f"remapnn,{grid_file}",
        str(fixed_mask),
        str(remapped_mask),])

    # Apply the regional mask to the annual model data.
    run_command([
        "cdo", "-O",
        "ifthen",
        str(remapped_mask),
        str(input_file),
        str(selected_data),])

    # Calculate the spatial mean for every year.
    run_command([
        "cdo", "-O",
        "fldmean",
        str(selected_data),
        str(output_file),])

    # Remove temporary files after successful processing.
    fixed_mask.unlink(missing_ok=True)
    remapped_mask.unlink(missing_ok=True)
    selected_data.unlink(missing_ok=True)
    grid_file.unlink(missing_ok=True)

# ============================================================
# PROCESS DATASETS
# ============================================================

def process_dataset(dataset, models, output_dir):
    """Process every selected region for one dataset."""

    regions = get_regions()

    for model in models:
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

                    mask_file = MASK_DIR / f"{region}_mask.nc"

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

                    work_dir = (
                        BASE_DIR / "tmp_regional"
                        / dataset / model / experiment
                        / variable / region)

                    calculate_region(
                        input_file,
                        mask_file,
                        output_file,
                        work_dir,)

                    # Remove the temporary directory if it is empty.
                    work_dir.rmdir()

def process_cru():
    """Calculate annual regional temperature means from CRU."""

    annual_file = (
        CRU_ANNUAL_DIR / "tas_CRU_year_1970-2024.nc")

    if not annual_file.is_file():
        raise FileNotFoundError(
            f"CRU annual file not found: {annual_file}")

    regions = get_regions()
    work_root = BASE_DIR / "tmp_regional" / "CRU"
    work_root.mkdir(parents=True, exist_ok=True)

    # Describe the CRU target grid.
    cru_grid = work_root / "cru_grid.txt"
    get_grid_description(annual_file, cru_grid)

    # Correct the original AR7 mask grid once per region.
    for region in regions:
        mask_file = MASK_DIR / f"{region}_mask.nc"

        region_dir = CRU_REGIONAL_DIR / "tas"
        region_dir.mkdir(parents=True, exist_ok=True)

        output_file = region_dir / (
            f"tas_CRU_{region}_year_1970-2024.nc")

        if output_file.exists():
            print(f"Already exists: {output_file}")
            continue

        print(f"\nCRU | tas | {region}")

        region_work = work_root / region
        region_work.mkdir(parents=True, exist_ok=True)

        fixed_mask = region_work / "fixed_mask.nc"
        remapped_mask = region_work / "remapped_mask.nc"
        selected_data = region_work / "selected_region.nc"

        try:
            run_command([
                "cdo", "-O",
                f"setgrid,{MASK_GRID}",
                str(mask_file),
                str(fixed_mask),
            ])

            # Nearest-neighbour remapping to the 0.5-degree CRU grid.
            run_command([
                "cdo", "-O",
                f"remapnn,{cru_grid}",
                str(fixed_mask),
                str(remapped_mask),
            ])

            run_command([
                "cdo", "-O",
                "ifthen",
                str(remapped_mask),
                str(annual_file),
                str(selected_data),
            ])

            run_command([
                "cdo", "-O",
                "fldmean",
                str(selected_data),
                str(output_file),
            ])

        finally:
            for temporary_file in (
                fixed_mask,
                remapped_mask,
                selected_data,):
                temporary_file.unlink(missing_ok=True)

            if region_work.exists():
                region_work.rmdir()

    # Remove the temporary grid description.
    cru_grid.unlink(missing_ok=True)
    work_root.rmdir()

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

    print("\nRegional processing finished.")

    process_cru()

if __name__ == "__main__":
    main()

