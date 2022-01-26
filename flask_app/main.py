# -*- coding: utf-8 -*-

"""
***************************************************************************
    plugins.xml filtering script
    ---------------------
    Date                 : April 2016
    Copyright            : (C) 2016 Boundless
                         : (C) 2020 Planet Inc.
    Author               : Alessandro Pasotti, Larry Shaffer

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""


import os
from flask import Flask, request, make_response, send_from_directory, abort
from lxml import etree

app = Flask(__name__)

# Try to load auth module for custom auth
try:
    import auth
except ImportError:
    pass


def vjust(s, level=3, delim='.', bitsize=3, fillchar=' ', force_zero=False):
    """
    Normalize a dotted version string.

    1.12 becomes : 1.    12
    1.1  becomes : 1.     1

    if force_zero=True and level=2:

    1.12 becomes : 1.    12.     0
    1.1  becomes : 1.     1.     0

    """
    if not s:
        return s
    nb = s.count(delim)
    if nb < level:
        if force_zero:
            s += (level-nb) * (delim+'0')
        else:
            s += (level-nb) * delim
    parts = []
    for v in s.split(delim)[:level+1]:
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
            min_version = vjust(e.find('qgis_minimum_version').text, force_zero=True)
            max_version = e.find('qgis_maximum_version').text
            # max_version will be None if not defined, or can be empty
            has_max_version = bool(max_version)
            if has_max_version:
                max_version = vjust(max_version, force_zero=True)
                if max_version < min_version:
                    # Error in metadata; set max unconstrained
                    # Equal min/max versions are OK, i.e. plugin only works with that version
                    has_max_version = False
            if min_version > qgis_version or (has_max_version and max_version < qgis_version):
                e.getparent().remove(e)
        response = make_response(etree.tostring(xml, pretty_print=app.debug,
                                                xml_declaration=True))
        response.headers['Content-type'] = 'text/xml'
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8000)
