#!/usr/bin/env python3

"""
Compute annual RegCM5 fields from daily CORDEX-CMIP6 files.
tas: annual mean temperature in degrees Celsius
pr:  annual precipitation accumulation in mm/year

Output:
    annual/RegCM5/<variable>_<model>_<experiment>_year_<start>-<end>.nc
"""

from pathlib import Path

import xarray as xr
import subprocess 

from config import (
    DOMAIN,
    REGCM_INPUT_DIR,
    REGCM_NAME,
    REGCM_VERSION,
    REGCM_REALIZATION,
    REGCM_VERSION_TAG,
    EXPERIMENTS,
    REGCM_PERIODS,
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

    if DOMAIN == "EUR-12":
        files = sorted(input_dir.glob("v*/*.nc"))
    else:
        files = sorted(input_dir.glob("*.nc"))

    if not files:
        print(f"  WARNING: No files found in {input_dir}")

    return files

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

        if variable == "tas":
            # Convert Kelvin to degrees Celsius.
            annual = (da - 273.15).resample(time="YS").mean(
                dim="time",
                skipna=True,)
            annual.attrs["units"] = "degC"
            annual.attrs["long_name"] = "Annual mean near-surface air temperature"

        elif variable == "pr":
            # Convert flux to daily precipitation amount.
            time = da["time"]
            seconds = (
                time.dt.days_in_month * 0 + 86400)

            # Daily mean flux: kg m-2 s-1 * seconds = kg m-2.
            # For water, 1 kg m-2 is equivalent to 1 mm.
            daily_amount = da * seconds

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

    models = sorted(
        path.name
        for path in REGCM_INPUT_DIR.iterdir()
        if path.is_dir() and path.name not in {"ERA5"})

    for model in models:
        for experiment in EXPERIMENTS:
            if model not in [
                "EC-Earth3-Veg",
                "MPI-ESM1-2-HR",
                "NorESM2-MM",]:
                continue

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

