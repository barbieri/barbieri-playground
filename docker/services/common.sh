
SVC=${SVC:?Missing Service Name}
IMG=${IMG:?Missing Image Name}
MNT=${MNT:?Missing Volume Mount Point}
RESTART_POLICY=${RESTART_POLICY:-unless-stopped}

DEF_OPTS=${DEF_OPTS:--v /etc/localtime:/etc/localtime:ro}
NET_MODE=${NET_MODE:-bridge}

VOL=${VOL:-$HOME/data/$SVC}
BKP=${BKP:-$HOME/backups/$SVC}

TIMESTAMP=`date +'%Y%m%d_%H%M'`
BKP_NAME="$SVC-$TIMESTAMP"
BKP_FILE="$BKP/$BKP_NAME.tar.xz"

set -e

start() {
    echo "Starting $SVC ($IMG)..."
    CID=`docker start $SVC 2>/dev/null || true`
    if [ -z "$CID" ]; then
        mkdir -p $VOL
        CID=`docker run -d --restart=$RESTART_POLICY --name=$SVC --net=$NET_MODE -v $VOL:$MNT $DEF_OPTS $OPTS $IMG`
        echo "Started $SVC as $CID"
    else
        echo "$SVC ($CID) started from existing run"
    fi
}

stop() {
    echo "Stopping $SVC..."
    CID=`docker stop $SVC || true`
    if [ -z "$CID" ]; then
        echo "$SVC was already stopped"
    else
        echo "Stopped $SVC ($CID)"
    fi
}

restart() {
    stop
    start
}

backup_internal() {
    stop
    echo "Committing Docker container as $SVC:save-$TIMESTAMP"

    docker commit -m "Backup at $TIMESTAMP" $SVC "$SVC:save-$TIMESTAMP"
    mkdir -p "$BKP"
    echo "Saving Volume $VOL as $BKP_FILE ..."
    set -xe
    docker run --rm -v $VOL:$MNT busybox sh -c \
           "tar -cf - '$MNT'" > "$BKP/$BKP_NAME.tar"
    xz -9v "$BKP/$BKP_NAME.tar"
    ls -l "$BKP_FILE"
}

backup() {
    backup_internal
    start
}

clean_backups() {
    echo "Cleaning backups for $SVC..."
    docker images --no-trunc  --filter "reference=$SVC:save-*" \
           --format '{{.Repository}}:{{.Tag}}' | sort -n | head -n -1 | \
        xargs --no-run-if-empty docker rmi
    ls -1 $BKP/$SVC-*.tar.xz | sort -n | head -n -1 | xargs --no-run-if-empty rm
}

remove() {
    backup_internal

    echo "Removing $SVC..."
    CID=`docker rm -f $SVC`
    echo "Removed $SVC ($CID)"
}


update() {
    echo "Updating $SVC from $IMG"
    docker pull $IMG

    remove
    start
}

handle_cmd() {
    if [ x"$DEBUG" = x"1" ]; then
        set -x
    fi

    CMD=${1:-start}
    shift || true
    case "$CMD" in
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        backup)
            backup
            ;;
        clean-backups)
            clean_backups
            ;;
        rm)
            remove
            ;;
        update)
            update
            ;;
        inspect)
            exec docker inspect $SVC "$@"
            ;;
        logs)
            exec docker logs $SVC "$@"
            ;;
        shell)
            CMD=${1:-sh}
            shift || true
            exec docker exec -it $SVC "$CMD" "$@"
            ;;
        *)
            echo "Unknown command $@"
    	exit 1
    esac
}
