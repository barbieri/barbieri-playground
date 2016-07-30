#!/usr/bin/python2

import sys
import os
import optparse
import datetime
import re
from ConfigParser import SafeConfigParser as ConfigParser

"""
TODO:
 - handle union
 - output gathered typedefs, structs and enums
"""

re_doublespaces = re.compile('\s\s+')

timestamp = datetime.datetime.now().strftime("%A, %Y-%B-%d %H:%M:%S")
progname = os.path.basename(sys.argv[0])

def header_tokenize(header_file, cfg):
    ignore_tokens = config_get_regexp(cfg, "global", "ignore-tokens-regexp")
    f = open(header_file)
    in_comment = False
    in_macro = False
    buf = []
    for line in f.readlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            in_macro = line.endswith("\\")
            continue
        if in_macro:
            in_macro = line.endswith("\\")
            continue

        while line:
            if in_comment:
                x = line.find("*/")
                if x < 0:
                    line = ""
                    break
                else:
                    line = line[x + 2:]
                    in_comment = False

            x = line.find("//")
            if x >= 0:
                line = line[:x]
                break

            x = line.find("/*")
            if x >= 0:
                y = line.find("*/", x + 2)
                if y >= 0:
                    line = line[:x] + line[y + 2:]
                else:
                    line = line[:x]
                    in_comment = True
            else:
                break

        line = line.replace("*", " * ").replace("=", " = ").strip()
        if not line:
            continue

        buf.append(line)

    buf = " ".join(buf)
    tokens = []
    attribute_regexp = re.compile("""\
__attribute__\s*[(]{2}(\
(\s+|[a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*){0,1}|\
(([a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*),\
([a-zA-Z0-9_ ]+|[a-zA-Z0-9_ ]+[(][^)]*[)]\s*))+\
)[)]{2}""")
    for line in buf.split(";"):
        line = line.strip()
        if not line:
            continue
        last_i = 0
        line = re_doublespaces.sub(' ', line)
        if ignore_tokens:
            line = ignore_tokens.sub("", line).strip()
            if not line:
                continue
        if line.startswith("static "):
            continue
        line = attribute_regexp.sub("", line).strip()
        for i, c in enumerate(line):
            if c in (",", "{", "}", "(", ")"):
                x = line[last_i:i].strip()
                if x:
                    tokens.append(x)
                tokens.append(c)
                last_i = i + 1

        x = line[last_i:].strip()
        if x:
            tokens.append(x)

        tokens.append(";")

    f.close()
    return tokens


_types = {}
_types_order = []

class Type(object):
    cls = None

    def __new__(cls, *args, **kargs):
        # each named type should be a singleton, also attribute an unique id
        name = kargs.get("name")
        if name is None:
            name = args[0]
        lst = _types.setdefault(cls.cls, [])
        if name is not None:
            for c in lst:
                if c.name == name:
                    return c
        o = object.__new__(cls)
        o.id = len(lst)
        lst.append(o)
        _types_order.append(o)
        return o

    def __init__(self, name, container=None):
        self.name = name
        self.container = container

    def find_name(self):
        if self.name:
            return self.name
        elif self.container:
            return "<anonymous-inside>" + self.container.find_name()
        else:
            return "<anonymous>%d" % (self.id,)

    def __str__(self):
        return "%s %s" % (self.cls, self.find_name())

    def __repr__(self):
        contents = []
        for k, v in self.__dict__.iteritems():
            if callable(v):
                continue
            if k.startswith("_"):
                continue
            contents.append((k, v))
        contents.sort(cmp=lambda a, b: cmp(a[0], b[0]))
        return "%s(%s)" % (self.cls, ", ".join("%s=%r" % x for x in contents))

    def variable_formatter(self, varname, pointer=0, prefix="", indent="",
                           newline=" "):
        p = ""
        if pointer:
            p += " *" * pointer
        if varname:
            p += " "
        return "%s%s%s%s" % (prefix, self, p, varname)

    def pretty_format(self, prefix="", indent="", newline=""):
        name = self.name
        if name is None:
            name = ""
        else:
            name = " " + name
        return "%s%s%s" % (prefix, self.cls, name)

    @classmethod
    def exists(cls, name):
        return bool(cls.find(name))

    @classmethod
    def find(cls, name):
        try:
            lst = _types[cls.cls]
        except KeyError:
            return None
        for c in lst:
            if c.name == name:
                return c
        return None

    @staticmethod
    def get_by_name(name):
        user_cls = {"enum": Enum, "struct": Struct, "union": Union}
        for uc, cls in user_cls.iteritems():
            if name.startswith(uc + " "):
                n = name[len(uc) + 1:]
                for t in _types.get(uc, ()):
                    if t.name == n:
                        return t
                t = cls(n)
                _types.setdefault(uc, []).append(t)
                return t

        for t in _types.get("builtin", ()):
            if t.name == name:
                return t
        t = BuiltinType(name)
        _types.setdefault("builtin", []).append(t)
        return t


class BuiltinType(Type):
    cls = "builtin"
    def __init__(self, name, container=None):
        Type.__init__(self, name, container)

    def __str__(self):
        return self.name

    def pretty_format(self, prefix="", indent="", newline=" "):
        name = self.name
        if name is None:
            name = ""
        return prefix + name


for bi in ("char", "int",
           "short", "short int",
           "long", "long int",
           "long long", "long long int"):
    BuiltinType(bi)
    BuiltinType("unsigned " + bi)
    BuiltinType("signed " + bi)
    BuiltinType("const " + bi)
    BuiltinType("const " + "unsigned " + bi)
    BuiltinType("const " + "signed " + bi)

for bi in ("float", "double", "void"):
    BuiltinType(bi)
    BuiltinType("const " + bi)

BuiltinType("long double")
BuiltinType("const long double")

for bi in (8, 16, 32, 64):
    BuiltinType("int%d_t" % bi)
    BuiltinType("uint%d_t" % bi)
    BuiltinType("const int%d_t" % bi)
    BuiltinType("const uint%d_t" % bi)

for bi in ("bool", "_Bool", "Bool"):
    BuiltinType(bi)
    BuiltinType("const " + bi)


class Enum(Type):
    cls = "enum"
    def __init__(self, name, container=None, members=None):
        Type.__init__(self, name, container)
        self.members = members or []

    def add_member(self, name, value=None):
        self.members.append((name, value))

    def pretty_format(self, prefix="", indent="", newline=" ",
                      show_members=True):
        s = Type.pretty_format(self, prefix, indent, newline)
        if self.members and show_members:
            m = []
            x = prefix + indent
            for n, v in self.members:
                if v:
                    m.append("%s%s = %s" % (x, n, v))
                else:
                    m.append("%s%s" % (x, n))
            m = ("," + newline).join(m)
            s += " {%s%s%s%s}" % (newline, m, newline, prefix)
        return s

    def variable_formatter(self, varname, pointer=0, prefix="", indent="",
                           newline=" "):
        show_members = not self.name
        s = self.pretty_format(prefix, indent, newline, show_members)
        p = ""
        if pointer:
            p += " *" * pointer
        if varname:
            p += " "
        return "%s%s%s" % (s, p, varname)


class Group(Type):
    def __init__(self, name, container=None, members=None):
        Type.__init__(self, name, container)
        self.members = members or []

    def add_member(self, variable):
        self.members.append(variable)

    def pretty_format(self, prefix="", indent="", newline=" ",
                      show_members=True):
        s = Type.pretty_format(self, prefix, indent, newline)
        if self.members and show_members:
            m = []
            subprefix = prefix + indent
            for v in self.members:
                m.append(v.variable_formatter(prefix=subprefix,
                                              indent=indent, newline=newline)
                         + ";")
            m = newline.join(m)
            s += " {%s%s%s%s}" % (newline, m, newline, prefix)
        return s

    def variable_formatter(self, varname, pointer=0, prefix="", indent="",
                           newline=" "):
        show_members = not self.name
        s = self.pretty_format(prefix, indent, newline, show_members)
        p = ""
        if pointer:
            p += " *" * pointer
        if varname:
            p += " "
        return "%s%s%s" % (s, p, varname)


class Struct(Group): cls = "struct"
class Union(Group): cls = "union"


