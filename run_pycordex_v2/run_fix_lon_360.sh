#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            fix_lon
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     1
#SBATCH --cpus-per-task       32
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                3:00:00

# Add 360 to negative lon values in all EAS-12 files (fixes CDXV003).
# Usage (from the run_pycordex_v2 folder):
#   sbatch run_fix_lon_360.sh
# Output: fix_lon_360_<jobid>.log

source /leonardo/home/userexternal/ggiulian/modules_new

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1

python3 "$SLURM_SUBMIT_DIR/fix_lon_360.py" --run -j "$SLURM_CPUS_PER_TASK" "$root" \
    > "$SLURM_SUBMIT_DIR/fix_lon_360_${SLURM_JOB_ID}.log" 2>&1
