#!/bin/bash
set -o xtrace
export PYTHONPATH="$PWD"
export GITHUB_ACTIONS=true
sudo chown -R "$USER":"$(id -gn)" /tmp/

create_db() {
    DBNAME="ci_test_gw${1}"
    export SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@localhost:5432/${DBNAME}"

    PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -c "create database $DBNAME;" || exit 1
    ./manage.py db upgrade
}

for i in $(seq 0 5); do
    create_db "$i" &
done
wait

export BASE_DATABASE_URI='postgresql://postgres:postgres@localhost:5432/ci_test_'

pytest --cov cg_worker_pool \
       --cov cg_threading_utils \
       --cov-report term-missing \
       "$(pwd)/cg_worker_pool/tests/" \
       "$(pwd)/cg_threading_utils/tests/" \
       -vvvv
res1="$?"

pytest --cov psef \
       --cov-append \
       --postgresql="${BASE_DATABASE_URI}gw5" \
       --cov-report term-missing \
       --timeout=300 \
       --timeout-method=thread \
       "$(pwd)/psef_test/test_auto_test.py" \
       -vvvv
res2="$?"

rm "$(pwd)/psef_test/test_auto_test.py"

pytest --cov psef \
       --cov-append \
       --postgresql="$BASE_DATABASE_URI" \
       --cov-report term-missing \
       "$(pwd)/psef_test/" \
       -n 4 \
       --timeout=300 \
       --timeout-method=thread \
       -vvvv
res3="$?"

make doctest
res4="$?"

[[ $(( res1 + res2 + res3 + res4 )) = 0 ]]
exit "$?"
