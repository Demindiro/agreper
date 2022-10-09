#!/usr/bin/env bash

SQLITE=sqlite3
PYTHON=python3

set -e

if [ $# != 1 ]
then
	echo "Usage: $0 <file>" >&2
	exit 1
fi

if [ -e "$1" ]
then
	echo "Database '$1' already exists" >&2
	exit 1
fi

read -p 'Admin username: ' username
read -sp 'Admin password: ' password

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
