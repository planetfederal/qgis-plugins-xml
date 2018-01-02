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
try:
    from qgis_repo.repo import QgisRepo, conf
except ImportError:
    sys.path.insert(0,
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # pprint.pprint(sys.path)
    from qgis_repo.repo import QgisRepo, conf

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

# Localhost test serving defaults
LOCALHOST_DOMAIN_TLD = 'localhost'
LOCALHOST_PORT = '8008'

# Read deployment override configuration from a settings.py sidecar file
try:
    # noinspection PyPackageRequirements
    from settings import conf as custom_conf
    conf.update(custom_conf)
except ImportError:
    custom_conf = {}

# default templates loaded from here (not module location)
local_templates = os.path.join(SCRIPT_DIR, 'templates')
if os.path.exists(local_templates) and custom_conf:
    conf['template_dir'] = local_templates

# Global repo instance
repo = None


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


# noinspection PyArgumentList
def arg_parser():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        description="""\
            Run commands on a QGIS plugin repository
            """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='plugins-xml'
    )
    repoopt = dict(action='store',
                   help='Actions apply to one of these output repositories '
                        '(must be defined in settings)',
                   metavar='(' + ' | '.join(conf['repos'].keys()) + ')',
                   choices=conf['repos'].keys())
    authopt = dict(action='store_true',
                   help='Download of stored archive needs authentication')
    roleopt = dict(action='store',
                   help='Specify role(s) needed to download a stored archive '
                        '(implies authentication)',
                   dest='auth_role',
                   metavar='role-a,...')
    namsfxopt = dict(action='store',
                     help='Suffix to add to plugin\'s name '
                          '(overrides suffix defined in repo settings)',
                     dest='name_suffix',
                     metavar='SUFFIX')
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
        '--git-hash',
        action='store',
        help='Short hash of associated git commit',
        default='',
        metavar='xxxxxxx'
    )
    parser_up.add_argument(
        '--keep-zip',
        action='store_true',
        help='Do not remove existing plugin ZIP archive when a new version of '
             'a plugin is uploaded'
    )
    parser_up.add_argument(
        '--remove-version', dest='versions',
        action='store',
        help='Remove existing plugin with specific version(s) '
             '(default: latest)',
        default='latest',
        metavar='(none | all | latest | oldest | #.#.#,...)'
    )
    parser_up.add_argument('repo', **repoopt)
    parser_up.add_argument(
        'zip_name',
        action='store',
        help='Name of uploaded ZIP archive, or all, in uploads directory',
        metavar='(all | zip-name.zip)'
    )
    parser_up.set_defaults(func=update_plugin)

    parser_rm = subparsers.add_parser(
        'remove', help='Remove ALL versions of a plugin from a repository '
                       '(unless otherwise constrained)')
    parser_rm.add_argument(
        '--keep-zip',
        action='store_true',
        help='Do not remove plugin ZIP archive(s)'
    )
    parser_rm.add_argument('--name-suffix', **namsfxopt)
    parser_rm.add_argument('repo', **repoopt)
    parser_rm.add_argument(
        'plugin_name',
        action='store',
        help='Name of plugin (NOT package) in repository',
        metavar='plugin_name'
    )
    parser_rm.add_argument(
        'versions',
        action='store',
        help='Remove existing plugin with specific version(s) '
             '(default: latest)',
        metavar='(all | latest | oldest | #.#.#,...)',
    )
    parser_rm.set_defaults(func=remove_plugin)

    parser_mrr = subparsers.add_parser(
        'mirror', help='Mirror an existing QGIS plugin repository')
    parser_mrr.add_argument('--auth', **authopt)
    parser_mrr.add_argument('--role', **roleopt)
    parser_mrr.add_argument('--name-suffix', **namsfxopt)
    parser_mrr.add_argument(
        '--only-xmls',
        action='store_true',
        help='Download all plugin.xml files for QGIS versions and '
             'generate download listing'
    )
    parser_mrr.add_argument(
        '--qgis-versions', dest='versions',
        action='store',
        help='Comma-separated version(s) of QGIS, to filter request results',
        metavar='#.#[,#.#,...]'
    )
    parser_mrr.add_argument(
        'plugins_xml_url',
        action='store',
        help='plugins.xml URL of repository to be mirrored',
        metavar='http://example.com/plugins.xml'
    )
    parser_mrr.add_argument('repo', **repoopt)
    parser_mrr.set_defaults(func=mirror_repo)

    parser_srv = subparsers.add_parser(
        'serve', help='Test-serve a local QGIS plugin repository '
                      '(NOT for production)')
    parser_srv.add_argument(
        '--host',
        action='store',
        metavar='hostname',
        default=LOCALHOST_DOMAIN_TLD,
        help='Host name to serve under'
    )
    parser_srv.add_argument(
        '--port',
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


def update_plugin():
    return repo.update_plugin(
        args.zip_name,
        name_suffix=args.name_suffix,
        auth=args.auth,
        auth_role=args.auth_role,
        git_hash=args.git_hash,
        versions=args.versions,
        keep_zip=args.keep_zip
    )


def remove_plugin():
    return repo.remove_plugin(
        args.plugin_name,
        versions=args.versions,
        keep_zip=args.keep_zip
    )


def mirror_repo():
    pass


def serve_repo():
    pass


def clear_repo():
    return repo.clear_repo()


if __name__ == '__main__':
    # get defined args
    args = arg_parser().parse_args()
    # out = pprint.pformat(conf) + '\n'
    # out += pprint.pformat(args)
    # print out

    # set up repo target dirs relative to passed args
    repo = QgisRepo(args.repo, conf, with_output=True)
    # repo.dump_attributes(echo=True)
    repo.setup_repo()

    sys.exit(not args.func())