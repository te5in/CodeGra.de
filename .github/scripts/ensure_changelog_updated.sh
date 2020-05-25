#!/bin/sh
set -o xtrace

git diff --name-only master..HEAD | grep '^docs/about/changelog.md$'
