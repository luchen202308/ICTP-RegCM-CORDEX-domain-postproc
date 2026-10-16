#!/bin/bash
# For each domain under DD/, take one .nc file and report:
#   - the lon range and how many rows are not increasing along rlon
#   - the Required flags from the compliance checker
# The lon grid is the same in every file of a domain, so one file is enough.
# Read-only. Takes about 10 s per domain; fine on the login node.
#
# Usage:
#   bash check_lon_domains.sh

source /leonardo/home/userexternal/ggiulian/modules_new

base=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD

for d in "$base"/*/; do
    d=${d%/}
    name=$(basename "$d")
    f=$(find -H "$d" -name '*.nc' -print -quit 2>/dev/null)
    if [ -z "$f" ]; then
        echo "=== $name: no .nc file found"
        continue
    fi
    echo "=== $name: $(basename "$f")"

    python3 - "$f" <<'EOF'
import sys
import numpy as np
from netCDF4 import Dataset
with Dataset(sys.argv[1]) as ds:
    if "lon" not in ds.variables:
        print("  no lon variable")
        sys.exit()
    v = ds.variables["lon"]
    lon = np.asarray(v[:])
    if lon.ndim != 2:
        print(f"  lon {lon.min():.1f} .. {lon.max():.1f} ({lon.ndim}-D)")
        sys.exit()
    ax = v.dimensions.index("rlon") if "rlon" in v.dimensions else 1
    bad = int((np.diff(lon, axis=ax) <= 0).any(axis=ax).sum())
    print(f"  lon {lon.min():.1f} .. {lon.max():.1f}, rows not increasing: {bad}")
EOF

    req=$(compliance-checker -t wcrp_cordex_cmip6:1.0 "$f" 2>/dev/null | awk '
        { t = $0; gsub(/^[ \t]+|[ \t]+$/, "", t) }
        t == "Required" { s = 1; next }
        t == "Recommended" || t == "Suggested" || t == "Optional" { s = 0 }
        s && /^\[[A-Z]+[0-9]+\]/ { k = substr($1, 2, length($1) - 2)
                                   if (!seen[k]++) c = c (c == "" ? "" : ", ") k }
        END { print (c == "" ? "none" : c) }')
    echo "  Required flags: $req"
done
