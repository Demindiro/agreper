PYTHON = python3
FLASK = flask
SQLITE = sqlite3

default: venv

test:: venv
	test/all.sh

venv:
	$(PYTHON) -m venv $@
	. ./venv/bin/activate && pip3 install -r requirements.txt

forum.db:
	$(SQLITE) $@ < schema.txt