class FunctionPointer(Type):
    cls = "function-pointer"
    def __init__(self, ret_type, parameters, ret_pointer=0, container=None):
        name = "%s%s (*)(%s)" % (ret_type, " *" * ret_pointer, ", ".join(
            x.type_formatter() for x in parameters))
        Type.__init__(self, name, container)
        self.ret_type = ret_type
        self.parameters = parameters
        self.ret_pointer = ret_pointer

    def __str__(self):
        return self.name

    def pretty_format(self, pointer=0, parameters_names=True,
                      prefix="", indent="", newline=" "):
        p = ""
        if pointer:
            p += " *" * pointer
        params = []
        for par in self.parameters:
            if parameters_names:
                params.append(str(par))
            else:
                params.append(par.type_formatter())
        return "%s%s (*%s)(%s)" % (prefix, self.ret_type, p, ", ".join(params))

    def variable_formatter(self, varname, pointer=0, parameters_names=True,
                           prefix="", indent="", newline=" "):
        p = ""
        if pointer:
            p += " *" * pointer
        if varname:
            p += " "
        params = []
        for par in self.parameters:
            if parameters_names:
                params.append(str(par))
            else:
                params.append(par.type_formatter())
        return "%s%s (*%s%s)(%s)" % (prefix, self.ret_type, p, varname,
                                     ", ".join(params))


class FunctionName(Type):
    cls = "function-name"
    def __init__(self, ret_type, name, parameters, ret_pointer=0,
                 container=None):
        Type.__init__(self, name, container)
        self.ret_type = ret_type
        self.parameters = parameters
        self.ret_pointer = ret_pointer

    def __str__(self):
        return self.formatter()

    def pretty_format(self, prefix="", indent="", newline=" "):
        return prefix + self.formatter()

    def formatter(self, parameters_names=True):
        params = self.parameters_str(parameters_names)
        ret = self.ret_type_str()
        return "%s %s(%s)" % (ret, self.name, params)

    def ret_type_str(self):
        return "%s%s" % (self.ret_type, " *" * self.ret_pointer)

    def has_parameters(self):
        if not self.parameters:
            return False
        p = self.parameters[0]
        return not (p.pointer == 0 and p.type.name == "void")

    def parameters_unnamed_fix(self, prefix=""):
        if not self.has_parameters():
            return
        for i, v in enumerate(self.parameters):
            if not v.name:
                v.name = "%s_par%d" % (prefix, i)

    def parameters_str(self, parameters_names=True):
        params = []
        for par in self.parameters:
            if parameters_names:
                params.append(str(par))
            else:
                params.append(par.type_formatter())
        return ", ".join(params)

    def parameters_names_str(self):
        return ", ".join(v.name for v in self.parameters if v.name)


class Typedef(Type):
    cls = "typedef"

    def __init__(self, name, reference, pointer=0):
        Type.__init__(self, name)
        self.reference = reference
        self.pointer = pointer

    def __str__(self):
        return "typedef %s" % \
               (self.reference.variable_formatter(self.name, self.pointer))

    def pretty_format(self, prefix="", indent="", newline=" "):
        s = self.reference.variable_formatter(
            self.name, self.pointer, prefix=prefix,
            indent=indent, newline=newline)
        s = s[len(prefix):] # the first is on the same line, do not prefix
        return "%stypedef %s" % (prefix, s)

    def type_formatter(self):
        return self.reference.variable_formatter("", self.pointer)


class Variable(object):
    def __init__(self, type, name, pointer=0):
        self.type = type
        self.name = name
        self.pointer = pointer

    def __str__(self):
        name = self.name
        if name is None:
            name = ""
        return self.type.variable_formatter(name, self.pointer)

    def __repr__(self):
        return "Variable(type=%r, name=%r, pointer=%d)" % \
               (self.type, self.name, self.pointer)

    def type_formatter(self):
        return self.type.variable_formatter("", self.pointer)

    def pretty_format(self, prefix="", indent="", newline=" "):
        name = self.name
        if name is None:
            name = ""
        return self.type.variable_formatter(
            name, self.pointer, prefix=prefix + indent,
            indent=indent, newline=newline)

    def variable_formatter(self, prefix="", indent="", newline=" "):
        return self.pretty_format(prefix, indent, newline)


class Node(object):
    def __init__(self, children, enclosure=None, parent=None):
        self.children = children or []
        self.enclosure = enclosure
        self.parent = parent

    def __repr__(self):
        parts = []
        for x in self.children:
            if isinstance(x, Node):
                parts.append(repr(x))
            else:
                parts.append(repr(x))
        parent = 0
        if self.parent:
            parent = id(self.parent)
        return "Node(%#x, parent=%#x, enclosure=%s, children=[%s])" % \
               (id(self), parent, self.enclosure, ", ".join(parts))

    def __str__(self):
        if self.enclosure is None:
            return "<%s>" % " ".join(str(x) for x in self.children)
        else:
            return "%s%s%s" % \
                   (self.enclosure[0],
                    " ".join(str(x) for x in self.children),
                    self.enclosure[1])

    def flattened(self):
        parts = []
        for c in self.children:
            if isinstance(c, Node):
                parts.append(c.flattened())
            else:
                parts.append(c)
        s = " ".join(parts)
        if self.enclosure is None:
            return s
        else:
            return "%s%s%s" % (self.enclosure[0], s, self.enclosure[1])


def build_function_params(param_nodes, data):
    params = []
    for p in param_nodes:
        for v in p.children:
            for c in process_single(v, data, True):
                if isinstance(c, Variable):
                    params.append(c)
    return params

cls_mapper = {"enum": Enum, "struct": Struct, "union": Union}
def process_single(n, data, allow_unamed_variables=False):
    processed = []
    parts = n.children[0].split(" ")
    t = None
    if parts[0] == "typedef":
        tmp = Node([" ".join(parts[1:])] + n.children[1:], parent=n)
        var = None
        for v in process_single(tmp, data):
            if isinstance(v, Variable):
                if var is not None:
                    raise ValueError("typedef with more than one declaration?")
                var = v
        if var is None:
            raise ValueError("typedef without type name?")
        t = Typedef(var.name, var.type, var.pointer)
        processed.append(t)
        data[parts[0]][t.name] = t

    elif parts[0] in ("enum", "struct", "union") and \
         not (len(n.children) > 1 and isinstance(n.children[-1], Node)
              and n.children[-1].enclosure == ("(", ")")):
        name = None
        varname = None
        members = None

        if len(parts) > 1:
            name = parts[1]
            if len(parts) > 2:
                varname = parts[2:]

        if len(n.children) > 1:
            members = n.children[1]
            if len(n.children) > 2:
                varname = n.children[2:]

        if members:
            if name:
                t = data[parts[0]].get(name)
            else:
                t = None

            if not t:
                t = cls_mapper[parts[0]](name)
                if name:
                    data[parts[0]][name] = t
                processed.append(t)

            for m in members.children:
                if parts[0] == "enum":
                    for v in m.children:
                        if len(v.children) < 1:
                            continue
                        x = v.children[0].split("=", 1)
                        enum_name = x[0].strip()
                        enum_value = None
                        if len(x) > 1:
                            enum_value = x[1].strip()
                            if len(v.children) > 1:
                                exp = " ".join(
                                    x.flattened() for x in v.children[1:])
                                if enum_value and exp:
                                    enum_value += " " + exp
                                elif exp:
                                    enum_value = exp
                        t.add_member(enum_name, enum_value)
                else:
                    for c in process(m, data):
                        c.container = t
                        if isinstance(c, Variable):
                            t.add_member(c)

        if name:
            if t:
                data[parts[0]][name] = t
            else:
                t = data[parts[0]].get(name)
                if not t:
                    data[parts[0]][name] = t = cls_mapper[parts[0]](name)
                    processed.append(t)

        if varname:
            assert(t)
            varname = " ".join(varname)
            pointer = varname.count("*")
            if pointer > 0:
                varname = re_doublespaces.sub(" ",
                                              varname.replace("*", "")).strip()
            processed.append(Variable(t, varname, pointer))
        elif allow_unamed_variables:
            processed.append(Variable(t, None))

    elif len(n.children) >= 3 and \
         isinstance(n.children[-1], Node) and \
         n.children[-1].enclosure == ("(", ")") and \
         isinstance(n.children[-2], Node) and \
         n.children[-2].enclosure == ("(", ")") and \
         len(n.children[-2].children) > 0 and \
         isinstance(n.children[-2].children[0], Node) and \
         len(n.children[-2].children[0].children) > 0 and \
         isinstance(n.children[-2].children[0].children[0], Node) and \
         len(n.children[-2].children[0].children[0].children) > 0 and \
         not isinstance(n.children[-2].children[0].children[0].children[0],
                        Node) and \
         n.children[-2].children[0].children[0].children[0].startswith("*"):
        # function pointer (union, struct, function parameters, typedefs...)

        ret_type = " ".join(n.children[:-2])
        ret_pointer =  ret_type.count("*")
        if ret_pointer > 0:
            ret_type = re_doublespaces.sub(" ",
                                           ret_type.replace("*", " ")).strip()
        name = n.children[-2].children[0].children[0].children[0][1:].strip()
        params = build_function_params(n.children[-1].children, data)
        ret_type = Type.get_by_name(ret_type)
        t = FunctionPointer(ret_type, params, ret_pointer)
        for p in params:
            p.container = t

        processed.append(t)
        if not name:
            if allow_unamed_variables:
                name = None
            else:
                raise ValueError("unnamed variable not allowed")

        processed.append(Variable(t, name))

    elif len(n.children) >= 2 and \
         isinstance(n.children[-1], Node) and \
         n.children[-1].enclosure == ("(", ")"):
        # function itself
        x = " ".join(n.children[:-1]).split(" ")
        if x[0] == "extern":
            x.pop(0)
        ret_type = " ".join(x[:-1])
        ret_pointer = ret_type.count("*")
        if ret_pointer > 0:
            ret_type = re_doublespaces.sub(" ",
                                           ret_type.replace("*", " ")).strip()

        name = x[-1]
        params = build_function_params(n.children[-1].children, data)
        ret_type = Type.get_by_name(ret_type)
        t = FunctionName(ret_type, name, params, ret_pointer)
        for p in params:
            p.container = t
        processed.append(t)
        data["function"][name] = t

    else:
        if parts[0] == "extern":
            parts.pop(0)

        x = len(parts)
        try:
            parts.remove("*")
            y = len(parts)
            pointer = x - y
        except ValueError, e:
            pointer = 0

        name = parts.pop(-1)
        if BuiltinType.exists(name) or Typedef.exists(name):
            if allow_unamed_variables:
                parts.append(name)
                name = None
            else:
                raise ValueError("name is a known type: %s" % name)

        t = BuiltinType(" ".join(parts))
        processed.append(Variable(t, name, pointer))
    return processed


