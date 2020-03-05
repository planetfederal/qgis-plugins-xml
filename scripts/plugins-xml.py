#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 plugins-xml.py

 Command line utility to generate/update a QGIS plugin repo's plugins.xml
                             -------------------
        begin                : 2016-02-22
        git sha              : $Format:%H$
        copyright            : (C) 2016, 2017 by Boundless Spatial Inc.
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

import argparse
import re
import os
# import pprint
import sys
import logging
import tarfile

from datetime import datetime
from urllib.parse import urlparse
from lxml import etree
from progress.bar import Bar
from wget import download
from flask import Flask, request, redirect, make_response, \
    send_from_directory, abort, url_for

try:
    from qgis_repo.repo import QgisRepo, QgisPluginTree, QgisPlugin, conf, vjust
except ImportError:
    sys.path.insert(0,
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # pprint.pprint(sys.path)
    from qgis_repo.repo import QgisRepo, QgisPluginTree, QgisPlugin, conf, vjust

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

# Read deployment override configuration from a settings.py sidecar file
try:
    # noinspection PyPackageRequirements
    from settings import conf as custom_conf
    conf.update(custom_conf)
except ImportError:
    custom_conf = {}

if os.environ.get('DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

# default templates loaded from here (not module location)
local_templates = os.path.join(SCRIPT_DIR, 'templates')
if os.path.exists(local_templates) and custom_conf:
    conf['template_dir'] = local_templates

# Global repo instance
repo = None


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
            Run commands on a QGIS plugin repository on the local filesystem
            """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='plugins-xml'
    )
    repoopt = dict(action='store',
                   help='Actions apply to one of these output repositories '
                        '(must be defined in settings)',
                   metavar='(' + ' | '.join(sorted(conf['repos'].keys())) + ')',
                   choices=conf['repos'].keys())
    authopt = dict(action='store_true',
                   help='Download of stored archive needs authentication')
    roleopt = dict(action='store',
                   help='Specify role(s) needed to download a stored archive '
                        '(implies authentication)',
                   dest='auth_role',
                   metavar='role-a,...')
    namsfxopt = dict(action='store',
                     help='Suffix to add to plugin\'s name '
                          '(overrides suffix defined in repo settings)',
                     dest='name_suffix',
                     metavar='SUFFIX')
    subparsers = parser.add_subparsers(
        title='subcommands',
        description="repository action to take... (see 'subcommand -h')",
        dest='command')

    parser_su = subparsers.add_parser(
        'setup', help='Set up an empty repository '
                      '(all other commands do this as an initial step)')
    parser_su.add_argument('repo', **repoopt)
    parser_su.set_defaults(func=setup_repo)

    parser_up = subparsers.add_parser(
        'update', help='Update/add a plugin in a repository '
                       '(by default, does not remove any existing versions)')
    parser_up.add_argument('--auth', **authopt)
    parser_up.add_argument('--role', **roleopt)
    parser_up.add_argument('--name-suffix', **namsfxopt)
    parser_up.add_argument(
        '--git-hash',
        action='store',
        help='Short hash of associated git commit',
        default='',
        metavar='xxxxxxx'
    )
    parser_up.add_argument(
        '--invalid-fields',
        action='store_true',
        help='Do not strictly validate recommended metadata fields'
    )
    parser_up.add_argument(
        '--remove-version', dest='versions',
        action='store',
        help='Remove existing plugin resources, for specific version(s) '
             '(default: none)',
        default='none',
        metavar='(none | all | latest | oldest | #.#.#,...)'
    )
    parser_up.add_argument(
        '--keep-zip',
        action='store_true',
        help='Do not remove existing plugin ZIP archive(s) '
             'when removing a plugin '
    )
    parser_up.add_argument(
        '--untrusted',
        action='store_true',
        help='Plugin is untrusted (default: trusted)'
    )
    parser_up.add_argument(
        '--sort-xml',
        action='store_true',
        help='Sort the plugins.xml repo index after updating/adding plugins'
    )
    parser_up.add_argument('repo', **repoopt)
    parser_up.add_argument(
        'zip_name',
        action='store',
        help='Name of ZIP archive, or all, in uploads directory to process',
        metavar='(all | zip-name.zip)'
    )
    parser_up.set_defaults(func=update_plugin)

    parser_rm = subparsers.add_parser(
        'remove', help='Remove ALL versions of a plugin from a repository '
                       '(unless otherwise constrained)')
    parser_rm.add_argument(
        '--keep-zip',
        action='store_true',
        help='Do not remove plugin ZIP archive(s)'
    )
    parser_rm.add_argument('--name-suffix', **namsfxopt)
    parser_rm.add_argument('repo', **repoopt)
    parser_rm.add_argument(
        'plugin_name',
        action='store',
        help='Name of plugin (NOT package) in repository',
        metavar='plugin_name'
    )
    parser_rm.add_argument(
        'versions',
        action='store',
        help='Remove existing plugin with specific version(s) '
             '(default: latest)',
        metavar='(all | latest | oldest | #.#.#,...)',
    )
    parser_rm.set_defaults(func=remove_plugin)

    parser_mrr = subparsers.add_parser(
        'mirror', help='Mirror an existing QGIS plugin repository')
    parser_mrr.add_argument('--auth', **authopt)
    parser_mrr.add_argument('--role', **roleopt)
    parser_mrr.add_argument('--name-suffix', **namsfxopt)
    parser_mrr.add_argument(
        '--validate-fields',
        action='store_true',
        help='Strictly validate recommended metadata fields'
    )
    parser_mrr.add_argument(
        '--only-xmls',
        action='store_true',
        help='Download all plugin.xml files for QGIS versions and '
             'generate download listing'
    )
    parser_mrr.add_argument(
        '--only-download',
        action='store_true',
        help='Download all plugin.xml files for QGIS versions, then download '
             'all referenced plugins (implies --only-xmls). '
             'Mostly for testing or when cautiously mirroring MANY plugins, '
             'where the uploads directory is copied to a backup afterwards.'
    )
    parser_mrr.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip downloading, as components are already downloaded. '
             'Mostly for testing or when updating MANY mirrored plugins MAY '
             'fail. The a backup of downloads (from --only-download) are '
             'copied back into the uploads directory and the merge.xml file is '
             'still present.'
    )
    parser_mrr.add_argument(
        '--qgis-versions',
        action='store',
        help='Comma-separated version(s) of QGIS, to filter request results'
             '(define versions to avoid undefined endpoint filtering behavior)',
        metavar='#.#[,#.#,...]'
    )
    parser_mrr.add_argument('repo', **repoopt)
    parser_mrr.add_argument(
        'plugins_xml_url',
        action='store',
        help='plugins.xml URL of repository to be mirrored',
        metavar='http://example.com/plugins.xml'
    )
    parser_mrr.set_defaults(func=mirror_repo)

    parser_srv = subparsers.add_parser(
        'serve', help='Test-serve a local QGIS plugin repository '
                      '(NOT FOR PRODUCTION)')
    parser_srv.add_argument(
        '--host',
        action='store',
        metavar='hostname',
        help='Host name to serve under'
    )
    parser_srv.add_argument(
        '--port',
        action='store',
        metavar='number',
        help='Port number to serve under'
    )
    parser_srv.add_argument(
        '--debug',
        action='store_true',
        help='Run test server in debug mode'
    )
    parser_srv.add_argument('repo', **repoopt)
    parser_srv.set_defaults(func=serve_repo)

    parser_pkg = subparsers.add_parser(
        'package', help='Package a repository into a compressed archive')
    parser_pkg.add_argument('repo', **repoopt)
    parser_pkg.set_defaults(func=package_repo)

    parser_cl = subparsers.add_parser(
        'clear', help='Clear all plugins, archives and icons from a repository')
    parser_cl.add_argument('repo', **repoopt)
    parser_cl.set_defaults(func=clear_repo)

    return parser


def setup_repo():
    # set up repo target dirs relative to passed args and conf
    repo.setup_repo()
    return True


def update_plugin():
    setup_repo()
    if args.zip_name.lower() == 'all':
        zips = [z for z in os.listdir(repo.upload_dir)
                if (os.path.isfile(os.path.join(repo.upload_dir, z))
                    and z.lower().endswith('.zip'))]
    else:
        zips = [args.zip_name]

    if not zips:
        if args.zip_name.lower() == 'all':
            print('No plugins archives found in uploads directory')
        else:
            print('No plugin archive name defined')
        return False

    repo.output = False  # nix qgis_repo output, since using progress bar
    up_bar = Bar("Updating plugins in '{0}'".format(repo.repo_name),
                 fill='=', max=len(zips))
    up_bar.start()
    for i in up_bar.iter(range(0, len(zips))):
        try:
            repo.update_plugin(
                zips[i],
                name_suffix=args.name_suffix,
                auth=args.auth,
                auth_role=args.auth_role,
                git_hash=args.git_hash,
                versions=args.versions,
                keep_zip=args.keep_zip,
                untrusted=args.untrusted,
                invalid_fields=args.invalid_fields
            )
        except KeyboardInterrupt:
            return False

    if args.sort_xml:
        print("Sorting repo plugins.xml")
        post_sort = QgisPluginTree.plugins_sorted_by_name(
            repo.plugins_tree.plugins())
        repo.plugins_tree.set_plugins(post_sort)

    return True


def remove_plugin():
    setup_repo()
    return repo.remove_plugin(
        args.plugin_name,
        versions=args.versions,
        keep_zip=args.keep_zip
    )


def mirror_repo():
    setup_repo()
    mirror_temp = 'mirror-temp'
    mirror_dir = os.path.join(SCRIPT_DIR, mirror_temp)
    merge_xml = 'merged.xml'

    if args.only_download and args.skip_download:
        print('Both --only-download and --skip-download specified! '
              'Choose either, but not both.')
        return False

    if args.skip_download:
        tree = QgisPluginTree(os.path.join(mirror_dir, merge_xml))
    else:
        xml_url = args.plugins_xml_url
        if not xml_url or not xml_url.lower().endswith('.xml'):
            print('Missing plugins.xml or URL does not end with .xml')
            return False
        url_parts = urlparse(xml_url)
        b_name = '{0}_{1}'.format(
            url_parts.hostname.replace('.', '-'),
            os.path.splitext(os.path.basename(xml_url))[0])

        if not os.path.exists(mirror_dir):
            os.mkdir(mirror_dir)
        repo.remove_dir_contents(mirror_dir, strict=False)

        q_vers = args.qgis_versions.replace(' ', '').split(',') \
            if args.qgis_versions is not None else None
        if q_vers is None:
            urls = [xml_url]
            names = ['{0}.xml'.format(b_name)]
        else:
            urls = ['{0}?qgis={1}'.format(xml_url, v)
                    for v in q_vers]
            names = ['{0}_{1}.xml'.format(b_name, v.replace('.', '-'))
                     for v in q_vers]

        tree = QgisPluginTree()
        dl_bar = Bar('Downloading/merging xml', fill='=', max=len(urls))
        dl_bar.start()
        try:
            for i in dl_bar.iter(range(0, len(urls))):
                out_xml = os.path.join(mirror_dir, names[i])
                download(urls[i], out=out_xml, bar=None)
                tree.merge_plugins(out_xml)
        except KeyboardInterrupt:
            return False

        print("Sorting merged plugins")
        name_sort = QgisPluginTree.plugins_sorted_by_name(tree.plugins())
        tree.set_plugins(name_sort)

        xml = tree.to_xml()

        print("Writing merged plugins to '{0}/{1}'".format(mirror_temp,
                                                           merge_xml))
        with open(os.path.join(mirror_dir, merge_xml), 'w') as f:
            f.write(xml)
        if args.only_xmls:
            return True

    downloads = {}
    elements = {}
    for p in tree.plugins():
        dl_url = p.findtext("download_url")
        file_name = p.findtext("file_name")
        if all([file_name, dl_url, dl_url not in downloads]):
            downloads[file_name] = dl_url
            elements[file_name] = p
            # for testing against plugins.qgis.org
            # if len(downloads) == 10:
            #     break

    if not args.skip_download:
        repo.remove_dir_contents(repo.upload_dir)

        dl_bar = Bar('Downloading plugins', fill='=', max=len(downloads))
        dl_bar.start()
        try:
            for f_name, dl_url in dl_bar.iter(downloads.items()):
                out_dl = os.path.join(repo.upload_dir, f_name)
                download(dl_url, out=out_dl, bar=None)
        except KeyboardInterrupt:
            return False

    if args.only_download:
        print("Downloads complete, exiting since --only-download specified")
        return True

    zips = [z for z in os.listdir(repo.upload_dir)
            if (os.path.isfile(os.path.join(repo.upload_dir, z))
                and z.lower().endswith('.zip'))]
    if not zips:
        print('No plugins archives found in uploads directory')
        return False

    repo.output = False  # nix qgis_repo output, since using progress bar
    up_bar = Bar("Adding plugins to '{0}'".format(repo.repo_name),
                 fill='=', max=len(downloads))
    up_bar.start()
    try:
        for zip_name in up_bar.iter(downloads):
            repo.update_plugin(
                zip_name,
                name_suffix=args.name_suffix,
                auth=args.auth,
                auth_role=args.auth_role,
                # don't remove existing or just-added plugins when mirroring
                versions='none',
                untrusted=True,
                invalid_fields=(not args.validate_fields)
            )
            # plugins are 'untrusted,' until overwritten with mirrored repo data
    except KeyboardInterrupt:
        return False

    print("Sort plugins in '{0}'".format(repo.repo_name))
    # Sorting is the right thing to do here, plus...
    # Helps ensure 'startswith' finding of plugins will find earliest occurrance
    # of a partial version, e.g. plugin.1.0 is found before plugin.1.0.1
    init_sort = QgisPluginTree.plugins_sorted_by_name(
        repo.plugins_tree.plugins())
    repo.plugins_tree.set_plugins(init_sort)

    up_bar = Bar("Updating '{0}' plugins with mirrored repo data"
                 .format(repo.repo_name),
                 fill='=', max=len(elements))
    up_bar.start()
    cp_tags = ['about', 'average_vote', 'author_name', 'create_date',
               'deprecated', 'description', 'downloads', 'experimental',
               'external_dependencies', 'homepage', 'rating_votes',
               'repository', 'tags', 'tracker', 'trusted', 'update_date',
               'uploaded_by']
    maybe_missing = []
    needs_resorted = False
    try:
        for file_name, el in up_bar.iter(elements.items()):
            nam, _ = os.path.splitext(file_name)
            p = repo.plugins_tree.find_plugin_by_package_name(nam,
                                                              starts_with=True)
            if not p:  # maybe the base version has been adjusted, try again
                temp_nam = re.sub(r'((\d+\.)?(\d+\.)?(\d+))', r'.\1', nam)
                p = repo.plugins_tree.find_plugin_by_package_name(
                    temp_nam, starts_with=True)
            if not p:
                maybe_missing.append(file_name)
                continue
            else:
                p = p[0]

            # print("Updating '{0}'...".format(p[0].get('name')))
            for tag in cp_tags:
                tag_el = el.find(tag)
                tag_p = p.find(tag)
                if tag_el is not None and tag_p is not None:
                    txt = tag_el.text
                    # print("  {0}: {1} <- {2}".format(tag, tag_p.text, txt))
                    if tag in QgisPlugin.metadata_types('cdata'):
                        if tag_el.text is not None:
                            txt = etree.CDATA(tag_el.text)
                    tag_p.text = txt
            # update plugin name
            ns = args.name_suffix if args.name_suffix is not None \
                else repo.plugin_name_suffix
            if el.get('name') is not None:
                el_name = u"{0}{1}".format(el.get('name'), ns)
                if p.get('name') != el_name:
                    needs_resorted = True
                    p.set('name', el_name)
    except KeyboardInterrupt:
        return False

    if needs_resorted:
        print("Re-sorting plugins in '{0}'".format(repo.repo_name))
        re_sort = QgisPluginTree.plugins_sorted_by_name(
            repo.plugins_tree.plugins())
        repo.plugins_tree.set_plugins(re_sort)

    print("Writing '{0}' {1}".format(repo.repo_name, repo.plugins_xml_name))
    repo.write_plugins_xml(repo.plugins_tree_xml())

    print('\nDone mirroring...')

    print("Plugin results:\n  attempted: {0}\n  mirrored: {1}"
          .format(len(tree.plugins()), len(repo.plugins_tree.plugins())))

    if maybe_missing:
        print('\nWARNING (version conflicts): plugins downloaded but MAY not '
              'be in XML after update:\n  {0}\n'
              .format(', '.join(maybe_missing)))

    return True


def serve_repo():
    setup_repo()
    web_dir = os.path.abspath(repo.web_dir)
    log.debug("web_dir: {0}".format(web_dir))
    app = Flask(__name__, root_path=web_dir)

    @app.route("/", methods=['GET'])
    @app.route("/<path:rsc>", methods=['GET'])
    def serve_resource(rsc=""):
        if os.path.isdir(os.path.join(web_dir, rsc)):
            rsc = os.path.join(rsc, repo.html_index)
        log.debug("Sending: {0}".format(rsc))
        return send_from_directory(web_dir, rsc)

    @app.route("/plugins.xml", methods=['GET'])
    def redirect_xml():
        url = url_for('filter_xml', **request.args)
        log.debug("Redirect URL: {0}".format(url))
        return redirect(url)

    @app.route("/plugins/plugins.xml", methods=['GET'])
    def filter_xml():
        """
        Filters plugins.xml removing incompatible plugins.
        If no qgis parameter is found in the query string,
        the whole plugins.xml file is served as is.
        """
        # Points to the real file, not the symlink
        if not request.query_string:
            web_plugins_dir = os.path.abspath(repo.web_plugins_dir)
            return send_from_directory(web_plugins_dir,
                                       repo.plugins_xml_name)
        elif request.args.get('qgis') is None:
            abort(404)
        else:
            tree = QgisPluginTree(repo.plugins_xml)
            root = tree.root_elem()
            qgis_version = vjust(request.args.get('qgis'), force_zero=True)
            for e in root.xpath('//pyqgis_plugin'):
                qv_min = vjust(e.find('qgis_minimum_version').text,
                               force_zero=True)
                qv_max = vjust(e.find('qgis_maximum_version').text,
                               force_zero=True)
                if not (qv_min <= qgis_version <= qv_max):
                    root.remove(e)
            response = make_response(tree.to_xml())
            response.headers['Content-type'] = 'text/xml'
            return response

    if args.host is not None:
        host = args.host
    elif repo.packages_host_name:
        host = repo.packages_host_name
    else:
        host = '127.0.0.1'

    if args.port is not None:
        port = args.port
    elif repo.packages_host_port:
        port = repo.packages_host_port
    else:
        port = '8008'

    app.run(host=host, port=int(port), threaded=True, debug=args.debug)


def package_repo():
    setup_repo()
    repo_name = repo.repo_name
    pkg_temp = 'packaged-repos'
    pkg_dir = os.path.join(SCRIPT_DIR, pkg_temp)

    web_base = os.path.dirname(os.path.abspath(repo.web_dir))
    if not os.path.exists(web_base):
        print("Parent directory of repo '{0}' not found at: {1}"
              .format(repo_name, web_base))
        return False
    os.chdir(web_base)

    print("Gathering '{0}' repo directory data".format(repo_name))
    item_count = sum(len(d) + len(f) for _, d, f in os.walk(repo_name)) + 1
    print("  {0} items to archive".format(item_count))

    if not os.path.exists(pkg_dir):
        os.mkdir(pkg_dir)

    curdatetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    targz = os.path.join(pkg_dir,
                         "{0}-repo_{1}.tar.gz".format(repo_name, curdatetime))
    if os.path.exists(targz):
        os.unlink(targz)

    bar = Bar('Archiving repo', fill='=', max=item_count)

    def size_progress(tarinfo):
        bar.next()
        return tarinfo

    os.chdir(web_base)  # just to make sure
    try:
        bar.start()
        with tarfile.open(targz, "w:gz") as tar:
            tar.add(repo_name, filter=size_progress)
    except KeyboardInterrupt:
        print("\nArchiving error: keyboard interrupt; archive incomplete")
        return False
    except tarfile.TarError as e:
        print("\nArchiving error: {0}".format(e))
        return False
    finally:
        bar.finish()

    print("Repo '{0}' archived: {1}".format(repo_name, targz))

    return True


def clear_repo():
    setup_repo()
    return repo.clear_repo()


if __name__ == '__main__':
    # get defined args
    args = arg_parser().parse_args()
    # out = pprint.pformat(conf) + '\n'
    # out += pprint.pformat(args)
    # print out

    repo = QgisRepo(args.repo, conf, with_output=True)
    # repo.dump_attributes(echo=True)

    sys.exit(not args.func())
