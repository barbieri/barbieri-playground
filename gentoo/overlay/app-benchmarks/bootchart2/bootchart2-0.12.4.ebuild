# Copyright 1999-2010 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="2"

inherit eutils linux-info

DESCRIPTION="Performance analysis and visualization of the system boot process"
HOMEPAGE="https://github.com/mmeeks/bootchart"
SRC_URI="https://github.com/downloads/mmeeks/bootchart/bootchart2-${PV}.tar.bz2"

LICENSE="GPL-3"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

CONFIG_CHECK="~PROC_EVENTS ~TASKSTATS ~TASK_DELAY_ACCT"

RDEPEND="dev-lang/python"
DEPEND="${RDEPEND}"

pkg_setup() {
	linux-info_pkg_setup
}

src_compile() {
	emake || die
}

src_install() {
	dodoc README README.pybootchart COPYING NEWS TODO || die

	emake DESTDIR="${D}" install || die "died running make install, $FUNCNAME"
}

pkg_postinst() {
	elog "To generate the chart, append this to your kernel commandline"
	elog "   initcall_debug printk.time=y quiet init=/sbin/bootchartd"
	elog "and reboot"
	elog "Note: genkernel users should replace init= with real_init= in the above"
	elog "see https://bugs.gentoo.org/show_bug.cgi?id=275251 for more info"
	elog
}
