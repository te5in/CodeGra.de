#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only

DEV_DB="codegrade_dev1"
DEV_BROKER_DB="codegrade_broker_dev1"

if [[ $1 = 'broker' ]]; then
    echo "NOTE THIS IS VERY HACKY AND PROBABLY WON'T WORK WITH YOUR POSTGRESQL INSTALL"
    echo "Dropping and creating broker database"

    dropdb "$DEV_BROKER_DB"
    psql -c "create database $DEV_BROKER_DB"
    psql "$DEV_BROKER_DB" -c 'create extension "uuid-ossp";'
    ./manage_broker.py db upgrade
    exit $?
fi

fix_perms() {
    psql -d "$DEV_DB" -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA  public TO "www-data"'
    psql -d "$DEV_DB" -c 'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "www-data"'
    psql -d "$DEV_DB" -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "www-data"'
    psql -d "$DEV_DB" -c 'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "www-data"'
    psql -c "grant all privileges on database $DEV_DB  to \"www-data\";"
    psql -d "$DEV_DB" -c 'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "www-data"'
    psql -d "$DEV_DB" -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "www-data"'
}


echo "NOTE THIS IS VERY HACKY AND PROBABLY WON'T WORK WITH YOUR POSTGRESQL INSTALL"
echo "Dropping and creating database"

if [[ $1 = "perms" ]]; then
    fix_perms
    exit 0
fi

dropdb "$DEV_DB"
psql -c "create database $DEV_DB"
if [[ "$1" = "prod" ]]; then
    fix_perms
fi
echo "Removing migrations and uploads directories"
rm -fr uploads/
echo "Deploying"
