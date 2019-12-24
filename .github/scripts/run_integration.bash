#!/bin/bash

set -o xtrace

# Make sure none of the tests are run as the only one.
if grep -r '\.only(' ./cypress; then
    printf >&2 'Cypress tests contain a .only()\n'
    exit 1
fi

make privacy_statement
make start_dev_npm &

DBNAME="ci_test"
export SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@localhost:5432/${DBNAME}"

cat >config.ini <<EOF
[Back-end]
sqlalchemy_database_uri = $SQLALCHEMY_DATABASE_URI
DEBUG = true
mirror_upload_dir = /tmp/psef/mirror_uploads
upload_dir = /tmp/psef/uploads

[Celery]
broker_url = redis://localhost:6379

[Features]
register = true
auto_test = true
course_register = true
groups = true

EOF

wget https://github.com/CodeGra-de/jplag/releases/download/v2.14.2-SNAPSHOT/jplag-2.14.2-SNAPSHOT-jar-with-dependencies.jar -O jplag.jar
export PYTHONPATH="$PYTHONPATH:${PWD}"
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -c "create database $DBNAME;" || exit 1
./manage.py db upgrade
./manage.py test_data

celery worker --app=runcelery:celery -E &
python run.py > /dev/null &

./node_modules/wait-on/bin/wait-on http://localhost:8080/api/v1/about -l
curl http://localhost:8080

sleep 4

NO_COLOR=1 xvfb-run --server-args="-screen 0 1600x1024x24" --auto-servernum npm run e2e
res="$?"

exit "$res"
