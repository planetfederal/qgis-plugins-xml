import unittest
import os
import sys
import logging
from logging import debug, info, warning, critical
import pprint

from qgis_repo import *

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

    def testPluginTreeLoad(self):
        tree = QgisPluginTree(_test_file('plugins_test.xml'))
        xml = tree.to_xml()
        self.assertIsNotNone(xml)
        self.assertEquals(len(tree.plugins()), 2)
        log.debug('Loaded plugins XML:\n\n%s',
                  pprint.pformat(xml).replace(r'\n', '\n'))

    def testPluginTreeMerge(self):
        tree = QgisPluginTree(_test_file('plugins_test.xml'))
        tree.merge_plugins(_test_file('plugins_test_merge.xml'))
        xml = tree.to_xml()
        self.assertIsNotNone(xml)
        self.assertEquals(len(tree.plugins()), 5)
        log.debug('Merged plugins XML:\n\n%s',
                  pprint.pformat(xml).replace(r'\n', '\n'))


def suite():
    test_suite = unittest.makeSuite(TestQgisRepo, 'test')
    return test_suite


def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())


if __name__ == '__main__':
    unittest.main()
