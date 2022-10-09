#!/usr/bin/env bash

set -e

if [ ! -e venv ]
then
	echo "venv not found, did you run make?" >&2
	exit 1
fi

if [ $# != 2 ]
then
	echo "Usage: $0 <file.db> <pid file>" >&2
	exit 1
fi

. ./venv/bin/activate

export DB="$1"
export SERVER=gunicorn
export PID="$2"
exec gunicorn -w 4 'main:app' --pid="$PID" -b 0.0.0.0:8000
