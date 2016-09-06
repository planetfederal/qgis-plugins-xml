#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 plugins-xml.py

 Command line utility to generate/update a QGIS plugin repo's plugins.xml
                             -------------------
        begin                : 2016-02-22
        git sha              : $Format:%H$
        copyright            : (C) 2016 by
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
import codecs
import ConfigParser
import fnmatch
import os
import pprint
import re
import shutil
import StringIO
import sys
import tempfile
import zipfile

from datetime import datetime
from lxml import etree

SCRIPT_DIR = os.path.dirname(__file__)
WEB_BASE_TEST = os.path.join(SCRIPT_DIR, 'www')
UPLOAD_BASE_TEST = SCRIPT_DIR
UPLOADED_BY_TEST = "Boundless"
DOMAIN_TLD_TEST = "boundless-test"
DOMAIN_TLD_DEV_TEST = "boundless-test-dev"

# FIXME: on deploy, assign correct base locations, uploader and domains
WEB_BASE = WEB_BASE_TEST
# UPLOAD_BASE should not be --dev or --auth dependent, and be outside www
UPLOAD_BASE = UPLOAD_BASE_TEST
UPLOADED_BY = UPLOADED_BY_TEST
DOMAIN_TLD = DOMAIN_TLD_TEST
DOMAIN_TLD_DEV = DOMAIN_TLD_DEV_TEST

DEV_NAME_SUFFIX = ' DEV'
AUTH_DLD_MSG = ' (AUTHENTICATED DOWNLOAD)'


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ValidationError(Error):
    pass


class XmlError(Error):
    pass


