#!/usr/bin/env bash

set -o pipefail
set -o errexit

if [ -d ~/p/os-sdk-light/ ]; then
    ./.tox/venv/bin/pip install -e ~/p/os-sdk-light/
    ./.tox/dev/bin/pip install -e ~/p/os-sdk-light/
fi
