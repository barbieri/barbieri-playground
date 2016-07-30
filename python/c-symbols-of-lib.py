#!/usr/bin/python3

import sys
import argparse
import subprocess
import os.path
from fnmatch import fnmatch
import re

class Symbol:
    __slots__ = ("type", "name", "version", "value", "is_global", "string")

    _type_to_string = {
        "A": "absolute",
        "B": "uninitialized data (BSS)",
        "C": "common uninitialized data",
        "D": "initialized data",
        "G": "initialized data section for small objects",
        "I": "indirect function (relocation)",
        "N": "debug symbol",
        "p": "stack unwind section",
        "R": "read only",
        "S": "uninitialized data for small objects",
        "T": "text (code)",
        "U": "undefined (external)",
        "u": "unique global (per process)",
        "V": "weak object",
        "W": "weak object (untagged)",
        "-": "stabs",
        "?": "unknown",
        }

    def __init__(self, type, name, version, value):
        self.type = type
        self.name = name
        self.version = version
        self.value = value
        self.is_global = type.isupper()
        self.string = "%s %s" % (type, name)

    def type_as_string(self):
        try:
            return self._type_to_string[self.type]
        except KeyError:
            try:
                return self._type_to_string[self.type.upper()]
            except KeyError:
                return "unknown: " + self.type

    def __hash__(self):
        return hash((self.string, self.version))

    def __eq__(self, other):
        return (self.string, self.version) == (other.string, other.version)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return (self.string, self.version) < (other.string, other.version)

    def __gt__(self, other):
        return (self.string, self.version) > (other.string, other.version)

    def __le__(self, other):
        return (self.string, self.version) <= (other.string, other.version)

    def __ge__(self, other):
        return (self.string, self.version) >= (other.string, other.version)

    def __str__(self):
        return self.string

    def __repr__(self):
        s = self.string
        if self.version:
            s += "@@" + self.version
        if self.value is not None:
            s += " = " + self.value
        return s

    def to_dict(self):
        return {
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "value": self.value,
            "is_global": self.is_global,
        }


class Unit:
    def __init__(self, path, symbol_exclude):
        self.path = os.path.realpath(path)
        self.name = os.path.basename(path)
        self.symbols = {}
        self.symbol_exclude = symbol_exclude or []
        self.excluded_symbols = []

    def _read_nm(self, *nm_args):
        pipe = subprocess.Popen(
            ["nm", *nm_args, self.path],
            stdout=subprocess.PIPE)
        for line in pipe.stdout:
            s = line.strip().decode("ascii").split()
            if len(s) == 3:
                value, type, sym = s
            else:
                value = None
                type, sym = s

            try:
                name, version = sym.split("@@")
            except:
                name = sym
                version = None

            if name in ("_fini", "_init"):
                continue

            sym = Symbol(type, name, version, value)
            for exclude in self.symbol_exclude:
                if fnmatch(name, exclude):
                    self.excluded_symbols.append(sym)
                    break
            else:
                self.symbols[name] = sym

        pipe.wait()
        if pipe.returncode != 0:
            raise SystemError("'nm %s %s' exit code: %s"
                              % (" ".join(nm_args), self.path, pipe.returncode))

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other.path

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if isinstance(other, Unit):
            return self.path < other.path
        elif isinstance(other, tuple):
            return True

    def __gt__(self, other):
        if isinstance(other, Unit):
            return self.path > other.path
        elif isinstance(other, tuple):
            return False

    def __le__(self, other):
        if isinstance(other, Unit):
            return self.path <= other.path
        elif isinstance(other, tuple):
            return True

    def __ge__(self, other):
        if isinstance(other, Unit):
            return self.path >= other.path
        elif isinstance(other, tuple):
            return False

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)


class User(Unit):
    def __init__(self, path, symbol_exclude):
        Unit.__init__(self, path, symbol_exclude)
        self._read_nm("--undefined-only")

    def to_dict(self, include_symbols=True):
        r = {"path": self.path,
             "name": self.name,
             }
        if include_symbols:
            symbols = [x.to_dict() for x in self.symbols.values()]
            symbols.sort(key=lambda x: x["name"])
            r["symbols"] = symbols

        return r


class Library(Unit):
    def __init__(self, path, symbol_exclude):
        Unit.__init__(self, path, symbol_exclude)
        self.users = set()
        self.non_users = set()
        self.used_symbols = {}
        self.source_references = []
        self._read_nm("--defined-only", "--extern-only")
        self._match_used_symbols_re = None

    def add_user(self, u):
        used = []
        for us in u.symbols.keys():
            try:
                ps = self.symbols[us]
                used.append(ps)
                lst = self.used_symbols.setdefault(ps, [])
                if u not in lst:
                    lst.append(u)
            except KeyError:
                pass

        if not used:
            self.non_users.add(u)
            return True

        self.users.add((u, tuple(used)))
        self._match_used_symbols_re = None
        return True

    def _create_match_used_symbols_re(self):
        match = r"\b(?P<sym>" + \
                "|".join(sym for sym in self.symbols) + \
                r")\b"
        self._match_used_symbols_re = re.compile(match)

    def scan_source(self, path):
        if not self.used_symbols:
            return

        if self._match_used_symbols_re is None:
            self._create_match_used_symbols_re()

        match_re = self._match_used_symbols_re
        matches = []
        with open(path, encoding="utf-8") as source:
            for i, line in enumerate(source):
                for m in match_re.finditer(line):
                    sym = m.group("sym")
                    ps = self.symbols[sym]
                    matches.append((i, ps))
                    for user in self.used_symbols.setdefault(ps, []):
                        if isinstance(user, tuple) and user[0] == path:
                            user[1].append(i)
                            break
                    else:
                        self.used_symbols[ps].append((path, [i]))

        if not matches:
            return
        self.source_references.append((path, matches))

    def summarize(self):
        unused_symbols = []
        for s in self.symbols.values():
            if s not in self.used_symbols:
                unused_symbols.append(s)

        unused_symbols.sort()

        return {
            "non_users": sorted(list(self.non_users)),
            "unused_symbols": unused_symbols,
            "used_symbols": self.used_symbols,
            "excluded_symbols": sorted(self.excluded_symbols),
            "users": sorted(list(self.users)),
        }


