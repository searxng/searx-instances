ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

install:
	python -m pip install --upgrade pip wheel setuptools
	pip install -r requirements.txt

install-update:
	pip install -r requirements-update.txt

install-all: install install-update
	pip install -r requirements-dev.txt

check:
	python -m searxinstances.check

qa:
	flake8 --max-line-length=120 --extend-ignore=E275,E0611,E1101,R0917,E0015,R0022,W0012 searxinstances tests
	pylint searxinstances tests
	python -m pytest --cov-report html --cov=searxinstances tests -vv
