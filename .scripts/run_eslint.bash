#!/bin/bash

set -o errexit
TREE="$1"
NPM_ROOT="$(npm root -g)"
CONFIG="$(mktemp -p "$NPM_ROOT" --dry-run --suffix ".json")"
ln -s "$2" "$CONFIG"
trap 'rm "$CONFIG"' EXIT SIGTERM SIGINT

eslint \
    --no-eslintrc \
    --format json \
    --config "$CONFIG" \
    --no-inline-config \
    --resolve-plugins-relative-to "$NPM_ROOT" \
    --report-unused-disable-directives \
    "$TREE"
