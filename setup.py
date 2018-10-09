#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
from setuptools import setup

setup(
    name='psef',
    version='0.1',
    packages=['psef'],
    long_description=__doc__,
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Migrate',
        'Psycopg2',
        'Flask-Login',
    ],
)
