# default target for "make" without args
help:
	@echo 'Makefile for Zubbi                                    '
	@echo '                                                      '
	@echo 'Usage:                                                '
	@echo '    make lint    Run linters and static code checks   '
	@echo '    make test    Run tests using pytest               '
	@echo '    make dist    Build python sdist and wheel using uv'

lint:
	uv run --frozen ruff check
# By default ruff does not format imports, so we have to call this explicitly
	uv run --frozen ruff check --select I
	uv run --frozen ruff format --check --diff .

test:
	uv run --frozen pytest
	uv run --frozen flask collectstatic --help

dist:
	uv build

# Commands without file dependencies
.PHONY: help lint test dist
