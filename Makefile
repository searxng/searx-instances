ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

install:
	python -m pip install --upgrade pip wheel setuptools
	pip install "cython<3.0.0"
	pip install "pyyaml==6.0" --no-build-isolation
	pip install -r requirements.txt

install-update:
	pip install -r requirements-update.txt

install-all: install install-update
	pip install -r requirements-dev.txt

check:
	python -m searxinstances.check

qa:
	flake8 --max-line-length=120 searxinstances tests
	pylint searxinstances tests
	python -m pytest --cov-report html --cov=searxinstances tests -vv
