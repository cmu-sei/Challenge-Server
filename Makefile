VENV_DIR := .venv
PYTHON := python3.13
REQUIREMENTS := requirements.txt
APP_DIR := ./src
APP := app.py

.PHONY: all setup run clean update freeze

all: venv run

venv:
	sudo $(PYTHON) -m venv $(VENV_DIR)
	sudo $(VENV_DIR)/bin/pip install --upgrade pip
	sudo $(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)

run:
	cd $(APP_DIR) && sudo ../$(VENV_DIR)/bin/python $(APP)

update:
	$(VENV_DIR)/bin/pip list --outdated | cut -d '=' -f 1 | xargs -n1 $(VENV_DIR)/bin/pip install -U

freeze:
	$(VENV_DIR)/bin/pip freeze | cut -d '=' -f 1 > $(REQUIREMENTS)

clean:
	sudo rm -rf $(VENV_DIR)
