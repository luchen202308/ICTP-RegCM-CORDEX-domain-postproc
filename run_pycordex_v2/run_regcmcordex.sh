#!/bin/bash

#SBATCH -N 1
#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH -p dcgp_usr_prod
#SBATCH --ntasks-per-node=108
#SBATCH -t 00:01:00

if [ $# -ne 2 ]; then
    echo "Usage: $0 <start_date_YYYYMMDD00> <end_date_YYYYMMDD00>"
    exit 1
fi

job_name="regcmcordex-ERA5_v2.sh"
this_name="run_regcmcordex.sh"

current_month="$1"
end_month="$2"

# Convert dates to comparable format (remove the 00 at the end for comparison)
current_compare="${current_month:0:8}"
end_compare="${end_month:0:8}"

echo "Starting chain from $current_month to $end_month"

# Check if we've passed the end month
if [[ "$current_compare" > "$end_compare" ]]; then
    echo "Current month ($current_month) is after end month ($end_month). Exiting."
    exit 0
fi

# Submit regcmpycordex job
echo "Submitting $job_name for $current_month"
job_id=$(sbatch --parsable $job_name "$current_month")
#job_id=$(bash --parsable $job_name "$current_month")
#job_id=$(bash $job_name "$current_month")

if [ -z "$job_id" ]; then
    echo "Failed to submit job for $current_month"
    exit 1
fi

echo "Job ID: $job_id"

# Calculate next month
year=${current_month:0:4}
month=${current_month:4:2}

# Remove leading zeros for arithmetic
month=$((10#$month))
year=$((10#$year))

# Increment month
month=$((month + 1))
if [ $month -gt 12 ]; then
    month=1
    year=$((year + 1))
fi

# Format next month
next_month=$(printf "%04d%02d0100" $year $month)

# Check if we should continue the chain
next_compare="${next_month:0:8}"
if [[ "$next_compare" -le "$end_compare" ]]; then
    echo "Scheduling next in chain: $next_month"
    sbatch --dependency=afterok:$job_id \
           --job-name="pycordex_chain_${next_month:0:6}" \
           $this_name "$next_month" "$end_month"
	#echo sbatch --dependency=afterok:$job_id --job-name="pycordex_chain_${next_month:0:6}" $this_name "$next_month" "$end_month"
    
    if [ $? -eq 0 ]; then
        echo "Chain continued successfully"
    else
        echo "Warning: Failed to submit next job in chain"
    fi
else
    echo "Chain complete. All months up to $end_month have been scheduled."
fi
