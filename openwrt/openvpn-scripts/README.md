# OpenWRT + OpenVPN Scripts

These scripts will help one to manage
[OpenVPN](https://openvpn.net/community-downloads/) in an OpenWRT
router, but may be of more general use (however not tested).

## Dependencies

Install OpenVPN-OpenSSL package. Other packages such as EasyRSA are
**NOT** needed, as these scripts will manage to create the
certificates and wrap them in an OpenVPN config file.

```shell-console
# opkg install openvpn-openssl
```

## Installation

Copy the scripts to `/etc/openvpn/scripts/` and make them executable,
result should be:

```shell-console
# ls -l /etc/openvpn/scripts/
-rwxr-xr-x    1 root     root           501 Aug 23  2018 create-client-cert.sh
-rwxr-xr-x    1 root     root           887 Aug 23  2018 create-client-config.sh
```

Then make sure the destination folders exist:

```shell-console
# mkdir -p /etc/openvpn/client-configs
# mkdir -p /etc/openvpn/ssl/client-certs
```

## OpenVPN configuration

In my setup the internal network is `10.7.0.x` while the VPN is
`10.8.0.x`. The domain is OpenWRT's default `lan`. Resulting
configuration:

```shell-console
# cat /etc/config/openvpn

config openvpn 'server'
	option enabled '1'
	option port '1194'
	option proto 'udp'
	option dev 'tun'
	option ca '/etc/openvpn/ca.crt'
	option cert '/etc/openvpn/server.crt'
	option key '/etc/openvpn/server.key'
	option dh '/etc/openvpn/dh2048.pem'
	option server '10.8.0.0 255.255.255.0'
	option ifconfig_pool_persist '/tmp/ipp.txt'
	list push 'route 10.7.0.0 255.255.255.0'   # <--- NOTE SETUP
	list push 'dhcp-option DNS 10.8.0.1'       # <--- NOTE SETUP
	list push 'dhcp-option DOMAIN lan'         # <--- NOTE SETUP
	list push 'dhcp-option WINS 10.8.0.1'      # <--- NOTE SETUP
	option keepalive '10 120'
	option persist_key '1'
	option persist_tun '1'
	option status '/tmp/openvpn-status.log'
	option verb '3'
	option comp_lzo 'adaptive'
	option mlock '1'
	option passtos '1'
	option fast_io '1'

```

## OpenSSL configuration

Configure your `/etc/openvpn/ssl/openssl.cnf` similar to the
`openssl.cnf` in this folder. Highlights:

```shell-console

[ CA_default ]
# 10 years expiry, you may wish to control this
default_days	= 3650
default_crl_days= 3650			# how long before next CRL

x509_extensions	= usr_cert		# The extentions to add to the cert

[ usr_cert ]
basicConstraints=CA:FALSE
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer

[ policy_match ]
countryName	= optional
stateOrProvinceName	= optional
organizationName = optional
organizationalUnitName	= optional
commonName = supplied
emailAddress = optional

[ req ]
default_bits = 4096
default_keyfile	= privkey.pem
distinguished_name = req_distinguished_name
attributes = req_attributes
x509_extensions = v3_ca # The extentions to add to the self signed cert

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment

[ v3_ca ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer
basicConstraints = CA:true

[ crl_ext ]
authorityKeyIdentifier=keyid:always

[ server ]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[ client ]
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
```

## Usage

First, create the client certificate if one doesn't exist. You must
give it a name, that is used both in the file and the subject
`/CN=`. Avoid using some special characters, spaces and all, I often
use lowercase names separated by dashes, such as `a-name-here123`:

```shell-console
# /etc/openvpn/scripts/create-client-cert.sh a-name-here123

+ cd /etc/openvpn/ssl
+ test '!' -f client-certs/a-name-here123.key
+ openssl req -batch -nodes -new -keyout client-certs/a-name-here123.key -out client-certs/a-name-here123.csr -subj '/CN=a-name-here123' -config /etc/openvpn/ssl/openssl.cnf
Generating a 4096 bit RSA private key
writing new private key to 'client-certs/a-name-here123.key'
-----
+ openssl ca -batch -keyfile ca.key -cert ca.crt -in client-certs/a-name-here123.csr -out client-certs/a-name-here123.crt -config /etc/openvpn/ssl/openssl.cnf -extensions client
Using configuration from /etc/openvpn/ssl/openssl.cnf
Check that the request matches the signature
Signature ok
Certificate Details:
        Serial Number: 4112 (0x1010)
        Validity
            Not Before: Jun  7 15:39:29 2020 GMT
            Not After : Jun  5 15:39:29 2030 GMT
        Subject:
            commonName                = a-name-here123
        X509v3 extensions:
            X509v3 Key Usage:
                Digital Signature
            X509v3 Extended Key Usage:
                TLS Web Client Authentication
Certificate is to be certified until Jun  5 15:39:29 2030 GMT (3650 days)

Write out database with 1 new entries
Data Base Updated
+ chmod 0600 client-certs/a-name-here123.key
```

While you could use it directly, it's more convenient to send your
users the `.ovpn` which contains everything in a single file that
OpenVPN clients know how to use:

```shell-console
# /etc/openvpn/scripts/create-client-config.sh a-name-here123 your-host.com
/etc/openvpn/client-configs/a-name-here123.ovpn
```

> **NOTE:** These tools create password-less certificates and the
> resulting `.opvn` will let the user to connect to your network. Keep
> it safe!


## References

- https://openwrt.org/docs/guide-user/services/vpn/openvpn/basic
