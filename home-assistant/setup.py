#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
from setuptools import setup

name = 'barbieri-home-assistant-scripts'
version = 1
release = 0


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name=name,
    version='{}.{}'.format(version, release),
    description="Barbieri's home-assistant.io Scripts",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Gustavo Sverzut Barbieri',
    author_email='barbieri@gmail.com',
    url='http://github.com/barbieri/barbieri-playground',
    license='ISCL',
    python_requires='>=3.9',
    requires=[],
    install_requires=['requests', 'PyYAML'],
    zip_safe=True,
    keywords='home-assistant homeassistant automation',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    platforms='any',
    scripts=['gen-delayed-service-sequence.py'],
)
