# EFL build setup for Windows64 environment

This script automates fetching required packages from
http://win-builds.org/ without the need to compile a toolchain or its
package manager (yypkg).

It assumes you have a local native build of EFL installed, since
`eolian_gen` must be in `$PATH`, as well as cross compiler tool chain
x86_64-w64-mingw32-gcc.

On ArchLinux you can install with:

```
$ sudo pacman -S community/mingw-w64 extra/efl
```

Then execute the python script to download and install Windows64
dependencies to `~/efl-windows_64`:

```
$ python3 efl-win64-install.py
```

It will generate couple of shell script files under
`~/efl-windows_64`, one is `compile-efl.sh`, which you can run from inside
an EFL checkout:

```
$ git clone https://git.enlightenment.org/core/efl.git
$ ~/efl-windows_64/compile-efl.sh
```

If you want to install more dependencies packages, use `-p` with the
package name, which can be queried with `-l`:

```
$ python3 efl-win64-install.py -l
$ python3 efl-win64-install.py -p glib2 -p openssl
```
