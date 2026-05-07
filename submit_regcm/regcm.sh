#!/bin/bash

#SBATCH -o logs/rcm_SLURM.out
#SBATCH -e logs/rcm_SLURM.err
#SBATCH -N 8
#SBATCH --ntasks-per-node=108
#SBATCH -t 12:00:00
#SBATCH -J CSAM-3
#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --mail-type=FAIL,END
#SBATCH --mail-user=clu@ictp.it
#SBATCH -p dcgp_usr_prod

{
set -eo pipefail

#module purge
#source /leonardo/home/userexternal/ggiulian/modules
source /leonardo/home/userexternal/ggiulian/modules_new

nl=$1
#mpirun ./bin/regcmMPICLM45 $nl
mpirun ./bin/regcmMPICLM45_cordex $nl
}
