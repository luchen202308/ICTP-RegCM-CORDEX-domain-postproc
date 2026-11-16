#!/usr/bin/env python3
"""
Fix the compliance-checker flags ATTR001 and ATTR004 (missing activity_id).

Files made with older pycordexer versions (on EAS-12 ERA5: 1970-01 to 1979-04)
have no "activity_id" global attribute. Current pycordexer writes "DD".
This script adds activity_id = "DD" where it is missing. Nothing else is
changed, and files that already have it are skipped, so it is safe to re-run.

Usage (after sourcing the modules):
  python3 fix_activity_id.py FILE_OR_DIR ...            # dry run: report only
  python3 fix_activity_id.py --run FILE_OR_DIR ...      # really change the files
  python3 fix_activity_id.py --run -j 32 /path/to/root  # 32 files in parallel
"""
import argparse
import os
import sys
from functools import partial
from multiprocessing import Pool

from netCDF4 import Dataset

VALUE = "DD"
OK_STATUSES = ("fixed", "would_fix", "already_ok")


def fix_one(path, run=False):
    try:
        with Dataset(path, "r+" if run else "r") as ds:
            if "activity_id" in ds.ncattrs():
                return "already_ok", path
            if run:
                ds.setncattr("activity_id", VALUE)
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
    print(f"activity_id {'RUN' if args.run else 'DRY RUN'}: {len(files)} files", flush=True)

    counts = {}
    with Pool(args.j) as pool:
        for status, path in pool.imap_unordered(partial(fix_one, run=args.run), files, chunksize=20):
            key = status.split(" ")[0]
            counts[key] = counts.get(key, 0) + 1
            if key not in OK_STATUSES:
                print(f"{status}: {path}", flush=True)

    print("activity_id summary: " + ", ".join(f"{k} {counts[k]}" for k in sorted(counts)))
    bad = sum(v for k, v in counts.items() if k not in OK_STATUSES)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
