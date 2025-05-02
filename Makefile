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

.PHONY: all venv run debug update freeze clean test docker-build docker-run docker-compose docker-all

all: venv run

venv:
	sudo $(PYTHON) -m venv $(VENV_DIR)
	sudo $(VENV_DIR)/bin/pip install --no-cache-dir --upgrade pip
	sudo $(VENV_DIR)/bin/pip install --no-cache-dir -r $(REQUIREMENTS)

run:
	rm -f $(APP_DIR)/challenge.db && cd $(APP_DIR) && sudo ../$(VENV_DIR)/bin/python $(APP)

debug:
	rm -f $(APP_DIR)/challenge.db && cd $(APP_DIR) && sudo ../$(VENV_DIR)/bin/python $(APP) --debug

test:
	rm -f $(APP_DIR)/challenge.db && cd $(APP_DIR) && sudo token1="MyToken1" token2="MyToken2" token3="MyToken3" token4="MyToken4" ../$(VENV_DIR)/bin/python $(APP)

update:
	$(VENV_DIR)/bin/pip list --outdated | cut -d '=' -f 1 | xargs -n1 $(VENV_DIR)/bin/pip install -U

freeze:
	$(VENV_DIR)/bin/pip freeze | cut -d '=' -f 1 > $(REQUIREMENTS)

docker-build:
	docker build -t challenge-server .

docker-run:
	docker run -p 8888:8888 challenge-server

docker-test:
	docker run -p 8888:8888 \
		-e token1="MyToken1" \
		-e token2="MyToken2" \
		-e token3="MyToken3" \
		-e token4="MyToken4" \
		challenge-server

docker-compose:
	docker-compose run --build --rm --service-ports challenge-server

docker-all: docker-build docker-run

clean:
	sudo rm -rf $(VENV_DIR)
