#!/bin/bash
#SBATCH --job-name=trends_EAS
#SBATCH --output=trends_%j.out
#SBATCH --error=trends_%j.err
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --account=CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH -p dcgp_usr_prod

# Annual means (step 1) and AR7 regional means (step 2) for EAS-12.
# Submit from this folder:   sbatch submit_compute.sh
# Run select_regions.py once before this (it writes regions_EAS-12.txt).
# Safe to re-submit: finished files are skipped.

set -e

cd "$SLURM_SUBMIT_DIR"

source /leonardo/home/userexternal/ggiulian/modules_gfortran

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

python3 -u compute_annual_means.py
python3 -u compute_srex_means.py
