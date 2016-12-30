#!/usr/bin/python3

try:
    from elftools.elf.elffile import ELFFile
    from elftools.elf.dynamic import DynamicTag, DynamicSegment
    from elftools.common.exceptions import ELFError
except ImportError as ex:
    print("ERROR: {}".format(ex))
    raise SystemExit("Missing pyelftools? https://github.com/eliben/pyelftools/")

import sys
import os.path
import re

# path -> Binary()
binaries = {}
sysroot = ""
ignore_libc_regex = None
lib_search_paths = []
show_fullpath = False
show_lines = True
show_used_symbols = False
max_depth = 0

ignore_missing_symbol_regex = re.compile(r"^(_dl_starting_up)$")
ignore_symbol_regex = None

class DependencyError(Exception):
    def __init__(self, binary, needed, search_paths):
        self.binary = binary
        self.needed = needed
        self.search_paths = tuple(search_paths)
        Exception.__init__(self, "{} misses {}, search paths: {}".format(
            self.binary.realpath, self.needed, ", ".join(self.search_paths)))


class Binary(object):
    __slots__ = ("dirname", "basename", "realpath", "aliases", "needs",
                 "needed_by", "symbols", "needs_symbols",
                 "needs_symbols_providers", "symbols_users",
                 "_resolve_needed_symbols")

    def __init__(self, dirname, basename, realpath, elf):
        self.dirname = dirname
        self.basename = basename
        self.realpath = realpath
        self.aliases = set()
        self.needs = set()
        self.needed_by = set()
        self.symbols = None
        self.needs_symbols = None
        self.needs_symbols_providers = {}
        self._resolve_needed_symbols = -1
        self.symbols_users = {}

        global binaries
        binaries[self.realpath] = self

        dt = elf.get_section_by_name(".dynamic")
        if not dt:
            return

        def _search_paths():
            for rpath in dt.iter_tags("DT_RPATH"):
                for d in rpath.rpath.split(":"):
                    yield os.path.realpath(sysroot + d)

            for d in lib_search_paths:
                yield d


        for tag in dt.iter_tags("DT_NEEDED"):
            needed = tag.needed
            if needed.startswith(os.path.sep):
                dep = self.try_binary(sysroot + needed)
                continue

            dep = None
            for d in _search_paths():
                deppath = os.path.join(d, needed)
                try:
                    dep = self.try_binary(deppath)
                    self.needs.add(dep)
                    dep.needed_by.add(self)
                    break
                except FileNotFoundError:
                    continue
            else:
                raise DependencyError(self, needed, _search_paths())

        if not show_used_symbols:
            return

        symtab = elf.get_section_by_name(".dynsym")
        if not symtab:
            print("INFO: {} has no .dynsym".format(self.realpath))
            return

        symbols = set()
        needs_symbols = set()
        for sym in symtab.iter_symbols():
            symname = sym.name
            if not symname:
                continue
            if sym["st_shndx"] != "SHN_UNDEF":
                symbols.add(symname)
            else:
                needs_symbols.add(symname)

        self.symbols = tuple(sorted(symbols))
        self.needs_symbols = tuple(sorted(needs_symbols))


    def resolve_needed_symbols(self):
        if self._resolve_needed_symbols >= 0:
            return self._resolve_needed_symbols

        missing = 0
        for symname in self.needs_symbols:
            for dep in self.needs:
                if symname in dep.symbols:
                    self.needs_symbols_providers[symname] = dep
                    dep.symbols_users.setdefault(symname, set()).add(self)
                    break
            else:
                if not ignore_missing_symbol_regex.match(symname):
                    self.needs_symbols_providers[symname] = None
                    missing += 1
        self._resolve_needed_symbols = missing
        return missing


    @classmethod
    def try_binary(cls, path):
        global binaries
        realpath = os.path.realpath(path)
        b = binaries.get(realpath)
        if b:
            if path != realpath:
                if path not in b.aliases:
                    b.aliases.add(path)
                    binaries[path] = b
            return b

        with open(realpath, "rb") as f:
            elf = ELFFile(f)
            dname, bname = os.path.split(realpath)
            b = cls(dname, bname, realpath, elf)
            if path != realpath:
                b.aliases.add(path)
                binaries[path] = b
            return b


