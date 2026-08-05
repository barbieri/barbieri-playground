#!/bin/sh

infile=${1:?missing input file}
outfile=${2:-${1}-recoded.mp4}

exec ffmpeg -i ${infile} -c:v libx264 -preset slow -crf 22 ${outfile}
