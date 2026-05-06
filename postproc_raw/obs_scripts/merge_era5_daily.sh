#!/bin/bash

#
source /leonardo/home/userexternal/ggiulian/modules_new

#
dir0=/leonardo_work/ICT25_ESP/OBS/ERA5/daily
dir1=/leonardo_work/ICT25_ESP/clu/OBS/ERA5/daily

#
#fyr=1950
#lyr=2023
fyr=1980
lyr=1985

{
set -eo pipefail
CDO(){
  cdo -O -L -f nc4 -z zip $@
}

var="pr"

#
for v in $var; do
    for y in `seq ${fyr} ${lyr}`; do
        ff=$dir1/${v}_${y}.nc
        # If files are all in one directory without year subfolders
        [[ ! -f $ff ]] && CDO -b f32 mergetime $dir0/${v}_${y}_*.nc $ff
    done

    yf=$dir1/$v.era5.day.${fyr}-${lyr}.nc
    ff=$( eval ls $dir1/${v}_????.nc )
    CDO -b f32 mergetime $ff $yf

    rm $dir1/${v}_*.nc
done

}
