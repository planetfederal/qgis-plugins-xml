# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TestPlugin3
                                 A QGIS plugin
 This is my third awesome plugin for testing.
                             -------------------
        begin                : 2016-02-29
        copyright            : (C) 2016 by Larry Shaffer (Boundless)
        email                : lshaffer@boundlessgeo.com
        git sha              : $Format:%H$
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


# noinspection PyPep8Naming
def classFactory(iface):
    from .test_plugin_3 import TestPlugin3
    return TestPlugin3(iface)
