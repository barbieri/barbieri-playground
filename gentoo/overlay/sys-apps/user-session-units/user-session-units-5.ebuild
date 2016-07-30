# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="2"

inherit multilib systemd

DESCRIPTION="systemd unit files to support user-sessions"
HOMEPAGE="http://github.com/sofar/user-session-units"
SRC_URI="http://foo-projects.org/~sofar/${PN}/${P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 arm x86"
IUSE="enlightenment gnome kde mythtv xfce xfwm"

RDEPEND="sys-apps/systemd[pam]
	x11-base/xorg-launch-helper
	sys-apps/dbus
	enlightenment? ( x11-wm/enlightenment:0.17 )
	gnome? ( gnome-base/gnome-session )
	kde? ( kde-base/kdebase-startkde )
	mythtv? ( media-tv/mythtv )
	xfce? ( xfce-base/xfce4-session )
	xfwm? ( xfce-base/xfwm4 )"
DEPEND="${RDEPEND}
	virtual/pkgconfig"

src_configure() {
	count=0
	for f in $IUSE; do
		if use $f; then
			count=$((count + 1))
		fi
	done

	if [ $count -eq 0 ]; then
		die "Should have at least one of use flags: $IUSE"
	fi

	econf
# Todo: ./configure should accept --enable-enlightenment, --enable-gnome...
# Todo: ./configure should accept --with-systemdunitdir="$(systemd_get_unitdir)"
}

target_map() {
	echo "
enlightenment:e17
xfce:xfce4
gnome:gnome
kde:kde
xfwm:xfce4
mythtv:mythtv
" | grep "^$1:" | cut -d: -f2
}

src_install() {
	emake DESTDIR="${D}" install || die "emake install failed"
	dodoc ChangeLog AUTHORS README NEWS

	elog "To manually start an user session (UID is the user-id):"
	elog "   systemd start user-session@UID.service"
	elog
	elog "To enable auto-logon at boot time:"
	elog "   systemctl enable user-session@UID.service"
	elog

	count=0
	used=""
	for f in $IUSE; do
		if use $f; then
			count=$((count + 1))
			if [ -z "$used" ]; then
				used="$f"
			else
				used="$used $f"
			fi
		fi
	done

	if [ $count -eq 1 ]; then
		name=$(target_map $used)
		d="$(systemd_get_unitdir)/../user"
		dosym "$d/${name}.target" "$d/default.target.wants/${name}.target"
		ewarn "Automatically added ${name}.target to user/default.target.wants/"
	else
		ewarn "You should choose your user/default.target manually:"
		for f in $IUSE; do
			if use $f; then
				n=$(target_map $f)
				ewarn "   $f: $n.target"
			fi
		done
		ewarn
	fi
}
