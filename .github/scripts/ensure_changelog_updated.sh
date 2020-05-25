#!/bin/sh
set -o xtrace

if [ "$(git diff origin/master -- docs/about/changelog.rst | wc -l)" -eq 0 ]; then
    printf 'Changelog was not updated!' >&2
    exit 1
fi
