#!/bin/sh
# Update symlinks to systemd units moved into /usr/systemd.
# (c) 2012 Michał Górny
# Released under the terms of the 2-clause BSD license

IFS_SAVE=${IFS}
IFS='
'
# follow + symlink type will match broken symlinks only
set -- $(find -L /etc/systemd/system -type l -print)
IFS=${IFS_SAVE}

for f; do
	old_path=$(readlink "${f}")
	new_path=/usr/lib${old_path#/lib}
	if [ -f "${new_path}" ]; then
		ln -v -s -f "${new_path}" "${f}"
	fi
done