def show_deps(b, parent_prefix, is_last, stack):
    if show_fullpath:
        path = b.realpath
    else:
        path = b.realpath[len(sysroot):]

    children = list(b.needs)
    children.sort(key=lambda x: x.realpath)
    if ignore_libc_regex:
        for dep in b.needs:
            if ignore_libc_regex.match(dep.basename):
                children.remove(dep)

    depth_limited = max_depth and len(stack) == max_depth
    cyclic = b in stack
    show_children = children and not cyclic and not depth_limited

    if not parent_prefix:
        local_prefix = ""
    else:
        if not show_lines:
            local_prefix = ""
        else:
            if is_last:
                local_prefix = "└"
            else:
                local_prefix = "├"

            if show_children:
                local_prefix += "─┬─ "
            else:
                local_prefix += "─── "

    note = ""
    if cyclic:
        note = " [cyclic-dependency, stop recursion]"

    print("{}{}{}{}".format(parent_prefix, local_prefix, path, note))

    if not show_lines:
        sub_prefix = parent_prefix + " "
    else:
        if is_last:
            sub_prefix = parent_prefix + "  "
        elif parent_prefix:
            sub_prefix = parent_prefix + "│ "
        else:
            sub_prefix = parent_prefix + "  "

    if show_used_symbols:
        b.resolve_needed_symbols()

        if show_children and show_lines:
            sym_prefix = "│"
        else:
            sym_prefix = " "

        missing_symbols = []
        for symname, provider in b.needs_symbols_providers.items():
            if ignore_symbol_regex and ignore_symbol_regex.match(symname):
                continue
            if provider is not None:
                continue
            missing_symbols.append(symname)

        if missing_symbols:
            print("{}{} missing symbols:".format(sub_prefix, sym_prefix))
            missing_symbols.sort()
            for symname in missing_symbols:
                print("{}{}  ! {}".format(sub_prefix, sym_prefix, symname))

        if stack:
            u = stack[-1]
            used_symbols = []
            for symname, users in b.symbols_users.items():
                if ignore_symbol_regex and ignore_symbol_regex.match(symname):
                    continue
                if u in users:
                    used_symbols.append(symname)

            if used_symbols:
                print("{}{} used symbols:".format(sub_prefix, sym_prefix))
                used_symbols.sort()
                for symname in used_symbols:
                    print("{}{}  * {}".format(sub_prefix, sym_prefix, symname))

    if not show_children:
        return
    last = len(children) - 1
    for i, d in enumerate(children):
        show_deps(d, sub_prefix, i == last, stack + (b,))


