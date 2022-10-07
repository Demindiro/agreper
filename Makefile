PYTHON = python3
FLASK = flask
SQLITE = sqlite3

default: test

test::
	test/all.sh

venv:
	$(PYTHON) -m venv $@

forum.db:
	$(SQLITE) $@ < schema.txt
