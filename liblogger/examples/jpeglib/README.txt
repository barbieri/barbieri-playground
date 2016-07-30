jpeg liblogger example
======================

this example will run liblogger on jpeglib, a nasty library that
abuses macros in his header file and hits cases liblogger cannot
handle by default.

although types files are generated, it's not used.

In this example we also use auto-generated formatter for "struct
jpeg_decompress_struct" and say "boolean" should be formatted with our
"bool" default formatter.


USAGE
=====

1. Run liblogger to generate files:

        # ./run.sh


2. Compile the logger module for a file:

        # make

   alternatively you can request it to log to a file (attention to quotes!):

        # make EXTRA_CFLAGS="'-D_log_jpeg_LOGFILE=\"/tmp/log.txt\"'"

   makefile already compiles multiple versions of the same file with
   various features like log color, timestamp, threads. All of them
   use the _log_jpeg_ prefix as it's auto-generated from libray name
   (jpeg). You can specify those with liblogger.py --prefix=MY_PREFIX.


3. Run some libjpeg.so based program (imagemagick's display):

        # LD_PRELOAD=./log-jpeg-color-timestamp.so display picture.jpg


4. Check out the resulting log on the standard error our /tmp/log.txt
   if you compiled with -D_log_jpeg_LOGFILE. Note that log files are
   always appended!

        # cat /tmp/log.txt

