#!/bin/sh

die() {
    echo "ERROR: $*" 1>&2
    exit 1
}

dname=`dirname $0`

$dname/fetch.sh || die "failed to fetch"
$dname/extract.sh || die "failed to extract"
$dname/convert.sh || die "failed to convert"

sync tmp/mb-radares.gpx
exec du -h tmp/mb-radares.gpx
