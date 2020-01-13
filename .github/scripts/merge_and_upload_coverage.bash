#!/bin/bash

set -o xtrace
mkdir coverage
OUT=coverage/lcov.info
"$(npm bin)"/lcov-result-merger 'frontend-*/lcov.info' "$OUT"

ls -hl frontend-unit-coverage
ls -hl frontend-integration-coverage
ls -hl coverage/

sed -i "s@^SF:$PWD/@SF:@g" "$OUT"

RUN=./.github/scripts/run_cc_test_reporter.bash
$RUN format-coverage "$OUT" -t lcov
$RUN upload-coverage

if [[ "$GITHUB_REF" == refs/pull/* ]]; then
    export GIT_BRANCH="$GITHUB_HEAD_REF"
    GIT_COMMIT_SHA="$(git rev-parse "origin/$GITHUB_HEAD_REF")"
    export GIT_COMMIT_SHA
else
    export GIT_COMMIT_SHA="$GITHUB_SHA"
    export GIT_BRANCH="${GITHUB_REF/refs\/heads\//}"
fi

"$(npm bin)/codacy-coverage" -c "$GIT_COMMIT_SHA" -v < "$OUT"
