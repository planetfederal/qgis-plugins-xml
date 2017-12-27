#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgis_repo.py

 Module of classes for components of a plugins.xml-based QGIS plugin repo
                             -------------------
        begin                : 2017-12-13
        git sha              : $Format:%H$
        copyright            : (C) 2017 by
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

import codecs
import ConfigParser
import fnmatch
import os
import logging
import pprint
import re
import shutil
import StringIO
import sys
import tempfile
import zipfile

from datetime import datetime
from lxml import etree

log = logging.getLogger(__name__)


def vjust(ver_str, level=3, delim='.', bitsize=3,
          fillchar=' ', force_zero=False):
    """
    Normalize a dotted version string.

    1.12 becomes : 1.    12
    1.1  becomes : 1.     1

    if force_zero=True and level=2:

    1.12 becomes : 1.    12.     0
    1.1  becomes : 1.     1.     0

    """
    if not ver_str:
        return ver_str
    nb = ver_str.count(delim)
    if nb < level:
        if force_zero:
            ver_str += (level-nb) * (delim+'0')
        else:
            ver_str += (level-nb) * delim
    parts = []
    for v in ver_str.split(delim)[:level+1]:
        if not v:
            parts.append(v.rjust(bitsize, '#'))
        else:
            parts.append(v.rjust(bitsize, fillchar))
    return delim.join(parts)


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RepoTreeError(Error):
    pass


class RepoSetupError(Error):
    pass


class ValidationError(Error):
    pass


class XmlError(Error):
    pass


