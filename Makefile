# SPDX-License-Identifier: AGPL-3.0-only
TEST_FILE?=psef_test/
SHELL=/bin/bash
TEST_FLAGS?=
PYTHON?=env/bin/python3
export PYTHONPATH=$(CURDIR)
PY_MODULES=psef cg_celery cg_sqlalchemy_helpers cg_json cg_broker cg_logger
PY_ALL_MODULES=$(PY_MODULES) psef_test

.PHONY: test_setup
test_setup:
	mkdir -p /tmp/psef/uploads
	mkdir -p /tmp/psef/mirror_uploads

.PHONY: test_quick
test_quick: test_setup
	TEST_FLAGS+=" -x" $(MAKE) test

.PHONY: test
test: test_setup
	DEBUG=on env/bin/pytest --postgresql=GENERATE --cov psef \
	    --cov-report term-missing  --last-failed  $(TEST_FILE) -vvvvv \
	    $(TEST_FLAGS)

.PHONY: doctest
doctest: test_setup
	pytest --cov psef \
	       --cov-append \
	       --cov-report term-missing \
	       --doctest-modules psef \
	       -vvvvv

.PHONY: reset_db
reset_db:
	DEBUG_ON=True ./.scripts/reset_database.sh
	$(MAKE) db_upgrade
	$(MAKE) test_data

.PHONY: migrate
migrate:
	DEBUG_ON=True $(PYTHON) manage.py db migrate
	DEBUG_ON=True $(PYTHON) manage.py db edit
	$(MAKE) db_upgrade

.PHONY: db_upgrade
db_upgrade:
	DEBUG_ON=True $(PYTHON) manage.py db upgrade

.PHONY: test_data
test_data:
	DEBUG_ON=True $(PYTHON) $(CURDIR)/manage.py test_data

.PHONY: broker_start_dev_celery
broker_start_dev_celery:
	DEBUG=on env/bin/celery worker --app=broker_runcelery:celery -E

.PHONY: start_dev_celery
start_dev_celery:
	DEBUG=on env/bin/celery worker --app=runcelery:celery -E

.PHONY: start_dev_server
start_dev_server:
	DEBUG=on ./.scripts/start_dev.sh python

.PHONY: start_dev_test_runner
start_dev_test_runner:
	DEBUG=on ./.scripts/start_dev_auto_test_runner.sh

.PHONY: start_dev_npm
start_dev_npm: privacy_statement
	DEBUG=on ./.scripts/start_dev.sh npm

.PHONY: privacy_statement
privacy_statement: src/components/PrivacyNote.vue
src/components/PrivacyNote.vue:
	./.scripts/generate_privacy.py

.PHONY: build_front-end
build_front-end: privacy_statement
	npm run build

.PHONY: seed_data
seed_data:
	DEBUG_ON=True $(PYTHON) $(CURDIR)/manage.py seed

.PHONY: isort
isort:
	isort --recursive $(PY_ALL_MODULES)

.PHONY: yapf
yapf:
	yapf -rip $(PY_ALL_MODULES)

.PHONY: format
format: isort yapf
	npm run format

.PHONY: shrinkwrap
shrinkwrap:
	npm shrinkwrap --dev

pylint:
	pylint psef cg_celery cg_model_types --rcfile=setup.cfg

isort_check:
	isort --check-only --diff --recursive $(PY_ALL_MODULES)

lint: mypy pylint isort_check
	npm run lint

mypy:
	mypy --ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs --disallow-subclassing-any \
		$(PY_MODULES)

.PHONY: create_permission
create_permission:
	python ./.scripts/create_permission.py
