#!/bin/sh

user=${1:-someuser}
outfile=${2:-tmp/maparadar.zip}

token=`curl -s -f -e "http://maparadar.com/" "http://v1.api.maparadar.com/Token?usuario=${user}" | tr -d '"' `

if [ -z "$token" ]; then
    echo "ERROR: could not fetch token using user=${user}" 1>&2
    exit 1
fi

if [ ! -d `dirname ${outfile}` ]; then
    mkdir -p `dirname ${outfile}` || exit 1
fi

exec curl -f -o ${outfile} \
     -e "http://maparadar.com/" \
     "http://v1.api.maparadar.com/Exporta?token=${token}&usuario=${user}&tipoExportacao=garmin&estado=&tipoAlerta=1%2C2%2C4%2C5%2C6%2C7%2C&direcao=true&arquivosExternos=true"
