PROJECT := multicloud_storage

.DEFAULT_GOAL := help
.PHONY: coverage deps help lint publish push test tox clean

include Makefile.venv

Makefile.venv:
	@curl \
		-o Makefile.venv \
		-L "https://github.com/sio/Makefile.venv/raw/v2020.08.14/Makefile.venv"

PYTHON := $(VENV)/python

coverage:  ## Run tests with coverage
	$(PYTHON) -m coverage erase
	$(PYTHON) -m coverage run --include=$(PROJECT)/* -m pytest -ra
	$(PYTHON) -m coverage report -m

deps: venv  ## Install dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install black coverage flake8 flake8_docstrings flit mccabe mypy pylint pytest tox tox-gh-actions
	$(PYTHON) -m flit install

lint:  ## Lint and static-check
	$(PYTHON) -m flake8 $(PROJECT)
	$(PYTHON) -m pylint $(PROJECT)
	$(PYTHON) -m mypy $(PROJECT)

build:	## Build
	$(PYTHON) -m flit build

publish:  ## Publish to PyPi
	$(PYTHON) -m flit publish

push:  ## Push code with tags
	git push && git push --tags

test:  ## Run tests
	$(PYTHON) -m pytest -ra

tox:   ## Run tox
	$(PYTHON) -m tox

clean: clean-venv   ## Clean
	@$(RM) -rf .eggs .mypy_cache .pytest_cache .tox tests/__pycache__ $(PROJECT)/__pycache__ .coverage .venv Makefile.venv

help: ## Show help message
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%s\n\n" "Usage: make [task]"; \
	printf "%-20s %s\n" "task" "help" ; \
	printf "%-20s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-20s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done
