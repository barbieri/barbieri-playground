#!/bin/sh

LICENSE=${1:?Missing license header file}
shift
echo "Using license header from file: $LICENSE"

for f in $@; do
    mv "$f" "$f.orig"
    cat "$LICENSE" "$f.orig" > "$f"
done