def process(node, data):
    processed = process_single(node.children[0], data)
    if len(node.children) == 1:
        return processed

    t = None
    for p in processed:
        if isinstance(p, Variable):
            t = p.type
        elif isinstance(p, Type):
            t = p

    assert(t)
    for c in node.children[1:]:
        varname = " ".join(c.children)
        pointer = varname.count("*")
        if pointer > 0:
            varname = re_doublespaces.sub(" ", varname.replace("*", "")).strip()
        v = Variable(t, varname, pointer)
        processed.append(v)

    return processed


def header_tree(header_file, cfg=None):
    tokens = header_tokenize(header_file, cfg)
    closing = {"(":")", "{":"}"}

    def make_tree(tokens, delim=None):
        tokens = list(tokens)
        nodes = Node([])
        current = Node([], parent=nodes)
        nodes.children.append(current)

        if delim:
            delims = (";", delim)
        else:
            delims = (";",)

        t = None
        while tokens:
            t = tokens.pop(0)
            if t == ",":
                current = Node([], parent=nodes)
                nodes.children.append(current)
            elif t in delims:
                break
            elif t in ("{", "("):
                enclosure = (t, closing.get(t))
                end = None
                sub = Node([], enclosure=enclosure, parent=current)
                current.children.append(sub)
                while tokens and end != enclosure[1]:
                    x, end, tokens = make_tree(tokens, enclosure[1])
                    if x.children and x.children[0].children:
                        x.parent = sub
                        sub.children.append(x)
            else:
                current.children.append(t)

        return (nodes, t, tokens)


    data = {"enum": {}, "struct": {}, "union": {}, "typedef": {},
            "function": {}, "global": {}}

    while tokens:
        n, ignored, tokens = make_tree(tokens)
        if n:
            process(n, data)

    return data


