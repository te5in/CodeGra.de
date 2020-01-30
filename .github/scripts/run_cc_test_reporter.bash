#!/bin/bash

if [[ "$GITHUB_REF" == refs/pull/* ]]; then
    export GIT_BRANCH="$GITHUB_HEAD_REF"
    GIT_COMMIT_SHA="$(git rev-parse "origin/$GITHUB_HEAD_REF")"
    export GIT_COMMIT_SHA
else
    export GIT_COMMIT_SHA="$GITHUB_SHA"
    export GIT_BRANCH="${GITHUB_REF/refs\/heads\//}"
fi

echo "COMMIT_SHA: $GIT_COMMIT_SHA" >&2
echo "BRANCH: $GIT_BRANCH" >&2
echo "CMD: ./cc-test-reporter $*" >&2

./cc-test-reporter "$@"
