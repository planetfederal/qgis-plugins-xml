#!/bin/bash

# Locally loads the plugins into the test directories

set -e

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}/../uploads"

for zp in test_plugin_1.zip test_plugin_2.zip
do
  ../plugins-xml.sh update $zp
  ../plugins-xml.sh update --dev $zp
done

for zp in test_plugin_3.zip
do
  ../plugins-xml.sh update --auth $zp
  ../plugins-xml.sh update --dev --auth $zp
done

