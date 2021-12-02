# Disconnect WiFi STA (clients) based on their signal levels

This is designed to work with openwrt's libiwinfo-lua, libuci-lua and
ubus services: network.wireless and hostapd.

On space constrained devices without standard lua modules, install:

```shell-session
  $ opkg update
  $ opkg install lua libiwinfo-lua libubus-lua luci-lib-nixio libuci-lua
```

# (Optional) Prerequisites

To improve the chances of clients roaming directly to other access points (APs) with no disconnection in between, consider the following additional steps:

1.  Allow clients to narrow down the list of available APs to scan when it is evaluating a handover to another AP by implementing this [script](https://forum.openwrt.org/t/how-does-rrm-work/32635/2) on all APs.  Note that the script will need to be customized per access point.

2.  (After step 1 is done) Enable 802.11k on each of the APs with these options under the wifi-device stanza:
```shell-session
	option ieee80211k '1'
	option rrm_neighbor_report '1'
```

3.  Anecdotal observations suggest certain Android devices may experience a severe wifi performance hit after AP roaming.  If you experience this issue, try disabling 802.11r fast roaming on your network setup.  It is worth noting that clients will stay connected while roaming even with 802.11r disabled, but data flow interruptions will take longer to recover due to clients having to perform the full 4-way handshake process to establish data link to a new AP.

# Credits

This is based on:

 * https://github.com/mk248/lede-modhostapd
 * [angry_wifi.sh](https://gist.github.com/lg/e91d1c5c9640d963e13dbb1901bb4396)

# Goals

 * lightweight (pure-lua instead of shell scripts);
 * no patches or compilation required;

# TODO

 * be notified of hostapd association requests to properly
   implement "signal_connect";

# Configuration

The configuration mimics
[lede-modhostapd](https://github.com/mk248/lede-modhostapd) (I hope
that gets merged in trunk one day, thus this script will not be
required anymore) and is per-access point at `/etc/config/wireless` for
each `config wifi-iface` entry.

Bellow are the configuration options, with their types and default
values (ie: "int:-128" says it's an integer and defaults to -128).

 * `signal_connect` (int:-128): minimum signal (dBm) to allow connection.
   128 means "allows all",
 * `signal_stay` (int:-128): minimum signal (dBm) to allow staying connected
 * `signal_snr_connect` (int:0): Signal-Noise-Ratio (SNR) to allow
   connection (SNR is defined signal - noise). If greater than
   zero, is used instead of signal_connect value.
   It's recommended to use 20 or 25 for voice communication, however
   some cards may have problems measuring noise levels and thus this
   is not set by default.
 * `signal_snr_stay` (int:0): Signal-Noise-Ratio (SNR) to allow
   staying connected (SNR is defined signal - noise). If greater
   than zero, is used instead of signal_stay value.
   It's recommended to use 20 or 25 for voice communication, however
   some cards may have problems measuring noise levels and thus this
   is not set by default.
 * `signal_poll_time` (int:10): polling interval in seconds
 * `signal_strikes` (int:3): maximum count of low signals before disconnect
 * `signal_whitelist` (string:""): comma-separated MAC Address
   prefixes to apply the algorithm. Uses the subject being the
   uppercase without the ":" separators
   (`string.upper(string.gsub(a, ":", ""))`). If provided, only
   matching STA will be considered.
 * `signal_blacklist` (string:""): comma-separators MAC Address
   prefixes to avoid applying the algorithm. Uses the subject being
   the uppercase without the ":" separators
   (`string.upper(string.gsub(a, ":", ""))`). If provided, only
   non-matching STA will be considered.

## Example Configuration

Edit the `/etc/config/wireless` either manually or using `uci` and add
the `option signal_NAME 'value'` to `config wifi-device` sections.

Using Signal-Noise-Ratio (SNR is actually signal - noise) of 25 to
allow new connections and 20 to let connected devices stay. A maximum
count of 3 low-signal in a row is allowed (`signal_strikes`) and the
polling time is every 5 seconds:

```
config wifi-iface 'default_radio0'
	option device 'radio0'
	option mode 'ap'
	option network 'lan'
	option ssid 'my-wifi'
	option key 'my-passwd'
	option encryption 'psk2+ccmp'
	option signal_snr_connect '25'
	option signal_snr_stay '20'
	option signal_strikes '3'
	option signal_poll_time '5'
```

If your WiFi adapter is not good at measuring noise, then use just
signal values instead. Note that this is not as good as SNR, since the
signal may be strong however noise may be equally high and the
lots of retransmissions will take place, degrading performance:

```
config wifi-iface 'default_radio0'
	option device 'radio0'
	option mode 'ap'
	option network 'lan'
	option ssid 'my-wifi'
	option key 'my-passwd'
	option encryption 'psk2+ccmp'
	option signal_connect '-70'
	option signal_stay '-80'
	option signal_strikes '3'
	option signal_poll_time '5'
```

## Black List

Say you have a device `AA:BB:CC:DD:EE:FF` that doesn't behave properly
and every time it's disconnected, it will keep reconnecting. You can
avoid disconnecting it using
`option signal_blacklist 'add_prefix1,addr_prefix2,...`:

```
config wifi-iface 'default_radio0'
	option device 'radio0'
	option mode 'ap'
	option network 'lan'
	option ssid 'my-wifi'
	option key 'my-passwd'
	option encryption 'psk2+ccmp'
	option signal_connect '-70'
	option signal_stay '-80'
	option signal_strikes '3'
	option signal_poll_time '5'
	option signal_blacklist 'AABBCCDDEEFF'
```

The blacklist is actually a **prefix**-matching list. So if all
devices with prefix `AA:BB:CC` misbehave, then you can use that prefix
instead of manually listing every device:

```
config wifi-iface 'default_radio0'
	option device 'radio0'
	option mode 'ap'
	option network 'lan'
	option ssid 'my-wifi'
	option key 'my-passwd'
	option encryption 'psk2+ccmp'
	option signal_connect '-70'
	option signal_stay '-80'
	option signal_strikes '3'
	option signal_poll_time '5'
	option signal_blacklist 'AABBCC'
```


## White List for Apple Devices

Say you only want to disconnect Apple devices, as they are known to
roam properly, as recommended by
[angry_wifi.sh](https://gist.github.com/lg/e91d1c5c9640d963e13dbb1901bb4396). This
can be done with `option signal_whitelist 'addr_prefix1,addr_prefix2,...'`
using a list of Apple prefixes:

```
config wifi-iface 'default_radio0'
	option device 'radio0'
	option mode 'ap'
	option network 'lan'
	option ssid 'my-wifi'
	option key 'my-passwd'
	option encryption 'psk2+ccmp'
	option signal_snr_connect '25'
	option signal_snr_stay '20'
	option signal_strikes '3'
	option signal_poll_time '5'
	option signal_whitelist 'F0766F,40CBC0,4098AD,6C4D73,C48466,B8634D,503237,D4619D,B0481A,989E63,DCA904,48A195,6CAB31,7C5049,E42B34,1C36BB,3C2EFF,6C96CF,3035AD,A8BE27,70A2B3,4C57CA,68FB7E,90C1C6,A4F1E8,AC61EA,38B54D,00CDFE,18AF61,CC4463,34159E,58B035,F0B479,109ADD,40A6D9,7CF05F,A4B197,0C74C2,403004,4860BC,D02B20,9CE33F,F0989D,ACE4B5,6C72E7,60FEC5,00A040,000D93,ACBC32,30D9D9,6030D4,94BF2D,C49880,E0338E,68FEF7,BCE143,645AED,C0B658,881908,FC2A9C,44D884,EC852F,286ABA,705681,7CD1C3,F0DCE2,B065BD,A82066,BC6778,68967B,848506,54AE27,6476BA,84B153,783A84,2CBE08,24E314,68D93C,2CF0EE,84788B,6C94F8,703EAC,B4F0AB,10DDB1,04F7E4,34C059,F0D1A9,BC3BAF,786C1C,041552,38484C,701124,C86F1D,685B35,380F4A,3010E4,04DB56,881FA1,04E536,F82793,ACFDEC,D0E140,8C7C92,7831C1,F437B7,50EAD6,28E02C,60C547,7C11BE,003EE1,C01ADA,34363B,C81EE7,9CFC01,CCC760,087402,285AEB,28F076,70700D,9CF48E,FCD848,001CB3,64B9E8,B8C111,3408BC,844167,B4F61C,68AB1E,2C61F6,E49ADC,D0817A,C4618B,3451C9,E0B9BA,D023DB,B88D12,B817C2,68A86D,78A3E4,680927,60FACD,1CABA7,784F43,404D7F,7C04D0,BC9FEF,8866A5,88E87F,B853AC,2C3361,A860B6,24F094,90B0ED,C4B301,E05F45,483B38,E0C767,1C9E46,0CD746,440010,E498D6,606944,0452F3,241EEB,F431C3,64A5C3,BC926B,0050E4,003065,000A27,001451,8C7B9D,88C663,C82A14,9803D8,8C5877,0019E3,002312,002332,002436,00254B,0026BB,70F087,886B6E,4C74BF,E80688,CC08E0,5855CA,5C0947,38892C,40831D,50BC96,985AEB,2078F0,78D75F,E0ACCB,98E0D9,C0CECD,70E72C,D03311,5CADCF,006D52,48437C,34A395,9CF387,A85B78,908D6C,0C1539,BC4CC4,0CBC9F,A45E60,544E90,9CE65E,90DD5D,08F69C,D461DA,C8D083,88E9FE,88AE07,18AF8F,C8B5B7,A8BBCF,90B21F,B8E856,1499E2,B418D1,80006E,60D9C7,C8F650,1C1AC0,E06678,5C8D4E,C0F2FB,00F76F,AC87A3,542696,D8D1CB,64A3CB,44FB42,F41BA1,3CE072,E88D28,CC785F,AC3C0B,88CB87,EC3586,F0C1F1,F4F951,8CFABA,5C95AE,E0C97A,BC52B7,14109F,A4E975,C0A53E,9800C6,787B8A,3866F0,20EE28,08F4AB,8C8590,68EF43,CC2DB7,D4A33D,E4E0A6,70EF00,B0CA68,9810E8,B49CDF,DCA4CA,8C8FE9,98CA33,FC253F,183451,C0847A,64200C,74E1B6,0C771A,00F4B9,C8334B,B8F6B1,C09F42,189EFC,6C3E6D,8C2DAA,E4E4AB,58404E,DC0C5C,2C200B,609AC1,F07960,9C8BA0,28A02B,B44BD2,9C4FDA,1C5CF2,3871DE,BC5436,5CF938,4C3275,2CF0A2,ECADB8,9801A7,B48B19,E49A79,406C8F,00C610,70DEE2,182032,6CC26B,1040F3,001D4F,001E52,001F5B,001FF3,0021E9,00236C,002500,60FB42,F81EDF,90840D,D8A25E,C8BCC8,28E7CF,D89E3F,040CCE,A4D1D2,7CFADF,101C0C,001124,6C709F,0C3E9F,34E2FD,609217,8863DF,80E650,006171,90FD61,5C97F3,6C4008,24A074,F02475,20A2E4,5CF5DA,649ABE,94E96A,AC293A,10417F,B844D9,DC2B2A,14205E,5C1DD9,18F1D8,F86FC1,F099B6,907240,0C4DE9,D89695,0C3021,F0F61C,B03495,848E0C,949426,E0F5C6,28E14C,54E43A,C8E0EB,A88808,444C0C,84FCFE,E48B7F,5C969D,A8FAD8,7014A6,A8667F,D02598,CC29F5,DCD3A2,08E689,DC415F,30636B,F45C89,68DBCA,044BED,6C8DC1,38CADA,A4D18C,186590,64B0A6,84FCAC,6C19C0,20AB37,203CAE,748D08,A03BE3,7C6D62,40D32D,D83062,C42C03,7CC537,70CD60,C0D012,D4DCCD,484BAA,F80377,14BD61,CC25EF,B8782E,000502,0010FA,000393,0016CB,409C28,78886D,A85C2C,00DB70,0C5101,086D41,04D3CF,BCEC5D,80B03D,C83C85,A04EA7,0017F2,001B63,001EC2,002608,A4C361,AC7F3E,280B5C,90B931,24A2E1,80EA96,600308,04F13E,54724F,48746E,D4F46F,787E61,60F81D,4C7C5F,48E9F1,FCE998,F099BF,68644B,789F70,24AB81,581FAA,A46706,3C0754,E4CE8F,E8040B,B8C75D,403CFC,98FE94,D8004D,98B8E3,80929F,885395,9C04EB,A8968A,DC3714,40331A,94F6A3,D81D72,70ECE4,38C986,FCFC48,4C8D79,207D74,F4F15A,042665,2CB43A,689C70,087045,3CAB8E,7C6DF8,48D705,78FD94,C88550,286AB8,7CC3A1,3CD0F8,98D6BB,4CB199,64E682,804971,CC20E8,209BCD,F0B0E7,A056F3,549963,28FF3C,1094BB,F01898,48A91C,84A134,1C9148,C0CCF8,80ED2C,E8B2AC,8489AD,20768F,28ED6A,34AB37,60A37D,0056CD,BCA920,5082D5,9C84BF,00B362,F86214,B0702D,D0C5F3,0023DF,0025BC,00264A,0026B0,041E64,D49A20,9027E4,60334B,5C5948,60F445,5CF7E6,A0D795,CC088D,8C8EF2,F40F24,24F677,7867D7,5433CB,D0D2B0,D88F76,3C2EF9,7081EB,086698,9060F1,741BB2,28CFE9,E425E7,B019C6,58E28F,AC1F74,48BF6B,245BA7,DC56E7,347C25,D4909C,080007,000A95,002241,18EE69,748114,18F643,D0A637,A01828,D0034B,A43135,9C35EB,507A55,A0999B,24240E,903C92,A88E24,E8802E,68AE20,E0B52D,80BE05,D8BB2C,D04F7E,2C1F23,549F13,B8098A,F0DBE2,8C2937,DC9B9C,98F0AB,F0DBF8,ACCF5C,3C15C2,04489A,D8CF9C,A886DD,54EAA8,E4C63D,843835,C06394,8C006D,B09FBA,DC86D8,78CA39,18E7F4,B8FF61,DC2B61,1093E9,442A60,E0F847,145A05,28CFDA,148FC6,283737,045453,F0CBA1,30F7C5,008865,40B395,3090AB,1CE62B,A0EDCD,842999,74E2F5,20C9D0,7073CB,9C207B,341298,9C293F,7C0191,70480F,A4B805,587F57,80D605,C869CD,BC6C21,0469F8,749EAF,B841A4,F895EA,50A67F,647033,846878'
```

This list can be created using
[IEEE registry for Apple](https://services13.ieee.org/RST/standards-ra-web/rest/assignments/download/?registry=MAC&text=apple),
a Comma-Separated-Values (CSV) file which can be processed as below:

Download using cURL or wget:

```shell-session
 $ curl 'https://services13.ieee.org/RST/standards-ra-web/rest/assignments/download/?registry=MAC&text=apple' -o MAC.CSV
 $ # or
 $ wget 'https://services13.ieee.org/RST/standards-ra-web/rest/assignments/download/?registry=MAC&text=apple' -O MAC.CSV
```

Convert the CSV to Prefix List:

```shell-session
 $ cut -d, -f2 MAC.CSV | grep -v 'Assignment' | tr '\n' ','
```

# Running

Once `/etc/config/wireless` contains enabled `wifi-iface` entries,
then just execute the lua script:

```shell-session
 $ lua wifi-disconnect-low-signal.lua
```

One can use `-v/--verbose` to make it log events as syslog's
`LOG_INFO` level. Use more than to make it verbose. Use `--stderr` to
also log to stderr in addition to syslog:

```shell-session
 $ lua wifi-disconnect-low-signal.lua -v             # info
 $ lua wifi-disconnect-low-signal.lua -v -v          # debug
 $ lua wifi-disconnect-low-signal.lua -v -v --stderr # debug and stderr
```

## Running as a OpenWRT service

Copy `wifi-disconnect-low-signal.lua` to `/usr/bin` and make it
executable, then copy `wifi-disconnect-low-signal` to `/etc/init.d`:

```shell-session
desktop$ export GW=root@gw.home.lan
desktop$ scp ./wifi-disconnect-low-signal.lua $GW:/usr/bin/
desktop$ scp ./wifi-disconnect-low-signal     $GW:/etc/init.d/
desktop$ ssh $GW

openwrt$ opkg update
openwrt$ opkg install lua libiwinfo-lua libubus-lua luci-lib-nixio libuci-lua

openwrt$ chmod +x /usr/bin/wifi-disconnect-low-signal.lua
openwrt$ chmod +x /etc/init.d/wifi-disconnect-low-signal
openwrt$ /etc/init.d/wifi-disconnect-low-signal enable
openwrt$ /etc/init.d/wifi-disconnect-low-signal start
```
