PROJECT := multicloud_storage
SYSTEM := unknown
ARCH := unknown
GCLOUD_VERSION := 347.0.0

.DEFAULT_GOAL := help
.PHONY: coverage deps help lint publish push test tox clean check-tools

ifeq ($(OS),Windows_NT)
	SYSTEM = windows
	ifeq ($(PROCESSOR_ARCHITEW6432),AMD64)
		ARCH = x86_64
	else
		ifeq ($(PROCESSOR_ARCHITECTURE),AMD64)
			ARCH = x86_64
		endif
		ifeq ($(PROCESSOR_ARCHITECTURE),x86)
			ARCH = x86
		endif
	endif
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		SYSTEM = linux
	endif
	ifeq ($(UNAME_S),Darwin)
		SYSTEM = darwin
	endif
	UNAME_P := $(shell uname -p)
	ifeq ($(UNAME_P),x86_64)
		ARCH = x86_64
	endif
	ifneq ($(filter %86,$(UNAME_P)),)
		ARCH = x86
	endif
	ifneq ($(filter arm%,$(UNAME_P)),)
		ARCH = arm
	endif
endif

include Makefile.venv

Makefile.venv:
	@curl \
		-o Makefile.venv \
		-L "https://github.com/sio/Makefile.venv/raw/v2020.08.14/Makefile.venv"

PYTHON := $(VENV)/python

coverage:  ## Run tests with coverage
	@docker compose up -d
	$(PYTHON) -m coverage erase
	$(PYTHON) -m coverage run --include=$(PROJECT)/* -m pytest -ra
	$(PYTHON) -m coverage report -m
	@docker compose down

deps: venv check-tools  ## Install dependencies
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
	@docker compose up -d
	LOGLEVEL=debug $(PYTHON) -m pytest -ra
	@docker compose down

tox:   ## Run tox
	$(PYTHON) -m tox

clean: clean-venv   ## Clean
	@$(RM) -rf .eggs .mypy_cache .pytest_cache .tox tests/__pycache__ $(PROJECT)/__pycache__ .coverage .venv Makefile.venv

check-tools: ## ensures required software is installed
	@if command -v gcloud >/dev/null 2>&1 ; then \
		gcloud components update ; \
	else \
		curl \
			-o /tmp/gcloud.tar.gz \
			-L "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-$(GCLOUD_VERSION)-$(SYSTEM)-$(ARCH).tar.gz" ; \
		tar -xvf /tmp/gcloud.tar.gz -C /tmp ; \
		/tmp/google-cloud-sdk/install.sh ; \
	fi
	@if ! command -v terraform >/dev/null 2>&1 ; then \
		echo Terraform is not installed. Please install Terraform: https://www.terraform.io/downloads.html ;\
		false ; \
	fi
	@if ! command -v jq >/dev/null 2>&1 ; then \
		echo Jq is not installed. Please install Jq: https://stedolan.github.io/jq/download/ ;\
		false ; \
	fi
	@if ! command -v kubectl >/dev/null 2>&1 ; then \
		echo kubectl is not installed. Installing... ; \
		gcloud components install kubectl ; \
	fi

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
