#!/usr/bin/env python3
"""
Fix the file written by Graziano's sfturfer.py so it passes the checker.

sfturfer.py copies the global attributes of the orog file, and writes NETCDF4.
This script, for each file given:
  - sets variable_id to the variable in the file name (e.g. "sfturf")   [ATTR005, PATH001]
  - gives the file its own tracking_id and a new creation_date
  - rewrites it as NETCDF4_CLASSIC, deflate level 1 with shuffle        [FILE002, FILE003]
  - stores missing_value with the same type as the data (CF rule)
Data and coordinates are copied unchanged. The file is replaced in place.

Usage (after sourcing the modules):
  python3 fix_sfturf.py /path/to/fx/sfturf/<version>/sfturf_..._fx.nc
"""
import datetime
import os
import sys
import uuid

from netCDF4 import Dataset


def fix(path):
    var_id = os.path.basename(path).split("_")[0]
    tmp = path + ".tmp"
    with Dataset(path) as src, Dataset(tmp, "w", format="NETCDF4_CLASSIC") as dst:
        print(f"{os.path.basename(path)}")
        print(f"  format:      {src.data_model} -> NETCDF4_CLASSIC")

        attrs = {k: src.getncattr(k) for k in src.ncattrs()}
        print(f"  variable_id: {attrs.get('variable_id')} -> {var_id}")
        attrs["variable_id"] = var_id
        old_tid = str(attrs.get("tracking_id", ""))
        prefix = old_tid.rsplit("/", 1)[0] + "/" if "/" in old_tid else "hdl:21.14103/"
        attrs["tracking_id"] = prefix + str(uuid.uuid4())
        print(f"  tracking_id: new ({attrs['tracking_id']})")
        attrs["creation_date"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dst.setncatts(attrs)

        for name, dim in src.dimensions.items():
            dst.createDimension(name, None if dim.isunlimited() else len(dim))

        for name, var in src.variables.items():
            var.set_auto_maskandscale(False)
            fill = var.getncattr("_FillValue") if "_FillValue" in var.ncattrs() else None
            comp = dict(zlib=True, complevel=1, shuffle=True) if var.ndim > 0 else {}
            out = dst.createVariable(name, var.dtype, var.dimensions, fill_value=fill, **comp)
            out.set_auto_maskandscale(False)
            vattrs = {k: var.getncattr(k) for k in var.ncattrs() if k != "_FillValue"}
            if "missing_value" in vattrs and var.dtype.kind == "f":   # same type as the data (CF)
                vattrs["missing_value"] = var.dtype.type(vattrs["missing_value"])
            out.setncatts(vattrs)
            out[...] = var[...]
    os.replace(tmp, path)
    print("  done")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        fix(p)