def generate_preamble(f, ctxt):
    repl = {
        "header": ctxt["header"],
        "header_name": os.path.splitext(os.path.basename(ctxt["header"]))[0],
        "prefix": ctxt["prefix"],
        "libname": ctxt["libname"],
        "progname": progname,
        "timestamp": timestamp,
        }

    f.write("""\
/* this file was auto-generated from %(header)s by %(progname)s.
 * %(timestamp)s
 */

""" % repl)

    cfg = ctxt["cfg"]
    headers = None
    if cfg:
        try:
            headers = cfg.get("global", "headers", vars=repl)
        except Exception, e:
            pass
        if headers:
            for h in headers.split(","):
                f.write("#include <%s>\n" % h.strip())

    if not headers:
        f.write("#include <%(header)s>\n" % ctxt)

    f.write("""
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>
#include <errno.h>

#ifdef %(prefix)s_USE_COLORS
#define %(prefix)s_COLOR_ERROR \"\\033[1;31m\"
#define %(prefix)s_COLOR_WARN \"\\033[1;33m\"
#define %(prefix)s_COLOR_OK \"\\033[1;32m\"
#define %(prefix)s_COLOR_ENTER \"\\033[1;36m\"
#define %(prefix)s_COLOR_EXIT \"\\033[1;35m\"
#define %(prefix)s_COLOR_CLEAR \"\\033[0m\"
#else
#define %(prefix)s_COLOR_ERROR \"\"
#define %(prefix)s_COLOR_WARN \"\"
#define %(prefix)s_COLOR_OK \"\"
#define %(prefix)s_COLOR_ENTER \"\"
#define %(prefix)s_COLOR_EXIT \"\"
#define %(prefix)s_COLOR_CLEAR \"\"
#endif

#ifdef %(prefix)s_HAVE_THREADS
#include <pthread.h>
static pthread_mutex_t %(prefix)s_th_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_t %(prefix)s_th_main = 0;
static unsigned char %(prefix)s_th_initted = 0;
#define %(prefix)s_THREADS_INIT \\
    do { \\
        pthread_mutex_lock(&%(prefix)s_th_mutex); \\
        if (!%(prefix)s_th_initted) { \\
            %(prefix)s_th_initted = 1; \\
            %(prefix)s_th_main = pthread_self(); \\
        } \\
        pthread_mutex_unlock(&%(prefix)s_th_mutex); \\
    } while(0)
#define %(prefix)s_IS_MAIN_THREAD (%(prefix)s_th_main == pthread_self())
#define %(prefix)s_THREAD_ID ((unsigned long)pthread_self())
#define %(prefix)s_LOCK pthread_mutex_lock(&%(prefix)s_th_mutex)
#define %(prefix)s_UNLOCK pthread_mutex_unlock(&%(prefix)s_th_mutex)
#define %(prefix)s_THREAD_LOCAL __thread
#else
#define %(prefix)s_THREADS_INIT do{}while(0)
#define %(prefix)s_IS_MAIN_THREAD (1)
#define %(prefix)s_THREAD_ID (0UL)
#define %(prefix)s_LOCK do{}while(0)
#define %(prefix)s_UNLOCK do{}while(0)
#define %(prefix)s_THREAD_LOCAL
#endif

#ifdef %(prefix)s_LOGFILE
static FILE *%(prefix)s_log_fp = NULL;
#define %(prefix)s_LOG_PREPARE \\
    do { if (!%(prefix)s_log_fp) %(prefix)s_log_prepare(); } while (0)

static void %(prefix)s_log_prepare(void)
{
    %(prefix)s_LOCK;
    if (!%(prefix)s_log_fp) {
        %(prefix)s_log_fp = fopen(%(prefix)s_LOGFILE, \"a+\");
        if (!%(prefix)s_log_fp) {
            fprintf(stderr,
                    %(prefix)s_COLOR_ERROR
                    \"ERROR: could not open logfile %%s: %%s.\"
                    \" Using stderr!\\n\"
                    %(prefix)s_COLOR_CLEAR,
                    %(prefix)s_LOGFILE, strerror(errno));
            %(prefix)s_log_fp = stderr;
        }
    }
    %(prefix)s_UNLOCK;
}
#else
static FILE *%(prefix)s_log_fp = NULL;
#define %(prefix)s_LOG_PREPARE \\
    do{ if (!%(prefix)s_log_fp) %(prefix)s_log_fp = stderr; }while(0)
#endif

#ifdef %(prefix)s_LOG_TIMESTAMP
#ifdef %(prefix)s_LOG_TIMESTAMP_CLOCK_GETTIME
#include <time.h>

#ifndef %(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE
#define %(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE CLOCK_MONOTONIC
#endif

#define %(prefix)s_LOG_TIMESTAMP_SHOW \\
    do { \\
        struct timespec spec = {0, 0}; \\
        clock_gettime(%(prefix)s_LOG_TIMESTAMP_CLOCK_SOURCE, &spec); \\
        fprintf(%(prefix)s_log_fp, \"[%%5lu.%%06lu] \", \\
                (unsigned long)tv.tv_sec, \\
                (unsigned long)tv.tv_usec / 1000); \\
    } while (0)

#else /* fallback to gettimeofday() */

#include <sys/time.h>
#define %(prefix)s_LOG_TIMESTAMP_SHOW \\
    do { \\
        struct timeval tv = {0, 0}; \\
        gettimeofday(&tv, NULL); \\
        fprintf(%(prefix)s_log_fp, \"[%%5lu.%%06lu] \", \\
                (unsigned long)tv.tv_sec, \\
                (unsigned long)tv.tv_usec); \\
    } while (0)

#endif
#else
#define %(prefix)s_LOG_TIMESTAMP_SHOW do{}while(0)
#endif

static void *%(prefix)s_dl_handle = NULL;

static unsigned char %(prefix)s_dl_prepare(void)
{
    unsigned char ok;

    %(prefix)s_THREADS_INIT;

    %(prefix)s_LOCK;
    ok = !!%(prefix)s_dl_handle;
    if (!ok) {
        char *errmsg;
        %(prefix)s_dl_handle = dlopen(\"%(libname)s\", RTLD_LAZY);
        errmsg = dlerror();
        if (errmsg) {
            %(prefix)s_dl_handle = NULL;
            fprintf(stderr,
                    %(prefix)s_COLOR_ERROR
                    \"ERROR: could not dlopen(%(libname)s): %%s\\n\"
                    %(prefix)s_COLOR_CLEAR, errmsg);
        }
        ok = !!%(prefix)s_dl_handle;
    }
    %(prefix)s_UNLOCK;

    return ok;
}

#define %(prefix)s_GET_SYM(v, name, ...) \\
    do { \\
        if (!v) { \\
            if (!%(prefix)s_dl_handle) { \\
                if (!%(prefix)s_dl_prepare()) \\
                    return __VA_ARGS__; \\
            } \\
            %(prefix)s_LOCK; \\
            if (!v) { \\
                char *%(prefix)s_dl_err; \\
                v = dlsym(%(prefix)s_dl_handle, name); \\
                %(prefix)s_dl_err = dlerror(); \\
                if (%(prefix)s_dl_err) { \\
                    fprintf(stderr, \\
                            %(prefix)s_COLOR_ERROR \\
                            \"ERROR: could not dlsym(%%s): %%s\\n\" \\
                            %(prefix)s_COLOR_CLEAR, \\
                            name, %(prefix)s_dl_err); \\
                } \\
            } \\
            %(prefix)s_UNLOCK; \\
            if (!v) \\
                return __VA_ARGS__; \\
        } \\
    } while (0)


static inline void %(prefix)s_log_params_begin(void)
{
    putc('(', %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_param_continue(void)
{
    fputs(\", \", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_params_end(void)
{
    putc(')', %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_params_output_begin(void)
{
    fputs(\"output-parameters=(\", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_param_output_continue(void)
{
    fputs(\", \", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_params_output_end(void)
{
    putc(')', %(prefix)s_log_fp);
}

#ifdef %(prefix)s_LOG_INDENT
static %(prefix)s_THREAD_LOCAL int %(prefix)s_log_indentation = 0;
#endif

static inline void %(prefix)s_log_enter_start(const char *name)
{
    %(prefix)s_LOG_PREPARE;
    %(prefix)s_LOCK;

    %(prefix)s_LOG_TIMESTAMP_SHOW;

#ifdef %(prefix)s_LOG_INDENT
    int i;

    for (i = 0; i < %(prefix)s_log_indentation; i++)
        fputs(%(prefix)s_LOG_INDENT, %(prefix)s_log_fp);
    %(prefix)s_log_indentation++;
#endif

    if (!%(prefix)s_IS_MAIN_THREAD)
        fprintf(%(prefix)s_log_fp, \"[T:%%lu]\", %(prefix)s_THREAD_ID);

    fprintf(%(prefix)s_log_fp, %(prefix)s_COLOR_ENTER \"LOG> %%s\", name);
}

static inline void %(prefix)s_log_enter_end(const char *name)
{
    fputs(%(prefix)s_COLOR_CLEAR \"\\n\", %(prefix)s_log_fp);
    fflush(%(prefix)s_log_fp);
    %(prefix)s_UNLOCK;
    (void)name;
}

static inline void %(prefix)s_log_exit_start(const char *name)
{
    %(prefix)s_LOG_PREPARE;
    %(prefix)s_LOCK;

    %(prefix)s_LOG_TIMESTAMP_SHOW;

#ifdef %(prefix)s_LOG_INDENT
    int i;

    %(prefix)s_log_indentation--;
    for (i = 0; i < %(prefix)s_log_indentation; i++)
        fputs(%(prefix)s_LOG_INDENT, %(prefix)s_log_fp);
#endif

    if (!%(prefix)s_IS_MAIN_THREAD)
        fprintf(%(prefix)s_log_fp, \"[T:%%lu]\", %(prefix)s_THREAD_ID);
    fprintf(%(prefix)s_log_fp, %(prefix)s_COLOR_EXIT \"LOG< %%s\", name);
}

static inline void %(prefix)s_log_exit_return(void)
{
    fputs(\" = \", %(prefix)s_log_fp);
}

static inline void %(prefix)s_log_exit_end(const char *name)
{
    fputs(%(prefix)s_COLOR_CLEAR \"\\n\", %(prefix)s_log_fp);
    fflush(%(prefix)s_log_fp);
    %(prefix)s_UNLOCK;
    (void)name;
}

static inline void %(prefix)s_log_fmt_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%d\", type, name, value);
    else
        fprintf(p, \"(%%s)%%d\", type, value);
}

static inline void %(prefix)s_log_fmt_uint(FILE *p, const char *type, const char *name, unsigned int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%u\", type, name, value);
    else
        fprintf(p, \"(%%s)%%u\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#x\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#x\", type, value);
}

static inline void %(prefix)s_log_fmt_errno(FILE *p, const char *type, const char *name, int value)
{
    const char *msg;
    switch (value) {
        case E2BIG: msg = \"E2BIG\"; break;
        case EACCES: msg = \"EACCES\"; break;
        case EADDRINUSE: msg = \"EADDRINUSE\"; break;
        case EADDRNOTAVAIL: msg = \"EADDRNOTAVAIL\"; break;
        case EAFNOSUPPORT: msg = \"EAFNOSUPPORT\"; break;
        case EAGAIN: msg = \"EAGAIN\"; break;
        case EALREADY: msg = \"EALREADY\"; break;
        case EBADF: msg = \"EBADF\"; break;
        case EBADMSG: msg = \"EBADMSG\"; break;
        case EBUSY: msg = \"EBUSY\"; break;
        case ECANCELED: msg = \"ECANCELED\"; break;
        case ECHILD: msg = \"ECHILD\"; break;
        case ECONNABORTED: msg = \"ECONNABORTED\"; break;
        case ECONNREFUSED: msg = \"ECONNREFUSED\"; break;
        case ECONNRESET: msg = \"ECONNRESET\"; break;
        case EDEADLK: msg = \"EDEADLK\"; break;
        case EDESTADDRREQ: msg = \"EDESTADDRREQ\"; break;
        case EDOM: msg = \"EDOM\"; break;
        case EDQUOT: msg = \"EDQUOT\"; break;
        case EEXIST: msg = \"EEXIST\"; break;
        case EFAULT: msg = \"EFAULT\"; break;
        case EFBIG: msg = \"EFBIG\"; break;
        case EHOSTUNREACH: msg = \"EHOSTUNREACH\"; break;
        case EIDRM: msg = \"EIDRM\"; break;
        case EILSEQ: msg = \"EILSEQ\"; break;
        case EINPROGRESS: msg = \"EINPROGRESS\"; break;
        case EINTR: msg = \"EINTR\"; break;
        case EINVAL: msg = \"EINVAL\"; break;
        case EIO: msg = \"EIO\"; break;
        case EISCONN: msg = \"EISCONN\"; break;
        case EISDIR: msg = \"EISDIR\"; break;
        case ELOOP: msg = \"ELOOP\"; break;
        case EMFILE: msg = \"EMFILE\"; break;
        case EMLINK: msg = \"EMLINK\"; break;
        case EMSGSIZE: msg = \"EMSGSIZE\"; break;
        case EMULTIHOP: msg = \"EMULTIHOP\"; break;
        case ENAMETOOLONG: msg = \"ENAMETOOLONG\"; break;
        case ENETDOWN: msg = \"ENETDOWN\"; break;
        case ENETRESET: msg = \"ENETRESET\"; break;
        case ENETUNREACH: msg = \"ENETUNREACH\"; break;
        case ENFILE: msg = \"ENFILE\"; break;
        case ENOBUFS: msg = \"ENOBUFS\"; break;
        case ENODATA: msg = \"ENODATA\"; break;
        case ENODEV: msg = \"ENODEV\"; break;
        case ENOENT: msg = \"ENOENT\"; break;
        case ENOEXEC: msg = \"ENOEXEC\"; break;
        case ENOLCK: msg = \"ENOLCK\"; break;
        case ENOLINK: msg = \"ENOLINK\"; break;
        case ENOMEM: msg = \"ENOMEM\"; break;
        case ENOMSG: msg = \"ENOMSG\"; break;
        case ENOPROTOOPT: msg = \"ENOPROTOOPT\"; break;
        case ENOSPC: msg = \"ENOSPC\"; break;
        case ENOSR: msg = \"ENOSR\"; break;
        case ENOSTR: msg = \"ENOSTR\"; break;
        case ENOSYS: msg = \"ENOSYS\"; break;
        case ENOTCONN: msg = \"ENOTCONN\"; break;
        case ENOTDIR: msg = \"ENOTDIR\"; break;
        case ENOTEMPTY: msg = \"ENOTEMPTY\"; break;
        case ENOTSOCK: msg = \"ENOTSOCK\"; break;
        case ENOTSUP: msg = \"ENOTSUP\"; break;
        case ENOTTY: msg = \"ENOTTY\"; break;
        case ENXIO: msg = \"ENXIO\"; break;
        //case EOPNOTSUPP: msg = \"EOPNOTSUPP\"; break;
        case EOVERFLOW: msg = \"EOVERFLOW\"; break;
        case EPERM: msg = \"EPERM\"; break;
        case EPIPE: msg = \"EPIPE\"; break;
        case EPROTO: msg = \"EPROTO\"; break;
        case EPROTONOSUPPORT: msg = \"EPROTONOSUPPORT\"; break;
        case EPROTOTYPE: msg = \"EPROTOTYPE\"; break;
        case ERANGE: msg = \"ERANGE\"; break;
        case EROFS: msg = \"EROFS\"; break;
        case ESPIPE: msg = \"ESPIPE\"; break;
        case ESRCH: msg = \"ESRCH\"; break;
        case ESTALE: msg = \"ESTALE\"; break;
        case ETIME: msg = \"ETIME\"; break;
        case ETIMEDOUT: msg = \"ETIMEDOUT\"; break;
        case ETXTBSY: msg = \"ETXTBSY\"; break;
        //case EWOULDBLOCK: msg = \"EWOULDBLOCK\"; break;
        case EXDEV: msg = \"EXDEV\"; break;
        default: msg = \"?UNKNOWN?\";
    };
    if (name)
        fprintf(p, \"%%s %%s=%%d %%s\", type, name, value, msg);
    else
        fprintf(p, \"(%%s)%%d %%s\", type, value, msg);
}

static inline void %(prefix)s_log_fmt_octal_int(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#o\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#o\", type, value);
}

static inline void %(prefix)s_log_fmt_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hhd (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%hhd (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_uchar(FILE *p, const char *type, const char *name, unsigned char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hhu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hhu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hhx (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%#hhx (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_octal_char(FILE *p, const char *type, const char *name, char value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hho (%%c)\", type, name, value, value);
    else
        fprintf(p, \"(%%s)%%#hho (%%c)\", type, value, value);
}

static inline void %(prefix)s_log_fmt_short(FILE *p, const char *type, const char *name, short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hd\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hd\", type, value);
}

static inline void %(prefix)s_log_fmt_ushort(FILE *p, const char *type, const char *name, unsigned short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%hu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%hu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_short(FILE *p, const char *type, const char *name, short value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#hx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#hx\", type, value);
}

static inline void %(prefix)s_log_fmt_long(FILE *p, const char *type, const char *name, long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%ld\", type, name, value);
    else
        fprintf(p, \"(%%s)%%ld\", type, value);
}

static inline void %(prefix)s_log_fmt_ulong(FILE *p, const char *type, const char *name, unsigned long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%lu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%lu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_long(FILE *p, const char *type, const char *name, long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#lx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#lx\", type, value);
}

static inline void %(prefix)s_log_fmt_long_long(FILE *p, const char *type, const char *name, long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%lld\", type, name, value);
    else
        fprintf(p, \"(%%s)%%lld\", type, value);
}

static inline void %(prefix)s_log_fmt_ulong_long(FILE *p, const char *type, const char *name, unsigned long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%llu\", type, name, value);
    else
        fprintf(p, \"(%%s)%%llu\", type, value);
}

static inline void %(prefix)s_log_fmt_hex_long_long(FILE *p, const char *type, const char *name, long long value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%#llx\", type, name, value);
    else
        fprintf(p, \"(%%s)%%#llx\", type, value);
}

static inline void %(prefix)s_log_fmt_bool(FILE *p, const char *type, const char *name, int value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%s\", type, name, value ? \"true\" : \"false\");
    else
        fprintf(p, \"(%%s)%%s\", type, value ? \"true\" : \"false\");
}

static inline void %(prefix)s_log_fmt_string(FILE *p, const char *type, const char *name, const char *value)
{
    if (name) {
        if (value)
            fprintf(p, \"%%s %%s=\\\"%%s\\\"\", type, name, value);
        else
            fprintf(p, \"%%s %%s=(null)\", type, name);
    } else {
        if (value)
            fprintf(p, \"(%%s)\\\"%%s\\\"\", type, value);
        else
            fprintf(p, \"(%%s)(null)\", type);
    }
}

static inline void %(prefix)s_log_fmt_double(FILE *p, const char *type, const char *name, double value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%g\", type, name, value);
    else
        fprintf(p, \"(%%s)%%g\", type, value);
}

static inline void %(prefix)s_log_fmt_pointer(FILE *p, const char *type, const char *name, const void *value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%p\", type, name, value);
    else
        fprintf(p, \"(%%s)%%p\", type, value);
}

static inline void %(prefix)s_log_checker_null(FILE *p, const char *type, const void *value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"NULL was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_non_null(FILE *p, const char *type, const void *value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"non-NULL was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_zero(FILE *p, const char *type, long long value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"ZERO was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_non_zero(FILE *p, const char *type, long long value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"non-ZERO was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_false(FILE *p, const char *type, long long value)
{
    if (value) fputs(%(prefix)s_COLOR_ERROR \"FALSE was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_true(FILE *p, const char *type, long long value)
{
    if (!value) fputs(%(prefix)s_COLOR_ERROR \"TRUE was expected\", p);
    (void)type;
}

static inline void %(prefix)s_log_checker_errno(FILE *p, const char *type, long long value)
{
    if (!errno) fprintf(p, %(prefix)s_COLOR_ERROR \"%%s\", strerror(errno));
    (void)type;
    (void)value;
}

""" % repl)
    if cfg:
        try:
            overrides = cfg.get("global", "overrides", vars=repl)
        except Exception, e:
            overrides = None
        if overrides:
            for o in overrides.split(","):
                f.write("#include \"%s\"\n" % o.strip())


