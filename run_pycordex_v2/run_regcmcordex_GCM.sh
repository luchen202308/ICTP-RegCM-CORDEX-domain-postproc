#!/bin/bash

#SBATCH -N 1
#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH -p dcgp_usr_prod
#SBATCH --ntasks-per-node=1
#SBATCH -t 00:05:00

# Chain of monthly pycordex jobs for a GCM-driven run. Each month starts
# only after the previous month finished successfully.
# Usage (from the run_pycordex_v2 folder):
#   bash run_regcmcordex_GCM.sh <start YYYYMM0100> <end YYYYMM0100> <gcm>
#   gcm: MPIESM, ECEarth, or NorESM
# Examples:
#   bash run_regcmcordex_GCM.sh 1970010100 2014120100 MPIESM   # historical
#   bash run_regcmcordex_GCM.sh 2015010100 2100120100 MPIESM   # ssp370
# A chain may also cross 2015; the experiment switches by itself.

if [ $# -ne 3 ]; then
    echo "Usage: $0 <start YYYYMM0100> <end YYYYMM0100> <gcm: MPIESM | ECEarth | NorESM>"
    exit 1
fi

job_name="regcmcordex-GCM.sh"
this_name="run_regcmcordex_GCM.sh"

current_month="$1"
end_month="$2"
gcm="$3"

case $gcm in
    MPIESM|ECEarth|NorESM) ;;
    *) echo "Unknown gcm: $gcm (use MPIESM, ECEarth, or NorESM)"; exit 1 ;;
esac

current_compare="${current_month:0:8}"
end_compare="${end_month:0:8}"

echo "Chain $gcm: $current_month to $end_month"

if [[ "$current_compare" > "$end_compare" ]]; then
    echo "Current month ($current_month) is after end month ($end_month). Exiting."
    exit 0
fi

# 1. Submit pycordex job for this month
job_id=$(sbatch --parsable --job-name="pyc_${gcm}_${current_month:0:6}" \
         $job_name "$current_month" "$gcm")
if [ -z "$job_id" ]; then
    echo "Failed to submit pycordex job for $current_month"
    exit 1
fi
echo "Pycordex job ID: $job_id"

# 2. Next month
year=$((10#${current_month:0:4}))
month=$((10#${current_month:4:2} + 1))
if [ $month -gt 12 ]; then
    month=1
    year=$((year + 1))
fi
next_month=$(printf "%04d%02d0100" $year $month)

# 3. Submit the next link, only if this month succeeds
if [[ "${next_month:0:8}" -le "$end_compare" ]]; then
    sbatch --dependency=afterok:$job_id \
           --job-name="chain_${gcm}_${next_month:0:6}" \
           $this_name "$next_month" "$end_month" "$gcm" \
        && echo "Next in chain: $next_month" \
        || echo "Warning: failed to submit next job in chain"
else
    echo "Chain complete. All months up to $end_month have been scheduled."
fi
