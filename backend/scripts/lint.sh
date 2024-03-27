#!/usr/bin/env bash

set -e
set -x

mypy app --ignore-missing-imports
ruff app
ruff format app --check
