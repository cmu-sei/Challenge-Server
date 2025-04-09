#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

VENV_DIR := .venv
PYTHON := python3.13
REQUIREMENTS := requirements.txt
APP_DIR := ./src
APP := app.py

.PHONY: all venv run update freeze clean

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
