#!/bin/bash

# Locally loads the plugins into the test directories

set -e

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}"

pushd .. > /dev/null
  VIRTENV=venv
  if [ ! -d "${VIRTENV}" ]; then
    virtualenv "${VIRTENV}";
    source "${VIRTENV}/bin/activate";
    pip install -r "requirements.txt";
  else
    source "${VIRTENV}/bin/activate";
  fi
popd > /dev/null

#export DEBUG=1
python test_qgis_repo.py
