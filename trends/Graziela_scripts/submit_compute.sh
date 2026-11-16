#!/bin/bash
#SBATCH --job-name=trends
#SBATCH --output=logs/trends_%j.out
#SBATCH --error=logs/trends_%j.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -A ICT26_ESP ##CMPNS_ictpclim
#SBATCH -p dcgp_usr_prod

set -e

cd /leonardo_work/ICT26_ESP/... #add your running dir 

source /leonardo/home/userexternal/ggiulian/modules_gfortran

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

#python3 -u compute_annual_means.py
python3 -u compute_srex_means.py
