#!/usr/bin/env python

import gzip

try:
    try:
        from cElementTree import ElementTree
    except ImportError, e:
        try:
            from xml.etree.ElementTree import ElementTree
        except ImportError, e:
            from elementtree.ElementTree import ElementTree
except ImportError, e:
    raise SystemExit("Missing python module: pyx (http://pyx.sourceforge.net)")


def get_attr_int(node, name, default=0):
    return int(node.get(name, default))
# get_attr_int()

def get_attr_float(node, name, default=0):
    return float(node.get(name, default))
# get_attr_float()

def get_child_int(node, name, default=0):
    child = node.find(name)
    try:
        return int(child.text)
    except Exception, e:
        return default
# get_child_int()


class Booking(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.diff = end - start
    # __init__()

    def __str__(self):
        return "Booking(start=%d, end=%d, diff=%d (%0.2fh))" % \
               (self.start, self.end, self.diff, self.diff / 3600.0)
    __repr__ = __str__
# Booking


class Resource(object):
    def __init__(self, doc, node, parent=None):
        self.node = node
        self.doc = doc
        self.parent = parent

        self.id = self.node.get("id")
        self.name = self.node.get("name")
        self.doc.resources[self.id] = self
        self.resources = []
        self.booking = {}

        self._process_resources()
    # __init__()

    def _process_resources(self):
        my_doc = self.doc
        for node in self.node.findall("resource"):
            r = Resource(my_doc, node, self)
            self.resources.append(r)
    # _process_resources()

    def __str__(self):
        if self.parent:
            pid = self.parent.id
        else:
            pid = None

        children = ", ".join(repr(c.id) for c in self.resources)
        return "Resource(id=%r, name=%r, parent=%r, children=[%s])" % \
               (self.id, self.name, pid, children)
    # __str__
    __repr__ = __str__
# Resource


class TaskScenario(object):
    STATUS_UNKNOWN = 0
    STATUS_NOT_STARTED = 1
    STATUS_WIP_LATE = 2
    STATUS_WIP = 3
    STATUS_ON_TIME = 4
    STATUS_WIP_AHEAD = 5
    STATUS_FINISHED = 6

    def __init__(self, task, node):
        self.node = node
        self.task = task

        self.id = self.node.get("scenarioId")
        self.status = get_attr_int(self.node, "status")
        self.complete = float(get_attr_float(self.node, "complete", -1)) / 100.0

        self.start = get_child_int(self.node, "start", None)
        self.end = get_child_int(self.node, "end", None)
        if self.end:
            self.duration = self.end - self.start

        if self.complete < 0:
            if self.status == TaskScenario.STATUS_FINISHED:
                self.complete = 1.0
            elif self.status == TaskScenario.STATUS_ON_TIME and self.end:
                r = self.task.project.now - self.start
                self.complete = float(r) / self.duration
    # __init__()


    def __str__(self):
        return "%s(id=%r, status=%r, complete=%r, start=%r, end=%r)" % \
               (self.__class__.__name__, self.id, self.status, self.complete,
                self.start, self.end)
    # __str__()
# TaskScenario


class Dependency(object):
    def __init__(self, task, node):
        self.parent = task
        self.node = node
        self.dependency = self.node.get("task")
    # __init__()


    def __str__(self):
        return "%s(dependency=%s)" % (self.__class__.__name__, self.dependency)
    # __str__()
# Dependency()


class Task(object):
    def __init__(self, doc, project, node):
        self.doc = doc
        self.project = project
        self.node = node

        self.id = self.node.get("id")
        self.name = self.node.get("name")
        self.is_milestone = bool(get_attr_int(self.node, "milestone"))

        self.depends = []
        self.precedes = []
        self.scenarios = {}
        self.tasks = []
        self.resources = []

        self._process_tasks()
        self._process_scenarios()
        self._process_depends()
        self._process_precedes()
        self._process_resources()
    # __init__()


    def _process_tasks(self):
        my_proj = self.project.id
        for node in self.node.findall("task"):
            assert node.get("projectId") == my_proj

            task = Task(self.doc, self.project, node)
            self.tasks.append(task)
            self.project.register_task(task)
    # _process_tasks()


    def _process_scenarios(self):
        for node in self.node.findall("taskScenario"):
            ts = TaskScenario(self, node)
            self.scenarios[ts.id] = ts
    # _process_scenarios()


    def _process_depends(self):
        for node in self.node.findall("depends"):
            d = Dependency(self, node)
            self.depends.append(d)
    # _process_depends()


    def _process_precedes(self):
        for node in self.node.findall("precedes"):
            d = Dependency(self, node)
            self.precedes.append(d)
    # _process_precedes()


    def _process_resources(self):
        doc_res = self.doc.resources
        for alloc in self.node.findall("allocate"):
            for node in alloc.findall("candidate"):
                r = doc_res[node.get("resourceId")]
                self.resources.append(r)
    # _process_resources()


    def __str__(self):
        lst_scenarios = []
        for o in self.scenarios.itervalues():
            lst_scenarios.append(str(o))
        lst_scenarios = ", ".join(lst_scenarios)

        lst_tasks = []
        for o in self.tasks:
            lst_tasks.append(str(o))
        lst_tasks = ", ".join(lst_tasks)

        lst_depends = []
        for o in self.depends:
            lst_depends.append(str(o))
        lst_depends = ", ".join(lst_depends)

        lst_precedes = []
        for o in self.precedes:
            lst_precedes.append(str(o))
        lst_precedes = ", ".join(lst_precedes)

        return ("%s(id=%r, name=%r, is_milestone=%s, scenarios=[%s], "
                "tasks=[%s], depends=[%s], precedes=[%s])") % \
                (self.__class__.__name__, self.id, self.name,
                self.is_milestone, lst_scenarios, lst_tasks,
                lst_depends, lst_precedes)
    # __str__()
# Task


class CurrencyFormat(object):
    def __init__(self, doc, project, node):
        self.doc = doc
        self.project = project
        self.node = node
        self.frac_digits = get_attr_int(node, "fracDigits")
        self.frac_sep = node.get("fractionSep", ".")
        self.group_sep = node.get("thousandSep", ",")
        self.sign_prefix = node.get("signPrefix", "-")
        self.sign_suffix = node.get("signSuffix", "")
# CurrencyFormat


class Project(object):
    def __init__(self, doc, node):
        self.doc = doc
        self.node = node
        self.timingResolution = int(self.node.get("timingResolution"))
        self.name = self.node.get("name")
        self.id = self.node.get("id")
        self.currency = self.node.get("currency")
        self.currency_format = CurrencyFormat(
            doc, self, node.find("currencyFormat"))
        self.daily_working_hours = get_attr_int(node, "dailyWorkingHours")

        self.start = get_child_int(self.node, "start")
        self.end = get_child_int(self.node,"end")
        self.now = get_child_int(self.node, "now")
        self.time_range = self.end - self.start
        self.time_scale = float(self.now - self.start) / self.time_range
        self.tasks = []
        self._known_tasks = {}
    # __init__()


    def register_task(self, task):
        self._known_tasks[task.id] = task
    # register_task()

    def find_task(self, id):
        return self._known_tasks[id]

    def __str__(self):
        lst_tasks = []
        for o in self.tasks:
            lst_tasks.append(str(o))
        lst_tasks = ", ".join(lst_tasks)

        return "%s(id=%r, name=%r, start=%d, stop=%d, now=%d, tasks=[%s])" % \
               (self.__class__.__name__, self.id, self.name, self.start,
                self.end, self.now, lst_tasks)
    # __str__()
# Project

class Vacation(object):
    def __init__(self, node):
        self.name = node.get("name")
        self.start = get_child_int(node, "start")
        self.end = get_child_int(node, "end")
    # __init__()

    def __str__(self):
        return "name=%s, start=%d, end=%d" % ( self.name, self.start, self.end)
    # __str__()
# Vacation

class Document(object):
    def __init__(self, filename):
        self.fd = gzip.open(filename)
        self.xml = ElementTree()
        self.xml.parse(self.fd)

        self.prjs = {}
        self.tasks = {}
        self.resources = {}
        self.vacations = []

        self._process_projects()
        self._process_resources()
        self._process_tasks()
        self._process_bookings()
        self._process_vacations()
    # __init__()


    def _process_projects(self):
        for node in self.xml.findall("project"):
            prj = Project(self, node)
            self.prjs[prj.id] = prj
    # _process_projects()


    def _process_tasks(self):
        for tl in self.xml.findall("taskList"):
            for node in tl.findall("task"):
                prj = self.prjs[node.get("projectId")]
                task = Task(self, prj, node)
                prj.tasks.append(task)
                prj.register_task(task)
    # _process_tasks()


    def _process_resources(self):
        for rl in self.xml.findall("resourceList"):
            for node in rl.findall("resource"):
                Resource(self, node)
    # _process_resources()


    def _process_bookings(self):
        for bl in self.xml.findall("bookingList"):
            for rb in bl.findall("resourceBooking"):
                resource = self.resources[rb.get("resourceId")]
                scenario = resource.booking.setdefault(rb.get("scenarioId"), {})
                for node in rb.findall("booking"):
                    task = scenario.setdefault(node.get("taskId"), [])
                    start = get_child_int(node, "start")
                    end = get_child_int(node, "end")
                    task.append(Booking(start, end))
    # _process_bookings()


    def _process_vacations(self):
        for vl in self.xml.findall("vacationList"):
            for node in vl.findall("vacation"):
                self.vacations.append(Vacation(node))
    #_process_vacations()

    def __str__(self):
        lst = []
        for p in self.prjs.itervalues():
            lst.append(str(p))
        return "%s(projects=[%s])" % (self.__class__.__name__,
                                      ", ".join(lst))
    # __str__()
# Document
