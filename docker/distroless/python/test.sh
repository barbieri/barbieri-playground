#!/bin/bash

set -ex

docker build --tag 'test-distroless-python' .
docker run -it --rm -e DEBUG=1 test-distroless-python
