#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 plugins-xml-utils.py

 Command line utilities for QGIS plugin repo's plugins.xml
                             -------------------
        begin                : 2020-03-20
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Planet Inc.
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
# import pprint
import sys
import logging

try:
    from qgis_repo.repo import QgisPluginTree
except ImportError:
    sys.path.insert(0,
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # pprint.pprint(sys.path)
    from qgis_repo.repo import QgisPluginTree

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

if os.environ.get('DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


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
            Run utilities on a QGIS plugin repository's plugins.xml file
            """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='plugins-xml-utils'
    )

    subparsers = parser.add_subparsers(
        title='subcommands',
        description="plugins.xml subcommand ... (see 'subcommand -h')",
        dest='command')

    parser_sp = subparsers.add_parser(
        'sort', help='Sort a plugins.xml file and output to new file')
    parser_sp.add_argument(
        'in_xml',
        action='store',
        help='Unsorted plugins.xml',
        default='',
        metavar='/path/to/input-plugins.xml'
    )
    parser_sp.add_argument(
        'out_xml',
        action='store',
        help='Output sorted plugins.xml (overwritten)',
        default='',
        metavar='/path/to/output-plugins.xml'
    )
    parser_sp.set_defaults(func=sort_plugins_xml)

    return parser


def sort_plugins_xml():
    in_xml = args.in_xml
    out_xml = args.out_xml

    if not os.path.exists(in_xml) or not in_xml.lower().endswith('.xml'):
        print('Missing input plugins.xml or file does not end with .xml')
        return False

    if not out_xml.lower().endswith('.xml'):
        print('Output plugins.xml file does not end with .xml')
        return False

    # if os.path.exists(out_xml):
    #     print("Removing existing '{0}'...".format(out_xml))
    #     os.remove(out_xml)

    tree = QgisPluginTree(in_xml)
    name_sort = QgisPluginTree.plugins_sorted_by_name(tree.plugins())
    """:type: list[etree._Element]"""
    tree.set_plugins(name_sort)

    xml = tree.to_xml()

    print("Writing sorted plugins to '{0}'".format(out_xml))
    with open(out_xml, 'wb') as f:
        f.write(xml)


if __name__ == '__main__':
    # get defined args
    arg_p = arg_parser()
    args = arg_p.parse_args()
    # out = pprint.pformat(args)
    # print(out)

    if not args.command:
        print('No subcommand specified!')
        print()
        print(arg_p.print_help())
        sys.exit(1)

    sys.exit(not args.func())
