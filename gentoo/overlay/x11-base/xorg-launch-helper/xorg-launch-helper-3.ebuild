# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="2"

inherit multilib systemd

DESCRIPTION=""
HOMEPAGE="http://github.com/sofar/user-session-units"
SRC_URI="http://foo-projects.org/~sofar/${PN}/${P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64 arm x86"
IUSE=""

RDEPEND=""
DEPEND="${RDEPEND}
	virtual/pkgconfig"

src_configure() {
	econf \
		--with-systemdunitdir="$(systemd_get_unitdir)"
}

src_install() {
	emake DESTDIR="${D}" install || die "emake install failed"
	dodoc ChangeLog AUTHORS README NEWS
}
