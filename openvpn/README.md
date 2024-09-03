# OpenVPN + Easy RSA helpers

Based on:
- https://ubuntu.com/server/docs/how-to-install-and-use-openvpn
- https://fedoraproject.org/wiki/OpenVPN

## Easy RSA
- [docs](https://easy-rsa.readthedocs.io/)
- [downloads](https://easy-rsa.readthedocs.io/en/latest/#obtaining-and-using-easy-rsa)
  - Fedora: `dnf install easy-rsa`
  - Ubuntu: `apt install easy-rsa`
  - macOS: `brew install easy-rsa`

### Setup PKI

🔐 Do the following in a **secure** environment as the `~/easy-rsa/pki`
will contain all private keys, including `ca.key` which will be used to
generate certificates for clients and servers. Leaking private keys,
in particular `ca.key`, is **really dangerous**.

```sh
# add the admin user to the openvpn group and use it
sudo gpasswd -a root openvpn
sudo gpasswd -a $USER openvpn
newgrp openvpn

mkdir --mode=0750 ~/easy-rsa

# easy-rsa is meant to be COPIED!
cp -a /usr/share/easy-rsa/3/* ~/easy-rsa
cd ~/easy-rsa

# init PKI and generate Certificate Authority (CA)
./easyrsa init-pki
cp pki/vars.example pki/vars
$EDITOR pki/vars  # do any required changes, ie: EASYRSA_REQ_ORG
./easyrsa build-ca

./easyrsa gen-dh  # takes a while since requires lots of entropy...

# create your server certificate and keys
./easyrsa build-server-full $SERVER_NAME

chmod g+r,o-rwx -R ~/easy-rsa
chgrp openvpn -R ~/easy-rsa
```

## OpenVPN
- [manpage (2.6.x)](https://openvpn.net/community-resources/reference-manual-for-openvpn-2-6/)
- [downloads](https://openvpn.net/community-downloads/)
  - Fedora: `dnf install openvpn`
  - Ubuntu: `apt install openvpn`
  - macOS: `brew install openvpn` or client `brew install --cask openvpn-connect`
  - iOS: [App Store](https://apps.apple.com/br/app/openvpn-connect-openvpn-app/id590379981)
  - Android: [Play Store](https://play.google.com/store/apps/details?id=net.openvpn.openvpn)

### Setup Server

```sh
curl https://github.com/barbieri/barbieri-playground/tree/master/openvpn/server.conf -o $SERVER_INSTANCE.conf
$EDITOR $SERVER_INSTANCE.conf  # do any required changes, ie: DNS, WINS...
sudo -g openvpn mkdir --mode=0750 -p /etc/openvpn/server
sudo -g openvpn mv $SERVER_INSTANCE.conf /etc/openvpn/server

cd ~/easy-rsa/pki

# copy keys matching /etc/openvpn/server/$SERVER_INSTANCE.conf
# NOTE: ideally you run easyrsa in a *DIFFERENT* machine and copy
# these files to the actual server using `scp`
sudo -g openvpn mkdir --mode=0750 -p /etc/openvpn/keys
sudo -g openvpn cp ./ca.crt             /etc/openvpn/keys/ca.crt
sudo -g openvpn cp ./dh.pem             /etc/openvpn/keys/dh.pem
sudo -g openvpn cp ./issued/server.crt  /etc/openvpn/keys/server.crt
sudo -g openvpn cp ./private/server.key /etc/openvpn/keys/server.key

# If using SELinux, restore security contexts (relabel):
sudo restorecon -Rv /etc/openvpn

# If all traffic is to be routed (push `redirect-gateway def1`):
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-ipv4-forward.conf
sudo systemctl restart systemd-sysctl.service

# Configure your firewall (WAN: outside, LAN: inside)
sudo iptables -A INPUT -i $WAN -p udp --dport 1194 -j ACCEPT
sudo iptables -A INPUT -i tun+ -j ACCEPT
sudo iptables -A FORWARD -i tun+ -j ACCEPT
sudo iptables -A FORWARD -i $WAN -o tun+ -m state --state ESTABLISHED,RELATED -j ACCEPT
if [ -n "$LAN" -a "$WAN" != "$LAN" ]; then
    sudo iptables -A FORWARD -i $LAN -o tun+ -j ACCEPT
fi

# If all traffic is to be routed (push `redirect-gateway def1`)
# we need NAT: https://tldp.org/HOWTO/html_single/Masquerading-Simple-HOWTO/
sudo iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o $WAN -j MASQUERADE

# If using systemd iptables.service:
sudo iptables-save  # saves to /etc/sysconfig/iptables

# The end: enable & start service
sudo systemctl enable openvpn-server@$SERVER_INSTANCE.service
sudo systemctl start openvpn-server@$SERVER_INSTANCE.service
```

#### Redirect All Traffic to OpenVPN

By default only local network (`10.8.0.x`) traffic will be routed to
the VPN, allowing extra traffic to go directly from the client to the
network, which is much more efficient.

To enable all traffic to be routed to the VPN one must explicitly
push `redirect-gateway` to the client as seen below. See
[documentation](https://openvpn.net/community-resources/how-to/#redirect).

```sh
# If enabled, this directive will configure
# all clients to redirect their default
# network gateway through the VPN, causing
# all IP traffic such as web browsing and
# and DNS lookups to go through the VPN
# (The OpenVPN server machine may need to NAT
# or bridge the TUN/TAP interface to the internet
# in order for this to work properly).
push "redirect-gateway def1 bypass-dhcp"
```

Where:
- `redirect-gateway [flags]` automatically execute routing commands to cause all outgoing IP traffic to be redirected over the VPN;
- `def1` flag to override the default gateway by using `0.0.0.0/1` and `128.0.0.0/1` rather than `0.0.0.0/0`. This has the benefit of overriding but not wiping out the original default gateway;
- `bypass-dhcp` flag to add a direct route to the DHCP server (if it is non-local) which bypasses the tunnel.

#### SELinux & Ports

OpenVPN is bound to port `1194` by default and if you want to run it
on a different port `$NEW_PORT` you will need to manage SELinux port
type mapping (see [man semanage-port(8)](https://man7.org/linux/man-pages/man8/semanage-port.8.html)):

```sh
sudo dnf install policycoreutils-python-utils  # install: semanage

sudo semanage port --add --type openvpn_port_t --proto udp $NEW_PORT
sudo semanage port --add --type openvpn_port_t --proto tcp $NEW_PORT

sudo semanage port --list | grep "\(openvpn\|$NEW_PORT\)"
```

## Creating Client Configuration:

The following shell will create a new client `$CLIENT_NAME` and
export it as an encrypted OpenVPN Configuration file (`.ovpn`), that
includes its certificate, private key and certificate authority all
in a single file.

> **NOTE:** the generated file will be encrypted with a symmetric
> GPG password. Be careful to distribute this file and password
> as any user with the `.ovpn` file will be authorized to connect
> to your VPN -- no other passwords or multi-factor authentication
> are needed (no TOTP, etc).

```sh
cd ~/easy-rsa

./easyrsa build-client-full $CLIENT_NAME

./create-client-config.sh $CLIENT_NAME $OPENVPN_SERVER`
```

Then send `~/easy-rsa/client-configs/$CLIENT_NAME.ovpn.gpg` to the user,
share the symmetric GPG password via a different media (off-band).

