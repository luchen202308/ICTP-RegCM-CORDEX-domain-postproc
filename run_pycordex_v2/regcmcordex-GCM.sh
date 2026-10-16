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

# pycordex for one month of a GCM-driven EAS-12 run.
# Usage:
#   sbatch regcmcordex-GCM.sh <YYYYMM0100> <gcm>
#   gcm: MPIESM, ECEarth, or NorESM (folder names; full model names also work)
# Example:
#   sbatch regcmcordex-GCM.sh 1970010100 MPIESM
# The experiment follows from the date: before 2015 historical, from 2015 ssp370.
# Normally submitted by run_regcmcordex_GCM.sh.

source /leonardo/home/userexternal/ggiulian/modules_new

if [ $# -ne 2 ]; then
    echo "Usage: $0 <YYYYMM0100> <gcm: MPIESM | ECEarth | NorESM>"
    exit 1
fi
idate=$1

# ------------------------------------------------ run and driving model
base=/leonardo_scratch/large/userexternal/clu00000/CORDEX
case $2 in
    MPIESM|MPI-ESM1-2-HR) run=MPIESM;  global=MPI-ESM1-2-HR ;;
    ECEarth|EC-Earth3-Veg) run=ECEarth; global=EC-Earth3-Veg ;;
    NorESM|NorESM2-MM)    run=NorESM;  global=NorESM2-MM ;;
    *) echo "Unknown gcm: $2 (use MPIESM, ECEarth, or NorESM)"; exit 1 ;;
esac
datadir=$base/$run/${run}-EastAsia

# ------------------------------------------------ experiment from the date
scenario=ssp370
if [ $((10#${idate:0:4})) -lt 2015 ]; then
    experiment=historical
else
    experiment=$scenario
fi

# ------------------------------------------------ driving institution
# MPI-ESM1-2-HR was run by different institutions (Natalia's message):
# MPI-M for historical, DKRZ for the SSPs. For EC-Earth3-Veg and NorESM2-MM,
# pycordex sets the institution itself, so no -G is passed.
ginst=""
if [ "$global" = MPI-ESM1-2-HR ]; then
    [ "$experiment" = historical ] && ginst=MPI-M || ginst=DKRZ
fi

# ------------------------------------------------ settings
pycordex=/leonardo/home/userexternal/ggiulian/RegCM-CORDEX5/Tools/Scripts/pycordexer
mail=clu@ictp.it
domain=EAS-12
ensemble=r1i1p1f1
notes="None"
output="/leonardo_work/ICT26_ESP"      # pycordex adds CORDEX-CMIP6/DD/... below this
proc=20
regcm_model=RegCM
regcm_release=5.0
regcm_version_id=v1-r1

allargs="-m $mail -d $domain -g $global -e $experiment -b $ensemble \
         -n "$notes" -o $output -p $proc --regcm-model-name $regcm_model \
         -r $regcm_release --regcm-version-id $regcm_version_id"
[ -n "$ginst" ] && allargs="$allargs -G $ginst"

echo "Run:         $global $experiment $ensemble"
echo "Institution: ${ginst:-set by pycordex}"
echo "Month:       $idate"
echo "Input:       $datadir"

# ------------------------------------------------ input files
srffile=$(ls $datadir/*_SRF.${idate}*.nc 2>/dev/null)
stsfile=$(ls $datadir/*_STS.${idate}*.nc 2>/dev/null)
radfile=$(ls $datadir/*_RAD.${idate}*.nc 2>/dev/null)
atmfile=$(ls $datadir/*_ATM.${idate}*.nc 2>/dev/null)
for t in srffile stsfile radfile atmfile; do
    if [ -z "${!t}" ]; then
        echo "ERROR: no ${t%file} file for $idate in $datadir"
        exit 1
    fi
done

srfvars=tas,pr,evspsbl,huss,hurs,ps,psl,sfcWind,uas,vas,clt,rsds,rlds
srfvars=$srfvars,ts,prc,prhmax,prsn,tauu,tauv,zmla,prw,rsus,rlus,hfss,hfls
srfvars=$srfvars,ua50m,ua100m,ua150m,va50m,va100m,va150m,ta50m,hus50m
srfvars=$srfvars,mrros,mrro,cape,cin,li,evspsblpot,z0,hfso,snw,snm
stsvars=prmean,psmean,tasmean,tasmax,tasmin,sfcWindmax,sundmean,wsgsmax
radvars=clwvi,clivi,rlut,rsut,rsdt,clh,clm,cll
atmvars=ua,va,ta,hus,zg,wa,mrsol,mrso,tsl

pids=""
$pycordex/pycordexer.py $allargs $srffile $srfvars & pids+="$! "
$pycordex/pycordexer.py $allargs $radfile $radvars & pids+="$! "
$pycordex/pycordexer.py $allargs $stsfile $stsvars & pids+="$! "
$pycordex/pycordexer.py $allargs $atmfile $atmvars & pids+="$! "

err=""
for p in $pids; do wait $p || err=$?; done
[[ $err ]] && exit 1

echo "Done"
