#!/bin/bash

SIZE=${SIZE:-128}
DEPTH=${DEPTH:-32}
DST=${DST:-./pngs}
RENAME=${RENAME:-1}

for a in $@; do
    case "$a" in
        -h|--help)
            cat <<EOF
$0 <filename1.icns> [... <filenameN.icns>]
Environment Variables:
  SIZE=<int>     size to generate icons, default=$SIZE
  DEPTH=<int>    bit depth of icon, default=$DEPTH
  DST=<folder>   where to place icons, default=$DST
  RENAME=[1|0]   if to rename icons so they do NOT have _SIZExSIZExDEPTH suffix,
                 default is to rename (RENAME=1).
EOF
            exit 1
            ;;
    esac
done

die()
{
    echo "ERROR: $*" 1>&2
    exit 1
}

mkdir -p "$DST" || die "could not create $DST"
for f in "$@"; do
    icns2png -x -d $DEPTH -s $SIZE -o "$DST/" "$f" >/dev/null || \
        die "could not create png for $f at size $SIZE, folder $DST"

    n=`basename "$f"`
    n=${n/%.icns/}
    s="$DST/${n}_${SIZE}x${SIZE}x${DEPTH}.png"
    if [ "$RENAME" = "1" ]; then
        d="$DST/${n}.png"
        mv "$s" "$d" || \
            die "could not rename \"$s\" \"$d\""

        echo "'$f' => '$d' (s:$SIZE, d:$DEPTH)"
    else
        echo "'$f' => '$s'"
    fi
done
