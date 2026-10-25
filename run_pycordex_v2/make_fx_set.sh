#!/bin/bash

#SBATCH --account CMPNS_ictpclim
#SBATCH --qos=qos_lowprio
#SBATCH --job-name            fx_set
#SBATCH --mail-type           FAIL,END
#SBATCH --mail-user           clu@ictp.it
#SBATCH --nodes               1
#SBATCH --ntasks-per-node     4
#SBATCH --partition           dcgp_usr_prod
#SBATCH --time                1:00:00

# Make the complete fx set (orog, sftlf, areacella, sfturf) for one simulation.
# Usage (from the run_pycordex_v2 folder):
#   sbatch make_fx_set.sh ERA5
#   sbatch make_fx_set.sh MPIESM historical
#   sbatch make_fx_set.sh MPIESM ssp370        (same for ECEarth and NorESM)
#
# Steps:
#   1. pycordex orog, sftlf, and areacella from one SRF file of the run,
#      into a staging folder on scratch
#   2. move them to fx/<var>/<version>/, named without a time range (as SAM-12)
#   3. make sfturf with Graziano's sfturfer.py (CLM45 file + pycordexed orog)
#   4. fix lon (EAS-12 crosses 180E), then run the checker on the four files
# Old fx files are moved to <staging folder>/old_fx, never deleted.
#
# Optional overrides: VERSION=v20260815, CLM45=/path/to/EAS-12_CLM45_surface.nc
#   e.g. sbatch --export=ALL,VERSION=v20261101 make_fx_set.sh MPIESM ssp370

source /leonardo/home/userexternal/ggiulian/modules_new

run=$1
experiment=$2
here=${SLURM_SUBMIT_DIR:-$PWD}
base=/leonardo_scratch/large/userexternal/clu00000/CORDEX
work=/leonardo_work/ICT26_ESP
pycordex=/leonardo/home/userexternal/ggiulian/RegCM-CORDEX5/Tools/Scripts/pycordexer
sfturfer=$here/sfturfer.py
[ -f "$sfturfer" ] || sfturfer=/leonardo/home/userexternal/ggiulian/sfturfer.py

die() { echo "ERROR: $*"; exit 1; }

# ------------------------------------------------ simulation settings
case $run in
    ERA5)    global=ERA5;          experiment=evaluation; datadir=$base/ERA5/test3-EastAsia ;;
    MPIESM)  global=MPI-ESM1-2-HR; datadir=$base/MPIESM/MPIESM-EastAsia ;;
    ECEarth) global=EC-Earth3-Veg; datadir=$base/ECEarth/ECEarth-EastAsia ;;
    NorESM)  global=NorESM2-MM;    datadir=$base/NorESM/NorESM-EastAsia ;;
    *) die "usage: $0 ERA5 | MPIESM|ECEarth|NorESM historical|ssp370" ;;
esac
case $experiment in
    evaluation|historical|ssp370) ;;
    *) die "experiment must be historical or ssp370 for $run" ;;
esac

ginst=""
if [ "$global" = MPI-ESM1-2-HR ]; then
    [ "$experiment" = historical ] && ginst=MPI-M || ginst=DKRZ
fi

