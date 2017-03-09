#!/bin/sh

zipfile=${1:-tmp/maparadar.zip}
outfile=${2:-tmp/garmin-radares.gpx}

if [ ! -d `dirname ${outfile}` ]; then
    mkdir -p `dirname ${outfile}` || exit 1
fi

exec unzip -p ${zipfile} maparadar/radares.gpx > ${outfile}
