#!/bin/bash

# Locally loads the plugins into the test directories

set -e

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}"

pushd ..
  VIRTENV=venv
  if [ ! -d "${VIRTENV}" ]; then
    virtualenv "${VIRTENV}";
    source "${VIRTENV}/bin/activate";
    pip install -r "requirements.txt";
  else
    source "${VIRTENV}/bin/activate";
  fi
popd

./test_qgis_repo.py