def get_type_alias(type, ctxt):
    cfg = ctxt["cfg"]
    if cfg:
        try:
            return cfg.get("type-aliases", type)
        except Exception, e:
            pass

    typedefs = ctxt["header_contents"]["typedef"]
    alias = Typedef.find(type.replace("-", " "))
    if not alias:
        typename = re.sub("[[][0-9]+[]]", "[]", type)
        if typename != type:
            return typename
        type = typename
        typename = type.replace("[]", "*")
        if typename != type:
            return typename
        return None

    return alias.type_formatter().replace(" ", "-")


def type_is_pointer(type, ctxt):
    if "*" in type:
        return True
    if "[" in type:
        return True
    if type == "va_list":
        return True

    typedefs = ctxt["header_contents"]["typedef"]
    alias = Typedef.find(type.replace("-", " "))
    if not alias:
        return False
    if alias.pointer > 0:
        return True
    reference = alias.reference
    if isinstance(reference, FunctionPointer):
        return True
    return type_is_pointer(str(reference), ctxt)


provided_formatters = {
    "int": "%(prefix)s_log_fmt_int",
    "signed-int": "%(prefix)s_log_fmt_int",
    "unsigned-int": "%(prefix)s_log_fmt_uint",
    "unsigned": "%(prefix)s_log_fmt_uint",
    "int32_t": "%(prefix)s_log_fmt_int",
    "uint32_t": "%(prefix)s_log_fmt_uint",

    "char": "%(prefix)s_log_fmt_char",
    "signed-char": "%(prefix)s_log_fmt_char",
    "unsigned-char": "%(prefix)s_log_fmt_uchar",
    "int8_t": "%(prefix)s_log_fmt_char",
    "uint8_t": "%(prefix)s_log_fmt_uchar",

    "short": "%(prefix)s_log_fmt_short",
    "signed-short": "%(prefix)s_log_fmt_short",
    "unsigned-short": "%(prefix)s_log_fmt_ushort",
    "signed-short-int": "%(prefix)s_log_fmt_short",
    "unsigned-short-int": "%(prefix)s_log_fmt_ushort",
    "int16_t": "%(prefix)s_log_fmt_short",
    "uint16_t": "%(prefix)s_log_fmt_ushort",

    "long": "%(prefix)s_log_fmt_long",
    "signed-long": "%(prefix)s_log_fmt_long",
    "unsigned-long": "%(prefix)s_log_fmt_ulong",
    "signed-long-int": "%(prefix)s_log_fmt_long",
    "unsigned-long-int": "%(prefix)s_log_fmt_ulong",

    "long-long": "%(prefix)s_log_fmt_long_long",
    "signed-long-long": "%(prefix)s_log_fmt_long_long",
    "unsigned-long-long": "%(prefix)s_log_fmt_ulong_long",
    "signed-long-long-int": "%(prefix)s_log_fmt_long_long",
    "unsigned-long-long-int": "%(prefix)s_log_fmt_ulong_long",
    "int64_t": "%(prefix)s_log_fmt_long_long",
    "uint64_t": "%(prefix)s_log_fmt_ulong_long",

    "bool": "%(prefix)s_log_fmt_bool",
    "Bool": "%(prefix)s_log_fmt_bool",
    "_Bool": "%(prefix)s_log_fmt_bool",
    "BOOL": "%(prefix)s_log_fmt_bool",

    "double": "%(prefix)s_log_fmt_double",
    "float": "%(prefix)s_log_fmt_double",

    "char-*": "%(prefix)s_log_fmt_string",
    "const-char-*": "%(prefix)s_log_fmt_string",
    "char-[]": "%(prefix)s_log_fmt_string",
    "char[]": "%(prefix)s_log_fmt_string",
    "const-char-[]": "%(prefix)s_log_fmt_string",
    "const-char[]": "%(prefix)s_log_fmt_string",
    "const-*-char-*": "%(prefix)s_log_fmt_string",
    "void-*": "%(prefix)s_log_fmt_pointer",
    }

