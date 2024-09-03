#!/bin/bash

CLIENT=${1:?-missing client name}
HOST=${2:?-missing host to connect}
PORT=${3:-1194}

set -e

function die() {
    echo "ERROR: $*" >&2
    exit 1
}

OVPN_DIR="$PWD/client-configs"
OVPN_FILE="$OVPN_DIR/$CLIENT.ovpn"
mkdir -p "$OVPN_DIR"

PKI_DIR="$PWD/pki"
CLIENT_INLINE_FILE="$PKI_DIR/inline/$CLIENT.inline"

cd "$PKI_DIR"
test ! -f "$OVPN_FILE" || die "file exists: $OVPN_FILE"
test -f "$CLIENT_INLINE_FILE" || die "missing cert/key inline file: $CLIENT_INLINE_FILE"

cat >"$OVPN_FILE" <<EOF
client
dev tun
proto udp
fast-io
remote ${HOST} ${PORT}
remote-cert-tls server
nobind
persist-key
persist-tun
verb 3
EOF

cat "$CLIENT_INLINE_FILE" >> "$OVPN_FILE"

gpg -c "$OVPN_FILE"
rm "$OVPN_FILE"
echo "Created: $OVPN_FILE.gpg"
