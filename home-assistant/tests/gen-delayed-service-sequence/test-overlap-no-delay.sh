#!/bin/sh

gen-delayed-service-sequence.py --overlap-steps -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3"