def get_type_formatter(func, name, type, ctxt):
    type = type.replace(" ", "-")

    formatter = "%(prefix)s_log_fmt_long_long"
    if type_is_pointer(type, ctxt):
        formatter = "%(prefix)s_log_fmt_pointer"
    elif type in provided_formatters:
        formatter = provided_formatters[type]
    formatter = formatter % ctxt

    cfg = ctxt["cfg"]
    if not cfg:
        return formatter

    safe = False
    try:
        safe = cfg.getboolean("global", "assume-safe-formatters")
    except Exception, e:
        pass

    try:
        custom_formatter = cfg.get("type-formatters", type, vars=ctxt)
    except Exception, e:
        custom_formatter = None

    section = "func-%s" % (func,)

    if name == "return":
        key = "return"
    else:
        key = "parameter-%s" % name

    try:
        safe = cfg.getboolean(section, key + "-safe")
    except Exception, e:
        pass

    try:
        param_formatter = cfg.get(section, key + "-formatter", vars=ctxt)
    except Exception, e:
        param_formatter = None

    if param_formatter:
        return param_formatter

    if not safe:
        try:
            safe = cfg.getboolean("safe-formatters", type)
        except Exception, e:
            safe_pointer_formatter = "%(prefix)s_log_fmt_pointer" % ctxt
            if not safe and custom_formatter == safe_pointer_formatter:
                safe = True

    if safe:
        if custom_formatter:
            return custom_formatter
        elif type_is_pointer(type, ctxt) and type in provided_formatters:
            formatter = provided_formatters[type] % ctxt
    elif custom_formatter:
        print "Ignoring formatter '%s': %s not safe" % (custom_formatter, type)
        custom_formatter = None

    alias = type
    while True:
        alias = get_type_alias(alias, ctxt)
        if not alias:
            break
        custom_formatter = get_type_formatter(func, name, alias, ctxt)
        if custom_formatter:
            return custom_formatter

    return formatter


def get_type_dereferenced_formatter(type, ctxt):
    idx = type.rfind("*")
    if idx >= 0:
        if idx != len(type) - 1:
            return None # it's a function pointer
        dtype = type[:idx].replace(" ", "-")
        while dtype[-1] == "-":
            dtype = dtype[:-1]
        cfg = ctxt["cfg"]
        if cfg:
            try:
                formatter = cfg.get("type-formatters", dtype, vars=ctxt)
                if formatter:
                    return formatter % ctxt
            except Exception, e:
                pass

        formatter = provided_formatters.get(dtype)
        if formatter:
            return formatter % ctxt
        return None
    else:
        alias = type
        while True:
            alias = get_type_alias(alias, ctxt)
            if not alias:
                return None
            if "*" in alias:
                return get_type_dereferenced_formatter(alias, ctxt)
        return None

# checkers:
#     %(prefix)s_log_checker_null
#     %(prefix)s_log_checker_non_null
#     %(prefix)s_log_checker_zero
#     %(prefix)s_log_checker_non_zero
#     %(prefix)s_log_checker_false
#     %(prefix)s_log_checker_true
#     %(prefix)s_log_checker_errno
def get_return_checker(func, type, ctxt):
    cfg = ctxt["cfg"]
    if not cfg:
        return

    type = type.replace(" ", "-")
    try:
        checker = cfg.get("return-checkers", type, vars=ctxt)
    except Exception, e:
        checker = None
        alias = type
        while not checker:
            alias = get_type_alias(alias, ctxt)
            if not alias:
                break
            checker = get_return_checker(func, alias, ctxt)

    section = "func-%s" % (func,)
    try:
        custom_checker = cfg.get(section, "return-checker", vars=ctxt)
    except Exception, e:
        custom_checker = None

    return custom_checker or checker


def generate_log_params(f, func, ctxt):
    if not func.parameters or \
       (func.parameters[0].pointer == 0 and
        func.parameters[0].type.name == "void"):
        return
    prefix = ctxt["prefix"]
    f.write("    %s_log_params_begin();\n" % (prefix,))
    for i, p in enumerate(func.parameters):
        type = p.type_formatter()
        name = p.name
        if "[" in name:
            idx = name.find("[")
            type += " " + re.sub("[0-9]", "", name[idx:])
            name = name[:idx]
        formatter = get_type_formatter(func.name, name, type, ctxt)
        f.write("    errno = %s_bkp_errno;\n" % prefix)
        f.write("    %s(%s_log_fp, \"%s\", \"%s\", %s);\n" %
                (formatter, prefix, type, name, name))
        if i + 1 < len(func.parameters):
            f.write("    %s_log_param_continue();\n" % (prefix,))
    f.write("    %s_log_params_end();\n" % (prefix,))


def generate_log_output_params(f, func, ctxt):
    if not func.parameters or \
       (func.parameters[0].pointer == 0 and
        func.parameters[0].type.name == "void"):
        return
    cfg = ctxt["cfg"]
    if not cfg:
        return
    prefix = ctxt["prefix"]
    f.write("    %s_log_params_output_begin();\n" % (prefix,))
    for i, p in enumerate(func.parameters):
        type = p.type_formatter()
        name = p.name
        if "[" in name:
            idx = name.find("[")
            type += " " + re.sub("[0-9]", "", name[idx:])
            name = name[:idx]

        section = "func-%s" % (func.name,)
        key = "parameter-%s" % (name,)
        try:
            is_return = cfg.get(section, key + "-return")
            if not is_return:
                continue
        except Exception, e:
            continue
        try:
            formatter = cfg.get(section, key + "-return-formatter")
        except Exception, e:
            formatter = None

        if not formatter:
            formatter = get_type_dereferenced_formatter(type, ctxt)
            if not formatter:
                print ("function %s() has output parameter %r "
                       "but no formatter is known. Ignore") % (func.name, name)
                continue

        f.write("""\
    if (%(name)s) {
        errno = %(prefix)s_bkp_errno;
        %(formatter)s(%(prefix)s_log_fp, \"%(type)s\", \"*%(name)s\", *%(name)s);
""" % {"name": name,
       "prefix": prefix,
       "formatter": formatter,
       "type": type,
       })
        if i + 1 < len(func.parameters):
            f.write("        %s_log_param_output_continue();\n" % (prefix,))
        f.write("    }\n")
    f.write("    %s_log_params_output_end();\n" % (prefix,))


