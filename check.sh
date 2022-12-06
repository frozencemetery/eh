#!/bin/sh

args="$@"
if [ -z "$args" ]; then
    args=.
fi

mypy --strict $args
exec flake8 --ignore=W504,E126,E201,E202,E261,E275,E302,E305,E731,E741 $args
