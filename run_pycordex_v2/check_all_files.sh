#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            cc_check
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     112
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                12:00:00

# Run the CORDEX-CMIP6 compliance checker on many files in parallel and
# summarise the flags.
#
# Usage:
#   sbatch check_all_files.sh sample             # first and last file of every variable
#   sbatch check_all_files.sh all                # every file
#   sbatch check_all_files.sh all after_fix      # optional label: separate output folder
#
# - One report per file, in $outdir/reports/<freq>/<var>/<version>/.
# - Files that already have a finished report are skipped, so if the job hits
#   the time limit, just submit it again with the same mode.
# - Results: $outdir/summary.txt lists every issue, its message, and where it
#   appears (frequency, variables, months). It is the one file to read or share.
#   Also results.tsv (one line per file), files_with_required.txt, checker_errors.txt.
# - To redo only the summary (e.g. on the login node):
#   python3 summarise_checks.py <outdir> <root> <mode>
# - To run fewer checks at once (e.g. if memory runs out):
#   sbatch --export=ALL,NPROC=56 check_all_files.sh all

source /leonardo/home/userexternal/ggiulian/modules_new

mode=${1:-sample}
label=${2:+_$2}
root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1
outdir=/leonardo_scratch/large/userexternal/clu00000/cordex_check/EAS-12_ERA5/$mode$label
nproc=${NPROC:-${SLURM_NTASKS:-8}}

case $mode in sample|all) ;; *) echo "Mode must be 'sample' or 'all'"; exit 1 ;; esac
mkdir -p "$outdir/reports" || exit 1
t0=$(date +%s)

# ---------------------------------------------------------------- file list
if [ "$mode" = all ]; then
    find "$root" -name '*.nc' | sort > "$outdir/files.txt"
else
    find "$root" -mindepth 3 -maxdepth 3 -type d | sort | while read -r d; do
        find "$d" -maxdepth 1 -name '*.nc' | sort | sed -n '1p;$p'
    done | sort -u > "$outdir/files.txt"
fi
ntotal=$(wc -l < "$outdir/files.txt")
echo "Mode: $mode   Files: $ntotal   Parallel: $nproc"

# ---------------------------------------------------------------- checks
check_one() {
    local f=$1 rel rep start rc
    rel=${f#"$root"/}
    rep=$outdir/reports/${rel%.nc}.txt
    grep -q '^#END' "$rep" 2>/dev/null && return 0     # done in an earlier job
    mkdir -p "$(dirname "$rep")"
    start=$(date +%s)
    compliance-checker -t wcrp_cordex_cmip6:1.0 "$f" > "$rep" 2>&1
    rc=$?
    echo "#END exit=$rc time=$(( $(date +%s) - start ))" >> "$rep"
}
export -f check_one
export root outdir

xargs -a "$outdir/files.txt" -d '\n' -P "$nproc" -n 1 bash -c 'check_one "$1"' _
echo "Checks finished in $(( ($(date +%s) - t0) / 60 )) min"

# ---------------------------------------------------------------- summary
NPROC_USED=$nproc python3 "${SLURM_SUBMIT_DIR:-$PWD}/summarise_checks.py" "$outdir" "$root" "$mode"
echo
echo "Results in: $outdir   (summary.txt is the file to share)"
