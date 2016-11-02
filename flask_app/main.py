# -*- coding: utf-8 -*-

"""
***************************************************************************
    plugins.xml filtering script
    ---------------------
    Date                 : April 2016
    Copyright            : © 2016 Boundless
    Contact              : apasotti@boundlessgeo.com
    Author               : Alessandro Pasotti

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
__author__ = 'Alessandro Pasotti'
__date__ = 'April 2016 '


import os
from flask import Flask, request, make_response, send_from_directory, abort
from lxml import etree

app = Flask(__name__)

# Try to load auth module for custom auth
try:
    import auth
except ImportError:
    pass


def vjust(str, level=3, delim='.', bitsize=3, fillchar=' ', force_zero=False):
    """
    Normalize a dotted version string.

    1.12 becomes : 1.    12
    1.1  becomes : 1.     1

    if force_zero=True and level=2:

    1.12 becomes : 1.    12.     0
    1.1  becomes : 1.     1.     0

    """
    if not str:
        return str
    nb = str.count(delim)
    if nb < level:
        if force_zero:
            str += (level-nb) * (delim+'0')
        else:
            str += (level-nb) * delim
    parts = []
    for v in str.split(delim)[:level+1]:
        if not v:
            parts.append(v.rjust(bitsize, '#'))
        else:
            parts.append(v.rjust(bitsize, fillchar))
    return delim.join(parts)



@app.route("/plugins.xml")
@app.route("/plugins/plugins.xml")
def filter_xml():
    """
    Filters plugins.xml removing incompatible plugins.
    If no qgis parameter is found in the query string,
    the whole plugins.xml file is served as is.
    """
    # Points to the real file, not the symlink
    xml_dir = os.path.join(os.getcwd(), 'www/qgis/plugins')
    if not request.query_string:
        xml_dir = os.path.join(os.getcwd(), 'www/qgis/plugins')
        return send_from_directory(xml_dir, 'plugins.xml')
    elif request.args.get('qgis') is None:
        abort(404)
    else:
        try:
            xml = etree.parse(os.path.join(xml_dir, 'plugins.xml'))
        except IOError:
            return make_response("Cannot find plugins.xml", 404)
        qgis_version = vjust(request.args.get('qgis'), force_zero=True)
        for e in xml.xpath('//pyqgis_plugin'):
            if not (vjust(e.find('qgis_minimum_version').text, force_zero=True)
                    <= qgis_version and qgis_version
                    <= vjust(e.find('qgis_maximum_version').text, force_zero=True)):
                e.getparent().remove(e)
        response = make_response(etree.tostring(xml, pretty_print=app.debug,
                                                xml_declaration=True))
        response.headers['Content-type'] = 'text/xml'
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8000)
