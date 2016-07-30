# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4

inherit autotools-utils bash-completion-r1 linux-info pam systemd user

DESCRIPTION="System and service manager for Linux"
HOMEPAGE="http://www.freedesktop.org/wiki/Software/systemd"
SRC_URI="http://www.freedesktop.org/software/systemd/${P}.tar.xz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE="acl audit cryptsetup doc gudev introspection lzma pam selinux tcpd"

# automake-1.11 was having problems generating src/gudev before glib-genmarshal
AUTOTOOLS_IN_SOURCE_BUILD=1

# A little higher than upstream requires
# but I had real trouble with 2.6.37 and systemd.
MINKV="2.6.38"

# dbus version because of systemd units
# sysvinit for sulogin
RDEPEND=">=sys-fs/udev-186
	>=sys-apps/dbus-1.4.10
	>=sys-apps/kmod-5
	sys-apps/pciutils
	sys-apps/sysvinit
	sys-apps/usbutils
	>=sys-apps/util-linux-2.20
	sys-libs/libcap
	acl? ( sys-apps/acl )
	audit? ( >=sys-process/audit-2 )
	cryptsetup? ( sys-fs/cryptsetup )
	gudev? ( dev-libs/glib:2 )
	introspection? ( dev-libs/gobject-introspection )
	lzma? ( app-arch/xz-utils )
	pam? ( virtual/pam )
	selinux? ( sys-libs/libselinux )
	tcpd? ( sys-apps/tcp-wrappers )"

DEPEND="${RDEPEND}
	app-arch/xz-utils
	app-text/docbook-xsl-stylesheets
	dev-libs/libxslt
	dev-util/gperf
	dev-util/intltool
	>=sys-kernel/linux-headers-${MINKV}
	doc? ( dev-util/gtk-doc )"

pkg_setup() {
	enewgroup lock # used by var-lock.mount
	enewgroup tty 5 # used by mount-setup for /dev/pts
}

src_prepare() {
	# systemd-analyze is for python2.7 only nowadays.
	sed -i -e '1s/python/&2.7/' src/analyze/systemd-analyze
	autotools-utils_src_prepare
}

src_configure() {
	local myeconfargs=(
		--with-distro=gentoo
		# install everything to /usr
		--with-rootprefix=/usr
		--with-rootlibdir=/usr/$(get_libdir)
		# but pam modules have to lie in /lib*
		--with-pamlibdir=/$(get_libdir)/security
		--localstatedir=/var
		# make sure we get /bin:/sbin in $PATH
		--enable-split-usr
		--disable-ima
		$(use_enable acl)
		$(use_enable audit)
		$(use_enable cryptsetup libcryptsetup)
		$(use_enable doc gtk-doc)
		$(use_enable gudev)
		$(use_enable introspection)
		$(use_enable lzma xz)
		$(use_enable pam)
		$(use_enable selinux)
		$(use_enable tcpd tcpwrap)
	)

	autotools-utils_src_configure
}

src_install() {
	autotools-utils_src_install \
		bashcompletiondir=/tmp

	# compat for init= use
	dosym ../usr/lib/systemd/systemd /bin/systemd
	dosym ../lib/systemd/systemd /usr/bin/systemd
	# rsyslog.service depends on it...
	dosym ../usr/bin/systemctl /bin/systemctl

	# move files as necessary
	newbashcomp "${D}"/tmp/systemd-bash-completion.sh ${PN}
	rm -r "${D}"/tmp || die

	# we just keep sysvinit tools, so no need for the mans
	rm "${D}"/usr/share/man/man8/{halt,poweroff,reboot,runlevel,shutdown,telinit}.8 \
		|| die
	rm "${D}"/usr/share/man/man1/init.1 || die

	# Create /run/lock as required by new baselay/OpenRC compat.
	insinto /usr/lib/tmpfiles.d
	doins "${FILESDIR}"/gentoo-run.conf

	# Migration helpers.
	exeinto /usr/libexec/systemd
	doexe "${FILESDIR}"/update-etc-systemd-symlinks.sh
	systemd_dounit "${FILESDIR}"/update-etc-systemd-symlinks.{service,path}
	systemd_enable_service sysinit.target update-etc-systemd-symlinks.path
#if LIVE

	# Check whether we won't break user's system.
	[[ -x "${D}"/bin/systemd ]] || die '/bin/systemd symlink broken, aborting.'
	[[ -x "${D}"/usr/bin/systemd ]] || die '/usr/bin/systemd symlink broken, aborting.'
#endif
}

