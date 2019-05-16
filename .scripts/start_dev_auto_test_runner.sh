#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only

export NO_BROWSER="true"
export CODEGRADE_CONFIG_FILE='config_auto_test.ini'

if [[ -z "$VIRTUAL_ENV" ]]; then
    source ./env/bin/activate
fi

./run_auto_test_runner.py