def generate_func(f, func, ctxt):
    if func.parameters and func.parameters[-1].name == "...":
        print "Ignored: %s() cannot handle variable arguments" % (func.name,)
        return

    if func.ret_pointer > 0 or type_is_pointer(str(func.ret_type), ctxt):
        ret_default = "NULL"
    else:
        ret_default = "0"

    cfg_section = "func-%s" % func.name
    if ctxt["cfg"]:
        try:
            ret_default = ctxt["cfg"].get(cfg_section, "return-default")
        except Exception, e:
            pass

    prefix = ctxt["prefix"]
    func.parameters_unnamed_fix(prefix + "_p_")
    ret_type = str(func.ret_type) + " *" * func.ret_pointer
    ret_name = "%s_ret" % (prefix,)
    repl = {
        "prefix": prefix,
        "name": func.name,
        "internal_name": "%s_f_%s" % (prefix, func.name),
        "ret_type": ret_type,
        "ret_name": ret_name,
        "ret_default": ret_default,
        "params_decl": func.parameters_str(),
        "params_names": func.parameters_names_str(),
        }
    returns_value = ret_type != "void"

    f.write("""
%(ret_type)s %(name)s(%(params_decl)s)
{
    static %(ret_type)s (*%(internal_name)s)(%(params_decl)s) = NULL;
    int %(prefix)s_bkp_errno = errno;
""" % repl)
    if returns_value:
        f.write("""\
    %(ret_type)s %(ret_name)s = %(ret_default)s;
    %(prefix)s_GET_SYM(%(internal_name)s, \"%(name)s\", %(ret_name)s);
""" % repl)
    else:
        f.write("    %(prefix)s_GET_SYM(%(internal_name)s, \"%(name)s\");\n" %
                repl)

    f.write("\n    %(prefix)s_log_enter_start(\"%(name)s\");\n" % repl)
    generate_log_params(f, func, ctxt)
    f.write("    %(prefix)s_log_enter_end(\"%(name)s\");\n" % repl)

    f.write("\n    errno = %(prefix)s_bkp_errno;\n    " % repl)

    if returns_value:
        f.write("%s = " % (ret_name,))

    override = None
    if ctxt["cfg"]:
        try:
            override = ctxt["cfg"].get(cfg_section, "override")
        except Exception, e:
            pass
    if override:
        repl["override"] = override
        f.write("%(override)s(%(internal_name)s, %(params_names)s);\n" % repl)
    else:
        f.write("%(internal_name)s(%(params_names)s);\n" % repl)

    f.write("    %(prefix)s_bkp_errno = errno;\n" % repl)
    f.write("\n    %(prefix)s_log_exit_start(\"%(name)s\");\n" % repl)
    generate_log_params(f, func, ctxt)

    if returns_value:
        formatter = get_type_formatter(func.name, "return", ret_type, ctxt)
        f.write("    %(prefix)s_log_exit_return();\n" % repl)
        f.write("    errno = %(prefix)s_bkp_errno;\n" % repl)
        f.write("    %s(%s_log_fp, \"%s\", NULL, %s);\n" %
                (formatter, prefix, ret_type, ret_name))
        checker = get_return_checker(func.name, ret_type, ctxt)
        if checker:
            f.write("    errno = %(prefix)s_bkp_errno;\n" % repl)
            f.write("    %s(%s_log_fp, \"%s\", %s);\n" %
                    (checker, prefix, ret_type, ret_name))

    generate_log_output_params(f, func, ctxt)
    f.write("    %(prefix)s_log_exit_end(\"%(name)s\");\n" % repl)

    if returns_value:
        f.write("\n    errno = %(prefix)s_bkp_errno;\n" % repl)
        f.write("    return %s;\n" % (ret_name,))

    f.write("}\n")


def generate(outfile, ctxt):
    f = open(outfile, "w")

    cfg = ctxt["cfg"]
    fignore_regexp = config_get_regexp(cfg, "global", "ignore-functions-regexp")
    fselect_regexp = config_get_regexp(cfg, "global", "select-functions-regexp")

    generate_preamble(f, ctxt)
    funcs = ctxt["header_contents"]["function"].items()
    funcs.sort(cmp=lambda a, b: cmp(a[0], b[0]))
    for name, func in funcs:
        if fignore_regexp and fignore_regexp.match(name):
            print "Ignoring %s as requested" % (name,)
            continue
        elif fselect_regexp and not fselect_regexp.match(name):
            continue
        generate_func(f, func, ctxt)
    f.close()


def generate_makefile(makefile, sourcefile, ctxt):
    source_dir = os.path.dirname(sourcefile)
    makefile_dir = os.path.dirname(makefile)

    if source_dir == makefile_dir:
        sourcename = os.path.basename(sourcefile)
        makefile_tmpl = os.path.basename(sourcefile)
    else:
        print ("WARNING: source and makefile are not in the same folder, "
               "using absolute paths!")
        sourcename = sourcefile
        makefile_tmpl = makefile

    sourcename = os.path.splitext(sourcename)[0]

    repl = {
        "prefix": ctxt["prefix"],
        "sourcefile": sourcefile,
        "sourcename": sourcename,
        "makefile": makefile_tmpl,
        "cflags": ctxt["cflags"],
        "ldflags": ctxt["ldflags"],
        }
    f = open(makefile, "w")
    f.write("""\
CFLAGS = -Wall -Wextra %(cflags)s $(EXTRA_CFLAGS)
LDFLAGS = -ldl -fPIC %(ldflags)s $(EXTRA_LDFLAGS)

BINS = \\
    %(sourcename)s.so \\
    %(sourcename)s-color.so \\
    %(sourcename)s-color-timestamp.so \\
    %(sourcename)s-color-threads.so \\
    %(sourcename)s-color-threads-timestamp.so \\
    %(sourcename)s-color-indent.so \\
    %(sourcename)s-color-indent-timestamp.so \\
    %(sourcename)s-color-indent-threads.so \\
    %(sourcename)s-color-indent-threads-timestamp.so

.PHONY: all clean
all: $(BINS)
clean:
\trm -f $(BINS) *~

%(sourcename)s.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-threads.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_HAVE_THREADS=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-threads-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_HAVE_THREADS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-indent.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-indent-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) $< -o $@

%(sourcename)s-color-indent-threads.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_HAVE_THREADS=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

%(sourcename)s-color-indent-threads-timestamp.so: %(sourcefile)s %(makefile)s
\t$(CC) -shared -D%(prefix)s_USE_COLORS=1 -D%(prefix)s_LOG_INDENT='\"  \"' -D%(prefix)s_HAVE_THREADS=1 -D%(prefix)s_LOG_TIMESTAMP=1 $(CFLAGS) $(LDFLAGS) -lpthread $< -o $@

""" % repl)
    f.close()


def generate_type(f, type, ctxt, indent_level=1):
    f.write(type.decl_name())

    if isinstance(type, Enum):
        if type.members:
            f.write(" {\n")
            for i, (member, value) in enumerate(type.members):
                f.write("\t" * (indent_level + 1))
                f.write(member)
                if value:
                    f.write(" = %s" % (value,))
                if i + 1 < len(type.members):
                    f.write(",")
                f.write("\n")
            f.write("\t" * indent_level)
            f.write("}")
    else:
        if type.members:
            f.write(" {\n")
            for p in type.members:
                f.write("\t" * (indent_level + 1))

                parts = p[0].split(" ")
                if parts[0] in ("enum", "struct", "union") and \
                   parts[1].startswith("<"):
                    sub = ctxt["header_contents"][parts[0]][parts[1]]
                    generate_type(f, sub, ctxt, indent_level + 1)
                    f.write(" %s;\n" % p[1])
                elif len(p) == 3:
                    f.write("%s (*%s)(%s);\n" % (p[0], p[1], ", ".join(p[2])))
                else:
                    f.write("%s %s;\n" % p)

            f.write("\t" * indent_level)
            f.write("}")


def generate_types_file(types_file, header, ctxt):
    data = ctxt["header_contents"]

    f = open(types_file, "w")
    f.write("""\
/* types file automatically generated from %(header)s by %(progname)s.
 * %(timestamp)s
 */
#ifndef %(prefix)s_TYPES_FILE
#define %(prefix)s_TYPES_FILE 1
""" % {"header": header,
       "progname": progname,
       "timestamp": timestamp,
       "prefix": ctxt["prefix"],
       })

    def needs_emission(t):
        return not isinstance(t, (BuiltinType, FunctionPointer))

    order = []
    done = set()
    todo = list(x for x in _types_order if x.name and not
                isinstance(x, (BuiltinType, FunctionPointer, FunctionName)))
    reorder_count = 0
    while todo:
        x = todo.pop(0)
        if isinstance(x, Enum):
            order.append(x)
            done.add(x)
            reorder_count = 0
        elif isinstance(x, Group):
            for y in x.members:
                if needs_emission(y.type) and y.type.name and \
                       y.type not in done:
                    print "Note: %s %s depends on %s, reorder..." % \
                          (x.cls, x.name, y)
                    todo.append(x)
                    reorder_count += 1
                    break
            else:
                order.append(x)
                done.add(x)
                reorder_count = 0
        elif isinstance(x, Typedef):
            if needs_emission(x.reference) and x.reference.name and \
                   x.reference not in done:
                print "Note: typedef %s depends on %s, reorder..." % \
                      (x.name, x.reference)
                todo.append(x)
                reorder_count += 1
            else:
                order.append(x)
                done.add(x)
                reorder_count = 0
        else:
            raise TypeError("unexpected type %r" % x)

        if reorder_count > len(todo):
            raise ValueError("circular dependency: %r" % (todo,))

    for t in order:
        f.write("%s;\n" %
                t.pretty_format(prefix="\t", indent="\t", newline="\n"))

    f.write("#endif /* %s_TYPES_FILE */\n" % (ctxt["prefix"],))
    f.close()


