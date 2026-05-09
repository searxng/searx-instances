ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

install:
	python -m pip install --upgrade pip wheel setuptools
	python -m pip install -r requirements.txt

install-update:
	python -m pip install -r requirements-update.txt

install-all: install install-update
	python -m pip install -r requirements-dev.txt

check:
	python -m searxinstances.check

qa:
	- python -m pylint searxinstances tests
	python -m pytest --cov-report html --cov=searxinstances tests -vv
