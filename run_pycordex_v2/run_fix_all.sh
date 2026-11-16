#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            fix_all
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     32
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                8:00:00

# Fix all EAS-12 ERA5 files in one job, one variable folder per task,
# 32 folders at a time. In each folder:
#   1. Graziano's fix_cordex_dates.py --apply   (CDXT004, TIME003: time units,
#      time values and bounds, file names)
#   2. fix_activity_id.py --run                 (ATTR001, ATTR004)
# Both scripts skip what is already correct, so the job is safe to re-run
# (e.g. after a time limit). The fx folder is not touched.
#
# Usage (from the run_pycordex_v2 folder, with both scripts in it):
#   sbatch run_fix_all.sh
# Results: fix_logs_<jobid>/  (one log per folder) and
#          fix_logs_<jobid>/fix_summary.txt  (read this first)

source /leonardo/home/userexternal/ggiulian/modules_new

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
here=${SLURM_SUBMIT_DIR:-$PWD}
logdir=$here/fix_logs_${SLURM_JOB_ID:-$(date +%Y%m%d%H%M%S)}
nproc=${SLURM_NTASKS:-8}
mkdir -p "$logdir" || exit 1

for s in fix_cordex_dates.py fix_activity_id.py; do
    [ -f "$here/$s" ] || { echo "ERROR: $here/$s not found"; exit 1; }
done

# <freq>/<var>/<version> folders, except fx
find "$root" -mindepth 3 -maxdepth 3 -type d -name 'v[0-9]*' ! -path "$root/fx/*" \
    | sort > "$logdir/folders.txt"
echo "Folders: $(wc -l < "$logdir/folders.txt")   Parallel: $nproc"

fix_folder() {
    local d=$1 rel log
    rel=${d#"$root"/}
    log=$logdir/$(echo "${rel%/*}" | tr '/' '_').log      # e.g. 1hr_hfls.log
    {
        echo "### $rel"
        python3 "$here/fix_cordex_dates.py" --apply "$d"
        echo "### dates exit=$?"
        python3 "$here/fix_activity_id.py" --run "$d"
        echo "### activity_id exit=$?"
    } > "$log" 2>&1
}
export -f fix_folder
export root here logdir

t0=$(date +%s)
xargs -a "$logdir/folders.txt" -d '\n' -P "$nproc" -n 1 bash -c 'fix_folder "$1"' _
echo "Finished in $(( ($(date +%s) - t0) / 60 )) min"

# ---------------------------------------------------------------- summary
{
    echo "Fix summary, $(date '+%Y-%m-%d %H:%M')"
    echo "Root: $root"
    echo "Folders: $(wc -l < "$logdir/folders.txt")   Logs: $(ls "$logdir"/*.log | wc -l)"
    echo
    echo "Dates fix (fix_cordex_dates.py):"
    cat "$logdir"/*.log | awk '/ file\(s\) fixed$/ { n += $1 } END { printf "  files fixed: %d\n", n }'
    echo "  folders where it stopped with an error: $(grep -l '^Traceback' "$logdir"/*.log | wc -l)"
    echo
    echo "activity_id fix:"
    cat "$logdir"/*.log | awk -F': ' '/^activity_id summary/ {
            n = split($2, a, ", "); for (i = 1; i <= n; i++) { split(a[i], kv, " "); c[kv[1]] += kv[2] } }
        END { for (k in c) printf "  %-12s %d\n", k, c[k] }' | sort
    echo
    echo "Files that must be REPROCESSED with pycordexer (count by problem):"
    cat "$logdir"/*.log | awk '/must be reprocessed/ { s = 1; next } /^###/ { s = 0 }
        s && /: / { sub(/^ +/, ""); p = $0; sub(/^.*\.nc: /, "", p); c[p]++ }
        END { for (k in c) printf "  %6d  %s\n", c[k], k }' | sort -rn
    echo "  (full list: reprocess.txt)"
    echo
    echo "Problems to look at (NOT renamed, ERROR, Traceback):"
    grep -h -E "NOT renamed|^ERROR|^Traceback|^error" "$logdir"/*.log | head -20
    echo "  (total: $(grep -h -c -E "NOT renamed|^ERROR|^Traceback|^error" "$logdir"/*.log | awk '{s+=$1} END {print s+0}'))"
} > "$logdir/fix_summary.txt"

cat "$logdir"/*.log | awk '/must be reprocessed/ { s = 1; next } /^###/ { s = 0 }
    s && /: / { sub(/^ +/, ""); print }' | sort > "$logdir/reprocess.txt"

cat "$logdir/fix_summary.txt"
