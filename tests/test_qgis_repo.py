import unittest
import os
import sys
import logging
from logging import debug, info, warning, critical
import pprint

from qgis_repo import *
from lxml import etree

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def _test_file(f):
    return os.path.join(os.path.dirname(__file__), 'data', f)


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


def suite():
    test_suite = unittest.makeSuite(TestQgisRepo, 'test')
    return test_suite


def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())


if __name__ == '__main__':
    unittest.main()
