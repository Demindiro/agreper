#!/usr/bin/env bash

SQLITE=sqlite3
FLASK=flask

set -e
set -x

tmp=$(mktemp -d)
trap 'rm -rf $tmp' EXIT
base=$(dirname "$0")

db=$tmp/forum.db

. $base/../venv/bin/activate

# initialize db
$SQLITE $db < $base/../schema.txt
$SQLITE $db < $base/init_db.txt
cd $base/..

DB=$db $FLASK --app main --debug run
