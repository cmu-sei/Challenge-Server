VENV_DIR := .venv
PYTHON := python3.13
REQUIREMENTS := requirements.txt
APP_DIR := ./src
APP := app.py

.PHONY: all venv run clean

all: venv run

venv:
	sudo $(PYTHON) -m venv $(VENV_DIR)
	sudo $(VENV_DIR)/bin/pip install --upgrade pip
	sudo $(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)

run:
	cd $(APP_DIR) && sudo ../$(VENV_DIR)/bin/python $(APP)

clean:
	sudo rm -rf $(VENV_DIR)