class QgisRepo(object):

    def __init__(self, args):
        self.args = args
        self.command = \
            args.command if hasattr(args, 'command') else None
        self.plugins_subdir = "plugins"
        self.keep_zip = True if hasattr(args, 'keep') and args.keep else False
        self.dev_suffix = '-dev' if hasattr(args, 'dev') and args.dev else ''
        self.authorization_role = getattr(args, 'role', None)
        self.auth_suffix = "-auth" \
            if (self.authorization_role is not None or
                (hasattr(args, 'auth') and args.auth)) else ''
        self.web_subdir = "qgis{0}".format(self.dev_suffix)
        self.web_dir = os.path.join(WEB_BASE, self.web_subdir)
        self.web_plugins_dir = os.path.join(self.web_dir, self.plugins_subdir)
        self.repo_url = 'http{0}://{1}'.format(
            's' if self.auth_suffix else '',
            DOMAIN_TLD_DEV if self.dev_suffix else DOMAIN_TLD)
        self.upload_dir = os.path.join(UPLOAD_BASE, 'uploads')
        self.max_upload_size = 512000000  # 512 MB
        self.template_dir = os.path.join(SCRIPT_DIR, "templates")

        self.packages_subdir = "packages{0}".format(self.auth_suffix)
        self.packages_dir = os.path.join(
            self.web_plugins_dir, self.packages_subdir)
        self.web_icon_dir = "icons"  # relative to plugins.xml
        self.icons_dir = os.path.join(self.web_plugins_dir, self.web_icon_dir)
        self.default_icon = 'default.png'
        self.web_default_icon = os.path.join(
            self.web_icon_dir, self.default_icon)
        self.plugins_xml_name = 'plugins.xml'
        self.plugins_xml = os.path.join(
            self.web_plugins_dir, self.plugins_xml_name)
        self.plugins_xml_tmpl = 'plugins.xml'
        self.plugins_xsl_name = 'plugins.xsl'
        self.plugins_xsl = os.path.join(
            self.web_plugins_dir, self.plugins_xsl_name)
        self.plugins_xsl_tmpl = 'plugins{0}.xsl'.format(self.dev_suffix)
        self.index_root_tmpl = 'index{0}_root.html'.format(self.dev_suffix)
        self.index_blank_tmpl = 'index_blank.html'
        self.favicon_tmpl = 'favicon.ico'

        self.plugins_tree = None

    def dump_attributes(self, echo=False):
        txt = 'args: {0}\n'.format(self.args)
        attrs = [
            'web_subdir',
            'web_dir',
            'repo_url',
            'upload_dir',
            'max_upload_size',
            'template_dir',
            'packages_subdir',
            'packages_dir',
            'icons_dir',
            'web_default_icon',
            'plugins_xml'
        ]
        for a in attrs:
            txt += '{0}: {1}\n'.format(a, self.__getattribute__(a))
        if echo:
            print(txt)
        return txt

    def setup_repo(self):
        # set up web dir
        if not os.path.exists(self.web_dir):
            os.makedirs(self.web_dir)

        # set up default root web contents, if needed
        root_index = os.path.join(self.web_dir, 'index.html')
        if not os.path.exists(root_index):
            shutil.copyfile(
                os.path.join(self.template_dir, self.index_root_tmpl),
                root_index)

        favicon = os.path.join(self.web_dir, self.favicon_tmpl)
        if not os.path.exists(favicon):
            shutil.copyfile(
                os.path.join(self.template_dir, self.favicon_tmpl), favicon)

        # set up web plugins dir
        if not os.path.exists(self.web_plugins_dir):
            os.makedirs(self.web_plugins_dir)

        # no index of web plugins dir
        plugins_index = os.path.join(self.web_plugins_dir, 'index.html')
        if not os.path.exists(plugins_index):
            shutil.copyfile(
                os.path.join(self.template_dir, self.index_blank_tmpl),
                plugins_index)

        # set up default plugins.xml, if needed
        if not os.path.exists(self.plugins_xml):
            shutil.copyfile(
                os.path.join(self.template_dir, self.plugins_xml_tmpl),
                self.plugins_xml)

        # set up default plugins.xsl, if needed
        if not os.path.exists(self.plugins_xsl):
            shutil.copyfile(
                os.path.join(self.template_dir, self.plugins_xsl_tmpl),
                self.plugins_xsl)

        # set up packages dir
        if not os.path.exists(self.packages_dir):
            os.makedirs(self.packages_dir)

        # set up icons dir
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)

        # setup default plugin icon
        default_icon_file = os.path.join(self.icons_dir, self.default_icon)
        if not os.path.exists(default_icon_file):
            shutil.copyfile(
                os.path.join(self.template_dir, self.default_icon),
                default_icon_file)

    def load_plugins_tree(self):
        if not self.plugins_tree:
            parser = etree.XMLParser(strip_cdata=False, remove_blank_text=True)
            # plugins_tree etree.parse(self.plugins_xml, parser)
            # docinfo = plugins_tree.docinfo
            # """:type: etree.DocInfo"""
            # print(etree.tostring(plugins_tree, pretty_print=True))
            self.plugins_tree = etree.parse(self.plugins_xml, parser)

    def clear_plugins_tree(self):
        self.plugins_tree = None

    def plugins_tree_xml(self):
        if self.plugins_tree:
            return etree.tostring(
                self.plugins_tree, pretty_print=True, method="xml",
                encoding='UTF-8', xml_declaration=True)
            # print(xml)
        return ''

    def remove_plugin_by_name(self, name):
        if not self.plugins_tree:
            return

        plugins = self.plugins_tree.getroot()
        """:type: etree._Element"""
        dev_sfx = DEV_NAME_SUFFIX \
            if self.dev_suffix and DEV_NAME_SUFFIX not in name else ''
        plugin_name = "{0}{1}".format(name, dev_sfx)
        # print "\nAttempt to remove: {0}".format(plugin_name)
        existing_plugins = plugins.findall(
            "pyqgis_plugin[@name='{0}']".format(plugin_name))

        for p in existing_plugins:
            fn_el = p.find("download_url")
            zurl = fn_el.text if fn_el is not None else None
            # print "zurl: {0}".format(zurl)
            ic_el = p.find("icon")
            ic_pth = ic_el.text if ic_el is not None else None
            # print "ic_pth: {0}".format(ic_pth)

            print "Removing from XML: {0}".format(plugin_name)
            plugins.remove(p)
            # print(etree.tostring(plugins_tree, pretty_print=True))

            if ic_pth is not None:
                icon_path = os.path.join(self.web_plugins_dir, ic_pth)
                # print "icon_path: {0}".format(icon_path)
                if os.path.isfile(icon_path):
                    prnt_dir = os.path.dirname(icon_path)
                    print "Removing icon: {0}".format(icon_path)
                    os.remove(icon_path)
                    # print "ls dir: {0}".format(os.listdir(prnt_dir))
                    if not os.listdir(prnt_dir):
                        os.rmdir(prnt_dir)

            # Remove zip (in pre-auth version, the zip was kept if command
            # != 'remove')
            if self.keep_zip or zurl is None:
                continue
            # remove ZIP archive from correct package dir
            m = re.search(r"/plugins/(packages.*)", zurl)
            if not m:
                continue
            pkg_pth = m.group(1)
            zip_path = os.path.join(self.web_plugins_dir, pkg_pth)
            # print "zip_path: {0}".format(zip_path)
            if os.path.isfile(zip_path):
                print "Removing zip: {0}".format(zip_path)
                os.remove(zip_path)

    def append_plugin_to_tree(self, plugin_elem):
        if self.plugins_tree:
            plugins = self.plugins_tree.getroot()
            plugins.append(plugin_elem)

    def write_plugins_xml(self, xml):
        # write out plugins.xml
        with open(self.plugins_xml, 'w') as f:
            f.write(xml)

    def update_plugin(self):
        plugin = QgisPlugin(self.args, self)
        # plugin.dump_attributes(echo=True)

        self.load_plugins_tree()
        # Remove any previous plugin of same name
        self.remove_plugin_by_name(plugin.metadata["name"])
        plugin.setup_plugin()
        self.append_plugin_to_tree(plugin.pyqgis_plugin_element())
        self.write_plugins_xml(self.plugins_tree_xml())
        self.clear_plugins_tree()

    def remove_plugin(self):
        if hasattr(self.args, 'plugin_name') and self.args.plugin_name:
            self.load_plugins_tree()
            self.remove_plugin_by_name(self.args.plugin_name)
            self.write_plugins_xml(self.plugins_tree_xml())
            self.clear_plugins_tree()

    @staticmethod
    def _remove_dir_contents(dir_path):
        for itm in os.listdir(dir_path):
            path = os.path.join(dir_path, itm)
            try:
                shutil.rmtree(path)
            except OSError:
                os.remove(path)

    def clear_repo(self):
        # clear packages[-auth] dirs
        for pkgs in ["packages", "packages-auth"]:
            d = os.path.join(self.web_plugins_dir, pkgs)
            if os.path.exists(d):
                self._remove_dir_contents(d)

        # clear icons dir
        if os.path.exists(self.icons_dir):
            self._remove_dir_contents(self.icons_dir)

        # reset plugins.xml
        if os.path.exists(self.plugins_xml):
            os.remove(self.plugins_xml)
        shutil.copyfile(
            os.path.join(self.template_dir, self.plugins_xml_tmpl),
            self.plugins_xml)


