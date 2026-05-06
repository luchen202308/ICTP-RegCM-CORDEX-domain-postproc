#!/bin/bash

#
source /leonardo/home/userexternal/ggiulian/modules_new

#
dir0=/leonardo_work/ICT25_ESP/OBS/CPC/precip
dir1=/leonardo_work/ICT25_ESP/clu/OBS/CPC/precip

{
set -eo pipefail
CDO(){
  cdo -O -L -f nc4 -z zip $@
}

sf=$dir1/precip.cpc.1979.2024.nc
ff=$( eval ls $dir0/precip.????.nc )
[[ ! -f $sf ]] && CDO mergetime $ff $sf

}
