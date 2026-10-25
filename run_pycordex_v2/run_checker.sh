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

source /leonardo/home/userexternal/ggiulian/modules_new

root=/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD/EAS-12/ICTP/ERA5/evaluation/r1i1p1f1/RegCM5-0/v1-r1

dir0="$root/6hr/clh/v20260815"
f0="$dir0/clh_EAS-12_ERA5_evaluation_r1i1p1f1_ICTP_RegCM5-0_v1-r1_6hr_197002010100-197003010000.nc"
#f0="$dir0/clh_EAS-12_ERA5_evaluation_r1i1p1f1_ICTP_RegCM5-0_v1-r1_6hr_197001010300-197001312100.nc"

compliance-checker -t wcrp_cordex_cmip6:1.0 $f0
