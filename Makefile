# default target for "make" without args
help:
	@echo 'Makefile for Zubbi                                    '
	@echo '                                                      '
	@echo 'Usage:                                                '
	@echo '    make lint    Run linters and static code checks   '
	@echo '    make test    Run tests using pytest               '
	@echo '    make dist    Build python sdist and wheel using uv'

lint:
	uv run --frozen flake8
	uv run --frozen black --check --diff .

test:
	uv run --frozen pytest
# TODO (felix): This command is currently failing as flask tries to connect to
# ES. I assume that this wasn't the case before as the command (resp. the old
# tox test env) was working before. Maybe flask is missing some config here?
# flask collectstatic --help

dist:
	uv build

# Commands without file dependencies
.PHONY: help lint test dist