pkg_preinst() {
	local CONFIG_CHECK="~AUTOFS4_FS ~BLK_DEV_BSG ~CGROUPS ~DEVTMPFS
		~FANOTIFY ~HOTPLUG ~INOTIFY_USER ~IPV6 ~NET ~PROC_FS ~SIGNALFD
		~SYSFS ~!IDE ~!SYSFS_DEPRECATED ~!SYSFS_DEPRECATED_V2"
	kernel_is -ge ${MINKV//./ } || ewarn "Kernel version at least ${MINKV} required"
	check_extra_config
}

optfeature() {
	local i desc=${1} text
	shift

	text="  [\e[1m$(has_version ${1} && echo I || echo ' ')\e[0m] ${1}"
	shift

	for i; do
		elog "${text}"
		text="& [\e[1m$(has_version ${1} && echo I || echo ' ')\e[0m] ${1}"
	done
	elog "${text} (${desc})"
}

pkg_postinst() {
	mkdir -p "${ROOT}"/run || ewarn "Unable to mkdir /run, this could mean trouble."
	if [[ ! -L "${ROOT}"/etc/mtab ]]; then
		ewarn "Upstream suggests that the /etc/mtab file should be a symlink to /proc/mounts."
		ewarn "It is known to cause users being unable to unmount user mounts. If you don't"
		ewarn "require that specific feature, please call:"
		ewarn "	$ ln -sf '${ROOT}proc/self/mounts' '${ROOT}etc/mtab'"
		ewarn
	fi

	elog "You may need to perform some additional configuration for some programs"
	elog "to work, see the systemd manpages for loading modules and handling tmpfiles:"
	elog "	$ man modules-load.d"
	elog "	$ man tmpfiles.d"
	elog

	elog "To get additional features, a number of optional runtime dependencies may"
	elog "be installed:"
	optfeature 'for systemd-analyze' \
		'dev-lang/python:2.7' 'dev-python/dbus-python'
	optfeature 'for systemd-analyze plotting ability' \
		'dev-python/pycairo[svg]'
	optfeature 'for GTK+ systemadm UI and gnome-ask-password-agent' \
		'sys-apps/systemd-ui'
	elog

	ewarn "Please note this is a work-in-progress and many packages in Gentoo"
	ewarn "do not supply systemd unit files yet. You are testing it on your own"
	ewarn "responsibility. Please remember than you can pass:"
	ewarn "	init=/sbin/init"
	ewarn "to your kernel to boot using sysvinit / OpenRC."

	# Don't run it if we're outta /
	if [[ ! ${ROOT%/} ]]; then
		# Update symlinks to moved units.
		sh "${FILESDIR}"/update-etc-systemd-symlinks.sh

		# Try to start migration unit.
		ebegin "Trying to start migration helper path monitoring."
		systemctl --system start update-etc-systemd-symlinks.path 2>/dev/null
		eend ${?}
	fi

	if has_version sys-apps/systemd-units; then
		ewarn
		ewarn "If you use systemd-units: "
		ewarn "   slim@.service"
		ewarn "   gdm@.service"
		ewarn "   kdm@.service"
		ewarn "please remove the 'dev-%i.device' entries in Requires and After"
		ewarn "since systemd does not do that for tty[1-7] anymore."
	fi
}
