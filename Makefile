# make documentation and run tests

PACKAGE=$(notdir $(PWD))
LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"
VENV=.venv/bin

all: docs test

$(VENV)/python:
	python3 -m venv .venv
	$(VENV)/pip install --upgrade pip

docs: $(VENV)/python
	$(VENV)/pip install --upgrade pdoc . -r requirements.txt
	$(VENV)/pdoc $(PACKAGE)/__init__.py -o $@ --logo $(LOGO) --math --mermaid --logo-link $(LINK)

test: $(VENV)/python
	$(VENV)/pip install -e . pytest
	$(VENV)/pytest

.PHONY: docs test
