#!/bin/bash

# Locally loads the plugins into the test directories

set -e

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}/../uploads"
rm test_plugin_*.zip
cp ${SCRIPT_DIR}/test_plugin_*.zip

for zp in test_plugin_1.zip test_plugin_2.zip test_plugin_4.zip
do
  ../plugins-xml.sh update $zp
  ../plugins-xml.sh update --dev $zp
  ../plugins-xml.sh update --beta $zp
done

for zp in test_plugin_3.zip
do
  ../plugins-xml.sh update --auth $zp
  ../plugins-xml.sh update --dev --auth $zp
  ../plugins-xml.sh update --beta --auth $zp
done
