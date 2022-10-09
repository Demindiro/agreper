#!/usr/bin/env bash

SQLITE=sqlite3
PYTHON=python3

set -e

make
. ./venv/bin/activate

if [ $# -le 0 ]
then
	echo "Usage: $0 <file> [--no-admin]" >&2
	exit 1
fi

if [ -e "$1" ]
then
	echo "Database '$1' already exists" >&2
	exit 1
fi

if [ "$2" != --no-admin ]
then
	read -p 'Admin username: ' username
	read -sp 'Admin password: ' password
fi

password=$($PYTHON tool.py password "$password")
time=$($PYTHON -c 'import time; print(time.time_ns())')

$SQLITE "$1" -init schema.txt "insert into config (
	version,
	name,
	description,
	secret_key,
	captcha_key,
	registration_enabled
)
values (
	'agreper-v0.1',
	'Agreper',
	'',
	'$(head -c 30 /dev/urandom | base64)',
	'$(head -c 30 /dev/urandom | base64)',
	0
);

insert into users (name, password, role, join_time)
values (lower('$username'), '$password', 2, $time);
"

echo "Database '$1' created" >&2
