#!/bin/bash

LOGFILE=`mktemp`

OVERWRITE=${OVERWRITE:-0}
ABITRATE=${ABITRATE:-128k}
PRESET=${PRESET:-normal}
ACODEC=${ACODEC:-libfaac}
LOGLEVEL=${LOGLEVEL:-quiet}
OUTDIR=${OUTDIR:-.}


FFMPEG_OPTS="-loglevel ${LOGLEVEL}"

ENCODE_OPTS="-vcodec libx264 -r 30000/1001 -vpre ${PRESET}"


if [ $# -lt 1 ]; then
    cat <<EOF
Convert videos to H.264 using FFMpeg + libx264

Usage:

    $0 <video1> ... <videoN>

Environment Variables:

    OVERWRITE=1|0         force overriding files
    ABITRATE=128k         choose ffmpeg's -ab parameter value.
    PRESET=normal         choose ffmpeg's -vpre parameter value.
    ACODEC=libfaac        choose ffmpeg's -acodec parameter value.
    LOGLEVEL=quiet        choose ffmpeg's -loglevel parameter value.
    OUTDIR=.              directory where to save movies.

Available presets: `ls -1 /usr/share/ffmpeg/libx264-*.ffpreset | sed 's/^.*libx264-\(.*\)[.]ffpreset.*$/\1, /g' | sort | tr -d '\n'`

EOF
    exit 0
fi

if ! which ffmpeg 2>/dev/null; then
    echo "ERROR: missing ffmpeg binary in \$PATH"
    exit 1
fi

if ! ffmpeg 2>&1 | grep -e "--enable-$ACODEC" >/dev/null; then
    echo "WARNING: asked for -acodec $ACODEC, but ffmpeg was not compiled with --enable-$ACODEC?"
fi

if ! ffmpeg 2>&1 | grep -e "--enable-libx264" >/dev/null; then
    echo "WARNING: asked for -vcodec libx264, but ffmpeg was not compiled with --enable-libx264?"
fi

if [ "${OVERWRITE}" = "1" ]; then
    echo "INFO: will overwrite files that already exist"
    FFMPEG_OPTS+=" -y"
fi

CPUCOUNT=`ls -1d /sys/class/cpuid/cpu* 2>/dev/null | wc -l`
[ -z "$CPUCOUNT" ] && CPUCOUNT=`grep '^processor' /proc/cpuinfo | wc -l`
[ -n "$CPUCOUNT" ] && FFMPEG_OPTS+=" -threads $CPUCOUNT"

echo "INFO: Using bitrates: audio(-ab)=$ABITRATE, video(-b)=$VBITRATE"
echo "INFO: Logs saved to $LOGFILE"

for inf in "$@"; do
    outf="${OUTDIR}/`echo $inf | sed 's/[.][^.]\+$//g'`.mp4"
    if [ "$outf" = "./$inf" ]; then
        outf="${OUTDIR}/${inf}-iphone.mp4"
    fi

    if [ -f "$outf" ]; then
        if [ "${OVERWRITE}" = "1" ]; then
            echo "WARNING: overriding '$outf' as requested by envvar"
        else
            echo "Skip '$inf': '$outf' already exists"
            continue
        fi
    fi

    echo "Converting: '$inf' to '$outf'" | tee -a "$LOGFILE"

    echo "    Pass1 (no audio)"
    echo ffmpeg $FFMPEG_OPTS -i "$inf" -an -pass 1 $ENCODE_OPTS "$outf" >>"$LOGFILE"
    ffmpeg $FFMPEG_OPTS -i "$inf" -an -pass 1 $ENCODE_OPTS "$outf" >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems converting (pass1) '$inf' to '$outf', see '$LOGFILE'" | \
            tee -a "$LOGFILE"
        continue
    fi

    echo "    Pass2"
    echo ffmpeg $FFMPEG_OPTS -y -i "$inf" -acodec $ACODEC -ab $ABITRATE -pass 2 $ENCODE_OPTS "$outf" >>"$LOGFILE"
    ffmpeg $FFMPEG_OPTS -y -i "$inf" -acodec $ACODEC -ab $ABITRATE -pass 2 $ENCODE_OPTS "$outf"  >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems converting (pass2) '$inf' to '$outf', see '$LOGFILE'" | \
            tee -a "$LOGFILE"
        continue
    fi
done
