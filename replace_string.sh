#!/bin/bash

#
#fs=$( eval ls *.sh | grep -v "replace_string.sh" )
fs=$( eval ls obs_scripts/*.sh )

#
for f in $fs; do
	echo $f
	sed -i 's/ICT24/ICT25/g' $f
done
