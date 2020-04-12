#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only

import os
import re
import sys
import json
import secrets
import datetime
import readline
import subprocess
from collections import OrderedDict

import flask_migrate

BASE_DIR = os.path.abspath(
    os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
)
PERMS_FILE = os.path.join(BASE_DIR, 'seed_data', 'permissions.json')

os.chdir(BASE_DIR)

MIGRATION_TEMPLATE = """""\"\"\"Creating "{perm_name}" permission.

Revision ID: {up_revision}
Revises: {down_revision}
Create Date: {create_date}

\"\"\"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '{up_revision}'
down_revision = '{down_revision}'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text(\"\"\"
    INSERT INTO "Permission" (name, default_value, course_permission)
    SELECT '{perm_name}', {default_value}, {course_permission} WHERE NOT EXISTS
        (SELECT 1 FROM "Permission" WHERE name = '{perm_name}')
    \"\"\"))


def downgrade():
    pass
"""


def get_input(question: str, allow_empty: bool = False) -> str:
    while True:
        user_input = input(question + ': ')
        if user_input or allow_empty:
            return user_input


def get_yes_or_no(question: str) -> bool:
    while True:
        res = get_input(question + ' [y/n]')
        if res in ('y', 'j', 'yes'):
            return True
        elif res in ('n', 'no'):
            return False


def main() -> None:
    name = ' '
    while not re.match(r'[a-z]+(_[a-z]+)+', name):
        name = get_input('Name of new permission')
    course_perm = get_yes_or_no('Is it a course permission')
    short_desc = get_input('Short description of permission')
    long_desc = get_input('Long description of permission')
    warning = get_input('Warning message (leave empty to ignore)', True)
    default_true = get_yes_or_no('Should the default value be True')

    r_f_name: str
    if course_perm:
        r_f_name = os.path.join(BASE_DIR, 'seed_data', 'course_roles.json')
    else:
        r_f_name = os.path.join(BASE_DIR, 'seed_data', 'roles.json')

    with open(r_f_name, 'r') as f:
        roles = json.load(f, object_pairs_hook=OrderedDict)

    for key, val in roles.items():
        if get_yes_or_no(
            'Should the role "{}" have this permission'.format(key)
        ):
            val['permissions'].append(name)

    with open(r_f_name, 'w') as f:
        json.dump(roles, f, indent=2, separators=(',', ': '))

    with open(PERMS_FILE, 'r') as f:
        perms = json.load(f, object_pairs_hook=OrderedDict)

    perms[name] = OrderedDict(
        default_value=default_true,
        course_permission=course_perm,
        short_description=short_desc,
        long_description=long_desc,
    )
    if warning:
        perms[name]['warning'] = warning

    with open(PERMS_FILE, 'w') as f:
        json.dump(perms, f, indent=2, separators=(',', ': '))

    print('Generating migration', end=' ...')
    sys.stdout.flush()
    out = subprocess.check_output([
        'python', os.path.join(BASE_DIR, 'manage.py'), 'db', 'heads'
    ]).decode('utf-8').strip().split('\n')[-1]
    match = re.match(r'([a-z0-9]+) \(head\)', out)
    assert match is not None, f'{out} does not match'
    old_rev = match.group(1)
    new_rev = secrets.token_hex(10)
    with open(
        os.path.join(
            BASE_DIR, 'migrations', 'versions', '{}_.py'.format(new_rev)
        ), 'w'
    ) as out:
        out.write(
            MIGRATION_TEMPLATE.format(
                up_revision=new_rev,
                down_revision=old_rev,
                perm_name=name,
                default_value=default_true,
                course_permission=course_perm,
                create_date=datetime.datetime.utcnow().isoformat(sep=' ')
            )
        )
    print('Done!')


if __name__ == '__main__':
    main()
