#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            rsync
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     1
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                5:00:00

# path to pycordex outputs on leonardo_scratch
dir0="/leonardo_scratch/large/userexternal/clu00000/CORDEX/CORDEX-CMIP6/DD"

# path to pycordex folder on leonardo_work
dir1="/leonardo_work/ICT26_ESP/CORDEX-CMIP6/DD"

# rsync
rsync -av $dir0/ $dir1

# rsync, dry run
#rsync -avn $dir0/ $dir1
