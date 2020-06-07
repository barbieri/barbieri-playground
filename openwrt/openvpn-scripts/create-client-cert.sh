#!/bin/sh

CLIENT=${1:?-missing name}

PKI_DIR="/etc/openvpn/ssl"
PKI_CNF=${PKI_DIR}/openssl.cnf

set -xe
cd $PKI_DIR

test ! -f "client-certs/${CLIENT}.key"

openssl req -batch -nodes -new -keyout "client-certs/${CLIENT}.key" -out "client-certs/${CLIENT}.csr" -subj "/CN=${CLIENT}" -config ${PKI_CNF}

openssl ca  -batch -keyfile "ca.key" -cert "ca.crt" -in "client-certs/${CLIENT}.csr" -out "client-certs/${CLIENT}.crt" -config ${PKI_CNF} -extensions client

chmod 0600 "client-certs/${CLIENT}.key"
