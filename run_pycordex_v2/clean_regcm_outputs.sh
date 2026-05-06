#!/bin/bash

#source /leonardo/home/userexternal/ggiulian/modules_gfortran
source /leonardo/home/userexternal/ggiulian/modules_new

#datadir=/leonardo_work/ICT25_ESP/nzazulie/SAM-12/ERA5/NoTo-SouthAmerica
#datadir=/leonardo_work/ICT25_ESP/clu/CORDEX/ERA5/test3-EastAsia
datadir=/leonardo_scratch/large/userexternal/clu00000/CORDEX/ERA5/test3-EastAsia

#idate=1970040100

yr=1970

for i in `seq 1 12`; do
	idate=${yr}$(printf '%0.2d' $i)
	echo "#---- processing $idate ----#"
	#
	srffile=$datadir/*_SRF.${idate}*.nc
	stsfile=$datadir/*_STS.${idate}*.nc
	radfile=$datadir/*_RAD.${idate}*.nc
	atmfile=$datadir/*_ATM.${idate}*.nc
	#
	savfile=$datadir/*_SAV.${idate}*.nc
	h0file=$datadir/*.clm.regcm.h0.${idate}*.nc
	h1file=$datadir/*clm.regcm.h1.${idate}*.nc
	rfile=$datadir/*clm.regcm.r.${idate}*.nc
	rh0file=$datadir/*clm.regcm.rh0.${idate}*.nc
	rh1file=$datadir/*clm.regcm.rh1.${idate}*.nc
	#txtfile=$datadir/*.${idate}*.txt
	#
	echo removing $srffile
	echo removing $stsfile
	echo removing $radfile
	echo removing $atmfile
	#rm $srffile $radfile $stsfile $atmfile
	#
	if [ $i -ne 6 -a $i -ne 12 ]; then
		if ls $savfile 1> /dev/null 2>&1; then
			echo removing $savfile
			#rm $savfile
		fi
		if ls $h0file 1> /dev/null 2>&1; then
			echo removing $h0file
			#rm $h0file
		fi
		if ls $h1file 1> /dev/null 2>&1; then
			echo removing $h1file
			#rm $h1file
		fi
		if ls $rfile 1> /dev/null 2>&1; then
			echo removing $rfile
			#rm $rfile
		fi
		if ls $rh0file 1> /dev/null 2>&1; then
			echo removing $rh0file
			#rm $rh0file
		fi
		if ls $rh1file 1> /dev/null 2>&1; then
			echo removing $rh1file
			#rm $rh1file
		fi
	fi
done