clm=${CLM45:-$(ls $base/$run/icbc/*_CLM45_surface.nc 2>/dev/null | head -1)}
[ -f "$clm" ] || die "no CLM45 surface file in $base/$run/icbc (set CLM45=...)"
[ -f "$sfturfer" ] || die "sfturfer.py not found"

# one SRF file from the right period
srf=$(ls $datadir/*_SRF.*.nc 2>/dev/null | sort | awk -F'_SRF.' -v e=$experiment '
        { y = substr($NF, 1, 4) + 0 }
        e == "evaluation" || (e == "historical" && y < 2015) || (e != "historical" && e != "evaluation" && y >= 2015) { print; exit }')
[ -n "$srf" ] || die "no SRF file for $experiment in $datadir"

simdir=$work/CORDEX-CMIP6/DD/EAS-12/ICTP/$global/$experiment/r1i1p1f1/RegCM5-0/v1-r1
stage=$base/fx_staging/${run}_${experiment}_$(date +%Y%m%d%H%M%S)
stagefx=$stage/CORDEX-CMIP6/DD/EAS-12/ICTP/$global/$experiment/r1i1p1f1/RegCM5-0/v1-r1/fx

# same version as the other variables of this simulation, if it has any
if [ -z "$VERSION" ]; then
    v=$(find "$simdir" -mindepth 3 -maxdepth 3 -type d -name 'v[0-9]*' ! -path "$simdir/fx/*" 2>/dev/null | head -1)
    VERSION=${v:+$(basename "$v")}
    VERSION=${VERSION:-v$(date +%Y%m%d)}
fi

echo "Simulation: $global $experiment (institution: ${ginst:-set by pycordex})"
echo "SRF file:   $srf"
echo "CLM45 file: $clm"
echo "Target:     $simdir/fx/<var>/$VERSION"
echo "Staging:    $stage"
echo

# ------------------------------------------------ 1. pycordex
allargs="-m clu@ictp.it -d EAS-12 -g $global -e $experiment -b r1i1p1f1 -n None \
         -o $stage -p 3 --regcm-model-name RegCM -r 5.0 --regcm-version-id v1-r1"
[ -n "$ginst" ] && allargs="$allargs -G $ginst"
mkdir -p "$stage" || die "cannot create $stage"
$pycordex/pycordexer.py $allargs $srf orog,sftlf,areacella || die "pycordex failed"

# ------------------------------------------------ 2. rename and move
move_old() {   # move any existing files of this fx variable out of the tree
    local var=$1
    [ -d "$simdir/fx/$var" ] || return 0
    local old
    old=$(find "$simdir/fx/$var" -name '*.nc')
    [ -z "$old" ] && return 0
    mkdir -p "$stage/old_fx/$var"
    echo "$old" | while read -r f; do
        mv "$f" "$stage/old_fx/$var/" && echo "  moved old file out: $(basename "$f")"
    done
}

for var in orog sftlf areacella; do
    src=$(find "$stagefx/$var" -name '*.nc' 2>/dev/null | head -1)
    [ -n "$src" ] || die "pycordex made no $var file"
    name=$(basename "$src" | sed -E 's/_fx_[0-9]+-[0-9]+\.nc$/_fx.nc/')
    move_old "$var"
    mkdir -p "$simdir/fx/$var/$VERSION"
    mv "$src" "$simdir/fx/$var/$VERSION/$name" || die "cannot move $var"
    echo "$var -> fx/$var/$VERSION/$name"
done

# ------------------------------------------------ 3. sfturf
orog=$(ls "$simdir/fx/orog/$VERSION"/orog_*_fx.nc)
sfname=$(basename "$orog"); sfname=sfturf_${sfname#orog_}
move_old sfturf
mkdir -p "$simdir/fx/sfturf/$VERSION"
python3 "$sfturfer" "$clm" "$orog" "$simdir/fx/sfturf/$VERSION/$sfname" || die "sfturfer.py failed"
echo "sfturf -> fx/sfturf/$VERSION/$sfname"

# ------------------------------------------------ 4. lon fix and check
echo
python3 "$here/fix_lon_360.py" --run "$simdir"/fx/{orog,sftlf,areacella,sfturf}/$VERSION
echo
echo "Required flags from the checker:"
for f in "$simdir"/fx/{orog,sftlf,areacella,sfturf}/$VERSION/*.nc; do
    req=$(compliance-checker -t wcrp_cordex_cmip6:1.0 "$f" 2>/dev/null | awk '
        { t = $0; gsub(/^[ \t]+|[ \t]+$/, "", t) }
        t == "Required" { s = 1; next }
        t == "Recommended" || t == "Suggested" || t == "Optional" { s = 0 }
        s && /^\[[A-Z]+[0-9]+\]/ { c = c (c == "" ? "" : ",") substr($1, 2, length($1) - 2) }
        END { print (c == "" ? "none" : c) }')
    printf '  %-10s %s\n' "$req" "$(basename "$f")"
done
echo "Done"