class QgisPlugin(object):

    def __init__(self, args, repo):
        self.args = args
        self.repo = repo
        """:type: QgisRepo"""
        self.zip_name = args.zip_name if hasattr(args, 'zip_name') else ''
        self.zip_path = os.path.join(self.repo.upload_dir, self.zip_name)
        self.required_metadata = (
            'name', 'description', 'version', 'qgisMinimumVersion', 'author',
            'about', 'tracker', 'repository'
        )
        self.optional_metadata = (
            'homepage', 'changelog', 'qgisMaximumVersion', 'tags', 'deprecated',
            'experimental', 'external_deps', 'server', 'email'
        )
        self.boolean_metadata = ('deprecated', 'experimental', 'server')
        self.cdata_metadata = (
            'about', 'author_name', 'changelog', 'description', 'repository',
            'tracker', 'uploaded_by'
        )
        # Role based authorization
        self.authorization_role = getattr(args, 'role', None)
        self.dev_suffix = DEV_NAME_SUFFIX \
            if hasattr(self.args, 'dev') and self.args.dev else ''
        self.auth_suffix = ''
        if (self.authorization_role is not None or
                (hasattr(self.args, 'auth') and self.args.auth)):
            self.auth_suffix = AUTH_DLD_MSG
        self.git_hash = self.args.hash \
            if hasattr(self.args, 'hash') and self.args.hash else None

        # undefined until validated
        self.package_name = None
        self.metadata = None
        self.metadatatxt = None
        self.new_metadatatxt = None
        self.curdatetime = None

        # undefined until archive moved into place
        self.new_zip_name = None
        self.new_zip_path = None

        self._validate()
        self._update_metadata()

    def dump_attributes(self, echo=False):
        txt = 'package_name: {0}\n'.format(self.package_name)
        pp = pprint.PrettyPrinter(indent=2)
        txt += 'metadata: \n{0}\n'.format(pp.pprint(self.metadata))
        if echo:
            print(txt)
        return txt

    def setup_plugin(self):
        self._move_plugin_archive()
        self._extract_icon()
        self._update_zip_archive()

    def _validate(self):
        # verify archive and get metadata
        try:
            self._validate_archive()
            self.metadata = dict(self._validate_metadata())
            # print metadata
        except ValidationError, e:
            msg = unicode('Not a valid plugin ZIP archive')
            raise ValidationError("{0}: {1}".format(msg, e))

    def _validate_archive(self):
        """
       Analyzes a plugin's ZIP archive
       Current checks:
         * archive path is absolute
         * archive size <= self.repo.max_upload_size
         * archive is readable
         * archive does not have security issues
       """
        self.zip_path = os.path.realpath(self.zip_path)
        if not os.path.isabs(self.zip_path) \
                or not os.path.exists(self.zip_path):
            raise ValidationError(
                "ZIP archive can not be resolved to an existing absolute path.")

        fsize = os.path.getsize(self.zip_path)
        if fsize > self.repo.max_upload_size:
            raise ValidationError(
                "ZIP archive is too big at ({0}) Bytes. Max size is {1} Bytes"
                .format(fsize, self.repo.max_upload_size))

        try:
            zip_obj = zipfile.ZipFile(self.zip_path)
        except:
            raise ValidationError("Could not unzip archive.")
        for zname in zip_obj.namelist():
            if zname.find('..') != -1 or zname.find(os.path.sep) == 0:
                raise ValidationError(
                    "For security reasons, ZIP archive cannot contain paths")
        bad_file = zip_obj.testzip()
        zip_obj.close()
        del zip_obj
        if bad_file:
            try:
                raise ValidationError(
                    'Bad ZIP (maybe a CRC error) on file {0}'.format(bad_file))
            except UnicodeDecodeError:
                raise ValidationError(
                    'Bad ZIP (maybe unicode filename) on file {0}'
                    .format(unicode(bad_file, errors='replace')))

    @staticmethod
    def _update_zip_in_place(zipname, filename, data):
        # culled from http://stackoverflow.com/a/25739108/2865523
        # generate a temp file
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(zipname))
        os.close(tmpfd)

        # create a temp copy of the archive without filename
        with zipfile.ZipFile(zipname, 'r') as zin:
            with zipfile.ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment  # preserve the comment
                for item in zin.infolist():
                    if item.filename != filename:
                        zout.writestr(item, zin.read(item.filename))

        # replace with the temp archive
        os.remove(zipname)
        os.rename(tmpname, zipname)

        # now add filename with its new data
        with zipfile.ZipFile(zipname, mode='a',
                             compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, data)

    def _update_zip_archive(self):
        if self.new_metadatatxt is not None and self.metadatatxt is not None:
            # self.dump_attributes(True)
            # print "new_metadatatxt:"
            # print self.new_metadatatxt
            self._update_zip_in_place(self.new_zip_path,
                                      self.metadatatxt[0],
                                      self.new_metadatatxt)

    def _update_metadata(self):
        if not self.dev_suffix or self.metadatatxt is None:
            return

        newmeta = ''

        # update version with datetime integer, so it is newer than stable ver
        curver = self.metadata['version']
        curdate = datetime.now().strftime("%Y%m")
        if curdate not in curver:
            gith = "-{0}".format(self.git_hash) \
                if self.git_hash is not None and \
                   self.git_hash not in curver else ''
            self.curdatetime = datetime.now().strftime("%Y%m%d%H%M")
            newver = "{0}-{1}{2}".format(self.metadata['version'],
                                         self.curdatetime, gith)
            newmeta = re.sub(
                re.compile(r'(\s*)(version\s*=\s*{0})(\s*)'.format(curver)),
                r'\1version={0}\3'.format(newver),
                newmeta if newmeta else self.metadatatxt[1])
            self.metadata['version'] = newver

        # update name with Dev suffix
        curname = self.metadata["name"]
        if not curname.endswith(self.dev_suffix):
            newname = "{0}{1}".format(curname, self.dev_suffix)
            newmeta = re.sub(
                re.compile(r'(\s*)(name\s*=\s*{0})(\s*)'.format(curname)),
                r'\1name={0}\3'.format(newname),
                newmeta if newmeta else self.metadatatxt[1])
            self.metadata["name"] = newname

        # update metadata.txt
        if newmeta:
            self.new_metadatatxt = newmeta

    def _validate_metadata(self):
        """
        Analyzes a zipped file, returns metadata if success, False otherwise.
        Current checks:
          * zip contains __init__.py in first level dir
          * mandatory metadata: self.required_metadata
          * package_name regexp: [A-Za-z][A-Za-z0-9-_]+
          * author regexp: [^/]+
        """
        try:
            zip_obj = zipfile.ZipFile(self.zip_path)
        except:
            raise ValidationError("Could not unzip file.")

        # Checks that package_name exists
        namelist = zip_obj.namelist()
        try:
            package_name = namelist[0][:namelist[0].index('/')]
        except:
            raise ValidationError(
                'Cannot find a folder inside the compressed package:'
                'this does not seems a valid plugin')

        # Cuts the trailing slash
        if package_name.endswith('/'):
            package_name = package_name[:-1]
        initname = package_name + '/__init__.py'
        metadataname = package_name + '/metadata.txt'
        if initname not in namelist and metadataname not in namelist:
            raise ValidationError(
                'Cannot find __init__.py or metadata.txt in the ZIP package:'
                'this does not seems a valid plugin'
                '(searched for {0} and {1})'.format(initname, metadataname))

        # Checks for __init__.py presence
        if initname not in namelist:
            raise ValidationError("Cannot find __init__.py in plugin package")

        # Checks metadata
        metadata = []
        # First parse metadata.txt
        if metadataname in namelist:
            if "metadata.txt" in metadataname:
                # store for later updating of dev plugins
                self.metadatatxt = [metadataname, zip_obj.read(metadataname)]
            try:
                parser = ConfigParser.ConfigParser()
                parser.optionxform = str
                parser.readfp(StringIO.StringIO(
                    codecs.decode(zip_obj.read(metadataname), "utf8")))
                if not parser.has_section('general'):
                    raise ValidationError(
                        "Cannot find a section named 'general' in {0}"
                        .format(metadataname))
                metadata.extend(parser.items('general'))
            except Exception, e:
                raise ValidationError("Errors parsing {0}: {1}"
                                      .format(metadataname, e))
            metadata.append(('metadata_source', 'metadata.txt'))
        else:
            raise ValidationError('Cannot find a valid metadata.txt')

        # Check for required metadata
        failed = []
        for md in self.required_metadata:
            if md not in dict(metadata) or not dict(metadata)[md]:
                failed.append(md)
        if failed:
            raise ValidationError(
                'Cannot find required metadata ({0}) in metadata source {1}'
                .format(' '.join(failed),
                        dict(metadata).get('metadata_source')))

        # Transforms booleans flags (experimental)
        for flag in self.boolean_metadata:
            if flag in dict(metadata):
                metadata[metadata.index((flag, dict(metadata)[flag]))] = \
                    (flag, dict(metadata)[flag].lower() == 'true' or
                     dict(metadata)[flag].lower() == '1')

        # Adds package_name
        if not re.match(r'^[A-Za-z][A-Za-z0-9-_]+$', package_name):
            raise ValidationError(
                "The name of top level directory inside the zip package must "
                "start with an ASCII letter and can only contain ASCII letters,"
                " digits and the signs '-' and '_'.")
        metadata.append(('package_name', package_name))
        self.package_name = package_name

        zip_obj.close()
        del zip_obj

        # Check author
        if 'author' in dict(metadata):
            if not re.match(r'^[^/]+$', dict(metadata)['author']):
                raise ValidationError("Author name cannot contain slashes.")

        # strip and check
        checked_metadata = []
        for k, v in metadata:
            try:
                if not (k in self.boolean_metadata):
                    # v.decode('UTF-8')
                    checked_metadata.append((k, v.strip()))
                else:
                    checked_metadata.append((k, v))
            except UnicodeDecodeError, e:
                raise ValidationError(
                    "There was an error converting metadata '{0}' to UTF-8. "
                    "Reported error was: {1}".format(k, e))

        # Add the role
        if self.authorization_role is not None:
            checked_metadata.append(('authorization_role',
                                     self.authorization_role))

        return checked_metadata

    def _extract_icon(self):
        package_icon_dir = os.path.join(self.repo.icons_dir, self.package_name)
        if not os.path.exists(package_icon_dir):
            os.makedirs(package_icon_dir)

        # dump any icon file
        try:
            zip_obj = zipfile.ZipFile(self.new_zip_path)
            # Strip leading dir for some plugins
            if self.metadata['icon'].startswith('./'):
                icon_path = self.metadata['icon'][2:]
            else:
                icon_path = self.metadata['icon']
            tmp_dir = tempfile.mkdtemp()
            zip_icon = zip_obj.extract(
                self.package_name + '/' + icon_path, tmp_dir)
            if zip_icon and os.path.exists(zip_icon) and \
                    os.path.isfile(zip_icon):
                fname, fext = os.path.splitext(zip_icon)
                ver_icon_path = '{0}/{1}{2}'.format(
                    package_icon_dir, self.metadata['version'], fext)

                if os.path.exists(ver_icon_path):
                    os.remove(ver_icon_path)
                shutil.move(zip_icon, ver_icon_path)
                self.metadata['plugin_icon'] = '{0}/{1}/{2}{3}'.format(
                    self.repo.web_icon_dir, self.package_name,
                    self.metadata['version'], fext)
            else:
                self.metadata['plugin_icon'] = self.repo.web_default_icon
            shutil.rmtree(tmp_dir)
        except KeyError:
            self.metadata['plugin_icon'] = self.repo.web_default_icon

    def _move_plugin_archive(self):
        nam, ext = os.path.splitext(os.path.basename(self.zip_path))
        self.new_zip_name = \
            "{0}.{1}{2}".format(nam, self.metadata['version'], ext)

        self.new_zip_path = os.path.join(self.repo.packages_dir,
                                         self.new_zip_name)

        if os.path.exists(self.new_zip_path):
            os.remove(self.new_zip_path)
        if fnmatch.fnmatch(self.zip_name, 'test_plugin_?.zip'):
            shutil.copy(self.zip_path, self.new_zip_path)
        else:
            shutil.move(self.zip_path, self.new_zip_path)
            os.chmod(self.new_zip_path, 0644)

        self.metadata['file_name'] = self.new_zip_name
        self.metadata['plugin_url'] = '{0}/{1}/{2}/{3}'.format(
            self.repo.repo_url, self.repo.plugins_subdir,
            self.repo.packages_subdir, self.new_zip_name)

    def wrap_cdata(self, tag, source):
        if tag is 'description' and self.auth_suffix:
            source += self.auth_suffix
        if tag in self.cdata_metadata:
            return etree.CDATA(source)
        else:
            return source

    def add_el(self, elem, tag, source, default=''):
        el = etree.SubElement(elem, tag)
        if isinstance(source, dict):
            # fixup some unequal metadata.txt -> plugins.xml mappings
            key = tag
            if tag is 'qgis_minimum_version':
                key = 'qgisMinimumVersion'
            elif tag is 'qgis_maximum_version':
                key = 'qgisMaximumVersion'
            elif tag is 'author_name':
                key = 'author'
            if key in source:
                el.text = self.wrap_cdata(tag, unicode(source[key]))
            else:
                el.text = self.wrap_cdata(tag, unicode(default))
        else:
            el.text = self.wrap_cdata(tag, unicode(source))

    def pyqgis_plugin_element(self):
        md = self.metadata
        el = etree.Element(
            "pyqgis_plugin", name=md["name"], version=md["version"])
        """:type: etree._Element"""
        self.add_el(el, 'description', md)
        self.add_el(el, 'about', md)
        self.add_el(el, 'version', md)
        self.add_el(el, 'authorization_role', md)
        self.add_el(el, 'qgis_minimum_version', md)
        self.add_el(el, 'qgis_maximum_version', md, default='2.99.0')
        self.add_el(el, 'homepage', md)
        self.add_el(el, 'file_name', self.new_zip_name)
        self.add_el(el, 'icon', md['plugin_icon'])
        self.add_el(el, 'author_name', md)
        # note: 'email' ignored, so it is not displayed in plugins.xml
        self.add_el(el, 'download_url', md['plugin_url'])
        self.add_el(el, 'uploaded_by', UPLOADED_BY)
        self.add_el(el, 'create_date', md)
        self.add_el(el, 'update_date', datetime.now().isoformat())
        self.add_el(el, 'experimental', md, default='False')
        self.add_el(el, 'deprecated', md, default='False')
        self.add_el(el, 'tracker', md)
        self.add_el(el, 'repository', md)
        self.add_el(el, 'changelog', md)
        self.add_el(el, 'tags', md)
        self.add_el(el, 'downloads', '0')
        self.add_el(el, 'average_vote', '0.0')
        self.add_el(el, 'rating_votes', '0')
        return el


