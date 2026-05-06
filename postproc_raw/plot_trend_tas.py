#%%
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.stats import t as student_t

ALPHA = 0.05
VMIN, VMAX = -1, 1

FILES = {"CRU": "trend_out/tas_CRU_annual_1970-2022.nc",
         "ERA5": "trend_out/tas_ERA5_annual_1970-2022.nc",
         "RegCM–ERA5": "trend_out/tas_annual_mean.nc",}

OUTFIG = "tas_trend_1970-2024_regcm_obs.png"

def trend_and_significance(ds, var="tas", alpha=0.05):
    tas = ds[var]
    years = ds.time.dt.year.astype(float)
    t = xr.DataArray(years - years[0], dims="time", coords={"time": ds.time})
    n = t.size

    t_mean = t.mean("time")
    tas_mean = tas.mean("time")
    cov = ((t - t_mean) * (tas - tas_mean)).mean("time")
    var_t = ((t - t_mean) ** 2).mean("time")
    slope = cov / var_t        # K / year
    trend = slope * 10.0       # °C / decade

    fitted = tas_mean + slope * t
    resid = tas - fitted
    ss_res = (resid ** 2).sum("time")
    ss_t = ((t - t_mean) ** 2).sum("time")
    stderr = np.sqrt(ss_res / ((n - 2) * ss_t))
    t_stat = slope / stderr

    pvals = xr.apply_ufunc(
        lambda x: 2 * (1 - student_t.cdf(np.abs(x), df=n - 2)),
        t_stat,
        dask="allowed",
        output_dtypes=[float],)

    significant = pvals < alpha
    return trend, significant
# PLOT
fig, axes = plt.subplots(
    ncols=3,
    figsize=(12, 5.5),
    subplot_kw=dict(projection=ccrs.PlateCarree()),
    constrained_layout=True,)

for ax, (label, path) in zip(axes, FILES.items()):
    ds = xr.open_dataset(path)

    # Subset only for regular lat/lon grids
    if {"lat", "lon"}.issubset(ds.dims):
        lat0 = ds.lat.isel(lat=0).item()
        lat1 = ds.lat.isel(lat=-1).item()

        ds = ds.sel(
            lon=slice(-25, 60),
            lat=slice(43, -45) if lat0 > lat1 else slice(-45, 43),)

    trend, sig = trend_and_significance(ds)

    im = trend.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        cmap="RdBu_r",
        vmin=VMIN,
        vmax=VMAX,
        add_colorbar=False,)

    xr.where(sig, np.nan, 1).plot.contourf(
        ax=ax,
        transform=ccrs.PlateCarree(),
        levels=[0.5, 1.5],
        colors="None",
        hatches=["///"],
        add_colorbar=False,)

    ax.set_extent([-25, 60, -44, 43.5], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE, linewidth=0.6)
    ax.add_feature(cfeature.BORDERS, linewidth=0.4)
    ax.set_title(label)

    vmin = float(trend.min())
    vmax = float(trend.max())

    ax.text(0.02, 0.02,
            f"min: {vmin:.2f} °C/dec\nmax: {vmax:.2f} °C/dec",
            transform=ax.transAxes,
            fontsize=8,
            ha="left",
            va="bottom",
            bbox=dict(facecolor="white",
                      alpha=0.5,
                      edgecolor="none",),)

cbar = fig.colorbar(
    im,
    ax=axes,
    orientation="horizontal",
    shrink=0.6,
    aspect=35,
    pad=0.04,
    label="Temperature trend (°C / decade)",)

fig.suptitle(
    "Mean Annual Temperature Trend (1970–2024) | Hatching: p ≥ 0.05",
    fontsize=12,
    y=0.98,)

plt.savefig(OUTFIG, dpi=200, bbox_inches="tight")
plt.close()

print(f"Saved: {OUTFIG}")

