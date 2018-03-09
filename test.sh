#!/bin/bash
set -ex
isort -c
flake8
pytest "$@"
echo "TEST SUCCESS"
