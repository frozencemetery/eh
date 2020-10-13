#!/bin/sh

args="$@"
if [ -z "$args" ]; then
    args=.
fi

mypy --strict $args
exec flake8 --ignore=E261,E302,E305,E731,E741 $args
