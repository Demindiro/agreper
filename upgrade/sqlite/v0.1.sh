set -ex
test $# == 1
"$SQLITE" "$1" "
begin exclusive;
	alter table threads rename dead to hidden;
	alter table comments rename dead to hidden;
	update config set version = 'agreper-v0.1.1';
end;
"
