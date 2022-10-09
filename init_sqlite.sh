#!/usr/bin/env bash

SQLITE=sqlite3

set -e

if [ $# != 1 ]
then
	echo "Usage: $0 <file>" >&2
	exit 1
fi

$SQLITE $1 -init schema.txt "insert into config (
	version,
	name,
	description,
	secret_key,
	captcha_key,
	registration_enabled
)
values (
	'agrepy-v0.1',
	'Agrepy',
	'',
	'$(head -c 30 /dev/urandom | base64)',
	'$(head -c 30 /dev/urandom | base64)',
	0
);"
