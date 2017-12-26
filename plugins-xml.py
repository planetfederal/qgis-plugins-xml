#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 plugins-xml.py

 Command line utility to generate/update a QGIS plugin repo's plugins.xml
                             -------------------
        begin                : 2016-02-22
        git sha              : $Format:%H$
        copyright            : (C) 2016, 2017 by
                               Larry Shaffer/Boundless Spatial Inc.
        email                : lshaffer@boundlessgeo.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import argparse
import os
import pprint
import sys

from datetime import datetime
from qgis_repo import QgisRepo

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

# Localhost test serving defaults
LOCALHOST_DOMAIN_TLD = 'localhost'
LOCALHOST_PORT = '8008'

# Default test configuration
conf = {
    'repo_defaults': {
        'auth_dld_msg': ' (Requires Subscription)',
        'html_index': 'index.html',
        'host_name': 'localhost',
        'host_port': '8008',
        'host_scheme': 'http',
        'max_upload_size': 512000000,  # in bytes
        'packages_dir': 'packages',
        'packages_dir_auth_suffix': '-auth',
        'packages_host_name': 'localhost',
        'packages_host_port': '8008',
        'packages_host_scheme': 'https',
        'plugin_name_suffix': '',
        'plugins_subdirectory': 'plugins',
        'template_name_suffix': '',
        'uploads_dir': os.path.join(SCRIPT_DIR, 'uploads'),
        'uploaded_by': 'Administrator',
        'web_base': os.path.join(SCRIPT_DIR, 'www'),
    },
    'repos': {
        'qgis': {
            'host_name': 'qgis-repo.test',
            'packages_host_name': 'qgis-repo.test',
        },
        'qgis-dev': {
            'host_name': 'dev.qgis-repo.test',
            'packages_host_name': 'dev.qgis-repo.test',
            'plugin_name_suffix': 'DEV',
            'template_name_suffix': '-dev',
        },
        'qgis-beta': {
            'host_name': 'beta.qgis-repo.test',
            'packages_host_name': 'beta.qgis-repo.test',
            'plugin_name_suffix': 'BETA',
            'template_name_suffix': '-beta',
        },
        'qgis-mirror': {
            'host_name': 'mirror.qgis-repo.test',
            'packages_host_name': 'mirror.qgis-repo.test',
            'template_name_suffix': '-mirror',
        },
    },
}

# Read deployment override configuration from a settings.py sidecar file
try:
    # noinspection PyPackageRequirements
    from settings import conf as custom_conf
    conf.update(custom_conf)
except ImportError:
    pass

conf['script_dir'] = SCRIPT_DIR


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def update_plugin():
    pass


def remove_plugin():
    pass


def mirror_repo():
    pass


def serve_repo():
    pass


def clear_repo():
    pass


def arg_parser():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        description="""\
            Run commands on a QGIS plugin repository
            """
    )
    repoopt = dict(action='store',
                   help='Actions apply to one of these output repositories '
                        '(must be defined in settings)',
                   metavar=', '.join(conf['repos'].keys()),
                   choices=conf['repos'].keys())
    authopt = dict(action='store_true',
                   help='Download of stored archive needs authentication')
    roleopt = dict(action='store',
                   help='Specify role(s) needed to download a stored archive '
                        '(implies authentication)',
                   metavar='role-a[,role-b,...]')
    namsfxopt = dict(action='store',
                     help='Suffix to add to plugin\'s name '
                          '(overrides repo settings)',
                     dest='name_suffix')
    subparsers = parser.add_subparsers(
        title='subcommands',
        description="repository action to take... (see 'subcommand -h')",
        dest='command')

    parser_up = subparsers.add_parser(
        'update', help='Update/add a plugin in the repository'
                       '(by default, does not remove previous version)')
    parser_up.add_argument('--auth', **authopt)
    parser_up.add_argument('--role', **roleopt)
    parser_up.add_argument('--name-suffix', **namsfxopt)
    parser_up.add_argument(
        '--git-hash', dest='hash',
        help='Short hash of associated git commit',
        metavar='xxxxxxx'
    )
    parser_up.add_argument(
        '--keep-zip', dest='keep',
        action='store_true',
        help='Do not remove plugin ZIP archive when a new version of '
             'a plugin is uploaded'
    )
    parser_up.add_argument(
        '--remove-version',
        dest='rm_ver',
        help='Remove existing plugin with specific version(s)',
        metavar='[all | latest | #.#[.#]]'
    )
    parser_up.add_argument('repo', **repoopt)
    parser_up.add_argument(
        'zip_name',
        help='Name of uploaded ZIP archive in uploads directory',
        metavar='zip-name.zip'
    )
    parser_up.set_defaults(func=update_plugin)

    parser_rm = subparsers.add_parser(
        'remove', help='Remove ALL versions of a plugin from a repository '
                       '(unless otherwise constrained)')
    parser_rm.add_argument(
        '--keep-zip', dest='keep',
        action='store_true',
        help='Do not remove plugin ZIP archive(s)'
    )
    parser_rm.add_argument(
        '--versions',
        help='Remove existing plugin with specific version(s)',
        default='latest',
        metavar='[all | latest | #.#[.#],#.#[.#]]'
    )
    parser_rm.add_argument('repo', **repoopt)
    parser_rm.add_argument(
        'plugin_name',
        help='Name of plugin (NOT package) in repository',
        metavar='plugin_name'
    )
    parser_rm.set_defaults(func=remove_plugin)

    parser_mrr = subparsers.add_parser(
        'mirror', help='Mirror an existing QGIS plugin repository')
    parser_mrr.add_argument('--auth', **authopt)
    parser_mrr.add_argument('--role', **roleopt)
    parser_mrr.add_argument('--name-suffix', **namsfxopt)
    parser_mrr.add_argument(
        '--only-xmls', dest='only_xmls',
        action='store_true',
        help='Download all plugin.xml files for QGIS versions and '
             'generate download listing'
    )
    parser_mrr.add_argument(
        '--versions',
        help='Comma-separated version(s) of QGIS, to filter request results',
        metavar='#.#[,#.#,...]'
    )
    parser_mrr.add_argument(
        'plugins_xml_url',
        help='plugins.xml URL of repository to be mirrored',
        metavar='http://example.com/plugins.xml'
    )
    parser_mrr.add_argument('repo', **repoopt)
    parser_mrr.set_defaults(func=mirror_repo)

    parser_srv = subparsers.add_parser(
        'serve', help='Test-serve a local QGIS plugin repository '
                      '(NOT for production)')
    parser_srv.add_argument(
        '--host', dest='host',
        action='store',
        metavar='hostname',
        default=LOCALHOST_DOMAIN_TLD,
        help='Host name to serve under'
    )
    parser_srv.add_argument(
        '--port', dest='port',
        action='store',
        metavar='number',
        default=LOCALHOST_PORT,
        help='Port number to serve under'
    )
    parser_srv.add_argument('repo', **repoopt)
    parser_srv.set_defaults(func=serve_repo)

    parser_cl = subparsers.add_parser(
        'clear', help='Clear all plugins, archives and icons from repository')
    parser_cl.add_argument('repo', **repoopt)
    parser_cl.set_defaults(func=clear_repo)

    return parser


def main():
    # get defined args
    args = arg_parser().parse_args()

    # out = pprint.pformat(conf) + '\n'
    # out += pprint.pformat(args)
    # print out

    # # set up repo target dirs relative to passed args
    repo = QgisRepo(args, conf)
    repo.dump_attributes(echo=True)
    repo.setup_repo()
    # getattr(repo, args.func)()
    return args.func()


if __name__ == '__main__':
    sys.exit(main())
