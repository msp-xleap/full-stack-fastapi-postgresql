#!/usr/bin/env bash

set -e
set -x

# ToDO: Activate mypy. Was disabled due to bug in pytorch
# mypy app --ignore-missing-imports
ruff check app
ruff format app --check
