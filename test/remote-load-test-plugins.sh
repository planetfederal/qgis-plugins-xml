#!/bin/bash

set -e

if [ $# -eq 0 ]; then
  echo "Usage: $0 <ssh-config-host>"
  echo "Loads test plugins into remote docker container and updates repository"
  exit 1
fi

# parent directory of script
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd -P)

cd "${SCRIPT_DIR}/../uploads"

SSH_HOST="${1}"
UPLOADS="/opt/repo-updater/uploads/"
UPDATER="/opt/repo-updater/plugins-xml/plugins-xml.sh"

for zp in test_plugin_1.zip test_plugin_2.zip
do
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update --dev ${zp}"
done

for zp in test_plugin_3.zip
do
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update --auth ${zp}"
  scp ${zp} ${SSH_HOST}:${UPLOADS}
  ssh ${SSH_HOST} "${UPDATER} update --dev --auth ${zp}"
done


