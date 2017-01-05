#!/bin/bash

# set -xe

if [ $# -lt 1 ] || [ $1 == "-h" ] || [ $1 == "--help" ]; then
    cat <<EOF
Usage:

    $0 <output-dir> <runtime-prefix> <binary1> ... <binaryN>

Creates a runtime inside <output-dir> where everything is prefixed
with <runtime-prefix>, example:

    $0 /tmp/test-runtime /opt/bash-runtime /bin/bash

Will create /tmp/test-runtime/opt/bash-runtime/bin/bash and all binary
dependencies, such as /tmp/test-runtime/opt/bash-runtime/lib/ld-linux.so.2
and /tmp/test-runtime/opt/bash-runtime/lib/libc-2.24.so

The contents of /tmp/test-runtime can be distributed stand-alone and
mounted as "/", with libraries fixed to use the dynamic linker and
libraries from /opt/bash-runtime.

Environment Variables:

    SOURCE_DIR: directory to use as "rootfs", defaults to /

    PATCHELF: path to 'patchelf' command, defaults to one in \$PATH

    STRIP: command to strip binaries, defaults to "" (nothing)

Dependencies:

    patchelf: https://nixos.org/patchelf.html
    readlink: coreutils
    realpath: coreutils
    sed: gnu sed
    grep: gnu grep
    tar: gnu tar

EOF
    [ $# -lt 1 ] && exit 1
    exit 0
fi

OUTPUT_DIR=${1?Missing output directory}
OUTPUT_PREFIX=${2?Missing output prefix, ie: /opt/myruntime}
shift 2

COLOR_DIR=""
COLOR_LNK=""
COLOR_REG=""
COLOR_ELF=""
COLOR_SCR=""
COLOR_ERR=""
COLOR_RESET=""

if [ -t 1 ]; then
    case $TERM in
        xterm*)
            COLOR_DIR=`echo -en "\033[1;34m"`
            COLOR_LNK=`echo -en "\033[1;36m"`
            COLOR_REG=`echo -en "\033[1m"`
            COLOR_ELF=`echo -en "\033[1;32m"`
            COLOR_SCR=`echo -en "\033[1;33m"`
            COLOR_ERR=`echo -en "\033[1;31m"`
            COLOR_RESET=`echo -en "\033[0m"`
        ;;
    esac
fi

die() {
    echo "${COLOR_ERR}ERROR: $*${COLOR_RESET}" 1>&2
    exit 1
}

OUTPUT_DIR=`realpath -sm $OUTPUT_DIR`
[ -z "$OUTPUT_DIR" ] && die "Need a valid output directory."

[ $# -lt 1 ] && die "Missing binaries to isolate"

if [ -z "$SOURCE_DIR" ]; then
    SOURCE_DIR="/"
fi
[ ! -d "$SOURCE_DIR" ] && die "Missing $SOURCE_DIR"

if [ -z "$PATCHELF" ]; then
    PATCHELF=`which patchelf`
    [ -z "$PATCHELF" ] && die "Missing patchelf"
fi
[ ! -x $PATCHELF ] && die "Missing \$PATCHELF=$PATCHELF"
[ which readlink >/dev/null 2>/dev/null ] && die "Missing readlink"
[ which realpath >/dev/null 2>/dev/null ] && die "Missing realpath"

rm -fr $OUTPUT_DIR
mkdir -p $OUTPUT_DIR/$OUTPUT_PREFIX || die "mkdir -p $OUTPUT_DIR/$OUTPUT_PREFIX"

ELF_HEADER=`echo -e "\x7fELF"`

resolve_symlink() {
    sdir="$1"
    dest=`readlink $2`
    if [ ${dest#/} = ${dest} ]; then
        realpath -sm $sdir/$dest
    else
        realpath -sm $SOURCE_DIR/$dest
    fi
}

dest_symlink() {
    dest=`readlink $1`
    if [ ${dest#/} = ${dest} ]; then
        echo $dest
    else
        realpath -sm $OUTPUT_PREFIX/$dest
    fi
}

create_parent_dir() {
    local sdir="$1"
    local cdir=${sdir#$SOURCE_DIR}
    local odir=`realpath -sm $OUTPUT_DIR/$OUTPUT_PREFIX/$cdir`

    if [ -e "$odir" ]; then
        return 0
    elif [ -z "$sdir" -o "$sdir" = "$SOURCE_DIR" ]; then
        return 0
    elif [ -L "$sdir" ]; then
        local pdir=`dirname $sdir`
        local target=`resolve_symlink $pdir $sdir`
        local dest_target=`dest_symlink $sdir`
        create_parent_dir $pdir
        create_parent_dir $target
        echo "INFO: lnk ${COLOR_LNK}$odir${COLOR_RESET} $dest_target"
        ln -sn "$dest_target" "$odir" || die "could not create parent dir as symlink: $odir"
    elif [ -d "$sdir" ]; then
        create_parent_dir `dirname $sdir`
        echo "INFO: dir ${COLOR_DIR}$odir${COLOR_RESET}"
        # no mkdir -p: preserve directory permissions, user and xattr
        (cd $SOURCE_DIR && tar --no-recursion --preserve-permissions --xattrs -cf - ./$cdir 2>/dev/null) | (cd $OUTPUT_DIR/$OUTPUT_PREFIX && tar --preserve-permissions --xattrs -xf - ) || die "could not create parent directory: $odir"
        test ! -d $odir && die "failed to create directory: $odir"
        return 0
    else
        die "Unsupported parent directory type $sdir: not link or directory"
        exit 1
    fi
}

cp_with_deps() {
    local f="$1"
    local sdir=`dirname $f`
    local cdir=${sdir#$SOURCE_DIR}
    local fname=`basename $f`
    local odir=`realpath -sm $OUTPUT_DIR/$OUTPUT_PREFIX/$cdir`

    if [ -e "$odir/$fname" ]; then
        return 0
    fi

    create_parent_dir "$sdir"

    if [ -L "$f" ]; then
        local target=`resolve_symlink $sdir $f`
        local dest_target=`dest_symlink $f`
        echo "INFO: lnk ${COLOR_LNK}$odir/$fname${COLOR_RESET} $dest_target"
        ln -sn "$dest_target" "$odir/$fname" || die "ln -sn $dest_target $odir/$fname"
        cp_with_deps "$target" || exit 1
    elif [ `head $f -c 4` == "$ELF_HEADER" ]; then
        echo "INFO: elf ${COLOR_ELF}$odir/$fname${COLOR_RESET}"
        cp -an "$f" "$odir/$fname" || die "cp -an $f $odir/$fname"
        chmod u+w "$odir/$fname"
        if [ -n "$STRIP" ]; then
            $STRIP "$odir/$fname"
        fi

        local INTERPRETER=`$PATCHELF --print-interpreter $odir/$fname 2>/dev/null`
        if [ -n "$INTERPRETER" ]; then
            cp_with_deps "$SOURCE_DIR/$INTERPRETER" || exit 1
            echo "INFO: elf ${COLOR_ELF}$odir/$fname${COLOR_RESET} --set-interpreter=${COLOR_ELF}$OUTPUT_PREFIX/$INTERPRETER${COLOR_RESET}"
            $PATCHELF --set-interpreter "$OUTPUT_PREFIX/$INTERPRETER" "$odir/$fname" || die "$PATCHELF --set-interpreter $OUTPUT_PREFIX/$INTERPRETER $odir/$fname"
        fi

        $PATCHELF --remove-rpath "$odir/$fname" || die "$PATCHELF --remove-rpath $odir/$fname"
        $PATCHELF --print-needed "$f" 2>/dev/null | while read dep; do
            find \
                $SOURCE_DIR/usr/lib \
                $SOURCE_DIR/lib \
                $SOURCE_DIR/lib32 \
                $SOURCE_DIR/lib64 \
                `$PATCHELF --print-rpath $f 2>/dev/null | sed -e "s#\(^\|:\)\([^:]\+\)#${SOURCE_DIR}\2 #g"` \
                -name "$dep" 2>/dev/null | while read depfile; do
                cp_with_deps "$depfile"
                local depdir=$OUTPUT_PREFIX`dirname ${depfile#$SOURCE_DIR}`
                local rpath=`$PATCHELF --print-rpath $odir/$fname`
                if ! echo "$rpath" | grep -e "\(^\|:\)$depdir\(\$\|:\)" >/dev/null 2>/dev/null; then
                    if [ -z "$rpath" ]; then
                        rpath="$depdir"
                    else
                        rpath="$rpath:$depdir"
                    fi
                    echo "INFO: elf ${COLOR_ELF}$odir/$fname${COLOR_RESET} --set-rpath=${COLOR_ELF}$rpath${COLOR_RESET}"
                    chmod u+w "$odir/$fname"
                    $PATCHELF --set-rpath "$rpath" "$odir/$fname" || die "$PATCHELF --set-rpath $rpath $odir/$fname"
                fi
            done || die "did not find $dep"
        done
    elif [ `head $f -c 3` == "#!/" ]; then
        local INTERPRETER=`head $f -n 1 | cut -d'!' -f2 | cut -f1`
        echo "INFO: scr ${COLOR_SCR}$odir/$fname${COLOR_RESET} ${COLOR_ELF}$INTERPRETER${COLOR_RESET}"
        cp -an "$f" "$odir/$fname" || die "cp -an $f $odir/$fname"
        if [ -n "$INTERPRETER" ]; then
            cp_with_deps "$SOURCE_DIR/$INTERPRETER" || exit 1
            sed -e "s:^#!${INTERPRETER}:#!${OUTPUT_PREFIX}/${INTERPRETER}:" -i $odir/$fname || die "sed -e s:^#!${INTERPRETER}:#!${OUTPUT_PREFIX}/${INTERPRETER}: -i $odir/$fname"
        else
            echo "WARNING: could not parse #! interpreter of $odir/$fname" 1>&2
        fi
    else
        echo "INFO: reg ${COLOR_REG}$odir/$fname${COLOR_RESET}"
        cp -an "$f" "$odir/$fname" || die "cp -an $f $odir/$fname"
    fi
}

for name in "$@"; do
    echo "INFO: isolate $name from \$SOURCE_DIR=$SOURCE_DIR"
    cp_with_deps `realpath -sm "$SOURCE_DIR/$name"`
done
echo "INFO: runtime `du -hs $OUTPUT_DIR`"
