#!/bin/bash
###########################################################################
#    plugins-xml.sh
#    ---------------------
#    Date                 : March 2016
#    Author               : Larry Shaffer
#    Copyright            : (C) 2016 by Boundless Spatial
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

# Wrapper script for activating Python virtenv and running plugins-xml.py

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

# Support older deployed path of this script via symlink in parent dir
if [ -f ./scripts/plugins-xml.py ]; then
  SCRIPT_DIR="${SCRIPT_DIR}/scripts"
fi

cd "${SCRIPT_DIR}"

# NOTE: assignment text is transformed by Docker's setup-repo.sh
pushd .. > /dev/null
  VIRTENV=venv
  if [ ! -d "${VIRTENV}" ]; then
    virtualenv --system-site-packages "${VIRTENV}"
  fi

  source "${VIRTENV}/bin/activate"
  # Check for 'progress' (bar) package
  if ! pip show progress 2>&1 > /dev/null; then
    pip install -r "requirements.txt"
  fi
popd > /dev/null

./plugins-xml.py "$@"

# FIXME: Apparently, when the packages[-auth] dirs are created in the base image
#        then overlaid with data image, copying the .zip upload to the /var/www/
#        dir causes the permissions to drop from -rw-r--r-- to -rw-------, and
#        there seems to be no way to set it back with Python `os` module calls.
#        (It may be some type of umasking under /var but the same Python calls
#         via `docker exec... bash` console work fine)

# first verify we are in docker container setup
if [ -d "/opt/repo-updater/plugins-xml" ]; then
  for repo in qgis qgis-dev qgis-beta qgis-mirror; do
    if [ -f "/var/www/${repo}/plugins/plugins.xml" ]; then
      chmod -R go+r /var/www/${repo}
    fi
  done
fi
