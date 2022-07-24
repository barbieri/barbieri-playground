#!/bin/bash

if [ $# -eq 0 ]; then
    TESTS="$(find . -name 'test-*.sh')"
else
    TESTS="$@"
fi

DIFF=${DIFF:-diff -u}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

for T in $TESTS; do
    E="${T%.sh}.expected"
    if [ ! -f "$E" ]; then
        die "ERROR: missing $E required by test $T"
    fi

    echo "TEST: $T"
    bash "$T" | $DIFF - "$E" || die "failed test $T"
done
