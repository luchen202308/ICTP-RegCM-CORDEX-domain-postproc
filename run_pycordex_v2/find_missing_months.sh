#!/bin/bash
# Find missing (or duplicated) monthly files in each <frequency>/<variable>
# folder of the pycordex output. Works before and after adding the
# version folder. Only reads file names; changes nothing.
#
# Usage:
#   ./find_missing_months.sh

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
y0=1970
y1=2024

# expected months: 197001 ... 202412
expected=$(for y in $(seq $y0 $y1); do for m in $(seq -w 1 12); do echo "$y$m"; done; done)

cd "$root" || { echo "Cannot cd to $root"; exit 1; }
summary=$(mktemp)

for vardir in */*/; do                      # <frequency>/<variable>/
    vardir=${vardir%/}
    [[ $vardir == fx/* ]] && continue       # fx files are not monthly

    # start month (YYYYMM) from the time range at the end of each file name
    present=$(find "$vardir" -maxdepth 2 -name '*.nc' -printf '%f\n' \
              | sed -E 's/.*_([0-9]{6})[0-9]*-[0-9]+\.nc$/\1/' | sort)

    missing=$(comm -23 <(echo "$expected") <(echo "$present" | uniq))
    dups=$(echo "$present" | uniq -d)

    if [ -n "$missing" ] || [ -n "$dups" ]; then
        echo "$vardir ($(echo "$present" | grep -c .) files)"
        [ -n "$missing" ] && echo "  missing:    $(echo $missing)"
        [ -n "$dups" ]    && echo "  duplicated: $(echo $dups)"
        for m in $missing; do echo "$m $vardir" >> "$summary"; done
    fi
done

echo
echo "===== Missing months, with the folders that lack them ====="
if [ -s "$summary" ]; then
    sort "$summary" | awk '{a[$1]=a[$1]" "$2} END {for (m in a) print m":"a[m]}' | sort
else
    echo "None. All folders have every month from ${y0}01 to ${y1}12."
fi
rm -f "$summary"
