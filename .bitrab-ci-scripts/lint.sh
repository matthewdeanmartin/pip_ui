#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run isort --check-only pip_ui tests
uv run black --check pip_ui tests
uv run ruff check --quiet pip_ui tests
uv run pylint --score=n --reports=n --rcfile=.pylintrc pip_ui
uv run pylint --score=n --reports=n --rcfile=.pylintrc_tests tests