class QgisPluginTree(object):

    def __init__(self, plugins_xml=None, plugins_xsl=None):
        self.plugins_xml = plugins_xml
        self.plugins_xsl = plugins_xsl
        self.plugins_xsl_default = 'plugins.xsl'
        # noinspection PyProtectedMember
        self.tree = None  # type: etree._ElementTree
        self.load_plugins_xml(plugins_xml=plugins_xml, plugins_xsl=plugins_xsl)

    def tree_obj(self):
        return self.tree

    def root_elem(self):
        """
        :rtype: etree._Element
        """
        if self.tree is None:
            return None
        return self.tree.getroot()

    def plugins(self):
        if self.tree is None:
            return []
        return self.tree.xpath('//pyqgis_plugin')

    def set_plugins(self, plugins):
        """
        :param plugins: list[etree._Element]
        """
        if self.tree is None:
            return []
        self.clear_plugins()
        for plugin in plugins:
            self.append_plugin(plugin)

    def plugin_xml_template(self, plugins_xsl=None):
        if plugins_xsl is None:
            plugins_xsl = self.plugins_xsl_default
        return """<?xml version = '1.0' encoding = 'UTF-8'?>
        <?xml-stylesheet type="text/xsl" href="{0}" ?>
        <plugins/>
        """.format(plugins_xsl)

    def load_plugins_xml(self, plugins_xml=None, plugins_xsl=None):

        self.clear_plugins()
        etree.clear_error_log()
        parser = etree.XMLParser(strip_cdata=False, remove_blank_text=True)
        if plugins_xml is None:
            # load template
            plugins_xml = StringIO.StringIO(
                self.plugin_xml_template(plugins_xsl))

        # plugins_tree etree.parse(self.plugins_xml, parser)
        # docinfo = plugins_tree.docinfo
        # """:type: etree.DocInfo"""
        # log.debug(etree.tostring(plugins_tree, pretty_print=True))
        e = None
        try:
            self.tree = etree.parse(plugins_xml, parser)
        except IOError, e:
            raise RepoTreeError(
                unicode("Error accessing repo XML file '{0}': {1}")
                .format(plugins_xml, e))
        except etree.XMLSyntaxError, e:
            pass
        if e is not None:
            elog = e.error_log.filter_from_errors()
            raise RepoTreeError(
                unicode("Error parsing repo XML file '{0}' (lxml2 log): {1}")
                .format(plugins_xml, elog))

        # override plugins.xsl if passed
        if plugins_xml is not None and plugins_xsl is not None:
            # if no plugins_xml defined, default template already applied
            # don't overwrite any existing (or missing) with default
            self.set_plugins_xsl(plugins_xsl)

    # noinspection PyProtectedMember
    def set_plugins_xsl(self, plugins_xsl=None):
        self.plugins_xsl = plugins_xsl
        if self.tree is None:
            return

        root = self.root_elem()
        if root is None:
            log.warning("Root element missing for setting XSL stylsheet")
            return
        e = root.getprevious()  # type: etree._XSLTProcessingInstruction
        while e is not None \
                and not isinstance(e, etree._XSLTProcessingInstruction):
            e = root.getprevious()

        if e is not None:
            if self.plugins_xsl is not None:
                e.set('href', self.plugins_xsl)
            else:  # remove the stylesheet PI
                etree.strip_tags(self.tree, e.tag)
        else:
            log.info("XML lacks stylsheet processing instruction, adding one")
            pi_str = 'type="text/xsl" href="{0}"'.format(self.plugins_xsl)
            root.addprevious(
                etree.ProcessingInstruction('xml-stylesheet', pi_str))

    def clear_plugins(self):
        if self.tree is None:
            return
        self.root_elem().clear()

    def to_xml(self):
        if self.tree is None:
            return ''
        return etree.tostring(
            self.tree, pretty_print=True, method="xml",
            encoding='UTF-8', xml_declaration=True)

    def append_plugin(self, plugin):
        if self.tree is None:
            return
        plugins = self.root_elem()
        plugins.append(plugin)

    @staticmethod
    def plugins_sorted_by_version(plugins, reverse=False):
        """
        Sort list of plugins by version
        :param plugins: list[etree._Element]
        :param reverse: bool Sort in reverse order
        :return: list[etree._Element]
        """
        return sorted(plugins, key=lambda plugin: plugin.get('version'),
                      reverse=reverse)

    @staticmethod
    def plugins_sorted_by_name(plugins, reverse=False):
        """
        Sort list of plugins, first by name, then by version
        :param plugins: list[etree._Element]
        :param reverse: bool Sort in reverse order
        :return: list[etree._Element]
        """
        return sorted(plugins, key=lambda plugin: (plugin.get('name'),
                                                   plugin.get('version')),
                      reverse=reverse)

    def find_plugin_by_name(self, name, versions='all', sort=False):
        """
        Find a plugin by its name (not package name),
        :param name:
        :param versions: str all [ | latest | #.#[.#][,...] ]
                         Which versions to return
        :param sort: bool Whether to sort the result by name
        :rtype: list[etree._Element]
        """
        if versions in ['all', 'latest']:
            pth = ".//pyqgis_plugin[@name='{0}']".format(name)
        elif versions != '':
            vers = versions.replace(' ', '').split(',')
            at_vers = ' or '.join(
                ["@version='{0}'".format(ver) for ver in vers])
            pth = ".//pyqgis_plugin[@name='{0}' and ({1})]/".format(
                name, at_vers)
        else:
            log.warning('No version(s) could be determined')
            return []

        log.debug('xpath = %s', pth)
        pth_res = self.tree.xpath(pth)
        log.debug('xpath result = %s', pth_res)
        if pth_res is None or len(pth_res) == 0:
            log.debug('No plugins found')
            return []
        if versions == 'latest':
            return pth_res if len(pth_res) == 1 else \
                self.plugins_sorted_by_version(pth_res)[0]
        else:
            return self.plugins_sorted_by_name(pth_res) if sort else pth_res

    def merge_plugins(self, other_plugins_xml):
        """
        Merge other plugins.xml into this tree, adding new plugins and
        avoiding  duplicates. Any to-merge plugin that matches name, version and
        file_name of an existing plugin is skipped, i.e. considered a duplicate.

        Note: this does not ensure parity of XML elements or base URLs, etc.
        :param other_plugins_xml: other plugins.xml path or URL (HTTP or FTP)
        """
        # plugins = self.tree.getroot()
        other_tree = QgisPluginTree(other_plugins_xml)
        for a_plugin in other_tree.plugins():
            name = a_plugin.get('name',)
            version = a_plugin.get('version')
            file_name = a_plugin.findtext('file_name')
            log.debug('name = %s\nversion = %s\nfile_name = %s',
                      name, version, file_name)
            if any([name is None, version is None, file_name is None]):
                log.warning(
                    "Plugin to merge lacks name, version or file_name: %s",
                    etree.tostring(a_plugin, pretty_print=True, method="xml",
                                   encoding='UTF-8', xml_declaration=True))
                continue
            pth = ".//pyqgis_plugin[@name='{0}' and @version='{1}']/" \
                  "file_name[. = '{2}']/text()".format(name, version, file_name)
            log.debug('xpath = %s', pth)
            pth_res = self.tree.xpath(pth)
            log.debug('xpath result = %s', pth_res)
            exists = (pth_res is not None and
                      len(pth_res) > 0
                      and pth_res[0] == file_name)
            log.debug('plugin exists already = %s', exists)
            if exists:
                continue
            self.append_plugin(a_plugin)


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
        if self.authorization_role:
            clean_roles = [s.replace('Desktop', '')
                           for s in self.authorization_role.split(',')]
            subscription_text = "<b>%s</b>" % '</b> or <b>'.join(clean_roles)
            self.authorization_message = \
                file('auth_text.html').read()\
                .replace('#SUBSCRIPTION_TEXT#', subscription_text)
        else:
            self.authorization_message = ''
        # Set dev and beta
        self.is_dev = False
        self.is_beta = False
        if hasattr(args, 'dev') and args.dev:
            self.is_dev = True
            self.name_suffix = DEV_NAME_SUFFIX
        elif hasattr(args, 'beta') and args.beta:
            self.is_beta = True
            self.name_suffix = BETA_NAME_SUFFIX
        else:
            self.name_suffix = ''

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
        except RuntimeError, e:
            raise ValidationError("Could not unzip archive:\n{0}".format(e))
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
        if not self.name_suffix or self.metadatatxt is None:
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

        # update name with Dev/Beta suffix
        curname = self.metadata["name"]
        if not curname.endswith(self.name_suffix):
            newname = "{0}{1}".format(curname, self.name_suffix)
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
        except RuntimeError, e:
            raise ValidationError("Could not unzip archive:\n{0}".format(e))

        # Checks that package_name exists
        namelist = zip_obj.namelist()
        try:
            package_name = namelist[0][:namelist[0].index('/')]
        except KeyError:
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
        """Add authorization_message to the top of the about field and append
        auth_suffix to the description"""
        if tag is 'description' and self.auth_suffix:
            source += self.auth_suffix
        if tag is 'about' and self.authorization_message:
            source = self.authorization_message + source
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


