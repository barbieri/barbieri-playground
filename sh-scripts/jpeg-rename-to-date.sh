#!/bin/bash

if ! `which exiv2 2>/dev/null >/dev/null`; then
    echo "Missing exiv2 program to read EXIF information"
    exit 1
fi

usage()
{
    cat <<EOF
Usage:

    $0 <file1.jpg> ... <fileN.jpg>

Rename given input files to YYYYMMDD_HHMMSS.jpg based on EXIF data of
file. If there is no EXIF in the file, it is left untouched.

EOF
}

for F in "$@"; do
    if [ "$F" = "-h" ] || [ "$F" = "--help" ]; then
        usage
        exit 0
    fi

    exiv2 -F -r "%Y%m%d_%H%M%S" rename "$F"
done
