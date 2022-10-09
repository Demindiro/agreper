#!/usr/bin/env python3

import sys, password

def arg(i, s):
    if i < len(sys.argv):
        return sys.argv[i]
    print(s)
    sys.exit(1)

def arg_last(i, s):
    if i == len(sys.argv) - 1:
        return sys.argv[i]
    print(s)
    sys.exit(1)

proc = 'tool.py' if len(sys.argv) < 1 else sys.argv[0]
cmd = arg(1, f'usage: {proc} <command> [...]')

if cmd == 'password':
    pwd = arg_last(2, 'usage: {proc} password <pwd>')
    print(password.hash(pwd))
else:
    print('unknown command ', cmd)
    sys.exit(1)
