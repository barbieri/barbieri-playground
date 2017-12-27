#!/usr/bin/env python3

import sys
import argparse
import urllib.request
import json
import os.path

repo_url = "http://win-builds.org/1.5.0/packages/windows_64"
download_dir = "/tmp"
install_dir = "~/efl-windows_64"

base_pkgs = [
    "zlib",
    "lua",
    "libjpeg",
    "freetype",
    "expat",
    "fontconfig",
    "fribidi",
    "giflib",
    "libtiff",
    "libpng",
    "dbus",
    "libsndfile",
    "curl",
]


def which(file):
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
                return os.path.join(path, file)


def download_file(fname):
    url = repo_url + "/" + fname
    print("Downloading: {}".format(url))
    with urllib.request.urlopen(url) as response:
        length = int(response.headers.get("Content-Length", 0))
        p = os.path.join(download_dir, fname)
        if length and os.path.exists(p):
            flen = os.path.getsize(p)
            if flen == length:
                print("\tFile {} size matches, skipped.".format(p))
                return
            print("\tFile {}, expected {}. Download again.".format(flen, length))
            os.unlink(p)

        print("\tSize: {}".format(length))
        with open(p, "wb") as f:
            while True:
                chunk = response.read(1024 * 16)
                if not chunk:
                    break
                f.write(chunk)


def get_package_list():
    download_file("package_list.json")
    with open(os.path.join(download_dir, "package_list.json"), "r") as f:
        contents = f.read()
        if not contents:
            raise SystemExit("missing package_list.json")
        return json.loads(contents)


def fix_pc_dir(dname):
    for fname in os.listdir(dname):
        if fname.endswith(".pc"):
            fname = os.path.join(dname, fname)
            with open(fname, "r") as f:
                contents = f.readlines()

            prefix = "/opt/windows_64"
            for line in contents:
                if line.startswith("prefix="):
                    prefix = line[len("prefix="):].rstrip()
                    break

            with open(fname, "w") as f:
                for line in contents:
                    f.write(line.replace(prefix, install_dir))


def install(fname):
    print("Installing: {}".format(fname))
    os.system("tar -xJf {} -C {} --strip-components=1".format(
        os.path.join(download_dir, fname),
        install_dir))

    for ld in ("lib", "lib64", "lib32"):
        dname = os.path.join(install_dir, ld, "pkgconfig")
        if os.path.isdir(dname):
            fix_pc_dir(dname)

