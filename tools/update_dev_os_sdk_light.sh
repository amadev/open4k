#!/usr/bin/env bash

set -o pipefail
set -o errexit

if [ -d ~/p/os-sdk-light/ ]; then
    ./.tox/dev/bin/pip install -e ~/p/os-sdk-light/
fi
