#!/bin/bash

SVC=unifi
IMG=jacobalberty/unifi:stable
MNT=/unifi
NET_MODE=host
OPTS="-e RUNAS_UID0=false -e UNIFI_UID=$UID -e UNIFI_GID=`id -g`"

. `dirname $0`/common.sh

handle_cmd "$@"
