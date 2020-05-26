#!/bin/sh
set -o xtrace

if [ -z "$(git diff origin/master -- "$1")" ]; then
    printf '%s was not updated!\n' "$1" >&2
    exit 1
fi
