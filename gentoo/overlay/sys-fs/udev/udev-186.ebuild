# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo-x86/virtual/emacs/emacs-23.ebuild,v 1.31 2012/06/01 17:21:19 ulm Exp $

EAPI=4

DESCRIPTION="empty udev that systemd depends on"
HOMEPAGE="http://www.freedesktop.org/wiki/Software/systemd"
SRC_URI=""

LICENSE=""
SLOT="0"
KEYWORDS="~amd64 ~arm ~hppa ~mips ~ppc ~ppc64 ~x86"
IUSE="build selinux debug +rule_generator hwdb gudev introspection keymap floppy doc static-libs +openrc"

DEPEND=""
RDEPEND="hwdb? ( sys-apps/hwids )
	openrc? ( >=sys-fs/udev-init-scripts-10
		!<sys-apps/openrc-0.9.9 )
	!sys-apps/coldplug
	!<sys-fs/lvm2-2.02.45
	!sys-fs/device-mapper
	!<sys-fs/udev-init-scripts-10
	!<sys-kernel/dracut-017-r1
	!<sys-kernel/genkernel-3.4.25"

