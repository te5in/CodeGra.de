#!/bin/bash
set -o xtrace
export PYTHONPATH="$PWD"
export GITHUB_ACTIONS=true
sudo chown -R "$USER":"$(id -gn)" /tmp/

cat >config.ini <<EOF
[Back-end]
external_url = http://localhost:1234

redis_cache_url = redis://localhost:6379/cg_cache
EOF

pip install -r test_requirements.txt

create_db() {
    DBNAME="ci_test_gw${1}"
    export SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@localhost:5432/${DBNAME}"

    PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -c "create database $DBNAME;" || exit 1
    PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres "$DBNAME" -c "create extension \"citext\";" || exit 1
    PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres "$DBNAME" -c "create extension \"uuid-ossp\";" || exit 1
    ./manage.py db upgrade
}

for i in $(seq 0 5); do
    create_db "$i" &
done

wait

rm package.json
rm npm-shrinkwrap.json

sudo chown -R "$USER":"$(id -gn "$USER")" ~/.config
sudo npm install -g eslint@6.8.0 \
     eslint-plugin-standard@4.0.1 \
     eslint-plugin-node@11.0.0 \
     eslint-plugin-promise@4.2.1 \
     eslint-plugin-import@2.19.1 \
     eslint-module-utils@2.4.1 \
     eslint-import-resolver-node@0.3.2 \
     eslint-config-standard@14.1.0

sudo npm list
sudo chown -R "$USER":"$(id -gn "$USER")" "$(npm root -g)"
sudo chown -R "$USER":"$(id -gn "$USER")" ~/.config

export BASE_DATABASE_URI='postgresql://postgres:postgres@localhost:5432/ci_test_'
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USERNAME=postgres
export PGPASSWORD=postgres

pytest --cov cg_worker_pool \
       --cov cg_threading_utils \
       --cov cg_signals \
       --cov cg_cache \
       --cov cg_helpers \
       --cov-report term-missing \
       "$(pwd)/cg_worker_pool/tests/" \
       "$(pwd)/cg_threading_utils/tests/" \
       "$(pwd)/cg_signals/tests/" \
       "$(pwd)/cg_cache/tests/" \
       "$(pwd)/cg_helpers/tests/" \
       -vvvv
res1="$?"
if [[ "$res1" -ne 0 ]]; then
    exit "$res1";
fi

timeout -k 600 600 \
        pytest --cov psef --cov cg_signals --cov cg_cache \
        --cov-append \
        --postgresql="${BASE_DATABASE_URI}gw5" \
        --cov-report term-missing \
        "$(pwd)/psef_test/test_auto_test.py" \
        -vvvv
res2="$?"
if [[ "$res2" -ne 0 ]]; then
    exit "$res2";
fi

rm "$(pwd)/psef_test/test_auto_test.py"

timeout -k 900 900 \
        pytest --cov psef --cov cg_signals --cov cg_cache \
        --cov-append \
        --postgresql="$BASE_DATABASE_URI" \
        --cov-report term-missing \
        "$(pwd)/psef_test/" \
        -n 4 \
        -vvvv
res3="$?"
if [[ "$res3" -ne 0 ]]; then
    exit "$res3";
fi

make doctest
res4="$?"

[[ $(( res1 + res2 + res3 + res4 )) = 0 ]]
exit "$?"
