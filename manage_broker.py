#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only

import alembic_autogenerate_enums
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from sqlalchemy_utils import PasswordType

import cg_broker


def render_item(type_, col, autogen_context):
    autogen_context.imports.add("import sqlalchemy_utils")
    if type_ == "type" and isinstance(col, PasswordType):
        return "sqlalchemy_utils.PasswordType"
    else:
        return False


app = cg_broker.create_app()

migrate = Migrate(
    app,
    cg_broker.models.db,
    render_item=render_item,
    directory='cg_broker/migrations',
    compare_type=True
)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