def show_deps_reverse(b, parent_prefix, is_last, stack):
    if show_fullpath:
        path = b.realpath
    else:
        path = b.realpath[len(sysroot):]

    children = list(b.needed_by)
    children.sort(key=lambda x: x.realpath)
    if ignore_libc_regex:
        for dep in b.needed_by:
            if ignore_libc_regex.match(dep.basename):
                children.remove(dep)

    depth_limited = max_depth and len(stack) == max_depth
    cyclic = b in stack
    show_children = children and not cyclic and not depth_limited

    if not parent_prefix:
        local_prefix = ""
    else:
        if not show_lines:
            local_prefix = ""
        else:
            if is_last:
                local_prefix = "└"
            else:
                local_prefix = "├"

            if show_children:
                local_prefix += "─┬─ "
            else:
                local_prefix += "─── "

    note = ""
    if cyclic:
        note = " [cyclic-dependency, stop recursion]"

    print("{}{}{}{}".format(parent_prefix, local_prefix, path, note))

    if not show_lines:
        sub_prefix = parent_prefix + " "
    else:
        if is_last:
            sub_prefix = parent_prefix + "  "
        elif parent_prefix:
            sub_prefix = parent_prefix + "│ "
        else:
            sub_prefix = parent_prefix + "  "

    if show_used_symbols:
        b.resolve_needed_symbols()

        if show_children and show_lines:
            sym_prefix = "│"
        else:
            sym_prefix = " "

        missing_symbols = []
        for symname, provider in b.needs_symbols_providers.items():
            if ignore_symbol_regex and ignore_symbol_regex.match(symname):
                continue
            if provider is not None:
                continue
            missing_symbols.append(symname)

        if missing_symbols:
            print("{}{} missing symbols:".format(sub_prefix, sym_prefix))
            missing_symbols.sort()
            for symname in missing_symbols:
                print("{}{}  ! {}".format(sub_prefix, sym_prefix, symname))

        if stack:
            p = stack[-1]
            used_symbols = []
            for symname, users in p.symbols_users.items():
                if ignore_symbol_regex and ignore_symbol_regex.match(symname):
                    continue
                if b in users:
                    used_symbols.append(symname)

            if used_symbols:
                print("{}{} used symbols:".format(sub_prefix, sym_prefix))
                used_symbols.sort()
                for symname in used_symbols:
                    print("{}{}  * {}".format(sub_prefix, sym_prefix, symname))

    if not show_children:
        return
    last = len(children) - 1
    for i, d in enumerate(children):
        show_deps_reverse(d, sub_prefix, i == last, stack + (b,))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Show ELF binary dependencies.")
    ap.add_argument("-a", "--all", action="store_true",
                    help=("display for all binaries, not just those "
                          "explicitly given"))
    ap.add_argument("-r", "--reverse", action="store_true",
                    help="Show reverse dependencies (needed by).")
    ap.add_argument("--no-lines", action="store_true",
                    help="Do not show lines in output, just indent.")
    ap.add_argument("-d", "--max-depth", type=int, default=0,
                    help=("Maximum depth to recurse, default to 0 = unlimited"))
    ap.add_argument("-i", "--ignore-libc", action="store_true",
                    help=("Do not print libc and dynamic linker"))
    ap.add_argument("--ignore-symbol-regex",
                    help="If the regular expression matches symbol, it's ignored.")
    ap.add_argument("-S", "--sysroot", type=str, default=sysroot,
                    help="sysroot to prefix to all lookups")
    ap.add_argument("-f", "--fullpath", action="store_true",
                    help=("Show full path, including -s/--sysroot"))
    ap.add_argument("-u", "--used-symbols", action="store_true",
                    help="Show used symbols for each dependency.")
    ap.add_argument("-L", "--libdir", action="append",
                    help=("set libraries directories to search. "
                          "If none is given, tries an heuristic based "
                          "standard paths."))
    ap.add_argument("binaries", nargs="+",
                    help="path to binary files to show dependencies")
    args = ap.parse_args()

    sysroot = args.sysroot

    ret = 0

    max_depth = args.max_depth
    show_fullpath = args.fullpath
    show_lines = not args.no_lines
    show_used_symbols = args.used_symbols

    if args.ignore_libc:
        ignore_libc_regex = re.compile(r"^(libc[-.]|ld-)")

    if args.ignore_symbol_regex:
        ignore_symbol_regex = re.compile(args.ignore_symbol_regex)

    if args.libdir:
        for d in args.libdir:
            path =  os.path.realpath(sysroot + d) # not join since d starts with '/'
            if os.path.isdir(path):
                if path not in lib_search_paths:
                    lib_search_paths.append(path)
                else:
                    print("WARNING: {} was already in search path".format(path))
            else:
                print("ERROR: {} is not a directory".format(path))
                ret = 1
    else:
        for d in ("/lib", "/lib32", "/lib64",
                  "/usr/lib", "/usr/lib32", "/usr/lib64"):
            path =  os.path.realpath(sysroot + d) # not join since d starts with '/'
            if os.path.isdir(path):
                if path not in lib_search_paths:
                    lib_search_paths.append(path)

    bins = []
    for path in args.binaries:
        try:
            b = Binary.try_binary(sysroot + path)
            bins.append(b)
        except FileNotFoundError as ex:
            print("ERROR: could not find '{}' sysroot={}".format(path, sysroot))
            ret = 1
        except ELFError as ex:
            print("ERROR: not an ELF binary '{}': {}".format(path, ex))
            ret = 1
        except Exception as ex:
            print("ERROR: could not process '{}': {}".format(path, ex))
            ret = 1

    if args.all:
        bins = list(binaries.values())
        bins.sort(key=lambda x: x.realpath)


    last = len(bins) - 1
    for i, b in enumerate(bins):
        if args.reverse:
            show_deps_reverse(b, "", i == last, tuple())
        else:
            show_deps(b, "", i == last, tuple())
        print()

    exit(ret)
