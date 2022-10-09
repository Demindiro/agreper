#!/usr/bin/env bash

set -e

if [ -z "$SERVER" ]
then
	echo "SERVER is not set" >&2
	exit 1
fi

case "$SERVER" in
	dev)
		touch main.py
		;;
	gunicorn)
		if [ -z "$PID" ]
		then
			echo "PID is not set" >&2
			exit 1
		fi
		kill -hup $(cat "$PID")
		;;
	*)
		echo "Unsupported $SERVER" >&2
		exit 1
		;;
esac
