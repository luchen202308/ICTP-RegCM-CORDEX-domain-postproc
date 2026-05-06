#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            pycordex
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     112
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                12:00:00

#source /leonardo/home/userexternal/ggiulian/modules_gfortran
source /leonardo/home/userexternal/ggiulian/modules_new

#datadir=/leonardo_work/ICT25_ESP/nzazulie/SAM-12/ERA5/NoTo-SouthAmerica
#datadir=/leonardo_work/ICT25_ESP/clu/CORDEX/ERA5/test3-EastAsia
datadir=/leonardo_scratch/large/userexternal/clu00000/CORDEX/ERA5/test3-EastAsia
#idate=$1
idate=1970010100
pycordex=/leonardo/home/userexternal/ggiulian/RegCM-CORDEX5/Tools/Scripts/pycordexer
mail=clu@ictp.it
domain=EAS-12
global=ERA5
experiment=evaluation
ensemble=r1i1p1f1
notes="None"
#output="/leonardo_work/ICT25_ESP/clu/CORDEX/"
output="/leonardo_scratch/large/userexternal/clu00000/CORDEX"
#output="."
proc=20
regcm_model=RegCM
regcm_release=5.0
regcm_version_id=v1-r1

allargs="-m $mail -d $domain -g $global -e $experiment -b $ensemble \
         -n "$notes" -o $output -p $proc --regcm-model-name $regcm_model \
         -r $regcm_release --regcm-version-id $regcm_version_id"

srffile=$datadir/*_SRF.${idate}*.nc
stsfile=$datadir/*_STS.${idate}*.nc
radfile=$datadir/*_RAD.${idate}*.nc
atmfile=$datadir/*_ATM.${idate}*.nc
#urfile=/leonardo_work/ICT26_ESP/nzazulie/SAM-12/ERA5/icbc/SAM-12_CLM45_surface.nc
urfile=/leonardo_scratch/large/userexternal/clu00000/CORDEX/ERA5/icbc/EAS-12_CLM45_surface.nc

#srfvars=tas,pr,evspsbl,huss,hurs,ps,psl,sfcWind,uas,vas,clt,rsds,rlds
#srfvars=$srfvars,ts,prc,prhmax,prsn,tauu,tauv,zmla,prw,rsus,rlus,hfss,hfls
#srfvars=$srfvars,ua50m,ua100m,ua150m,va50m,va100m,va150m,ta50m,hus50m
#srfvars=$srfvars,mrros,mrro,cape,cin,li,evspsblpot,z0,hfso,snw,snm
#stsvars=prmean,psmean,tasmean,tasmax,tasmin,sfcWindmax,sundmean,wsgsmax
##x me radvars=clwvi,clivi,rlut,rsut,rsdt,clh,clm,cll,cld
#radvars=clwvi,clivi,rlut,rsut,rsdt,clh,clm,cll
##x me atmvars=ua,va,ta,hus,zg,wa,mrsol,mrso,tsl,cli,clw
#atmvars=ua,va,ta,hus,zg,wa,mrsol,mrso,tsl
fxvars=orog,sftlf
urvars=sfturf
pids=""
#$pycordex/pycordexer.py $allargs $srffile $srfvars & pids+="$! "
#$pycordex/pycordexer.py $allargs $radfile $radvars & pids+="$! "
#$pycordex/pycordexer.py $allargs $stsfile $stsvars & pids+="$! "
#$pycordex/pycordexer.py $allargs $atmfile $atmvars & pids+="$! "
$pycordex/pycordexer.py $allargs $srffile $fxvars & pids+="$! "
$pycordex/pycordexer.py $allargs $urfile $urvars & pids+="$! "

for p in $pids; do wait $p || err=$?; done
[[ $err ]] && exit -1

#rm $srffile $radfile $stsfile $atmfile
echo "Done"