class QgisRepo(object):

    def __init__(self, args, conf):
        self.args = args
        self.command = \
            args.command if hasattr(args, 'command') else None
        self.repo_name = args.repo \
            if hasattr(args, 'repo') and args.repo else None
        if self.repo_name is None:
            raise RepoSetupError(unicode('No repo name defined'))
        if any(['repo_defaults' not in conf, 'repos' not in conf]):
            raise RepoSetupError(unicode('Repo base settings incomplete'))
        self.repo = conf['repo_defaults']
        if self.repo_name not in conf['repos']:
            raise RepoSetupError(
                unicode('Repo \'{0}\' has no settings defined')
                .format(self.repo_name))
        self.repo.update(conf['repos'][self.repo_name])
        self.conf = conf

        self.templ_suffix = self.repo['template_name_suffix']
        self.name_suffix = self.repo['plugin_name_suffix']

        self.authorization_role = getattr(args, 'role', None)
        self.auth_suffix = self.repo['packages_dir_auth_suffix'] \
            if (self.authorization_role is not None or
                (hasattr(args, 'auth') and args.auth)) else ''
        self.plugins_subdir = self.repo['plugins_subdirectory']
        self.web_dir = os.path.join(self.repo['web_base'], self.repo_name)
        self.web_plugins_dir = os.path.join(self.web_dir, self.plugins_subdir)

        pport = self.repo['packages_host_port']
        self.repo_url = '{0}://{1}{2}'.format(
            self.repo['packages_host_scheme'],
            self.repo['packages_host_name'],
            ':{0}'.format(pport) if pport else ''
        )
        self.upload_dir = self.repo['uploads_dir']
        self.max_upload_size = self.repo['max_upload_size']

        self.packages_subdir = "{0}{1}".format(self.repo['packages_dir'],
                                               self.auth_suffix)
        self.packages_dir = os.path.join(
            self.web_plugins_dir, self.packages_subdir)
        self.web_icon_dir = "icons"  # relative to plugins.xml
        self.icons_dir = os.path.join(self.web_plugins_dir, self.web_icon_dir)

        self.template_dir = os.path.join(self.conf['script_dir'], 'templates')
        self.default_icon_name = 'default.png'
        self.default_icon_tmpl = 'default{0}.png'.format(self.templ_suffix)
        self.web_default_icon = os.path.join(
            self.web_icon_dir, self.default_icon_name)
        self.html_index = self.repo['html_index']
        self.index_root_tmpl = 'index-root{0}.html'.format(self.templ_suffix)
        self.index_blank_tmpl = 'index-blank.html'
        self.favicon_name = 'favicon.ico'
        self.favicon_tmpl = 'favicon{0}.ico'.format(self.templ_suffix)

        self.plugins_xml_name = 'plugins.xml'
        self.plugins_xml = os.path.join(
            self.web_plugins_dir, self.plugins_xml_name)
        self.plugins_xml_tmpl = 'plugins.xml'
        self.plugins_xsl_name = 'plugins.xsl'
        self.plugins_xsl = os.path.join(
            self.web_plugins_dir, self.plugins_xsl_name)
        self.plugins_xsl_tmpl = 'plugins{0}.xsl'.format(self.templ_suffix)

        self.plugins_tree = None  # type: QgisPluginTree

    def dump_attributes(self, echo=False):
        txt = '### args ###\n{0}\n'.format(pprint.pformat(self.args))
        txt += '### conf ###\n{0}\n'.format(pprint.pformat(self.conf))
        txt += '### attributes ###\n'
        attrs = [
            'web_dir',
            'repo_url',
            'upload_dir',
            'max_upload_size',
            'template_dir',
            'packages_subdir',
            'packages_dir',
            'icons_dir',
            'default_icon_tmpl',
            'web_default_icon',
            'plugins_xml_tmpl',
            'plugins_xml',
            'plugins_xsl_tmpl',
            'plugins_xsl',
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
        root_index = os.path.join(self.web_dir, self.html_index)
        if not os.path.exists(root_index):
            shutil.copyfile(
                os.path.join(self.template_dir, self.index_root_tmpl),
                root_index)

        favicon = os.path.join(self.web_dir, self.favicon_name)
        if not os.path.exists(favicon):
            shutil.copyfile(
                os.path.join(self.template_dir, self.favicon_tmpl), favicon)

        # set up web plugins dir
        if not os.path.exists(self.web_plugins_dir):
            os.makedirs(self.web_plugins_dir)

        # no index of web plugins dir
        plugins_index = os.path.join(self.web_plugins_dir, self.html_index)
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
        default_icon_file = os.path.join(self.icons_dir, self.default_icon_name)
        if not os.path.exists(default_icon_file):
            shutil.copyfile(
                os.path.join(self.template_dir, self.default_icon_tmpl),
                default_icon_file)

    def load_plugins_tree(self):
        if not self.plugins_tree:
            self.plugins_tree = QgisPluginTree(self.plugins_xml,
                                               self.plugins_xsl)

    def clear_plugins_tree(self):
        self.plugins_tree = None

    def plugins_tree_xml(self):
        return self.plugins_tree.to_xml() if self.plugins_tree else ''

    def remove_plugin_by_name(self, name):
        if not self.plugins_tree:
            return

        plugins = self.plugins_tree.root_elem()
        """:type: etree._Element"""
        if self.name_suffix and self.name_suffix not in name:
            plugin_name = "{0}{1}".format(name, self.name_suffix)
        else:
            plugin_name = name
        log.debug("\nAttempt to remove: {0}".format(plugin_name))
        existing_plugins = plugins.findall(
            "pyqgis_plugin[@name='{0}']".format(plugin_name))

        for p in existing_plugins:
            fn_el = p.find("download_url")
            zurl = fn_el.text if fn_el is not None else None
            # log.debug("zurl: {0}".format(zurl))
            ic_el = p.find("icon")
            ic_pth = ic_el.text if ic_el is not None else None
            # log.debug("ic_pth: {0}".format(ic_pth))

            print "Removing from XML: {0}".format(plugin_name)
            plugins.remove(p)
            # log.debug(etree.tostring(plugins_tree, pretty_print=True))

            if ic_pth is not None:
                icon_path = os.path.join(self.web_plugins_dir, ic_pth)
                # log.debug("icon_path: {0}".format(icon_path))
                if os.path.isfile(icon_path):
                    prnt_dir = os.path.dirname(icon_path)
                    print "Removing icon: {0}".format(icon_path)
                    os.remove(icon_path)
                    # log.debug("ls dir: {0}".format(os.listdir(prnt_dir)))
                    if not os.listdir(prnt_dir):
                        os.rmdir(prnt_dir)

            # Remove zip (in pre-auth version, the zip was kept if command
            # != 'remove')
            if (hasattr(args, 'keep') and args.keep) or zurl is None:
                continue
            # remove ZIP archive from correct package dir
            m = re.search(r"/{0}/({1}.*)"
                          .format(self.plugins_subdir, self.packages_dir), zurl)
            if not m:
                continue
            pkg_pth = m.group(1)
            zip_path = os.path.join(self.web_plugins_dir, pkg_pth)
            # log.debug("zip_path: {0}".format(zip_path))
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


if __name__ == '__main__':
    sys.exit(0)