def pkg_find(lst, name):
    for p in lst:
        if p["name"] == name:
            return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Setup EFL build system for Windows64')
    ap.add_argument('--repo', metavar='URL',
                    help='win-builds.org repository URL to use.',
                    default=repo_url)
    ap.add_argument('--install-dir', metavar='DIR',
                    help='Where to install.',
                    default=install_dir)
    ap.add_argument('--download-dir', metavar='DIR',
                    help='Where to download.',
                    default=download_dir)
    ap.add_argument("--extra-package", "-p",
                    help="Extra package to install.",
                    action="append")
    ap.add_argument("--no-base-packages", "-N",
                    help="Do not install base packages, just -p/--extra-package",
                    action="store_true")
    ap.add_argument("--list-packages", "-l",
                    help="List available packages",
                    action="store_true")

    args = ap.parse_args()
    repo_url = args.repo
    install_dir = os.path.expanduser(args.install_dir)
    download_dir = os.path.expanduser(args.download_dir)

    if not which("eolian_gen"):
        raise SystemExit("missing native eolian_gen in $PATH!")
    if not which("x86_64-w64-mingw32-gcc"):
        raise SystemExit("missing toolchain (x86_64-w64-mingw32-gcc) in $PATH")

    os.makedirs(install_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    pkg_list = get_package_list()

    if args.list_packages:
        pkg_list.sort(key=lambda x: x["name"])
        for p in pkg_list:
            print("{} {}: {}".format(p["name"], p["version"], p["description"]))
        sys.exit(0)

    to_install = []
    if not args.no_base_packages:
        to_install.extend(base_pkgs)

    if args.extra_package:
        to_install.extend(args.extra_package)

    for pname in to_install:
        p = pkg_find(pkg_list, pname)
        if not p:
            raise SystemExit("missing {}".format(pname))

        download_file(p["filename"])
        install(p["filename"])

    fname = os.path.join(install_dir, "env.sh")
    with open(fname, "w") as f:
        f.write("""\
# Include this file to configure your EFL build environment.

export EFL_WIN64_PREFIX={0}
export EFL_WIN64_LIBDIR=$EFL_WIN64_PREFIX/lib64

export PKG_CONFIG_PATH=""
export PKG_CONFIG_LIBDIR="$EFL_WIN64_LIBDIR/pkgconfig"
export PATH="$EFL_WIN64_PREFIX/bin:$PATH"
export CPPFLAGS="-I$EFL_WIN64_PREFIX/include -DECORE_WIN64_WIP_POZEFLKSD"
export LDFLAGS="-L$EFL_WIN64_LIBDIR"
export CFLAGS="-pipe -O2 -W -Wall -Wextra -g -ggdb3 -mtune=core2"
export HOST="--host=x86_64-w64-mingw32"
export CC="x86_64-w64-mingw32-gcc"
export CXX="x86_64-w64-mingw32-g++"
export NATIVE_EOLIAN_GEN=`which eolian_gen`
export NATIVE_EDJE_CC=`which edje_cc`
export NATIVE_ELM_PREFS_CC=`which elm_prefs_cc`

EFL_WIN64_OPTS="--prefix=$EFL_WIN64_PREFIX $HOST "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --enable-i-really-know-what-i-am-doing-and-that-this-will-probably-break-things-and-i-will-fix-them-myself-and-send-patches-aaa "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --with-bin-eolian-gen=$NATIVE_EOLIAN_GEN"
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --with-bin-edje-cc=$NATIVE_EDJE_CC"
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --with-bin-elm-prefs-cc=$NATIVE_ELM_PREFS_CC"
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-static "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --with-windows-version=win7 "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --with-tests=none "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-gstreamer1 "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-gstreamer "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-pulseaudio "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-physics "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-libmount "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-valgrind "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --enable-lua-old "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-avahi "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-image-loader-jp2k "
EFL_WIN64_OPTS="$EFL_WIN64_OPTS --disable-cxx-bindings "

echo "Suggestion: ./configure $EFL_WIN64_OPTS"

if [ -z "$NATIVE_EOLIAN_GEN" ]; then
    echo -e "\\033[1;31mmissing native eolian_gen\\033[0m"
fi

if ! which x86_64-w64-mingw32-gcc 2>/dev/null >/dev/null; then
    echo -e "\\033[1;31mmissing x86_64-w64-mingw32-gcc\\033[0m"
fi
""".format(install_dir))
    print("Env file at {}".format(fname))

    fname = os.path.join(install_dir, "env-shell.sh")
    with open(fname, "w") as f:
        f.write("""\
#!/bin/bash
. {0}/env.sh
exec $SHELL
""".format(install_dir))
    os.chmod(fname, 0o755)
    print("Env shell at {}".format(fname))

    fname = os.path.join(install_dir, "compile-efl.sh")
    with open(fname, "w") as f:
        f.write("""\
#!/bin/bash
. {0}/env.sh

if [ ! -x configure ]; then
    echo -e "\\033[1;33mrunning autogen.sh...\\033[0m"
    NOCONFIGURE=1 ./autogen.sh || exit 1
fi

echo -e "\\033[1;33mrunning configure...\\033[0m"
./configure $EFL_WIN64_OPTS || exit 1
echo -e "\\033[1;33mrunning make...\\033[0m"
make ${MAKEOPTS} || exit 1
echo -e "\\033[1;33mrunning make install...\\033[0m"
make install || exit 1
echo -e "\\033[1;33mfinished. Installed at $EFL_WIN64_PREFIX...\\033[0m"
""".format(install_dir))
    os.chmod(fname, 0o755)
    print("Env shell at {}".format(fname))