def generate_enum(f, t, ctxt):
    repl = {
        "prefix": ctxt["prefix"],
        "name": t.name,
        "type": t.pretty_format("", show_members=False),
        }

    f.write("""

static inline void %(prefix)s_log_fmt_custom_valuestr_enum_%(name)s(FILE *p, const char *type, const char *name, %(type)s value)
{
    putc('[', p);
    switch (value) {
""" % repl)
    for k, v in t.members:
        f.write("        case %s: fputs(\"%s\", p); break;\n" % (k, k))

    f.write("""\
        default: fputs(\"???\", p);
    }
    putc(']', p);
}

static inline void %(prefix)s_log_fmt_custom_value_enum_%(name)s(FILE *p, const char *type, const char *name, %(type)s value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%d \", type, name, value);
    else
        fprintf(p, \"(%%s)%%d \", type, value);
}

static inline void %(prefix)s_log_fmt_custom_pointer_enum_%(name)s(FILE *p, const char *type, const char *name, const %(type)s *value)
{
    if (name)
        fprintf(p, \"%%s %%s=%p \", type, name, value);
    else
        fprintf(p, \"(%%s)%p \", type, value);
    if (value)
        %(prefix)s_log_fmt_custom_valuestr_enum_%(name)s(p, *value);
    else
        fputs(\"[???]\", p);
}
""" % repl)


def generate_group_member(f, m, ctxt, access):
    if not (m.pointer == 0 and isinstance(m.type, Group)):
        type = m.type_formatter()
        formatter = get_type_formatter("", m.name, type, ctxt)
        if formatter:
            f.write("        %s(p, \"%s\", \"%s\", %s%s);\n" %
                    (formatter, type, m.name, access, m.name))
        else:
            f.write("        fputs(\"unhandled member '%s %s'\", p);\n" %
                    (type, m.name))
    else:
        type = m.type.pretty_format(show_members=False)
        f.write("        fputs(\"%s %s=\", p);\n" % (type, m.name))
        subaccess = access + ("%s." % m.name)
        generate_group_member_list(f, m.type, ctxt, subaccess)


def generate_group_member_list(f, t, ctxt, access):
    f.write("        putc('{', p);\n")
    for i, v in enumerate(t.members):
        generate_group_member(f, v, ctxt, access)
        if i + 1 < len(t.members):
            f.write("        fputs(\", \", p);\n")
    f.write("        putc('}', p);\n")


def generate_group(f, t, ctxt):
    repl = {
        "prefix": ctxt["prefix"],
        "name": t.name,
        "type": t.pretty_format("", show_members=False),
        "cls": t.cls,
        }

    f.write("""
static inline void %(prefix)s_log_fmt_custom_pointer_%(cls)s_%(name)s(FILE *p, const char *type, const char *name, const %(type)s *value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%p\", type, name, value);
    else
        fprintf(p, \"(%%s)%%p\", type, value);

    if (value) {
""" % repl)
    generate_group_member_list(f, t, ctxt, "value->")
    f.write("""\
    }
}

static inline void %(prefix)s_log_fmt_custom_pointer_pointer_%(cls)s_%(name)s(FILE *p, const char *type, const char *name, const %(type)s **value)
{
    if (name)
        fprintf(p, \"%%s %%s=%%p\", type, name, value);
    else
        fprintf(p, \"(%%s)%%p\", type, value);
    if (value) {
""" % repl)
    generate_group_member_list(f, t, ctxt, "(*value)->")
    f.write("""\
    }
}

static inline void %(prefix)s_log_fmt_custom_value_%(cls)s_%(name)s(FILE *p, const char *type, const char *name, %(type)s value)
{
    if (name)
        fprintf(p, \"%%s %%s=\", type, name);
    else
        fprintf(p, \"(%%s)\", type);
""" % repl)
    generate_group_member_list(f, t, ctxt, "value.")
    f.write("}\n")


def generate_custom_formatters(formatters_file, header, ctxt):
    data = ctxt["header_contents"]

    f = open(formatters_file, "w")
    f.write("""\
/* custom formatters file automatically generated from \
%(header)s by %(progname)s.
 * %(timestamp)s
 */
""" % {"header": header,
       "progname": progname,
       "timestamp": timestamp,
       })

    lst = list(data["enum"].itervalues())
    lst.sort(cmp=lambda a, b: cmp(a.name, b.name))
    for t in lst:
        assert(t.name)
        if not t.members:
            continue
        generate_enum(f, t, ctxt)

    lst = list(data["struct"].itervalues())
    lst.sort(cmp=lambda a, b: cmp(a.name, b.name))
    for t in lst:
        assert(t.name)
        if not t.members:
            continue
        generate_group(f, t, ctxt)

    lst = list(data["union"].itervalues())
    lst.sort(cmp=lambda a, b: cmp(a.name, b.name))
    for t in lst:
        assert(t.name)
        if not t.members:
            continue
        generate_group(f, t, ctxt)

    f.close()



def prefix_from_libname(libname):
    prefix = libname
    if prefix.startswith("lib"):
        prefix = prefix[len("lib"):]
    try:
        prefix = prefix[:prefix.index(".")]
    except ValueError:
        pass
    return "_log_" + prefix


def config_get_regexp(cfg, section, key, default=None):
    if cfg:
        try:
            s = cfg.get(section, key)
            if s:
                return re.compile(s)
        except Exception, e:
            pass
    if default:
        return re.compile(default)
    return None


if __name__ == "__main__":
    usage = "usage: %prog [options] <header.h> <libname.so> <outfile.c>"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-c", "--config", action="store", default=None,
                      help="Configuration file to use with this library")
    parser.add_option("-p", "--prefix", action="store", default=None,
                      help="Symbol prefix to use (defaults to autogenerated)")
    parser.add_option("-M", "--makefile", action="store", default=None,
                      help="Generate sample makefile")
    parser.add_option("--makefile-cflags", action="store", default=None,
                      help="CFLAGS to use with makefile")
    parser.add_option("--makefile-ldflags", action="store", default=None,
                      help="LDFLAGS to use with makefile")
    parser.add_option("-t", "--types-file", action="store", default=None,
                      help="Generate header file with all parsed types")
    parser.add_option("-F", "--custom-formatters", action="store", default=None,
                      help=("Generate C file with custom formatters based on "
                            "typedefs, enums, structs and unions"))
    parser.add_option("-D", "--dump", action="store_true", default=False,
                      help="Dump parsed elements")

    options, args = parser.parse_args()
    try:
        header = args[0]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: header.h")
    try:
        libname = args[1]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: libname.so")
    try:
        outfile = args[2]
    except IndexError:
        parser.print_help()
        raise SystemExit("Missing parameter: outfile.c")

    cfg = None
    if options.config:
        cfg = ConfigParser()
        cfg.read([options.config])

    header_contents = header_tree(header, cfg)
    if options.dump:
        hc = header_contents.items()
        hc.sort(cmp=lambda a, b: cmp(a[0], b[0]))
        for k, v in hc:
            c = v.values()
            if not c:
                continue
            print "%s:" % (k,)
            c.sort(cmp=lambda a, b: cmp(a.name, b.name))
            for p in c:
                print "\t%s" % (p,)
            print

    prefix = options.prefix
    if not prefix:
        prefix = prefix_from_libname(libname)

    prefix = re.sub("[^a-zA-z0-9_]", "_", prefix)

    ctxt = {
        "header": header,
        "header_contents": header_contents,
        "prefix": prefix,
        "libname": libname,
        "cfg": cfg,
        }
    generate(outfile, ctxt)

    if options.makefile:
        ctxt["cflags"] = options.makefile_cflags or ""
        ctxt["ldflags"] = options.makefile_ldflags or ""
        generate_makefile(options.makefile, outfile, ctxt)

    if options.types_file:
        generate_types_file(options.types_file, header, ctxt)

    if options.custom_formatters:
        generate_custom_formatters(options.custom_formatters, header, ctxt)
