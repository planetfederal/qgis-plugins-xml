#!/bin/bash
###########################################################################
#    load-test-plugins-remote.sh
#    ---------------------
#    Date                 : March 2016
#    Author               : Larry Shaffer
#    Copyright            : (C) 2016 by Boundless Spatial, Inc.
#                         : (C) 2020 by Planet Inc.
###########################################################################
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
###########################################################################

set -e

if [ $# -eq 0 ]; then
  echo "Usage: $0 <ssh-config-host>"
  echo "Loads test plugins into remote docker container and updates repository"
  exit 1
fi

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)
cd "${SCRIPT_DIR}"

cd ../tests/data/plugins

SSH_HOST="${1}"
UPLOADS="/opt/repo-updater/uploads/"
UPDATER="/opt/repo-updater/plugins-xml/scripts/plugins-xml.sh"

for zp in test_plugin_1.zip test_plugin_2.zip test_plugin_4.zip
do
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis-dev ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis-beta ${zp}"
done

for zp in test_plugin_3.zip
do
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis --auth ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis-dev --auth ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update qgis-beta --auth ${zp}"
done
