from pathlib import Path

# ============================================================
# MAIN PATHS
# ============================================================

DOMAIN = "EAS-12"

# Folder that holds these scripts (mask_grid.txt and the region list live here).
SCRIPT_DIR = Path(__file__).resolve().parent

# All generated data and figures go here.
BASE_DIR = Path(
    "/leonardo_work/ICT26_ESP/clu/trends/EAS-12")

# Existing annual GCM files (from Graziela's AFR-12 setup).
# They are reused only if they are global: select_regions.py checks this.
GCM_INPUT_DIR = Path(
    "/leonardo_work/ICT26_ESP/gluziada/AFR-12/validation/trends/GCMs")

# Original CORDEX-CMIP6 daily RegCM5 data
REGCM_INPUT_DIR = Path(
    "/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP")

# CRU TS observational data (global)
CRU_INPUT_FILE = Path(
    "/leonardo_work/ICT26_ESP/OBS/CRU/tmp.dat.nc")

# IPCC AR7 reference-region masks (global 0.11 degree grid)
MASK_DIR = Path(
    "/leonardo/home/userexternal/ggiulian/masks/new")

# Grid description for the AR7 masks (lets CDO see them as lon/lat grids)
MASK_GRID = SCRIPT_DIR / "mask_grid.txt"


def mask_grid_lonlat():
    """1D longitudes and latitudes of the AR7 masks, from MASK_GRID."""

    import numpy as np

    grid = {}

    for line in MASK_GRID.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            grid[key.strip()] = value.strip()

    lon = float(grid["xfirst"]) + float(grid["xinc"]) * np.arange(int(grid["xsize"]))
    lat = float(grid["yfirst"]) + float(grid["yinc"]) * np.arange(int(grid["ysize"]))

    return lon, lat

# ============================================================
# MODELS AND EXPERIMENTS
# ============================================================

GCM_MODELS = [
    "EC-Earth3-Veg",
    "MPI-ESM1-2-HR",
    "NorESM2-MM",]

REGCM_NAME = "RegCM5"
REGCM_VERSION = "RegCM5-0"
REGCM_REALIZATION = "r1i1p1f1"
REGCM_VERSION_TAG = "v1-r1"

EXPERIMENTS = [
    "historical",
    "ssp370",]

# ============================================================
# PERIODS
# ============================================================

# GCM annual files
PERIODS = {
    "historical": (1970, 2014),
    "ssp370": (2015, 2100),}

# RegCM5 daily data availability (EAS-12: first 10 years of ssp370)
REGCM_PERIODS = {
    "historical": (1970, 2014),
    "ssp370": (2015, 2024),}

# A year with fewer daily values than this counts as incomplete.
# An annual file is written only when every year of the period is complete,
# so a run that is still being post-processed is never saved half-done.
MIN_DAYS_PER_YEAR = 360

# ============================================================
# VARIABLES
# ============================================================

VARIABLES = ["tas", "pr"]

VARIABLE_INFO = {
    "tas": {
        "input_units": "K",
        "output_units": "degC",
        "annual_statistic": "mean",},
    "pr": {
        "input_units": "kg m-2 s-1",
        "output_units": "mm/year",
        "annual_statistic": "sum",},}

# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

ANNUAL_DIR = BASE_DIR / "annual"
REGIONAL_DIR = BASE_DIR / "regional"
TREND_DIR = BASE_DIR / "trends"
FIGURE_DIR = BASE_DIR / "figures"

GCM_ANNUAL_DIR = ANNUAL_DIR / "GCM"
REGCM_ANNUAL_DIR = ANNUAL_DIR / "RegCM5"
CRU_ANNUAL_DIR = ANNUAL_DIR / "OBS"

GCM_REGIONAL_DIR = REGIONAL_DIR / "GCM"
REGCM_REGIONAL_DIR = REGIONAL_DIR / "RegCM5"
CRU_REGIONAL_DIR = REGIONAL_DIR / "OBS"

GCM_TREND_DIR = TREND_DIR / "GCM"
REGCM_TREND_DIR = TREND_DIR / "RegCM5"

TIMESERIES_FIGURE_DIR = FIGURE_DIR / "timeseries"
TREND_MAP_FIGURE_DIR = FIGURE_DIR / "trend_maps"

# ============================================================
# REFERENCE REGIONS
# ============================================================

# The AR7 regions inside EAS-12 are chosen by select_regions.py, which
# writes this file. Edit the file by hand to drop or rename regions.
REGION_FILE = SCRIPT_DIR / f"regions_{DOMAIN}.txt"

# select_regions.py keeps a region if at least this share of its area
# lies inside the RegCM domain.
REGION_MIN_COVERAGE = 0.9

# Grid points to ignore along each domain edge when measuring coverage.
# 0 keeps the full domain (as for the other domains). Set it to the
# relaxation width (nspgx = 40 for EAS-12) to exclude the buffer zone.
REGION_BUFFER_POINTS = 0


def read_region_file():
    """Read region codes and full names from REGION_FILE."""

    codes, names = [], {}

    if not REGION_FILE.is_file():
        return codes, names

    for line in REGION_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        codes.append(parts[0])
        names[parts[0]] = parts[1].strip() if len(parts) > 1 else parts[0]

    return codes, names


REGIONS, REGION_NAMES = read_region_file()


def get_regions():
    """Return selected AR7 regions after checking their mask files."""

    if not REGIONS:
        raise FileNotFoundError(
            f"No region list found: {REGION_FILE}\n"
            f"Run 'python3 select_regions.py' first.")

    missing = [
        region
        for region in REGIONS
        if not (MASK_DIR / f"{region}_mask.nc").is_file()
    ]

    if missing:
        raise FileNotFoundError(
            f"Missing AR7 mask files for regions: {missing}\n"
            f"Expected location: {MASK_DIR}"
        )

    return REGIONS.copy()

# ============================================================
# PLOT OPTIONS
# ============================================================

# Years shown on the x-axis, e.g. (1970, 2024). None shows every year
# available (GCMs run to 2100), as in the other domains.
PLOT_YEARS = None

# EAS-12 regions range from cold (Tibet, Siberia) to tropical, so one
# shared y-axis flattens every curve. False gives each panel its own range.
SHARED_Y_AXIS = False

# EAS-12 crosses 180°E, so draw the region map with 0–360 longitudes.
MAP_LON_0_360 = True

# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

def create_output_directories():
    """Create all directories used for generated data and figures."""
    directories = [
        ANNUAL_DIR,
        REGIONAL_DIR,
        TREND_DIR,
        FIGURE_DIR,
        GCM_ANNUAL_DIR,
        REGCM_ANNUAL_DIR,
        CRU_ANNUAL_DIR,
        GCM_REGIONAL_DIR,
        REGCM_REGIONAL_DIR,
        CRU_REGIONAL_DIR,
        GCM_TREND_DIR,
        REGCM_TREND_DIR,
        TIMESERIES_FIGURE_DIR,
        TREND_MAP_FIGURE_DIR,]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
