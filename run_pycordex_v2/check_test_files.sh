#!/bin/bash
# Test the CORDEX-CMIP6 compliance checker on one or two files.
#
# Usage:
#   ./check_test_files.sh                  # checks the default test files below
#   ./check_test_files.sh /path/to/a.nc    # checks the file(s) you give
#
# Reports are printed and also saved in $outdir.

source /leonardo/home/userexternal/ggiulian/modules_new

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
version=v20260815
outdir=$HOME/cordex_check/test
mkdir -p "$outdir"

if [ $# -gt 0 ]; then
    files=("$@")
else
    files=(
        # 1. a normal file (daily, last month of the run)
        "$root/day/va200/$version/va200_EAS-12_ERA5_evaluation_r1i1p1f1_ICTP_RegCM5-0_v1-r1_day_20241201-20241231.nc"
        # 2. a fixed (fx) file, whose naming differs from the SAM-12 example
        "$(find "$root/fx/orog/$version" -name '*.nc' | sort | head -1)"
    )
fi

for f in "${files[@]}"; do
    if [ ! -f "$f" ]; then
        echo "Not found: $f"
        continue
    fi
    report="$outdir/$(basename "${f%.nc}").txt"
    echo "=== $f"
    start=$(date +%s)
    compliance-checker -t wcrp_cordex_cmip6:1.0 "$f" | tee "$report"
    echo "Exit code: ${PIPESTATUS[0]}   Time: $(( $(date +%s) - start )) s"
    echo "Report saved: $report"
    echo
done
