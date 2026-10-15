#!/bin/bash
# Insert the CORDEX-CMIP6 version folder between each variable folder
# and its .nc files:
#   .../<frequency>/<variable>/*.nc  ->  .../<frequency>/<variable>/vYYYYMMDD/*.nc
#
# Usage:
#   ./add_version_folder.sh        # dry run: only prints what it would do
#   ./add_version_folder.sh run    # really moves the files
#
# Safe to re-run: it only moves .nc files still sitting directly in a
# variable folder. "mv" on the same file system is only a rename, so no
# data are copied.

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
version=v20260815
mode=${1:-dry}

cd "$root" || { echo "Cannot cd to $root"; exit 1; }

before=$(find . -name '*.nc' | wc -l)
echo "Root:    $root"
echo "Version: $version"
echo "Mode:    $mode"
echo ".nc files before: $before"
echo

for vardir in */*/; do                      # <frequency>/<variable>/
    vardir=${vardir%/}
    n=$(find "$vardir" -maxdepth 1 -name '*.nc' | wc -l)
    if [ "$n" -eq 0 ]; then
        echo "skip  $vardir (no .nc files at this level)"
        continue
    fi
    other=$(find "$vardir" -mindepth 1 -maxdepth 1 -type d -name 'v[0-9]*' ! -name "$version")
    [ -n "$other" ] && echo "WARN  $vardir already has another version folder: $other"
    echo "move  $n files: $vardir/ -> $vardir/$version/"
    if [ "$mode" = "run" ]; then
        mkdir -p "$vardir/$version" || exit 1
        find "$vardir" -maxdepth 1 -name '*.nc' -exec mv -t "$vardir/$version/" {} + \
            || { echo "ERROR moving files in $vardir"; exit 1; }
    fi
done

if [ "$mode" = "run" ]; then
    after=$(find . -name '*.nc' | wc -l)
    inside=$(find . -mindepth 4 -maxdepth 4 -path "*/$version/*" -name '*.nc' | wc -l)
    left=$(find . -mindepth 3 -maxdepth 3 -name '*.nc' | wc -l)
    echo
    echo ".nc files after:          $after"
    echo "  inside $version:       $inside"
    echo "  still without version:  $left"
    if [ "$after" -eq "$before" ] && [ "$left" -eq 0 ]; then
        echo "OK: all files moved, none lost."
    else
        echo "WARNING: please check the counts above."
    fi
else
    echo
    echo "Dry run only. Run './add_version_folder.sh run' to move the files."
fi
