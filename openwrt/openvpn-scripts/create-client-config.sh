#!/bin/sh

CLIENT=${1:?-missing name}
HOST=${2:?-missing host to connect}

PKI_DIR="/etc/openvpn/ssl"
CLIENT_CERTS_DIR="$PKI_DIR/client-certs"

OVPN_FILE=/etc/openvpn/client-configs/${CLIENT}.ovpn

set -e

die() {
  echo "ERROR: $*" >&2
  exit 1
}

cd $PKI_DIR
test ! -f $OVPN_FILE || die "file exists: $OVPN_FILE"
test -f $CLIENT_CERTS_DIR/$CLIENT.crt || die "missing cert:  $CLIENT_CERTS_DIR/$CLIENT.crt"

tee $OVPN_FILE >/dev/null <<EOF
  client
  dev tun
  proto udp
  fast-io
  remote ${HOST} 1194
  remote-cert-tls server
  nobind
  persist-key
  persist-tun
  verb 3

<ca>
EOF

cat $PKI_DIR/ca.crt               >> ${OVPN_FILE}
echo -e '</ca>\n<cert>'           >> ${OVPN_FILE}
cat $CLIENT_CERTS_DIR/$CLIENT.crt >> ${OVPN_FILE}
echo -e '</cert>\n<key>'          >> ${OVPN_FILE}
cat $CLIENT_CERTS_DIR/$CLIENT.key >> ${OVPN_FILE}
echo '</key>'                     >> ${OVPN_FILE}

echo ${OVPN_FILE}

