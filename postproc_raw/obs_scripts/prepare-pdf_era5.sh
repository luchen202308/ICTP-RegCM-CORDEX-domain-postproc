#!/bin/bash

#OBSDIR=/leonardo_work/ICT25_ESP/OBS
OBSDIR=/leonardo_work/ICT25_ESP/clu/OBS
wdir=$2
cd $wdir

{
set -eo pipefail
CDO(){
  cdo -O -L -f nc4 -z zip $@
}

obs=ERA5
hdir=$OBSDIR/$obs/daily
ys=$1
fyr=$( echo $ys | cut -d- -f1 )
lyr=$( echo $ys | cut -d- -f2 )

#
RED='\033[0;31m'
NC='\033[0m' # No Color

if [[ $fyr -lt 1950 || $lyr -lt 1950 || $fyr -gt 2022 || $lyr -gt 2022 ]]; then
  echo -e "${RED}Attention${NC}: $obs from 1950-01-01 to 2022-12-31, check input time range."
  exit 1 
fi

#
vars="pr"
for v in $vars; do
  [[ $v = pr ]] && vc=tp
  sf=$hdir/pr.era5.day.1980-1985.nc
  yf=${v}_${obs}_${ys}.nc
  if [ $v = pr ]; then # m/day to mm/day
    eval CDO mulc,24000 -chname,$vc,$v -selvar,$vc -selyear,$fyr/$lyr $sf $yf
#	CDO mulc,1000 -timmean -selseas,$s -selyear,$fyr/$lyr \
#		-chname,$vc,$v -selvar,$vc $yf $mf
	ncatted -O -a units,pr,m,c,mm/day $yf
  fi
done
echo "Done."
}
