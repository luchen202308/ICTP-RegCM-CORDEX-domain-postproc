#!/bin/bash
# Test the CORDEX-CMIP6 compliance checker on one file per frequency
# (1hr, 3hr, 6hr, day, fx, ...), then print a short summary.
#
# Usage:
#   bash check_test_files.sh                  # one file per frequency
#   bash check_test_files.sh /path/to/a.nc    # checks the file(s) you give
#
# Full reports are saved in $outdir.

source /leonardo/home/userexternal/ggiulian/modules_new

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
outdir=$HOME/cordex_check/test
mkdir -p "$outdir"

if [ $# -gt 0 ]; then
    files=("$@")
else
    # last file of the first variable in each frequency folder
    files=()
    for fdir in "$root"/*/; do
        vdir=$(find "$fdir" -mindepth 1 -maxdepth 1 -type d | sort | head -1)
        f=$(find "$vdir" -name '*.nc' | sort | tail -1)
        [ -n "$f" ] && files+=("$f")
    done
fi

summary=()
for f in "${files[@]}"; do
    if [ ! -f "$f" ]; then
        echo "Not found: $f"
        continue
    fi
    report="$outdir/$(basename "${f%.nc}").txt"
    echo "=== $f"
    start=$(date +%s)
    compliance-checker -t wcrp_cordex_cmip6:1.0 "$f" > "$report" 2>&1
    rc=$?
    cat "$report"
    echo "Exit code: $rc   Time: $(( $(date +%s) - start )) s   Report: $report"
    echo

    # Required flags and time units, for the summary
    req=$(awk '
        { t = $0; gsub(/^[ \t]+|[ \t]+$/, "", t) }
        t == "Required" { s = 1; next }
        t == "Recommended" || t == "Suggested" || t == "Optional" { s = 0 }
        s && /^\[[A-Z]+[0-9]+\]/ { k = substr($1, 2, length($1) - 2)
                                   if (!seen[k]++) c = c (c == "" ? "" : ",") k }
        END { print (c == "" ? "none" : c) }' "$report")
    tunits=$(ncdump -h "$f" 2>/dev/null | sed -n 's/.*time:units = "\(.*\)" ;/\1/p')
    rel=${f#"$root"/}
    summary+=("$(printf '%-6s %-28s %-36s %s' "${rel%%/*}" "$req" "${tunits:-no time}" "$(basename "$f")")")
done

echo "==================== Summary ===================="
printf '%-6s %-28s %-36s %s\n' "freq" "Required flags" "time units" "file"
printf '%s\n' "${summary[@]}"
