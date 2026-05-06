#!/bin/bash

#SBATCH -A ICT23_ESP_1
#SBATCH -p dcgp_usr_prod
#SBATCH -N 1
#SBATCH -t 2:00:00
#SBATCH --ntasks-per-node=112
#SBATCH --mail-type=FAIL

# module purge
source /leonardo/home/userexternal/ggiulian/modules_new

##############################
### change inputs manually ###
##############################

n=$1       # domain name, e.g. EastAsia
path=$2-$1 # config-domain, e.g. ERA5-EastAsia
rdir=$3    # path to RegCM output, e.g. /leonardo_work/ICT25_ESP/clu/CORDEX/ERA5
odir=$4    # path to obs (unused here, kept for interface consistency with postproc.sh)
ys=$5      # year range, e.g. 1971-1975
scrdir=$6  # path to scripts directory

##############################
####### end of inputs ########
##############################

export REMAP_EXTRAPOLATE=off
export SKIP_SAME_TIME=1

{

set -eo pipefail

CDO(){
    cdo -O -L -f nc4 -z zip $@
}

fyr=$( echo $ys | cut -d- -f1 )
lyr=$( echo $ys | cut -d- -f2 )

export hdir=$rdir/$path

if [ ! -d $hdir ]; then
    echo 'Path does not exist: '$hdir
    exit -1
fi

pdir=$hdir/yearly
mkdir -p $pdir

# Variables to process
# tas/tasmax/tasmin: K -> Celsius, singleton m2 dimension dropped
# pr: kg m-2 s-1 -> mm day-1 -> mm year-1 (or mm season-1)
vars="tas tasmax tasmin pr"

for v in $vars; do

    echo "#### yearly postprocessing: $v $n $ys ####"

    typ=STS  # RegCM surface-type file tag for all four variables

    # ------------------------------------------------------------------
    # Step 1: Collect all monthly files for this variable over the full
    # year range (all 12 months), extract the variable, and merge into
    # one continuous daily time series.  selyear clips the fence-post
    # record (e.g. 1976-01-01) that RegCM writes at the end of the last
    # monthly file.
    # ------------------------------------------------------------------

    set +e
    allfiles="`eval ls $hdir/*${typ}.{${fyr}..${lyr}}[0-9][0-9]*.nc 2>/dev/null`"
    set -e

    if [ -z "$allfiles" ]; then
        echo "WARNING: No ${typ} files found for years ${fyr}-${lyr} in $hdir. Skipping $v."
        continue
    fi

    tmps=""
    for f in $allfiles; do
        ftmp=$pdir/${n}_${v}_$( basename $f | cut -d'.' -f2 )_sel.nc
        CDO selvar,$v $f $ftmp
        tmps="$tmps $ftmp"
    done

    # Merge and immediately clip to the intended year range
    tmpmerge=$pdir/${n}_${v}_${ys}_daily_merge.nc
    CDO selyear,${fyr}/${lyr} -mergetime $tmps $tmpmerge
    rm -f $tmps

    # ------------------------------------------------------------------
    # Step 2: Unit conversion
    #   pr           : kg m-2 s-1  -> mm day-1  (multiply by 86400)
    #   tas/max/min  : K           -> Celsius   (subtract 273.15)
    # For tas/tasmax/tasmin we also drop the singleton m2 level dimension
    # that RegCM includes in near-surface temperature output.
    # ncwa -a m2 averages over (and thereby removes) a degenerate dim.
    # ------------------------------------------------------------------

    tmpconv=$pdir/${n}_${v}_${ys}_daily_conv.nc

    if [ $v = pr ]; then
        coftmp=$pdir/${n}_${v}_${ys}_daily_conv_tmp.nc
        CDO mulc,86400 $tmpmerge $coftmp
        ncatted -O -a units,pr,m,c,mm/day $coftmp
        mv $coftmp $tmpconv

    elif [ $v = tas ] || [ $v = tasmax ] || [ $v = tasmin ]; then
		# NEW — chain sellevidx and subc to avoid any intermediate large file
		coftmp=$pdir/${n}_${v}_${ys}_daily_conv_tmp.nc
		CDO subc,273.15 -sellevidx,1 $tmpmerge $coftmp
		ncatted -O -a units,${v},m,c,Celsius $coftmp
		mv $coftmp $tmpconv
    fi
    rm -f $tmpmerge

    # ------------------------------------------------------------------
    # Step 3a: Annual value — one value per year (time dim = nyrs x lat x lon)
    #   tas/tasmax/tasmin : annual mean (Celsius)
    #   pr               : annual total = yearsum of daily mm/day = mm/year
    # ------------------------------------------------------------------

    of_ann=$pdir/${v}_RegCM_${ys}_ANN_yearly.nc

    if [ $v = pr ]; then
        CDO yearsum $tmpconv $of_ann
        ncatted -O -a units,pr,m,c,mm/year $of_ann
    else
        CDO yearmean $tmpconv $of_ann
    fi
    echo "  -> $of_ann"

    # ------------------------------------------------------------------
    # Step 3b: Seasonal values — one value per year per season
    #          (time dim = nyrs x lat x lon)
    #   tas/tasmax/tasmin : seasonal mean (Celsius)
    #   pr               : seasonal total = yearsum of selected months = mm/season
    #
    # Note on DJF: selmonth,12,1,2 + yearmean/yearsum groups Dec, Jan,
    # Feb of the *same* calendar year.  This is a convenient approximation
    # for trend checking (all 5 years have a complete DJF value).  For
    # strict meteorological DJF (Dec[Y-1] + Jan[Y] + Feb[Y]) use
    # "cdo seasmean/seassum" instead, noting the first season will be
    # incomplete if input starts in January.
    # ------------------------------------------------------------------

    for s in DJF MAM JJA SON; do

        [[ $s = DJF ]] && mmons="12,1,2"
        [[ $s = MAM ]] && mmons="3,4,5"
        [[ $s = JJA ]] && mmons="6,7,8"
        [[ $s = SON ]] && mmons="9,10,11"

        tmpseas=$pdir/${n}_${v}_${ys}_${s}_seas_tmp.nc
        of_seas=$pdir/${v}_RegCM_${ys}_${s}_yearly.nc

        if [ $v = pr ]; then
            CDO yearsum -selmonth,$mmons $tmpconv $tmpseas
            ncatted -O -a units,pr,m,c,mm/season $tmpseas
            mv $tmpseas $of_seas
        else
            CDO yearmean -selmonth,$mmons $tmpconv $tmpseas
            mv $tmpseas $of_seas
        fi

        echo "  -> $of_seas"

    done

    rm -f $tmpconv

done

echo "#### yearly process complete! ####"

}
