#!/bin/bash

#SBATCH -A ICT23_ESP_1
#SBATCH -p dcgp_usr_prod
#SBATCH -N 1
#SBATCH -t 0:30:00
#SBATCH --ntasks-per-node=112
#SBATCH --mail-type=FAIL

# module purge
source /leonardo/home/userexternal/ggiulian/modules_new

##############################
### change inputs manually ###
##############################

n=$1       # domain name, e.g. EastAsia
rdir=$2    # path to RegCM output, e.g. /leonardo_work/ICT25_ESP/clu/CORDEX/ERA5
conf=$3    # config name, e.g. ERA5
fyr=$4     # first year of the full period, e.g. 1970
lyr=$5     # last  year of the full period, e.g. 2005

##############################
####### end of inputs ########
##############################

{

set -eo pipefail

CDO(){
    cdo -O -L -f nc4 -z zip $@
}

export hdir=$rdir/$conf-$n

if [ ! -d $hdir ]; then
    echo 'Path does not exist: '$hdir
    exit -1
fi

pdir=$hdir/yearly

if [ ! -d $pdir ]; then
    echo 'Yearly directory does not exist: '$pdir
    exit -1
fi

vars="tas tasmax tasmin pr"
periods="ANN DJF MAM JJA SON"

for v in $vars; do
    for p in $periods; do

        # Collect all chunk files for this variable and period, sorted by name
        # (chronological because the year-range string is part of the filename)
        set +e
        chunks=$( ls $pdir/${v}_RegCM_*_${p}_yearly.nc 2>/dev/null | sort )
        set -e

        if [ -z "$chunks" ]; then
            echo "WARNING: No files found for ${v} ${p}. Skipping."
            continue
        fi

        nchunks=$( echo $chunks | wc -w )
        echo "#### merging ${v} ${p}: $nchunks chunk(s) ####"

        of=$pdir/${v}_RegCM_${fyr}-${lyr}_${p}_yearly.nc

        # Check none of the input chunks is the target output file itself
        # (guards against re-running on an already-merged period)
        safe_chunks=""
        for c in $chunks; do
            if [ "$c" != "$of" ]; then
                safe_chunks="$safe_chunks $c"
            fi
        done

        if [ -z "$safe_chunks" ]; then
            echo "  Only output file present, nothing to merge. Skipping."
            continue
        fi

        CDO mergetime $safe_chunks $of
        echo "  -> $of"

    done
done

echo "#### merge complete! ####"

}
