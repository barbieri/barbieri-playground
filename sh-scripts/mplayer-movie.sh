#!/bin/sh

# Environment Variables:
#  W=<INT>        screen width, empty to auto-discover using maximum of xrandr
#  H=<INT>        screen width, empty to auto-discover using maximum of xrandr
#  NO_PP=<BOOL>   do not use post processing filters to enhance quality
#  SWS=<BOOL>     use software scaler (slower but may look better)
#  SWS_METH=<INT> -sws parameter
#  VF=<STRING>    user video filter options

SWS_METH=${SWS_METH:-9} # lanczos

if test -z "$W" -o -z "$H"; then
    LVDS_W=0
    LVDS_H=0
    VGA_W=0
    VGA_H=0

    MAX_W=0
    MAX_H=0

    for cfg in `xrandr -q | grep '\(VGA\|LVDS\)[0-9]* connected \([^x]\+\)x\([^+]\+\).*' | sed 's/\(VGA\|LVDS\)[0-9]* connected \([^x]\+\)x\([^+]\+\).*/\1:\2:\3/g'`; do
        t=`echo $cfg | cut -d: -f1`
        w=`echo $cfg | cut -d: -f2`
        h=`echo $cfg | cut -d: -f3`
        case $t in
            VGA)
                if test $VGA_W -lt $w; then
                    VGA_W=$w
                fi
                if test $VGA_H -lt $h; then
                    VGA_H=$h
                fi
                ;;
            LVDS)
                if test $LVDS_W -lt $w; then
                    LVDS_W=$w
                fi
                if test $LVDS_H -lt $h; then
                    LVDS_H=$h
                fi
                ;;
            *)
                echo "Unknown output $t"
                exit 1
        esac

        if test $MAX_W -lt $w; then
            MAX_W=$w
        fi
        if test $MAX_H -lt $h; then
            MAX_H=$h
        fi
    done

    echo "Detected: VGA=${VGA_W}x${VGA_H}, LVDS=${LVDS_W}x${LVDS_H}, MAX=${MAX_W}x${MAX_H}"

    if test -z "$W"; then
        W=$MAX_W
    fi
    if test -z "$H"; then
        H=$MAX_H
    fi
fi

_VF=""
add_vf() {
    if test -z "$_VF"; then
        _VF="-vf $@"
    else
        _VF="$_VF,$@"
    fi
}

if test ! -z "$SWS"; then
    add_vf "scale=$W:-3,expand=$W:$H:0:0:1"
fi

if test -z "$NO_PP"; then
    add_vf "pp=ac"
fi

if test ! -z "$VF"; then
    add_vf "$VF"
fi

exec nice -n-1 mplayer -fs -xy $W -sws $SWS_METH $_VF -utf8 "$@"
