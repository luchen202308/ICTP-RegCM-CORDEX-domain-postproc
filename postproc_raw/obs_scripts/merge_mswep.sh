#!/bin/bash

#
source /leonardo/home/userexternal/ggiulian/modules_new

#
dir0=/leonardo_work/ICT25_ESP/OBS/MSWEP/monthly
dir1=/leonardo_work/ICT25_ESP/clu/OBS/MSWEP/monthly

{
set -eo pipefail
CDO(){
  cdo -O -L -f nc4 -z zip $@
}

sf=$dir1/mswep.mon.1979-2020.nc
ff=$( eval ls $dir0/??????.nc )
[[ ! -f $sf ]] && CDO mergetime $ff $sf

}
