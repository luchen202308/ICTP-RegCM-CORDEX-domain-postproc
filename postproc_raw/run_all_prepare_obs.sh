#!/bin/bash

{
#source /leonardo/home/userexternal/ggiulian/modules_gfortran
source /leonardo/home/userexternal/ggiulian/modules_new
set -eo pipefail

if [ $# -ne 1 ]
then
   echo "Please provide period"
   echo "Example: $0 2000-2001" 
   exit 1
fi

ys=$1 

# directory to output
rdir=/leonardo_work/ICT26_ESP/clu/CORDEX/obs

###################
###################

# directory to prepare obs scripts
hdir=/leonardo_work/ICT26_ESP/clu/RegCM_scripts/postproc_raw/obs_scripts

# Processing the average
#list1="cru cpc gpcp eobs mswep era5 gpcc"
#list1="era5 gpcc"
#list1="cru eobs era5 gpcc"
#list1="cpc"
#list1="gpcp"
#list1="mswep"
#list1="gpcc"
###list1="era5_uv"
#list1=""

# Processing the pdf
#list2="cpc cru eobs gpcc"
#list2="cru eobs"
#list2="cpc"
#list2="era5"
#list2="cru"
 list2="gpcc"
#list2=""

for l in $list1; do
  echo "===== processing mean: $l ====="
  bash ${hdir}/prepare_${l}.sh $ys $rdir
done

for l in $list2; do
  echo "===== processing pdf: $l ====="
  bash ${hdir}/prepare-pdf_${l}.sh $ys $rdir
done

}
