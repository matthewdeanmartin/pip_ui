#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run interrogate pip_ui --verbose --fail-under 70
uv run codespell --ignore-words=private_dictionary.txt pip_ui tests README.md CHANGELOG.md docs || true
uv run pylint --score=n --reports=n --rcfile=.pylintrc_spell pip_ui || true
