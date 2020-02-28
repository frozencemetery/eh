#!/bin/sh
mypy --strict .
exec flake8 --ignore=E261,E302,E305,E731,E741
