#!/bin/bash
set -ex
isort -y
flake8
pytest "$@"
echo "TEST SUCCESS"
