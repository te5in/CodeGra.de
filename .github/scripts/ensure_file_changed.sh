#!/bin/sh
set -o xtrace

if [ "$(git diff origin/master -- "$1" | wc -l)" -eq 0 ]; then
    printf '%s was not updated!\n' "$1" >&2
    exit 1
fi
