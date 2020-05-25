#!/bin/sh
set -o xtrace

git diff --name-only master.. | grep '^docs/about/changelog.rst'