def arg_parser():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        description="""\
            Run commands on a QGIS plugin repository
            """
    )
    devopt = dict(action='store_true',
                  help='Actions apply to development repository')
    authopt = dict(action='store_true',
                   help='Indicates download archive needs authentication')
    roleopt = dict(action='store',
                   help='Specify the role(s) needed to download an archive (implies authentication). Multiple roles can be entered as comma separated values.')
    subparsers = parser.add_subparsers(
        title='subcommands',
        description="repository action to take... (see 'subcommand -h')",
        dest='command')

    parser_up = subparsers.add_parser(
        'update', help='Update/add a plugin in the repository')
    parser_up.add_argument('--role', **roleopt)
    parser_up.add_argument('--dev', **devopt)
    parser_up.add_argument('--auth', **authopt)
    parser_up.add_argument(
        '--git-hash', dest='hash',
        help='Short hash of associated git commit'
    )
    parser_up.add_argument(
        '--keep-zip', dest='keep',
        action='store_true',
        help='Do not remove plugin ZIP archive when a new version of a plugin is uploaded'
    )
    parser_up.add_argument(
        'zip_name',
        help='Name of uploaded ZIP archive in uploads directory'
    )
    parser_up.set_defaults(func='update_plugin')

    parser_rm = subparsers.add_parser(
        'remove', help='Remove a plugin from the repository')
    parser_rm.add_argument('--dev', **devopt)
    parser_rm.add_argument(
        '--keep-zip', dest='keep',
        action='store_true',
        help='Do not remove plugin ZIP archive'
    )
    parser_rm.add_argument(
        'plugin_name',
        help='Name of plugin (not package) in repository'
    )
    parser_rm.set_defaults(func='remove_plugin')

    parser_cl = subparsers.add_parser(
        'clear', help='Clear all plugins, archives and icons from repository')
    parser_cl.add_argument('--dev', **devopt)
    parser_cl.set_defaults(func='clear_repo')

    return parser


def main():
    # get defined args
    args = arg_parser().parse_args()
    # print args

    # set up repo target dirs relative to passed args
    repo = QgisRepo(args)
    # repo.dump_attributes(echo=True)
    repo.setup_repo()
    getattr(repo, args.func)()

if __name__ == '__main__':
    main()
    sys.exit(0)
