#!/usr/bin/env python

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name="taskjuggler_utils",
    author="Gustavo Sverzut Barbieri",
    author_email="barbieri@gmail.com",
    description="""\
Tools to help use "taskjuggler" without its GUI and produce nice reports.\
""",
    long_description="""\
Tools to help use "taskjuggler" without its GUI and produce nice reports.

This package provides tools that will provide nice reports
(taskjuggler-report), gantt charts (taskjuggler-gantt) and time shift
the whole taskjuggler project file (taskjuggler-timeshift).

The best thing is that you don't need to use Graphical User Interfaces
for that, so these can be automated from cron jobs, web servers and
makefiles.

Reports are generated using LaTeX syntax since I use them in my LaTeX
files easily, but we can easily add code to generate HTML reports as
well in future.
""",
    classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: Python Software Foundation License",
    "Programming Language :: Python",
    "Topic :: Office/Business :: Scheduling",
    "Topic :: Scientific/Engineering :: Information Analysis",
    "Topic :: Text Processing :: Markup :: LaTeX",
    ],
    license="PSF",
    keywords="taskjuggler helper scripts tools project management gantt",
    url="http://barbieri-playground.googlecode.com/svn/python/taskjuggler-utils/",
    version="0.1",
    packages=find_packages(),
    scripts=["taskjuggler-gantt",
             "taskjuggler-timeshift",
             "taskjuggler-report",
             ],
    install_requires=["pyx >= 0.9"],
    zip_safe=True,
    )
