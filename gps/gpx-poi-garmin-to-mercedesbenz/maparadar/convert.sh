#!/bin/sh

infile=${1:-tmp/garmin-radares.gpx}
outfile=${2:-tmp/mb-radares.gpx}

dname=`dirname $0`/..

if [ ! -d `dirname ${outfile}` ]; then
    mkdir -p `dirname ${outfile}` || exit 1
fi

exec python $dname/gpx-poi-garmin-to-mercedesbenz.py \
     --ignore-tag link \
     --ignore-tag cmt \
     --ignore-tag desc \
     --ignore-tag sym \
     --link-to-icon 'Data/RadarF*:camera' \
     --link-to-category 'Data/RadarF*:Radar Fixo' \
     --link-to-icon 'Data/RadarM*:tripod' \
     --link-to-category 'Data/RadarM*:Radar Movel' \
     --link-to-icon 'Data/Lombada:camping' \
     --link-to-category 'Data/Lombada:Lombada' \
     --link-to-icon 'Data/Pedagio:pin' \
     --link-to-category 'Data/Pedagio:Pedagio' \
     --link-to-icon 'Data/Police:pin' \
     --link-to-category 'Data/Police:Policia' \
     --link-to-icon 'Data/Sem*:camera' \
     --link-to-category 'Data/Sem*:Semaforo' \
     ${infile} ${outfile}
