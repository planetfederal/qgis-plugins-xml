#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 test_qgis_repo.py

 Unit tests for components of a plugins.xml-based QGIS plugin repo
                             -------------------
        begin                : 2017-12-13
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Boundless Spatial, Inc.
                             : (C) 2020 by Planet Inc.
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

import unittest
import os
import sys
import logging
import pprint

from logging import debug, info, warning, critical
from lxml import etree

try:
    from qgis_repo.repo import *
except ImportError:
    sys.path.insert(0,
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # pprint.pprint(sys.path)
    from qgis_repo.repo import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# pprint.pprint('SCRIPT_DIR={0}'.format(SCRIPT_DIR))

if os.environ.get('DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


def _test_file(f):
    return os.path.join(os.path.dirname(__file__), 'data', f)


def _test_plugin(p):
    return os.path.join(os.path.dirname(__file__), 'data', 'plugins', p)


def _dump_plugins(plugins):
    """
    :param plugins: list[etree._Element]
    """
    for plugin in plugins:
        log.debug(pprint.pformat(
            etree.tostring(plugin, pretty_print=True,
                           method="xml", encoding='UTF-8')
        ).replace(r'\n', '\n'))


class TestQgisRepo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testPluginTreeDefault(self):
        tree = QgisPluginTree()
        xml = tree.to_xml()
        self.assertIsNotNone(xml)
        self.assertEquals(len(tree.plugins()), 0)
        log.debug('Default plugins XML:\n\n%s',
                  pprint.pformat(xml).replace(r'\n', '\n'))

    def testPluginTreeLoadXml(self):
        tree = QgisPluginTree(_test_file('plugins_test.xml'))
        xml = tree.to_xml()
        self.assertIsNotNone(xml)
        self.assertEquals(len(tree.plugins()), 2)
        log.debug('Loaded plugins XML:\n\n%s',
                  pprint.pformat(xml).replace(r'\n', '\n'))

    def testPluginTreeLoadXsl(self):
        tree = QgisPluginTree()
        xml1 = tree.to_xml()
        log.debug('Current default plugins XML:\n\n%s',
                  pprint.pformat(xml1).replace(r'\n', '\n'))
        self.assertIn('type="text/xsl"', xml1)
        self.assertEqual(len(tree.plugins()), 0)

        tree.set_plugins_xsl('blah.xsl')

        xml2 = tree.to_xml()
        self.assertIn('href="blah.xsl"', xml2)
        log.debug('Updated default plugins XML:\n\n%s',
                  pprint.pformat(xml2).replace(r'\n', '\n'))

        tree2 = QgisPluginTree(_test_file('plugins_test_no-xsl-pi.xml'))
        xml3 = tree2.to_xml()
        log.debug('Current plugins XML (no stylesheet PI):\n\n%s',
                  pprint.pformat(xml3).replace(r'\n', '\n'))
        self.assertNotIn('type="text/xsl"', xml3)

        tree2.set_plugins_xsl('blah.xsl')

        xml4 = tree2.to_xml()
        self.assertIn('type="text/xsl"', xml4)
        self.assertIn('href="blah.xsl"', xml4)
        log.debug('Updated plugins XML (added stylesheet PI):\n\n%s',
                  pprint.pformat(xml4).replace(r'\n', '\n'))

        # Removing stylesheet PI
        tree3 = QgisPluginTree(_test_file('plugins_test.xml'))
        xml5 = tree3.to_xml()
        log.debug('Current plugins XML (has stylesheet PI):\n\n%s',
                  pprint.pformat(xml5).replace(r'\n', '\n'))
        self.assertIn('type="text/xsl"', xml5)
        self.assertIn('href="plugins.xsl"', xml5)

        tree3.set_plugins_xsl()

        xml6 = tree3.to_xml()
        self.assertNotIn('type="text/xsl"', xml6)
        self.assertNotIn('href="plugins.xsl"', xml6)
        log.debug('Updated plugins XML (removed stylesheet PI):\n\n%s',
                  pprint.pformat(xml6).replace(r'\n', '\n'))

    def testPluginTreeMerge(self):
        tree = QgisPluginTree(_test_file('plugins_test.xml'))
        self.assertEqual(len(tree.plugins()), 2)
        tree.merge_plugins(_test_file('plugins_test_merge.xml'))
        xml = tree.to_xml()
        self.assertIsNotNone(xml)
        self.assertEquals(len(tree.plugins()), 5)
        log.debug('Merged plugins XML:\n\n%s',
                  pprint.pformat(xml).replace(r'\n', '\n'))

    def testPluginTreeSort(self):
        tree = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        name_sort = QgisPluginTree.plugins_sorted_by_name(tree.plugins())
        """:type: list[etree._Element]"""
        ver_sort = QgisPluginTree.plugins_sorted_by_version(tree.plugins())
        """:type: list[etree._Element]"""

        tree2 = QgisPluginTree(_test_file('plugins_test_sorted-name.xml'))

        tree.set_plugins(name_sort)
        self.assertEqual(tree.to_xml(), tree2.to_xml())

        for i in range(0, len(tree.plugins())):
            tree_plugin = etree.tostring(name_sort[i], pretty_print=True,
                                         method="xml",
                                         encoding='UTF-8')
            tree2_plugin = etree.tostring(tree2.plugins()[i], pretty_print=True,
                                          method="xml",
                                          encoding='UTF-8')
            self.assertEqual(tree_plugin, tree2_plugin)

        tree3 = QgisPluginTree(_test_file('plugins_test_sorted-version.xml'))

        tree.set_plugins(ver_sort)
        self.assertEqual(tree.to_xml(), tree3.to_xml())

        for i in range(0, len(tree.plugins())):
            tree_plugin = etree.tostring(ver_sort[i], pretty_print=True,
                                         method="xml",
                                         encoding='UTF-8')
            tree3_plugin = etree.tostring(tree3.plugins()[i], pretty_print=True,
                                          method="xml",
                                          encoding='UTF-8')
            self.assertEqual(tree_plugin, tree3_plugin)

    def testPluginTreeRemoveByPackageName(self):
        tree = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        self.assertEqual(len(tree.plugins()), 7)
        tree.remove_plugin_by_package_name('geoserverexplorer-0.2.zip')
        self.assertEqual(len(tree.plugins()), 6)

        find_pkg = tree.find_plugin_by_package_name('geoserverexplorer-0.2.zip')
        self.assertEqual(len(find_pkg), 0)

    def testPluginTreeRemoveByName(self):
        tree = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        self.assertEqual(len(tree.plugins()), 7)
        tree.clear_plugins()
        self.assertEqual(len(tree.plugins()), 0)

        tree2 = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        self.assertEqual(
            len(tree2.find_plugin_by_name('GeoServer Explorer')), 3)
        latest1 = tree2.find_plugin_by_name('GeoServer Explorer',
                                            versions='latest')
        self.assertEqual(latest1[0].get('version'), '1.0')
        tree2.remove_plugin_by_name('GeoServer Explorer')  # latest
        self.assertEqual(len(tree2.plugins()), 6)
        self.assertEqual(
            len(tree2.find_plugin_by_name('GeoServer Explorer')), 2)
        latest2 = tree2.find_plugin_by_name('GeoServer Explorer',
                                            versions='latest')
        self.assertEqual(latest2[0].get('version'), '0.3')  # not 1.0

        tree3 = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        self.assertEqual(
            len(tree3.find_plugin_by_name('GeoServer Explorer')), 3)
        oldest1 = tree3.find_plugin_by_name('GeoServer Explorer',
                                            versions='oldest')
        self.assertEqual(oldest1[0].get('version'), '0.2')
        tree3.remove_plugin_by_name('GeoServer Explorer', versions='oldest')
        self.assertEqual(len(tree3.plugins()), 6)
        self.assertEqual(
            len(tree3.find_plugin_by_name('GeoServer Explorer')), 2)
        oldest2 = tree3.find_plugin_by_name('GeoServer Explorer',
                                            versions='oldest')
        self.assertEqual(oldest2[0].get('version'), '0.3')  # not 0.2

        tree4 = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        allp = tree4.find_plugin_by_name('GeoServer Explorer',
                                         versions='all')
        self.assertEqual(len(allp), 3)
        tree4.remove_plugin_by_name('GeoServer Explorer', versions='all')
        self.assertEqual(len(tree4.plugins()), 4)
        self.assertEqual(
            len(tree4.find_plugin_by_name('GeoServer Explorer')), 0)

        tree5 = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))
        self.assertEqual(
            len(tree5.find_plugin_by_name('GeoServer Explorer')), 3)
        vers1 = tree5.find_plugin_by_name('GeoServer Explorer',
                                          versions='1.0,0.2')
        self.assertEqual(len(vers1), 2)
        tree5.remove_plugin_by_name('GeoServer Explorer', versions='1.0,0.2')
        self.assertEqual(len(tree5.plugins()), 5)
        self.assertEqual(
            len(tree5.find_plugin_by_name('GeoServer Explorer')), 1)
        vers2 = tree5.find_plugin_by_name('GeoServer Explorer')
        self.assertEqual(vers2[0].get('version'), '0.3')  # not 1.0 or 0.2

    def testPluginTreeFindPackage(self):
        tree = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))

        find_pkg = tree.find_plugin_by_package_name('geoserverexplorer-0.2.zip')
        """:type: list[etree._Element]"""
        log.debug('Find package:\n')
        _dump_plugins(find_pkg)
        self.assertEqual(len(find_pkg), 1)

    def testPluginTreeFindName(self):
        tree = QgisPluginTree(_test_file('plugins_test_find-sort.xml'))

        find_all = tree.find_plugin_by_name('GeoServer Explorer')
        """:type: list[etree._Element]"""
        # log.debug('Find ALL plugins:\n')
        # _dump_plugins(find_all)
        self.assertEqual(len(find_all), 3)

        find_latest = tree.find_plugin_by_name('GeoServer Explorer',
                                               versions='latest')
        """:type: list[etree._Element]"""
        # log.debug('Find LATEST plugin:\n')
        # _dump_plugins(find_latest)
        self.assertEqual(len(find_latest), 1)
        self.assertEqual(find_latest[0].get('version'), '1.0')

        find_oldest1 = tree.find_plugin_by_name('GeoServer Explorer',
                                                versions='latest',
                                                reverse=True)
        """:type: list[etree._Element]"""
        # log.debug('Find opposit of LATEST plugin:\n')
        # _dump_plugins(find_oldest1)
        self.assertEqual(len(find_oldest1), 1)
        self.assertEqual(find_oldest1[0].get('version'), '0.2')

        find_oldest2 = tree.find_plugin_by_name('GeoServer Explorer',
                                                versions='oldest')
        """:type: list[etree._Element]"""
        # log.debug('Find OLDEST plugin:\n')
        # _dump_plugins(find_oldest2)
        self.assertEqual(len(find_oldest2), 1)
        self.assertEqual(find_oldest2[0].get('version'), '0.2')

        find_ver = tree.find_plugin_by_name('GeoServer Explorer',
                                            versions='1.0')
        """:type: list[etree._Element]"""
        # log.debug('Find single VERSION of plugin:\n')
        # _dump_plugins(find_ver)
        self.assertEqual(len(find_ver), 1)
        self.assertEqual(find_ver[0].get('version'), '1.0')

        find_vers = tree.find_plugin_by_name('GeoServer Explorer',
                                             versions=' 0.3, 0.2 ',
                                             sort=True)
        """:type: list[etree._Element]"""
        # log.debug('Find VERSIONS of plugins:\n')
        # _dump_plugins(find_vers)
        self.assertEqual(len(find_vers), 2)
        self.assertEqual(find_vers[0].get('version'), '0.2')
        self.assertEqual(find_vers[1].get('version'), '0.3')

        find_vers_rev = tree.find_plugin_by_name('GeoServer Explorer',
                                                 versions=' 1.0, 0.2, ',
                                                 sort=True,
                                                 reverse=True)
        """:type: list[etree._Element]"""
        # log.debug('Find reversed VERSIONS of plugins:\n')
        # _dump_plugins(find_vers_rev)
        self.assertEqual(len(find_vers_rev), 2)
        self.assertEqual(find_vers_rev[0].get('version'), '1.0')
        self.assertEqual(find_vers_rev[1].get('version'), '0.2')


def suite():
    test_suite = unittest.makeSuite(TestQgisRepo, 'test')
    return test_suite


def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())


if __name__ == '__main__':
    unittest.main()
