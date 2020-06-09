#!/bin/bash

export DEBUG=on
CMD=("env/bin/celery" "worker" "--app=runcelery:celery" "-EB")

if command -v watchmedo > /dev/null; then
    watchmedo auto-restart --directory=./ \
              --pattern='*.py;*.ini' \
              --ignore-patterns='*/.*;*/flycheck_*' \
              --recursive -- "${CMD[@]}"
else
    echo "Watchmedo was not found, please install watchdog and argh using pip" >&2
    "${CMD[@]}"
fi
