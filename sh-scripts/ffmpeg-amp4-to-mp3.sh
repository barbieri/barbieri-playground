#!/bin/bash

LOGFILE=`mktemp`

OVERWRITE=${OVERWRITE:-0}
BITRATE=${BITRATE:-128k}
LOGLEVEL=${LOGLEVEL:-quiet}

ALBUM=""
ARTIST=""
GENRE=""
YEAR=""
TITLE=""
TRACK=""

FFMPEG_OPTS="-loglevel ${LOGLEVEL}"

if [ $# -lt 1 ]; then
    cat <<EOF
Convert musics in given *.mp4 to *.mp3

Usage:

    $0 <file1.mp4> ... <fileN.mp4>

Environment Variables:

    OVERWRITE=1|0         force overriding files
    BITRATE=128k          choose ffmpeg's -ab parameter value.
    LOGLEVEL=quiet        choose ffmpeg's -loglevel parameter value.

    ALBUM="string"        specify album name, overrides input file
    ARTIST="string"       specify artist name, overrides input file
    GENRE="string"        specify genre, overrides input file
    YEAR=1999             specify year, overrides input file
    TITLE="string"        specify title, overrides input file
    TRACK=123             specify track number, overrides input file

EOF
    exit 0
fi

if ! which ffmpeg 2>/dev/null; then
    echo "ERROR: missing ffmpeg binary in \$PATH"
    exit 1
fi

if ! which id3v2 2>/dev/null; then
    echo "ERROR: missing id3v2 binary in \$PATH"
    exit 1
fi

if [ $# -gt 1 ]; then
    if [ -n "$TITLE" ] && [ -n "$TRACK" ]; then
        echo "ERROR: it is forbidden to set the same TITLE and TRACK in multiple files"
        exit 2
    fi
fi

if [ "${OVERWRITE}" = "1" ]; then
    echo "INFO: will overwrite files that already exist"
    FFMPEG_OPTS+=" -y"
fi

echo "INFO: Using audio bitrate (-ab): $BITRATE"
echo "INFO: Logs saved to $LOGFILE"

for inf in "$@"; do
    outf=${inf/%.mp4/.mp3}

    if [ "$inf" = "$outf" ]; then
        echo "Skip '$inf': does not end in .mp4"
        continue
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
    echo ffmpeg $FFMPEG_OPTS -i "$inf" -vn -ab $BITRATE -acodec libmp3lame "$outf" >>"$LOGFILE"
    ffmpeg $FFMPEG_OPTS -i "$inf" -vn -ab $BITRATE -acodec libmp3lame "$outf" >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems converting '$inf' to '$outf', see '$LOGFILE'" | \
            tee -a "$LOGFILE"
        continue
    fi

    unset META_artist META_title META_album META_track META_date META_year META_genre META_genre_num

    eval `ffmpeg -i "$inf" 2>&1 >/dev/null |
    sed -e 's/^[\t ]*\(artist\|title\|album\|track\|date\|year\|genre\)[\t ]*:[\t ]*\(.*\)[\t ]*$/META_\1=\"\2\"/g' |
    grep -e '^META_\(artist\|title\|album\|track\|date\|year\|genre\)='`

    if [ -z "$META_year" ]; then
        META_year=`echo "$META_date" | grep '[0-9]\{4\}'`
    fi

    [ -n "$ALBUM" ] && META_album="$ALBUM"
    [ -n "$ARTIST" ] && META_artist="$ARTIST"
    [ -n "$GENRE" ] && META_genre="$GENRE"
    [ -n "$YEAR" ] && META_year="$YEAR"
    [ -n "$TITLE" ] && META_title="$TITLE"
    [ -n "$TRACK" ] && META_track="$TRACK"

    META_genre_num=""
    if [ -n "$META_genre_num" ]; then
        META_genre_num=`id3v2 -L | grep ": $META_genre\$" | cut -d: -f1`
    fi

    ID3V2_OPTS=""
    [ -n "$META_album" ] && ID3V2_OPTS+=" --album=\"$META_album\""
    [ -n "$META_artist" ] && ID3V2_OPTS+=" --artist=\"$META_artist\""
    [ -n "$META_year" ] && ID3V2_OPTS+=" --year=\"$META_year\""
    [ -n "$META_genre_num" ] && ID3V2_OPTS+=" --genre=\"$META_genre_num\""
    [ -n "$META_genre" ] && ID3V2_OPTS+=" --TCON=\"$META_genre\""
    [ -n "$META_title" ] && ID3V2_OPTS+=" --song=\"$META_title\""
    [ -n "$META_track" ] && ID3V2_OPTS+=" --track=\"$META_track\""

    echo id3v2 $ID3V2_OPTS "$outf" >>"$LOGFILE"
    eval id3v2 $ID3V2_OPTS "'$outf'" >>"$LOGFILE" 2>&1
    if [ $? -ne 0 ]; then
        echo "Problems saving id3 to '$outf', see '$LOGFILE'" | tee -a "$LOGFILE"
        continue
    fi
done
