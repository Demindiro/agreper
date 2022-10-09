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
$base/../init_sqlite.sh $db --no-admin
$SQLITE $db < $base/init_db.txt
cd $base/..

export DB=$db
export SERVER=dev
$FLASK --app main --debug run
