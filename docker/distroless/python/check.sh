#!/bin/bash

set -ex

FILES=docker_entrypoint.py

black $FILES
flake8 $FILES
