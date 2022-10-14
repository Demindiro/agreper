#!/usr/bin/env bash

# Script to upgrade a database from one version to another by adding columns,
# tables etc.
# Upgrade scripts go into upgrade/sqlite/
# If there are multiple changes after a revision but before a new one, suffix a
# letter (e.g. `v0.1.1a`).
# When a new revision is out, add a script that changes just the version.

LAST_VERSION=agreper-v0.1.1

SQLITE=sqlite3

export SQLITE

set -e

if [ $# -lt 1 ]
then
	echo "Usage: $0 <file.db> [--no-backup]" >&2
	exit 1
fi

make_backup=0

if [ $# -ge 2 ]
then
	case "$2" in
		--no-backup)
			make_backup=1
			;;
		*)
			echo "Unknown option $2"
			exit 1
			;;
	esac
fi

if ! [ -f "$1" ]
then
	echo "Database '$1' doesn't exist" >&2
	exit 1
fi

version=$(sqlite3 "$1" 'select version from config')

while true
do
	case "$version" in 
		# Last version, do nothing
		agreper-v0.1.1)
			echo "$version is the latest version"
			exit 0
			;;
		# Try to upgrade
		agreper-*)
			echo "Upgrading from $version"

			if [ $make_backup ]
			then
				backup="$1.bak-$version"
				if [ -f "$backup" ]
				then
					echo "Backup '$backup' already exists (did a previous upgrade fail?)" >&2
					exit 1
				fi
				echo "Creating backup of $1 at $backup"
				cp --reflink=auto "$1" "$backup"
				make_backup=1
			fi

			script="./upgrade/sqlite/${version#agreper-}.sh"
			if ! bash "$script" "$1"
			then
				echo "Error while executing $script"
				exit 1
			fi
			;;
		# Unrecognized version
		*)
			echo "Unknown version $version" >&2
			exit 1
			;;
	esac
	version=$(sqlite3 "$1" 'select version from config')
done
