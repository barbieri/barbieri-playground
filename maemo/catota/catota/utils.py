#!/usr/bin/env

import os
import stat
import sys
import logging
import urllib
import gobject
import imp

log = logging.getLogger("catota.utils")

__all__ = ("which", "parse_qsl", "gsignal", "load_plugins", "PluginSet")

def which(app):
    """function to implement which(1) unix command"""
    pl = os.environ["PATH"].split(os.pathsep)
    for p in pl:
        path = os.path.join(p, app)
        if os.path.isfile(path):
            st = os.stat(path)
            if st[stat.ST_MODE] & 0111:
                return path
    return ""
# which()


# from python cgi
def parse_qsl(qs, keep_blank_values=0, strict_parsing=0):
    """Parse a query given as a string argument.

    Arguments:

    qs: URL-encoded query string to be parsed

    keep_blank_values: flag indicating whether blank values in
        URL encoded queries should be treated as blank strings.  A
        true value indicates that blanks should be retained as blank
        strings.  The default false value indicates that blank values
        are to be ignored and treated as if they were  not included.

    strict_parsing: flag indicating what to do with parsing errors. If
        false (the default), errors are silently ignored. If true,
        errors raise a ValueError exception.

    Returns a list, as G-d intended.
    """
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r = []
    for name_value in pairs:
        if not name_value and not strict_parsing:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            if strict_parsing:
                raise ValueError, "bad query field: %r" % (name_value,)
            # Handle case of a control-name with no equal sign
            if keep_blank_values:
                nv.append('')
            else:
                continue
        if len(nv[1]) or keep_blank_values:
            name = urllib.unquote(nv[0].replace('+', ' '))
            value = urllib.unquote(nv[1].replace('+', ' '))
            r.append((name, value))

    return r
# parse_qsl()


# from kiwi.utils
def gsignal(name, *args, **kwargs):
    """
    Add a GObject signal to the current object.
    It current supports the following types:
      - str, int, float, long, object, enum
    @param name:     name of the signal
    @type name:      string
    @param args:     types for signal parameters,
      if the first one is a string 'override', the signal will be
      overridden and must therefor exists in the parent GObject.
    @keyword flags: A combination of;
      - gobject.SIGNAL_RUN_FIRST
      - gobject.SIGNAL_RUN_LAST
      - gobject.SIGNAL_RUN_CLEANUP
      - gobject.SIGNAL_NO_RECURSE
      - gobject.SIGNAL_DETAILED
      - gobject.SIGNAL_ACTION
      - gobject.SIGNAL_NO_HOOKS
    @keyword retval: return value in signal callback
    """

    frame = sys._getframe(1)
    try:
        locals = frame.f_locals
    finally:
        del frame

    dict = locals.setdefault('__gsignals__', {})

    if args and args[0] == 'override':
        dict[name] = 'override'
    else:
        retval = kwargs.get('retval', None)
        if retval is None:
            default_flags = gobject.SIGNAL_RUN_FIRST
        else:
            default_flags = gobject.SIGNAL_RUN_LAST

        flags = kwargs.get('flags', default_flags)
        if retval is not None and flags != gobject.SIGNAL_RUN_LAST:
            raise TypeError(
                "You cannot use a return value without setting flags to "
                "gobject.SIGNAL_RUN_LAST")

        dict[name] = (flags, retval, args)
# gsignal()


def _load_module(pathlist, name):
    fp, path, desc = imp.find_module(name, pathlist)
    try:
        module = imp.load_module(name, fp, path, desc)
        return module
    finally:
        if fp:
            fp.close()
# _load_module()


class PluginSet(object):
    def __init__(self, basetype, *items):
        self.basetype = basetype
        self.map = {}
        self.list = []

        for i in items:
            self._add(i)
        self._sort()
    # __init__()


    def _add(self, item):
        self.map[item.name] = item
        self.list.append(item)
    # _add()


    def add(self, item):
        self._add()
        self._sort()
    # add()


    def __getitem__(self, spec):
        if isinstance(spec, basestring):
            return self.map[spec]
        else:
            return self.list[spec]
    # __getitem__()


    def get(self, name, default=None):
        return self.map.get(name, default)
    # get()


    def __iter__(self):
        return self.list.__iter__()
    # __iter__()


    def __len__(self):
        return len(self.list)
    # __len__()


    def _sort(self):
        self.list.sort(lambda a, b: cmp(a.priority, b.priority))
    # _sort()


    def update(self, pluginset):
        self.map.update(pluginset.map)
        self.list.extend(pluginset.list)
        self._sort()
    # update()


    def load_from_directory(self, directory):
        for i in load_plugins(directory, self.basetype):
            self._add(i)
        self._sort()
    # load_from_directory()


    def __str__(self):
        lst = []
        for o in self.list:
            lst.append('"%s" (%s)' % (o.name, o.__name__))

        return "%s(basetype=%s, items=[%s])" % \
               (self.__class__.__name__,
                self.basetype.__name__,
                ", ".join(lst))
    # __str__()
# PluginSet


def load_plugins(directory, basetype):
    tn = basetype.__name__
    log.debug("Loading plugins from %s, type=%s" % (directory, tn))


    plugins = []
    for d in os.listdir(directory):
        if not d.endswith(".py"):
            continue

        name = d[0: -3]
        if name == "__init__":
            continue

        directory.replace(os.path.sep, ".")
        mod = _load_module([directory], name)
        for sym in dir(mod):
            cls = getattr(mod, sym)
            if isinstance(cls, type) and issubclass(cls, basetype) and \
                cls != basetype:
                plugins.append(cls)
                log.info("Loaded %s (%s) from %s" % \
                         (cls.__name__, tn, os.path.join(directory, d)))

    return plugins
# load_plugins()
