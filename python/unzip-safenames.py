#!/usr/bin/env python3

import argparse
import re
import os.path
import shutil
from zipfile import ZipFile

parser = argparse.ArgumentParser(description='Unzip file fixing unsafe names')
parser.add_argument(
    '-l', '--list',
    help='list files',
    action='store_true',
    default=False,
)
parser.add_argument(
    '-n', '--never',
    help='never overwrite existing files',
    action='store_true',
    default=False,
)
parser.add_argument(
    '-o', '--overwrite',
    help='overwrite existing files',
    action='store_true',
    default=False,
)
parser.add_argument(
    '-d', '--dir',
    help='extract files into dir',
    default='',
)
parser.add_argument(
    'file',
    help='the input ZIP file',
)

args = parser.parse_args()

name_re = re.compile(r'([^][A-Za-z0-9_. -])')


def escape(match):
    code = ord(match.group(0))
    return f'%{code:02x}'


def fix_name(name: str) -> str:
    return name_re.sub(escape, name)


def handle_existing_files(path):
    try:
        stat = os.stat(path)
        if args.overwrite:
            os.unlink(path)
        elif args.never:
            print(f'WARNING: Ignored already existing file {path}')
            return
        else:
            while True:
                c = input(f'replace {path}? [y]es, [n]o, [A]ll, [N]one: ')
                if c in ('y', 'A'):
                    os.unlink(path)
                    if c == 'A':
                        args.overwrite = True
                    return
                elif c in ('n', 'N'):
                    print(f'WARNING: Ignored already existing file {path}')
                    if c == 'N':
                        args.never = True
                    return
    except FileNotFoundError:
        return



# This is Python 3.7 ZipFile._extract_member() with a change to use `name`
# instead of member.filename and handling unzip-like -o/-n or prompt:
def _extract_member(zipfile, name, member, targetpath, pwd=None):
    # build the destination pathname, replacing
    # forward slashes to platform specific separators.
    arcname = name.replace('/', os.path.sep)

    # NOTE: from here on it's Python 3.7 ZipFile._extract_member()
    # replacing 'self' with 'zipfile':
    # -- BEGIN --

    if os.path.altsep:
        arcname = arcname.replace(os.path.altsep, os.path.sep)
    # interpret absolute pathname as relative, remove drive letter or
    # UNC path, redundant separators, "." and ".." components.
    arcname = os.path.splitdrive(arcname)[1]
    invalid_path_parts = ('', os.path.curdir, os.path.pardir)
    arcname = os.path.sep.join(x for x in arcname.split(os.path.sep)
                               if x not in invalid_path_parts)
    if os.path.sep == '\\':
        # filter illegal characters on Windows
        arcname = zipfile._sanitize_windows_name(arcname, os.path.sep)

    targetpath = os.path.join(targetpath, arcname)
    targetpath = os.path.normpath(targetpath)

    # Create all upper directories if necessary.
    upperdirs = os.path.dirname(targetpath)
    if upperdirs and not os.path.exists(upperdirs):
        os.makedirs(upperdirs)

    if member.is_dir():
        if not os.path.isdir(targetpath):
            os.mkdir(targetpath)
        return targetpath

    # -- END --

    # Handle 'unzip' -o/-n or prompt behavior
    handle_existing_files(targetpath)

    with zipfile.open(member, pwd=pwd) as source, \
         open(targetpath, 'wb') as target:
        shutil.copyfileobj(source, target)

    return targetpath


if args.list:
    print('      Size Name')
    print('---------- -------------------------------------------------------')
else:
    if args.dir is None:
        targetdir = os.getcwd()
    else:
        targetdir = os.fspath(args.dir)

with ZipFile(args.file) as infile:
    for member in infile.infolist():
        name = fix_name(member.filename)
        if args.list:
            print(f'{member.file_size:-10d} {name}')
        else:
            _extract_member(infile, name, member, targetdir)
