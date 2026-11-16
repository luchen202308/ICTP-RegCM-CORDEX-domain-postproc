#!/usr/bin/env python3
"""
Is daily evspsblpot the mean of the hourly values, or one hourly value
("thinned")? Compares one month of day and 1hr files on a coarse subset of
grid points (every 20th), so it is light enough for the login node.

Usage: python3 check_evspsblpot.py [root] [YYYYMM]
"""
import datetime, glob, sys
import numpy as np
from netCDF4 import Dataset, num2date

root = sys.argv[1] if len(sys.argv) > 1 else \
    "/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1"
month = sys.argv[2] if len(sys.argv) > 2 else "197001"
fd = sorted(glob.glob(f"{root}/day/evspsblpot/*/*_day_{month}*.nc"))[0]
fh = sorted(glob.glob(f"{root}/1hr/evspsblpot/*/*_1hr_{month}*.nc"))[0]
print("daily: ", fd.split("/")[-1]); print("hourly:", fh.split("/")[-1])

with Dataset(fd) as d, Dataset(fh) as h:
    dv = d["evspsblpot"][:, ::20, ::20].astype("f8")
    hv = h["evspsblpot"][:, ::20, ::20].astype("f8")
    t = h["time"]
    # 1 minute back, so values stamped 00:00 count for the day that ends there
    days = [(x - datetime.timedelta(minutes=1)).day for x in num2date(t[:], t.units, t.calendar)]

days = np.array(days)
print(f"\n{'day':>3}  {'daily':>11}  {'mean of hourly':>14}  best single hour (diff)")
thinned = averaged = 0
for k in range(min(len(dv), 5)):
    hk = hv[days == k + 1]
    mean = hk.mean(axis=0)
    diffs = [np.abs(dv[k] - hk[i]).max() for i in range(len(hk))]
    i = int(np.argmin(diffs))
    print(f"{k+1:3d}  {dv[k].mean():11.4e}  {mean.mean():14.4e}  hour #{i}  ({diffs[i]:.1e})")
for k in range(len(dv)):
    hk = hv[days == k + 1]
    scale = np.abs(hk).max() or 1.0
    if np.abs(dv[k] - hk.mean(axis=0)).max() < 1e-4 * scale:
        averaged += 1
    elif min(np.abs(dv[k] - hk[i]).max() for i in range(len(hk))) < 1e-6 * scale:
        thinned += 1
print(f"\nDays equal to the hourly mean: {averaged};  equal to one hourly value: {thinned};  "
      f"of {len(dv)}")
