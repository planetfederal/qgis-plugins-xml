#!/bin/bash

set -e

# Wrapper script for activating Python virtenv and running plugins-xml.py

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}"

# NOTE: assignment text is transformed by Docker's setup-repo.sh
VIRTENV=venv
if [ ! -d "${VIRTENV}" ]; then
  virtualenv "${VIRTENV}";
  source "${VIRTENV}/bin/activate";
  pip install -r "${SCRIPT_DIR}/requirements.txt";
else
  source "${VIRTENV}/bin/activate";
fi

./plugins-xml.py "$@"

# FIXME: Apparently, when the packages[-auth] dirs are created in the base image
#        then overlaid with data image, copying the .zip upload to the /var/www/
#        dir causes the permissions to drop from -rw-r--r-- to -rw-------, and
#        there seems to be no way to set it back with Python `os` module calls.
#        (It may be some type of umasking under /var but the same Python calls
#         via `docker exec... bash` console work fine)
chmod -R go+r /var/www/qgis
chmod -R go+r /var/www/qgis-dev
chmod -R go+r /var/www/qgis-beta
