dbus liblogger example
======================

this example will run liblogger on various libdbus-1 headers,
providing loggers for each of them.

although types files are generated, not every type is known from it as
one header refers to others, so we just stick with dbus/dbus.h anyway.


USAGE
=====

1. Run liblogger to generate files:

        # ./run.sh

   alternatively do it just for few files:

        # PRJ_FILES="dbus-connection.h dbus-message.h" ./run.sh



2. Compile the logger module for a file:

        # make -f Makefile.dbus-connection

   alternatively you can request it to log to a file (attention to quotes!):

        # make -f Makefile.dbus-connection \
                EXTRA_CFLAGS="'-D_log_dbus_1_LOGFILE=\"/tmp/log.txt\"'"

   makefile already compiles multiple versions of the same file with
   various features like log color, timestamp, threads. All of them
   use the _log_dbus_1_ prefix as it's auto-generated from libray name
   (dbus-1). You can specify those with liblogger.py --prefix=MY_PREFIX.


3. Run some libdbus-1.so based program (d-feet):

        # LD_PRELOAD=./log-dbus-connection-color-timestamp.so d-feet


4. Check out the resulting log on the standard error our /tmp/log.txt
   if you compiled with -D_log_dbus_1_LOGFILE. Note that log files are
   always appended! For example checking the socket filedescriptor:

        # grep 'dbus_watch_get_socket.* = ' /tmp/log.txt

