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

pushd "${SCRIPT_DIR}/uploads" > /dev/null
  rm test_plugin_*.zip
  cp ${SCRIPT_DIR}/data/plugins/test_plugin_*.zip ./
popd > /dev/null

for zp in test_plugin_1.zip test_plugin_2.zip test_plugin_4.zip
do
  ../scripts/plugins-xml.sh update qgis ${zp}
  ../scripts/plugins-xml.sh update qgis-dev ${zp}
  ../scripts/plugins-xml.sh update qgis-beta ${zp}
done

for zp in test_plugin_3.zip
do
  ../scripts/plugins-xml.sh update qgis --auth ${zp}
  ../scripts/plugins-xml.sh update qgis-dev --auth ${zp}
  ../scripts/plugins-xml.sh update qgis-beta --auth ${zp}
done
