#!/bin/bash

SVC=home-assistant
IMG=homeassistant/home-assistant:stable
MNT=/config
NET_MODE=host

. `dirname $0`/common.sh

handle_cmd "$@"
