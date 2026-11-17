# Regional trends for EAS-12

Graziela’s trend scripts (`../Graziela_scripts`, AFR-12) adapted to EAS-12.
They plot annual regional means of RegCM5, the three driving GCMs, and CRU
over the AR7 regions inside the domain.

## Steps on Leonardo

```bash
cd <this folder>
source /leonardo/home/userexternal/ggiulian/modules_gfortran

# 0. pycordex for the first 10 years of ssp370 (if not done yet)
#    (from run_pycordex_v2, one chain per GCM)
#    bash run_regcmcordex_GCM.sh 2015010100 2024120100 ECEarth   # also MPIESM, NorESM

# 1. Choose the AR7 regions (login node, about a minute)
python3 select_regions.py          # prints a table, writes regions_EAS-12.txt

# 2. Annual and regional means (re-submit any time; finished files are skipped)
sbatch submit_compute.sh

# 3. Figures (in BASE_DIR/figures/timeseries)
python3 plot_regional_timeseries_withmap.py
python3 plot_regional_timeseries.py
```

You can run steps 1 to 3 while the ssp370 pycordex is still running.
Unfinished runs are skipped (no annual file is written until every year is
complete), so just re-submit step 2 and re-plot when pycordex is done.

## What changed from the AFR-12 version

- `config.py`: EAS-12 paths, `BASE_DIR` under `clu/trends/EAS-12`,
  RegCM ssp370 period 2015–2024, and new options (`PLOT_YEARS`,
  `SHARED_Y_AXIS`, `MAP_LON_0_360`, region-selection settings).
- Regions: `select_regions.py` measures how much of each AR7 mask lies inside
  EAS-12 and keeps those with at least 90% (`REGION_MIN_COVERAGE`). It also
  checks that the GCM annual files cover EAS-12. Edit `regions_EAS-12.txt`
  to drop regions or add full names.
- `compute_annual_means.py`: finds files with or without a `v<YYYYMMDD>`
  folder, does not compare lat/lon between files (faster, and safe across the
  180°E longitude fix), and skips runs with missing months.
- `compute_srex_means.py`: each mask is regridded once per grid and reused
  (same results, much faster); `mask_grid.txt` is read from this folder.
- Plots: domain name in the title, region map drawn in 0–360° longitudes
  (EAS-12 crosses 180°E), one y-axis per panel by default (EAS-12 regions
  range from Siberia to the tropics), and a clearer CRU legend entry.

## Notes

- GCM annual files are taken from Graziela’s folder. `select_regions.py`
  reports whether they are global; if not, EAS-12 versions are needed.
- If some RegCM runs have the 180°E longitude fix and others not, CDO prints
  “Geographic location of some grid points differ!”. This is harmless: the
  points are the same, only the longitude convention differs.
- As in the AFR-12 version, CDO averages RegCM grid cells with equal weights
  (pycordex files have no cell bounds). On the rotated EAS-12 grid, cell
  areas vary by about 5–15% across one region, so the effect on regional
  means is small (a few hundredths of a degree) and on trends negligible.
