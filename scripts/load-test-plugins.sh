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
  rm -f test_plugin_*.zip
popd > /dev/null

copy_plugin()
{
  cp -f ../tests/data/plugins/${1} uploads/
}

for zp in test_plugin_1.zip test_plugin_2.zip test_plugin_4.zip
do
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-dev ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-beta ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-mirror ${zp}
done

for zp in test_plugin_3.zip
do
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis --auth ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-dev --auth ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-beta --auth ${zp}
  copy_plugin ${zp}
  ./plugins-xml.sh update qgis-mirror --auth ${zp}
done
