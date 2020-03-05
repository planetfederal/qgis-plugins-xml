# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TestPlugin1
                                 A QGIS plugin
 This is my first awesome plugin for testing.
                             -------------------
        begin                : 2016-02-29
        copyright            : (C) 2016 by Boundless Spatial, Inc.
                             : (C) 2020 by Planet Inc.
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
    from .test_plugin_1 import TestPlugin1
    return TestPlugin1(iface)
