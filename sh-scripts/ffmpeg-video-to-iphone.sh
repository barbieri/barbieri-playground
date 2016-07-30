#!/bin/bash

LOGFILE=`mktemp`

OVERWRITE=${OVERWRITE:-0}
ABITRATE=${ABITRATE:-128k}
VBITRATE=${VBITRATE:-512k}
ACODEC=${ACODEC:-libfaac}
TARGET_WIDTH=${TARGET_WIDTH:-480}
TARGET_HEIGHT=${TARGET_HEIGHT:-320}
LOGLEVEL=${LOGLEVEL:-quiet}
OUTDIR=${OUTDIR:-.}


FFMPEG_OPTS="-loglevel ${LOGLEVEL}"

# from http://h264.code-shop.com/trac/wiki/Encoding
ENCODE_OPTS="-vcodec libx264 -r 30000/1001 -b ${VBITRATE} \
           -flags +loop+mv4 -cmp 256 \
	   -partitions +parti4x4+parti8x8+partp4x4+partp8x8+partb8x8 \
	   -me_method hex -subq 7 -trellis 1 -refs 5 -bf 0 \
	   -flags2 +mixed_refs -coder 0 -me_range 16 \
           -g 250 -keyint_min 25 -sc_threshold 40 -i_qfactor 0.71 -qmin 10 \
	   -qmax 51 -qdiff 4"


if [ $# -lt 1 ]; then
    cat <<EOF
Convert videos to be used by iPhone (MP4 480x320)

Usage:

    $0 <video1> ... <videoN>

Environment Variables:

    OVERWRITE=1|0         force overriding files
    ABITRATE=128k         choose ffmpeg's -ab parameter value.
    VBITRATE=512k         choose ffmpeg's -b parameter value.
    ACODEC=libfaac        choose ffmpeg's -acodec parameter value.
    TARGET_WIDTH=480      output target width
    TARGET_HEIGHT=320     output target height
    LOGLEVEL=quiet        choose ffmpeg's -loglevel parameter value.
    OUTDIR=.              directory where to save movies.

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

TARGET_ASPECT=$((TARGET_WIDTH * 1000 / TARGET_HEIGHT))

CPUCOUNT=`ls -1d /sys/class/cpuid/cpu* 2>/dev/null | wc -l`
[ -z "$CPUCOUNT" ] && CPUCOUNT=`grep '^processor' /proc/cpuinfo | wc -l`
[ -n "$CPUCOUNT" ] && FFMPEG_OPTS+=" -threads $CPUCOUNT"

echo "INFO: Using bitrates: audio(-ab)=$ABITRATE, video(-b)=$VBITRATE"
echo "INFO: Output video size: ${TARGET_WIDTH}x${TARGET_HEIGHT} (aspect=${TARGET_ASPECT}/1000)"
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

    unset ORIG_WIDTH ORIG_HEIGHT
    eval `ffmpeg -i "$inf" 2>&1 | grep 'Video: .* [0-9]\+x[0-9]\+' | head -n1 | sed 's/^.* \([0-9]\+\)x\([0-9]\+\),\? .*$/ORIG_WIDTH=\1;ORIG_HEIGHT=\2/g'`

    ORIG_ASPECT=$((ORIG_WIDTH * 1000 / ORIG_HEIGHT))
    if [ $ORIG_ASPECT -gt $TARGET_ASPECT ]; then
        WIDTH=$TARGET_WIDTH
        HEIGHT=$((TARGET_WIDTH * 1000 / ORIG_ASPECT))
    else
        WIDTH=$((TARGET_HEIGHT * ORIG_ASPECT / 1000))
        HEIGHT=$TARGET_HEIGHT
    fi

    PAD_LEFT=$(( (TARGET_WIDTH - WIDTH) / 2 ))
    PAD_RIGHT=$((TARGET_WIDTH - WIDTH - PAD_LEFT))

    PAD_TOP=$(( (TARGET_HEIGHT - HEIGHT) / 2 ))
    PAD_BOTTOM=$((TARGET_HEIGHT - HEIGHT - PAD_TOP))

    echo "Converting: '$inf' to '$outf' (${WIDTH}x${HEIGHT} +$PAD_LEFT+$PAD_TOP -$PAD_RIGHT-$PAD_BOTTOM)" | tee -a "$LOGFILE"

    OUTPUT_OPTS="-padtop $PAD_TOP -padbottom $PAD_BOTTOM \
        -padleft $PAD_LEFT -padright $PAD_RIGHT \
        -s ${WIDTH}x${HEIGHT} -aspect ${TARGET_ASPECT}:1000"

    echo "    Pass1 (no audio)"
    echo ffmpeg $FFMPEG_OPTS -i "$inf" -an -pass 1 $ENCODE_OPTS $OUTPUT_OPTS "$outf" >>"$LOGFILE"
    ffmpeg $FFMPEG_OPTS -i "$inf" -an -pass 1 $ENCODE_OPTS $OUTPUT_OPTS "$outf" >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems converting (pass1) '$inf' to '$outf', see '$LOGFILE'" | \
            tee -a "$LOGFILE"
        continue
    fi

    echo "    Pass2"
    echo ffmpeg $FFMPEG_OPTS -i "$inf" -acodec $ACODEC -ab $ABITRATE -pass 2 $ENCODE_OPTS $OUTPUT_OPTS "$outf" >>"$LOGFILE"
    ffmpeg $FFMPEG_OPTS -y -i "$inf" -acodec $ACODEC -ab $ABITRATE -pass 2 $ENCODE_OPTS $OUTPUT_OPTS "$outf" >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems converting (pass2) '$inf' to '$outf', see '$LOGFILE'" | \
            tee -a "$LOGFILE"
        continue
    fi
done
