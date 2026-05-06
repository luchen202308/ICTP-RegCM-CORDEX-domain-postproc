#!/bin/bash

ncks -h -d rlat,1,671 -d rlon,1,815 sfturf_EAS-12_ERA5_evaluation_r1i1p1f1_ICTP_RegCM5-0_v1-r1_fx_197001151200-197012151200.nc tmp.nc
ncap2 -h -O -s 'sfturf=sfturf(0,:,:)+sfturf(1,:,:)+sfturf(2,:,:)' tmp.nc sfturf_EAS-12_ERA5_evaluation_r1i1p1f1_ICTP_RegCM5-0_v1-r1_fx.nc
