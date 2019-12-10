#!/bin/bash
set -e

skip="${1}"

if ! [[ "$skip" = skip_pip ]]; then
    sudo apt-get update
    sudo apt-get install -y lxc lxc-dev lxcfs libvirt0 libssl-dev postgresql-client &

    (
        python -m pip install --upgrade pip;
        pip install 'celery[redis]' coveralls pytest-cov codecov travis-sphinx;
        pip install -r requirements.txt;
        pip install -r broker_requirements.txt;
    ) &
else
    pip install mistune &
fi

(
    wget https://github.com/pmd/pmd/releases/download/pmd_releases%2F6.18.0/pmd-bin-6.18.0.zip -O pmd.zip;
    unzip pmd.zip;
    mv pmd-bin-6.* pmd;
) &

wget https://github.com/checkstyle/checkstyle/releases/download/checkstyle-8.15/checkstyle-8.15-all.jar \
     -O ./checkstyle.jar &

if ! [[ "$skip" = skip_npm ]]; then
    npm ci
fi

wait
