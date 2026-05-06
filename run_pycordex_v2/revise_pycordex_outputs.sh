#!/bin/bash

source /leonardo/home/userexternal/ggiulian/modules_new

#for file in find $1 -name *r0i0p0f0*nc
#do
#  ncatted -h -a driving_variant_label,global,m,c,'r1i1p1f1' $file
#  mkdir -p dirname $file | sed -e 's/r0i0p0f0/r1i1p1f1/'
#  mv $file echo $file | sed -e 's/r0i0p0f0/r1i1p1f1/g'
#done

#dir0="/leonardo_scratch/large/userexternal/clu00000/CORDEX/CORDEX-CMIP6"
#files=$( eval find $dir0 -name *r0i0p0f0*nc )
#for file in $files; do
#	echo $file
#	ncatted -h -a driving_variant_label,global,m,c,'r1i1p1f1' $file
#done

dir0="/leonardo_scratch/large/userexternal/clu00000/CORDEX/CORDEX-CMIP6"
files=$( eval find $dir0 -name *r0i0p0f0*nc )
for file in $files; do
	echo $file
	dir1=$(dirname $file)
	dir2=$( echo $dir1 | sed -e 's/r0i0p0f0/r1i1p1f1/' )
	mkdir -p $dir2
	fo=$( echo $file | sed -e 's/r0i0p0f0/r1i1p1f1/g' )
	mv $file $fo
done