def get_file_lines(path, line_numbers):
    line_numbers = list(line_numbers)
    lines = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i in line_numbers:
                lines.append((i, line.strip()))
                line_numbers.remove(i)
                if not line_numbers:
                    break
    return lines


def format_text(lib):
    summary = lib.summarize()

    if summary["non_users"]:
        print("Non users:")
        for u in summary["non_users"]:
            print("  %s" % (u.path,))
        print("")

    if summary["unused_symbols"]:
        print("Unused symbols:")
        for s in summary["unused_symbols"]:
            print("  %s" % (s.name,))
        print("")

    if summary["excluded_symbols"]:
        print("Excluded symbols:")
        for s in summary["excluded_symbols"]:
            print("  %s" % (s.name,))
        print("")

    if summary["used_symbols"]:
        print("Used symbols:")
        used_symbols = summary["used_symbols"]
        for sym in sorted(used_symbols.keys()):
            s = "  %s" % (sym.name,)
            if sym.version:
                s += "@@" + sym.version
            s += " [%s: %s]" % (sym.type, sym.type_as_string())
            print(s)
            for user in sorted(used_symbols[sym]):
                if isinstance(user, User):
                    print("    binary: %s" % (user.path,))
                else:
                    print("    source: %s" % (user[0],))
                    lines = get_file_lines(user[0], user[1])
                    size = len(str(user[1][-1]))
                    for i, l in lines:
                        print("       %*d: %s" % (size, i, l))
        print("")


def format_json(lib):
    import json

    summary = lib.summarize()
    non_users = []
    for u in summary["non_users"]:
        non_users.append(u.to_dict())

    non_users.sort(key=lambda x: x["path"])

    users = []
    for u, usage in summary["users"]:
        symbols = [s.to_dict() for s in usage]
        symbols.sort(key=lambda x: x["name"])
        users.append({"user": u.to_dict(), "used_symbols": symbols})

    users.sort(key=lambda x: x["user"]["path"])

    unused_symbols = []
    for s in summary["unused_symbols"]:
        unused_symbols.append(s.to_dict())

    unused_symbols.sort(key=lambda x: x["name"])

    excluded_symbols = []
    for s in summary["excluded_symbols"]:
        excluded_symbols.append(s.to_dict())

    excluded_symbols.sort(key=lambda x: x["name"])

    used_symbols = {}
    for s, user in summary["used_symbols"].items():
        lst = used_symbols.setdefault(s.name, [])
        for u in user:
            if isinstance(u, User):
                lst.append(("binary", u.path))
            elif isinstance(u, tuple):
                lines = get_file_lines(u[0], u[1])
                lst.append(("source", lines))
        lst.sort()

    report = {
            "non_users": non_users,
            "users": users,
            "unused_symbols": unused_symbols,
            "excluded_symbols": excluded_symbols,
            "used_symbols": used_symbols,
        }

    json.dump(report, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="List users of the C symbols of a given library")

    formatters = {
        "text": format_text,
        "json": format_json,
        }

    ap.add_argument(
        "-f", "--format", choices=sorted(formatters.keys()),
        default="text",
        help=("Output format. "
              "Default=%(default)s."))
    ap.add_argument(
        "-d", "--source-dir", action="append",
        default=[],
        help=("Source code directory root (scanned recursively). "
              "Default=%(default)s"))
    ap.add_argument(
        "-e", "--source-extension", action="append",
        default=["c", "h", "hh", "hpp"],
        help=("Extension to match source code. "
              "Default=%(default)s"))
    ap.add_argument(
        "-X", "--source-exclude", action="append",
        default=[],
        help=("Source filenames to exclude (fnmatch/glob pattern)."))
    ap.add_argument(
        "-x", "--symbol-exclude", action="append",
        default=[],
        help=("Symbol name exclude (fnmatch/glob pattern)."))
    ap.add_argument(
        "library",
        help="The library to use as symbol provider")
    ap.add_argument(
        "users", nargs="*",
        help="The possible users of the library")

    args = ap.parse_args()

    try:
        lib = Library(args.library, args.symbol_exclude)
    except SystemError as e:
        sys.stderr.write("ERROR: invalid file %s (%s)\n" % (args.library, e))
        sys.exit(1)

    for path in args.users:
        try:
            u = User(path, args.symbol_exclude)
        except SystemError as e:
            sys.stderr.write("ERROR: invalid file %s (%s)\n" % (path, e))
            continue
        lib.add_user(u)

    extensions = set()
    for e in args.source_extension:
        if not e.startswith(os.path.extsep):
            e = os.path.extsep + e
        extensions.add(e)

    for d in args.source_dir:
        for dirpath, dirnames, filenames in os.walk(os.path.expanduser(d)):
            for f in filenames:
                _, ext = os.path.splitext(f)
                if ext in extensions:
                    for exclude in args.source_exclude:
                        if fnmatch(f, exclude):
                            break
                    else:
                        lib.scan_source(os.path.join(dirpath, f))

    formatters[args.format](lib)
