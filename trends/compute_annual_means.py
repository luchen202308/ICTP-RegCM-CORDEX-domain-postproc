#!/usr/bin/env python3

"""
Compute annual RegCM5 fields from daily CORDEX-CMIP6 files.
tas: annual mean temperature in degrees Celsius
pr:  annual precipitation accumulation in mm/year

Output:
    annual/RegCM5/<variable>/<variable>_<model>_<experiment>_year_<start>-<end>.nc

EAS-12 changes from Graziela's AFR-12 version:
  - finds files with or without a v<YYYYMMDD> version folder (latest wins)
  - opens files without comparing lat/lon between files (faster, and safe
    when the 180°E longitude fix was applied to only some files)
  - writes a file only when every year of the period is complete
"""

import subprocess

import xarray as xr

from config import (
    GCM_MODELS,
    REGCM_INPUT_DIR,
    REGCM_VERSION,
    REGCM_REALIZATION,
    REGCM_VERSION_TAG,
    EXPERIMENTS,
    REGCM_PERIODS,
    MIN_DAYS_PER_YEAR,
    VARIABLES,
    REGCM_ANNUAL_DIR,
    CRU_INPUT_FILE,
    CRU_ANNUAL_DIR,
    create_output_directories,)

# ============================================================
# PROCESSING
# ============================================================

def run_command(command):
    """Run a command and stop if it fails."""
    print("  Running:", " ".join(map(str, command)))
    subprocess.run(command, check=True)


def find_daily_files(model, experiment, variable):
    """Find daily RegCM5 files for one model, experiment and variable."""

    input_dir = (
        REGCM_INPUT_DIR
        / model
        / experiment
        / REGCM_REALIZATION
        / REGCM_VERSION
        / REGCM_VERSION_TAG
        / "day"
        / variable)

    # Use the latest v<YYYYMMDD> folder if there is one, else the
    # variable folder itself.
    version_dirs = sorted(
        path for path in input_dir.glob("v*") if path.is_dir())

    if version_dirs:
        input_dir = version_dirs[-1]

    files = sorted(input_dir.glob("*.nc"))

    if not files:
        print(f"  WARNING: No files found in {input_dir}")

    return files


def missing_years(da, start_year, end_year):
    """Return the years with fewer than MIN_DAYS_PER_YEAR daily values."""

    counts = da["time"].dt.year.to_series().value_counts()

    return [
        year
        for year in range(start_year, end_year + 1)
        if counts.get(year, 0) < MIN_DAYS_PER_YEAR]


def process_annual_file(model, experiment, variable, start_year, end_year):
    """Calculate annual values from daily RegCM5 data."""

    output_dir = REGCM_ANNUAL_DIR / variable
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / (
        f"{variable}_{model}_{experiment}_year_"
        f"{start_year}-{end_year}.nc")

    if output_file.exists():
        print(f"  Already exists: {output_file.name}")
        return

    files = find_daily_files(model, experiment, variable)

    if not files:
        return

    print(f"  Opening {len(files)} files for {variable}...")

    with xr.open_mfdataset(
        files,
        combine="by_coords",
        data_vars="minimal",
        coords="minimal",
        compat="override",
        parallel=False,) as ds:

        if variable not in ds:
            raise KeyError(
                f"Variable '{variable}' not found in {files[0].name}")

        da = ds[variable]

        # Restrict to the configured period.
        da = da.sel(
            time=slice(
                f"{start_year}-01-01",
                f"{end_year}-12-31",))

        if da.sizes.get("time", 0) == 0:
            print(f"  WARNING: No data for {start_year}-{end_year}")
            return

        # Skip runs that are not finished yet (no partial annual files).
        incomplete = missing_years(da, start_year, end_year)

        if incomplete:
            print(
                f"  SKIPPED: {len(incomplete)} incomplete year(s): "
                f"{incomplete[:10]}{' ...' if len(incomplete) > 10 else ''}")
            return

        if variable == "tas":
            # Convert Kelvin to degrees Celsius.
            annual = (da - 273.15).resample(time="YS").mean(
                dim="time",
                skipna=True,)
            annual.attrs["units"] = "degC"
            annual.attrs["long_name"] = "Annual mean near-surface air temperature"

        elif variable == "pr":
            # Daily mean flux: kg m-2 s-1 * 86400 s = kg m-2 per day.
            # For water, 1 kg m-2 is equivalent to 1 mm.
            daily_amount = da * 86400.0

            annual = daily_amount.resample(time="YS").sum(
                dim="time",
                skipna=True,)
            annual.attrs["units"] = "mm/year"
            annual.attrs["long_name"] = "Annual precipitation accumulation"

        else:
            raise ValueError(f"Unsupported variable: {variable}")

        annual = annual.sel(
            time=slice(
                f"{start_year}-01-01",
                f"{end_year}-12-31",))

        annual.name = variable
        annual.attrs["source_model"] = model
        annual.attrs["experiment"] = experiment
        annual.attrs["processing"] = "Annual aggregation from daily RegCM5 data"

        out_ds = annual.to_dataset(name=variable)

        print(f"  Saving {output_file}")
        out_ds.to_netcdf(output_file)


def process_cru_annual():
    """Convert monthly CRU temperature to annual mean temperature."""

    if not CRU_INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"CRU input file not found: {CRU_INPUT_FILE}")

    CRU_ANNUAL_DIR.mkdir(parents=True, exist_ok=True)

    output_file = (
        CRU_ANNUAL_DIR / "tas_CRU_year_1970-2024.nc")

    if output_file.exists():
        print(f"Already exists: {output_file}")
        return

    run_command([
        "cdo", "-O",
        "yearmean",
        "-selyear,1970/2024",
        "-selname,tmp",
        str(CRU_INPUT_FILE),
        str(output_file),])

    print(f"Annual CRU temperature saved: {output_file}")


def main():
    create_output_directories()

    for model in GCM_MODELS:
        for experiment in EXPERIMENTS:

            start_year, end_year = REGCM_PERIODS[experiment]

            print(
                f"\nProcessing {model} | {experiment} "
                f"| {start_year}-{end_year}")

            for variable in VARIABLES:
                process_annual_file(
                    model,
                    experiment,
                    variable,
                    start_year,
                    end_year,)

    process_cru_annual()
    print("\nAnnual RegCM5 processing finished.")


if __name__ == "__main__":
    main()
