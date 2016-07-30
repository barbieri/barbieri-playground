# Copyright 1999-2011 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo-x86/sys-fs/udisks/udisks-1.0.2-r3.ebuild,v 1.1 2011/05/09 16:14:55 ssuominen Exp $

EAPI=4
inherit eutils bash-completion linux-info

DESCRIPTION="Daemon providing interfaces to work with storage devices"
HOMEPAGE="http://www.freedesktop.org/wiki/Software/udisks"
#SRC_URI="http://hal.freedesktop.org/releases/${P}.tar.gz"
SRC_URI="http://people.profusion.mobi/~gustavo/udisks_slim-1.0.2.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~alpha ~amd64 ~arm ~hppa ~ia64 ~ppc ~ppc64 ~sh ~sparc ~x86"
IUSE="+atasmart debug device-mapper disk-partition doc lvm nls remote-access"

COMMON_DEPEND=">=sys-fs/udev-147
	>=dev-libs/glib-2.16.1:2
	>=sys-apps/dbus-1.4.0
	>=dev-libs/dbus-glib-0.92
	>=sys-auth/polkit-0.97
        disk-partition? ( >=sys-block/parted-1.8.8[device-mapper?] )
	lvm? ( >=sys-fs/lvm2-2.02.66 )
	atasmart? ( >=dev-libs/libatasmart-0.14 )
	>=sys-apps/sg3_utils-1.27.20090411
	!sys-apps/devicekit-disks"
RDEPEND="${COMMON_DEPEND}
	virtual/eject
	remote-access? ( net-dns/avahi )"
DEPEND="${COMMON_DEPEND}
	app-text/docbook-xsl-stylesheets
	dev-libs/libxslt
	>=dev-util/intltool-0.40.0
	dev-util/pkgconfig
	doc? ( dev-util/gtk-doc
		app-text/docbook-xml-dtd:4.1.2 )"

RESTRICT="test" # this would need running dbus and sudo available

pkg_setup() {
	DOCS=( AUTHORS HACKING NEWS README )

	if use amd64 || use x86; then
		CONFIG_CHECK="~USB_SUSPEND ~!IDE"
		linux-info_pkg_setup
	fi
}

src_configure() {
	econf \
		--localstatedir="${EPREFIX}"/var \
		--disable-static \
		$(use_enable debug verbose-mode) \
		--enable-man-pages \
                $(use_enable atasmart libatasmart) \
                $(use_enable device-mapper devmapper) \
                $(use_enable disk-partition parted) \
		$(use_enable doc gtk-doc) \
                $(use_enable lvm lvm2) \
		$(use_enable remote-access) \
		$(use_enable nls) \
		--with-html-dir="${EPREFIX}"/usr/share/doc/${PF}/html
}

src_install() {
	default

	rm -f "${ED}"/etc/profile.d/udisks-bash-completion.sh
	dobashcompletion tools/udisks-bash-completion.sh ${PN}

	find "${ED}" -name '*.la' -exec rm -f {} +

	keepdir /media
}
