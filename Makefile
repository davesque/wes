CHECK_ARGS=wes tests setup.py

.PHONY: dev_install
dev_install:
	pip install -e .[dev]

.PHONY: test
test:
	pytest --cov-report=term-missing --cov=wes

.PHONY: lint
lint:
	pyright $(CHECK_ARGS)
	flake8 $(CHECK_ARGS)
	black --check $(CHECK_ARGS)
	isort --check-only --diff $(CHECK_ARGS)
