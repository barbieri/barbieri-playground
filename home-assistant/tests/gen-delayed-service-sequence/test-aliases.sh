#!/bin/sh

gen-delayed-service-sequence.py \
    --overlap-steps=5s \
    --default-step-alias="{start} {action} {friendly_name} ({duration_human})" \
    -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3=Custom Alias ({duration})"