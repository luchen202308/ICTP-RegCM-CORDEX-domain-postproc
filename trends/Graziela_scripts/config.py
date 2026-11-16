from pathlib import Path

# ============================================================
# MAIN PATHS
# ============================================================

DOMAIN = "AFR-12"

BASE_DIR = Path(
    "/leonardo_work/ICT26_ESP/gluziada/AFR-12/validation/trends")

# Existing annual GCM files
GCM_INPUT_DIR = BASE_DIR / "GCMs"

# Original CORDEX-CMIP6 daily RegCM5 data
REGCM_INPUT_DIR = Path(
    "/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/AFR-12/ICTP")

# CRU TS observational data
CRU_INPUT_FILE = Path(
    "/leonardo_work/ICT26_ESP/OBS/CRU/tmp.dat.nc")

# IPCC AR7 reference-region masks
MASK_DIR = Path(
    "/leonardo/home/userexternal/ggiulian/masks/new")

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

# RegCM5 daily data availability
REGCM_PERIODS = {
    "historical": (1970, 2014),
    "ssp370": (2015, 2030),}

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

# All 14 AR7 regions for AFR-12
REGIONS = [
    "SMED",  # Southern Mediterranean
    "NWSH",  # Northwestern Sahara
    "NCSH",  # North Central Sahara
    "NESH",  # Northeastern Sahara
    "SWSH",  # Southwestern Sahara
    "SCSH",  # South Central Sahara
    "SESH",  # Southeastern Sahara
    "WAF",   # Western Africa
    "NCAF",  # North Central Africa
    "SCAF",  # South Central Africa
    "NEAF",  # Northeastern Africa
    "SEAF",  # Southeastern Africa
    "WSAF",  # Western Southern Africa
    "ESAF",  # Eastern Southern Africa
    "MDG",   # Madagascar
]

REGION_NAMES = {
    "SMED": "Southern Mediterranean",
    "NWSH": "North-Western Sahara",
    "NCSH": "North-Central Sahara",
    "NESH": "North-Eastern Sahara",
    "SWSH": "South-Western Sahara",
    "SCSH": "South-Central Sahara",
    "SESH": "South-Eastern Sahara",
    "WAF": "West Africa",
    "NCAF": "North-Central Africa",
    "SCAF": "South-Central Africa",
    "NEAF": "North-Eastern Africa",
    "SEAF": "South-Eastern Africa",
    "WSAF": "Western Southern Africa",
    "ESAF": "Eastern Southern Africa",
    "MDG": "Madagascar",
}


def get_regions():
    """Return selected AR7 regions after checking their mask files."""

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

