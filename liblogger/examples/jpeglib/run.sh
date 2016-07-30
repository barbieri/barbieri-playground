#!/bin/bash

LIBLOGGER=`which liblogger.py 2>/dev/null`
if [ -z "$LIBLOGGER" ]; then
    LIBLOGGER="`dirname $0`/../../liblogger.py"
fi

PRJ_DIR=${PRJ_DIR:-/usr/include/}
PRJ_FILE=${PRJ_FILE:-jpeglib.h}
PRJ_LIB=${PRJ_LIB:-libjpeg.so}

fname=jpeglib

# jpeglib.h is nasty and abuses macro such as:
#     EXPORT(rettype) funcname JPP((args))
# so we must pre-process it with cpp to parse something

cpp "$PRJ_DIR/$PRJ_FILE" > cpp-$fname.h

$LIBLOGGER \
    --config jpeglib.cfg \
    --makefile Makefile \
    --types types-$fname.h \
    --custom-formatters formatters-$fname.c \
    cpp-$fname.h \
    $PRJ_LIB \
    log-$fname.c
