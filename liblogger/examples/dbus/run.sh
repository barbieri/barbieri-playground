#!/bin/bash

LIBLOGGER=`which liblogger.py 2>/dev/null`
if [ -z "$LIBLOGGER" ]; then
    LIBLOGGER="`dirname $0`/../../liblogger.py"
fi

PRJ_DIR=${PRJ_DIR:-/usr/include/dbus-1.0/dbus/}
PRJ_FILES=${PRJ_FILES:-dbus-address.h dbus-bus.h dbus-connection.h dbus-message.h dbus-pending-call.h}
PRJ_LIB=${PRJ_LIB:-libdbus-1.so}

for f in $PRJ_FILES; do
    fname=${f/%.h/}
    $LIBLOGGER \
        --config dbus.cfg \
        --makefile Makefile.$fname \
        --makefile-cflags "\`pkg-config --cflags dbus-1\` -I$PWD" \
        --types types-$fname.h \
        --custom-formatters formatters-$fname.c \
        $PRJ_DIR/$f \
        $PRJ_LIB \
        log-$fname.c
done
