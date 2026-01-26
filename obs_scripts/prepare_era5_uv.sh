#!/bin/bash

OBSDIR=/leonardo_work/ICT25_ESP/OBS
wdir=$2
cd $wdir

{
set -eo pipefail
CDO(){
  cdo -O -L -f nc4 -z zip $@
}

set -a

#
obs=ERA5
hdir=$OBSDIR/$obs/monthly
ys=$1
fyr=$( echo $ys | cut -d- -f1 )
lyr=$( echo $ys | cut -d- -f2 )

#
RED='\033[0;31m'
NC='\033[0m' # No Color

if [[ $fyr -lt 1950 || $lyr -lt 1950 || $fyr -gt 2023 || $lyr -gt 2023 ]]; then
  echo -e "${RED}Attention${NC}: $obs from 1950-01 to 2023-12, check input time range."
  exit 1 
fi

#
#vars="uwnd vwnd"
vars="uwnd"
seas="DJF MAM JJA SON"
seasdays=( 30.5 30.5 30.5 30.5 )
is=0

for v in $vars; do
  [[ $v = uwnd ]] && vc=u && vo=uwnd
  [[ $v = vwnd ]] && vc=v && vo=vwnd

	for y in `seq ${fyr} ${lyr}`; do
		ff=${v}_${y}.nc
		for month in {01..12}; do
			f0=$hdir/$y/${v}_${y}_${month}.nc
			tmp_f1=${v}_${y}_${month}_t1.nc
			tmp_f2=${v}_${y}_${month}_t2.nc
			#CDO settaxis,${y}-$month-15,00:00:00,1hour $f0 $tmp_f1
			CDO settaxis,${y}-$month-15,00:00:00,1mon $f0 $tmp_f1
			CDO setreftime,1900-01-01,00:00:00,1hour $tmp_f1 $tmp_f2
			rm $tmp_f1
		done
		[[ ! -f $ff ]] && CDO -b f32 mergetime ${v}_${y}_*_t2.nc $ff
		rm ${v}_${y}_*_t2.nc
	done

  yf=${v}_${obs}_${ys}.nc
  ff=$( eval ls ${v}_????.nc )
  CDO -b f32 mergetime $ff $yf
  rm $ff

  for s in $seas ; do
    echo "## Processing $v $ys $s"
    mf=${v}_${obs}_${ys}_${s}_mean.nc
    CDO -timmean -selseas,$s -chname,$vc,$v -selvar,$vc $yf $mf
    is=$(( is+1 ))
  done
#  rm $yf
done

echo "Done."

}
