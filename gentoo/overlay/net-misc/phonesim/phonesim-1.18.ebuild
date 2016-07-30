# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="2"

DESCRIPTION="Phone Simulator for modem testing"
HOMEPAGE="http://ofono.org/"
SRC_URI="mirror://kernel/linux/network/ofono/${P}.tar.bz2"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 arm x86"
IUSE=""

RDEPEND="
	x11-libs/qt-core
	x11-libs/qt-dbus
	x11-libs/qt-gui
	x11-libs/qt-script"
DEPEND="${RDEPEND}
	virtual/pkgconfig"

src_install() {
	emake DESTDIR="${D}" install || die "emake install failed"
	dodoc ChangeLog AUTHORS doc/*.txt
}
