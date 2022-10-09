PYTHON = python3
FLASK = flask
SQLITE = sqlite3

default: install

test::
	test/all.sh

install:: venv
	. ./venv/bin/activate && pip3 install -r requirements.txt

venv:
	$(PYTHON) -m venv $@

forum.db:
	$(SQLITE) $@ < schema.txt
