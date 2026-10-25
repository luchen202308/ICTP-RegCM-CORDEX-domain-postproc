#!/usr/bin/env python3
"""
Fix the compliance-checker flag CDXV003 ("The longitude coordinate should be
strictly monotonically increasing") for the EAS-12 domain.

Why: the north-east corner of EAS-12 reaches about 192E. pycordex writes lon
in the range -180..180, so those rows jump from +180 to -180. Adding 360 to
the negative values gives lon = ~40..~193, which increases along every row.

What it does: changes only the "lon" variable, in place. The data variables
are not touched. Files with no negative lon are skipped, so it is safe to
re-run.

Usage (after sourcing the modules):
  python3 fix_lon_360.py FILE_OR_DIR ...             # dry run: report only
  python3 fix_lon_360.py --run FILE_OR_DIR ...       # really change the files
  python3 fix_lon_360.py --run -j 32 /path/to/root   # 32 files in parallel
"""
import argparse
import os
import sys
from functools import partial
from multiprocessing import Pool

import numpy as np
from netCDF4 import Dataset


def increasing_along_rlon(var, values):
    axis = var.dimensions.index("rlon") if "rlon" in var.dimensions else values.ndim - 1
    return bool(np.all(np.diff(values, axis=axis) > 0))


def fix_one(path, run=False):
    try:
        with Dataset(path, "r+" if run else "r") as ds:
            if "lon" not in ds.variables:
                return "no_lon", path
            var = ds.variables["lon"]
            var.set_auto_maskandscale(False)
            lon = var[:]
            if increasing_along_rlon(var, lon):      # nothing to fix (e.g. SAM-12)
                return "already_ok", path
            if not (lon < 0).any():
                return "still_not_increasing", path
            new = np.where(lon < 0, lon + 360, lon).astype(lon.dtype)
            if not increasing_along_rlon(var, new):
                return "still_not_increasing", path
            if run:
                var[:] = new
                if "valid_max" in var.ncattrs():
                    var.valid_max = np.array(360, dtype=lon.dtype)
                if "valid_range" in var.ncattrs():
                    var.valid_range = np.array([-180, 360], dtype=lon.dtype)
                return "fixed", path
            return "would_fix", path
    except Exception as e:  # report and carry on with the other files
        return f"error ({e})", path


def collect(paths):
    for p in paths:
        if os.path.isdir(p):
            for d, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith(".nc"):
                        yield os.path.join(d, f)
        else:
            yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help=".nc files and/or folders")
    ap.add_argument("--run", action="store_true", help="change the files (default: dry run)")
    ap.add_argument("-j", type=int, default=1, help="number of files in parallel")
    args = ap.parse_args()

    files = sorted(collect(args.paths))
    print(f"{'RUN' if args.run else 'DRY RUN'}: {len(files)} files, {args.j} in parallel", flush=True)

    counts = {}
    with Pool(args.j) as pool:
        for status, path in pool.imap_unordered(partial(fix_one, run=args.run), files, chunksize=20):
            key = status.split(" ")[0]
            counts[key] = counts.get(key, 0) + 1
            if key not in ("fixed", "would_fix", "already_ok"):
                print(f"{status}: {path}", flush=True)

    print("\nSummary:")
    for k in sorted(counts):
        print(f"  {k:22s} {counts[k]}")
    if not args.run:
        print("\nDry run only. Add --run to change the files.")
    bad = sum(v for k, v in counts.items() if k not in ("fixed", "would_fix", "already_ok"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
