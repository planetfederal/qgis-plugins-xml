# QGIS Python Plugin Repository Generation and Updater Utility

Generate and manage a QGIS plugin repository (repo) on the local filesystem.

_**Note**: This is a simple script, geared towards specific tasks. If you are
looking for something more robust, with a frontend and user management, like
what the QGIS project uses for [http://plugins.qigs.org][qp], see the
[QGIS-Django][qd] project._

[qp]: http://plugins.qigs.org
[qd]: https://github.com/qgis/QGIS-Django

This utility helps with deploying and updating your own QGIS plugin repo, either
to help with plugin development or manage a remote custom repo.

**Things you can do with the utility...** 

- Generate and manage a local filesystem, static repo.
- Copy or sync such a repo to a website or S3 bucket.
- Test-serve a local repo for validating plugin installation in QGIS.
- Send a continuous integration job's plugin archive artifact to a repo
- Mirror entire other plugin repos, for various versions of QGIS
- Maintain multiple repos, relative to purpose and authentication needs

## How to use

Clone this code repo or download the latest archive. Then:

    $> cd <path/to/code/repo>/scripts
    
This is the working directory for all operations, unless otherwise defined in
customized settings.

    $> tree .
    .
    ├── load-test-plugins-remote.sh
    ├── load-test-plugins.sh
    ├── plugins-xml.py
    ├── plugins-xml.sh
    ├── settings.py.tmpl
    ├── templates_tmpl
    │   └── ...
    ├── uploads
    └── www

Generally, you will want to use the **`plugins-xml.sh`** script, as it is a
wrapper for `plugins-xml.py` and ensures that a proper Python `virtualenv` is
set up prior to running any subcommands.

**The [`virtualenv` utility][ve] is required and must be found on PATH.**
                                 
[ve]: https://virtualenv.pypa.io/en/stable/

Note: The Python scripts have been developed and tested against Python 3.8.1+,
they will not work with Python 2.7, which is now unsupported.

The `settings.py.tmpl` file and `templates_tmpl` directory offer a means of
*custom configuration** or your own repo(s). Review their contents for
customization hints. To enable these settings, simply duplicate them and remove
the `_tmpl` suffix from each. Otherwise, the scripts will use the defaults
outlined below in the subcommand help.

The `uploads` and `www` are the default input and output directories, though
these can be located elsewhere on the file system, if so defined in custom
settings.

The `load-test-plugins*.sh` scripts allow you to quickly test a repo setup and
remote execution.

## Help for plugins-xml.sh subcommands

_**IMPORTANT**: All commands require a 'repo' parameter, which must match an
entry in the default or custom settings. It is recommended to keep separate
repos for different plugin release types, e.g. dev, beta, release or mirrored.
This aids with long term maintenance of repos._

_However, this is not required and all plugin types can be stored in one repo;
albeit this relies heavily upon QGIS's plugin manager to handle all
multi-version resolutions. Undefined plugin results filtering may occur with
plugins that have non-symantic version syntax._

    $> ./plugins-xml.sh --help
    usage: plugins-xml [-h] {setup,update,remove,mirror,serve,package,clear} ...
    
    Run commands on a QGIS plugin repository on the local filesystem
    
    optional arguments:
      -h, --help            show this help message and exit
    
    subcommands:
      repository action to take... (see 'subcommand -h')
    
      {setup,update,remove,mirror,serve,package,clear}
        setup               Set up an empty repository (all other commands do this
                            as an initial step)
        update              Update/add a plugin in a repository (by default, does
                            not remove any existing versions)
        remove              Remove ALL versions of a plugin from a repository
                            (unless otherwise constrained)
        mirror              Mirror an existing QGIS plugin repository
        serve               Test-serve a local QGIS plugin repository (NOT FOR
                            PRODUCTION)
        package             Package a repository into a compressed archive
        clear               Clear all plugins, archives and icons from a
                            repository

## The `setup` subcommand

Sets up an empty repository (all other commands do this as an initial step). You
may wish to do this to verify the `serve` command or any custom configurations.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh setup -h
    usage: plugins-xml setup [-h] (qgis | qgis-beta | qgis-dev | qgis-mirror)
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
    
    optional arguments:
      -h, --help            show this help message and exit

## The `update` subcommand

Main command for adding/updating a plugin in a repository. By default, it does
not remove any existing versions, unless otherwise specified.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh update --help
    usage: plugins-xml update [-h] [--auth] [--role role-a,...]
                              [--name-suffix SUFFIX] [--git-hash xxxxxxx]
                              [--invalid-fields]
                              [--remove-version (none | all | latest | oldest | #.#.#,...)]
                              [--keep-zip] [--untrusted] [--sort-xml]
                              (qgis | qgis-beta | qgis-dev | qgis-mirror)
                              (all | zip-name.zip)
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
      (all | zip-name.zip)  Name of ZIP archive, or all, in uploads directory to
                            process
    
    optional arguments:
      -h, --help            show this help message and exit
      --auth                Download of stored archive needs authentication
      --role role-a,...     Specify role(s) needed to download a stored archive
                            (implies authentication)
      --name-suffix SUFFIX  Suffix to add to plugin's name (overrides suffix
                            defined in repo settings)
      --git-hash xxxxxxx    Short hash of associated git commit
      --invalid-fields      Do not strictly validate recommended metadata fields
      --remove-version (none | all | latest | oldest | #.#.#,...)
                            Remove existing plugin resources, for specific
                            version(s) (default: none)
      --keep-zip            Do not remove existing plugin ZIP archive(s) when
                            removing a plugin
      --untrusted           Plugin is untrusted (default: trusted)
      --sort-xml            Sort the plugins.xml repo index after updating/adding
                            plugins

The `update` command parses the 'uploads_dir' setting location to process either
a single specified plugin .zip archive or all archives found there. It _does
not_ accept a .zip file path.

The command uses the plugin's [metadata.txt][md] (embedded in a
plugin's ZIP archive) to add a new, or update an existing, plugin in the repo's
`plugins.xml` file.

_Note: the required fields in [metadata.txt][md] are validated by the updater
script (unless otherwise skipped). Ensure your plugin's fields are correctly
annotated. The one exception is `email` address, which is not required for a
simple repository setup (since it would expose it via plain XML)._

[md]: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins.html#plugin-metadata

Because this is a simple `plugins.xml`-based QGIS plugin repository, with no
user input tracking, the following items are _not supported_ in QGIS's plugin
manager interface (unless you are mirroring a repo that already has such data
per plugin):

- Rating
- Rating votes
- Number of downloads

**Defining special plugin types**

By default, there is _no need to pre-package a plugin differently_ for uploading
as a 'dev' or 'beta' version. This is one of the main advantages for using the
`plugins-xml.sh` script, which will handle this for you.

You just need to define a `--name-suffix` command line or `name_suffix` custom
repo setting, which triggers the following changes:

* Adds suffix to name, e.g. using `--name-suffix ' Dev'`
  * plugin name `My Plugin` --> `My Plugin DEV`

* Adds date/time stamp to version and ZIP archive
  * version `0.1.0` --> `0.1.0-201603112146`
  * archive name `plugin_name_0.1.0.zip` --> `plugin_name_0.1.0-201603112146.zip`
  * (optionally) any `--git-hash <myhash>` short hash is appended
    * `0.1.0` --> `0.1.0-201603112146-<myhash>`
    * `plugin_name_0.1.0.zip` --> `plugin_name_0.1.0-201603112146-<myhash>.zip`

These changes ensure:

* New revisions with the same base version, e.g. `0.1.0`, will always be
  considered as _newer_ by QGIS's plugin manager.

* Users browsing the plugin manager will easily see that the name and version
  indicate a _special version_, regardless of whether the plugin is
  installed via remote connection to the plugin repo or the user directly
  downloads a plugin archive and manually installs it.

* Manually downloaded plugin archives from the plugin repo server can easily
  be referenced by their date/time stamped file name, as well as any optionally
  supplied git short hash.

**NOTE:** These changes are _applied_ to the `metadata.txt` within the plugin's
ZIP archive as well, so they are persistent even after the user has installed
the plugin. No such changes are done for non-'name suffix' plugin repo updates.

**Defining authentication constraints**

Using the `--auth` flag allows the plugin's package to be stored in and served 
from a separate directory. This facilitate web server authentication 
configuration, e.g. SSL with HTTP Basic auth.

The `--role` option(s) helps maintain authorization roles, useful for checking
the user's ability to actually download the plugin's archive once the plugin's
role is validated against the user's permissions. Of course, this assumes some
form of external validation already exists, e.g. OAuth, some auth API, etc., 
that is managed by your web server application.

**Examples**

    # Regular 'release' version of plugin added to repo
    
    $> ./plugins-xml.sh update qgis test_plugin_1.zip
    Updating plugins in 'qgis' |================================| 1/1
    
    
    # Authenticated 'beta' version of plugin added to 'beta' repo with role
    
    $> ./plugins-xml.sh update --auth --role 'beta-tester' --name-suffix ' \
       BETA' --git-hash xxxxxxx qgis-beta test_plugin.zip
    Updating plugins in 'qgis-beta' |================================| 1/1

    # Results in:
    #   plugin XML appended to end of plugins.xml
    #   plugin version in XML and metadata.txt: 0.1-201801080917-xxxxxxx
    #   download archive name: test_plugin.0.1-201801080917-xxxxxxx.zip
    #   archive placed in 'packages-auth' instead of 'packages'
    #   <authorization_role>beta-tester</authorization_role> added to plugins.xml
    #   no version of plugin removed (so previous betas remain avaliable)
        

    # Add 'dev' version of plugin added to separate 'dev' repo
    # (with overrides of repo settings and allowing incomplete metadata.txt)
    
    $> ./plugins-xml.sh update --name-suffix ' DEV' --git-hash xxxxxxx \
       --invalid-fields --remove-version 'latest' qgis-dev test_plugin.zip
    Updating plugins in 'qgis' |================================| 1/1
    
    # Results in:
    #   plugin XML appended to end of plugins.xml
    #   plugin version in XML and metadata.txt: 0.1-201801080855-xxxxxxx
    #   download archive name: test_plugin.0.1-201801080855-xxxxxxx.zip
    #   most recent version of existing plugin removed (only latest dev version exists)

    
    # Add a third-party plugin to your repo, but don't want to vouch for its 
    # trustworthiness or metadata.txt
    
    $> ./plugins-xml.sh update --untrusted --invalid-fields qgis test_plugin.zip
    Updating plugins in 'qgis' |================================| 1/1

        
    # Manual package-only mirroring of already-downloaded, trusted plugins
    # (see also 'mirror' subcommand)
    
    $> ./plugins-xml.sh update --remove-version 'none' --sort-xml qgis-mirror all
    
    
    # Upload a plugin archive and run repo updater script on a remote server
    # Note: `domain.local` is a reference to an SSH config alias
    #       see http://www.openssh.com/manual.html
    
    # Upload a test plugin archive to server (example paths):
    
    $> scp uploads/test_plugin_1.zip domain.local:/opt/repo-updater/uploads/
    
    # Run remote updater script on uploaded archive (example paths)
    
    $> ssh domain.local "/opt/repo-updater/plugins-xml/scripts/plugins-xml.sh \
       update --remove-version 'latest' qgis-repo-name my_plugin.zip"

## The `remove` subcommand

Removes ALL versions of a plugin from a repository (unless otherwise 
constrained).

**Warning**: If you are maintaining multiple versions of the same plugin in a
single repo, e.g. for different versions of QGIS accessing the repo, you have
to **very careful** not to unintentionally remove older versions. You can go to the 
`plugins/plugins.xml` served URL path in your Web browser, or browse
QGIS's plugin manager, to help find the exact version you wish to remove.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh remove --help
    usage: plugins-xml remove [-h] [--keep-zip] [--name-suffix SUFFIX]
                              (qgis | qgis-beta | qgis-dev | qgis-mirror)
                              plugin_name (all | latest | oldest | #.#.#,...)
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
      plugin_name           Name of plugin (NOT package) in repository
      (all | latest | oldest | #.#.#,...)
                            Remove existing plugin with specific version(s)
                            (default: latest)
    
    optional arguments:
      -h, --help            show this help message and exit
      --keep-zip            Do not remove plugin ZIP archive(s)
      --name-suffix SUFFIX  Suffix to add to plugin's name (overrides suffix
                            defined in repo settings)

**Examples**

    # Remove all versions of a plugin from 'release' repo

    $> ./plugins-xml.sh remove qgis "Test Plugin" all
    Loading plugin tree from plugins.xml
    Attempt to remove: Test Plugin
    Removing 2 found 'Test Plugin' plugins...
    Removing version 0.1 ...
      removing from plugins.xml
      removing icon: ./www/qgis/plugins/icons/test_plugin/0.1.png
      removing .zip: ./www/qgis/plugins/packages/test_plugin.0.1.zip
    Removing version 0.2 ...
      removing from plugins.xml
      removing icon: ./www/qgis/plugins/icons/test_plugin/0.2.png
      removing .zip: ./www/qgis/plugins/packages/test_plugin.0.2.zip
    Writing plugins.xml: ./www/qgis/plugins/plugins.xml
    

    # Remove a 'dev' version plugin, accidentally added to the 'release' repo

    $> ./plugins-xml.sh remove qgis "Test Plugin 3 DEV" "0.1-201801080855-xxxxxxx"
    Loading plugin tree from plugins.xml
    Attempt to remove: Test Plugin 2 DEV
    Removing 1 found 'Test Plugin 2 DEV' plugins...
    Removing version 0.1-201801080855-xxxxxxx ...
      removing from plugins.xml
      removing icon: ./www/qgis/plugins/icons/test_plugin_2/0.1-201801080855-xxxxxxx.png
      removing .zip: ./www/qgis/plugins/packages/test_plugin_2.0.1-201801080855-xxxxxxx.zip
    Writing plugins.xml: ./www/qgis/plugins/plugins.xml

## The `mirror` subcommand

Mirrors an existing locally or remotely served QGIS plugin repository.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh mirror -h
    usage: plugins-xml mirror [-h] [--auth] [--role role-a,...]
                              [--name-suffix SUFFIX] [--validate-fields]
                              [--only-xmls] [--only-download] [--skip-download]
                              [--qgis-versions #.#[,#.#,...]]
                              (qgis | qgis-beta | qgis-dev | qgis-mirror)
                              http://example.com/plugins.xml
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
      http://example.com/plugins.xml
                            plugins.xml URL of repository to be mirrored
    
    optional arguments:
      -h, --help            show this help message and exit
      --auth                Download of stored archive needs authentication
      --role role-a,...     Specify role(s) needed to download a stored archive
                            (implies authentication)
      --name-suffix SUFFIX  Suffix to add to plugin's name (overrides suffix
                            defined in repo settings)
      --validate-fields     Strictly validate recommended metadata fields
      --only-xmls           Download all plugin.xml files for QGIS versions and
                            generate download listing
      --only-download       Download all plugin.xml files for QGIS versions, then
                            download all referenced plugins (implies --only-xmls).
                            Mostly for testing or when cautiously mirroring MANY
                            plugins, where the uploads directory is copied to a
                            backup afterwards.
      --skip-download       Skip downloading, as components are already
                            downloaded. Mostly for testing or when updating MANY
                            mirrored plugins MAY fail. The a backup of downloads
                            (from --only-download) are copied back into the
                            uploads directory and the merge.xml file is still
                            present.
      --qgis-versions #.#[,#.#,...]
                            Comma-separated version(s) of QGIS, to filter request
                            results(define versions to avoid undefined endpoint
                            filtering behavior)

Mirroring does the following steps:

- Downloads all .xml output for each specified QGIS version
- Downloads any found plugins when parsing the combined .xml files
- Loads the found plugins them into a new or existing repo after validating the
.zip archives

Note: The command _does not_ just copy the .zip archives to a repo and append
the combined XML, but instead processes each downloaded plugin the same as
running the `update` subcommand on it.

When mirroring very large repos, like [plugins.qgis.org](plugins.qgis.org), 
it is prudent to break up the operation into two steps: _downloading_ and
_processing_. This allows multiple attempts at mirroring without having to
re-download all the plugins. Errors in archive validation or manipulation (as
is done to all archives when specifying a `name-suffix`) can occur. See
examples below for command options to aid each step.

**Examples**

    # Full mirroring of plugins.qgis.org to 'qgis-mirror' repo, but prudently
    # start by only downloading .xml files (merging them) and .zip archives.
    
    $> time ./plugins-xml.sh mirror --only-download  \
       --qgis-versions "3.4,3.8,3.10,3.12" \
       qgis-mirror http://plugins.qgis.org/plugins/plugins.xml
    Downloading/merging xml |================================| 6/6
    Sorting merged plugins
    Writing merged plugins to 'mirror-temp/merged.xml'
    Downloading plugins |================================| 960/960
    Downloads complete, exiting since --only-download specified
    
    real    72m22.574s
    user    0m56.382s
    sys     0m19.886s
    
    # You can now copy 'mirror-temp/merged.xml' and 'uploads' directory
    # somewhere as a backup, to be used (copied back into place) if the next
    # operation fails. If working with a fresh repo, consider using the 'clear' 
    # subcommand to reset repo before retrying next step after an error occurred.
    
    # Finish full mirroring of plugins.qgis.org; process downloaded plugins
    
    $> ./plugins-xml.sh mirror --skip-download \
       qgis-mirror http://plugins.qgis.org/plugins/plugins.xml
    Adding plugins to 'qgis-mirror' |================================| 960/960
    Sort plugins in 'qgis-mirror'
    Updating 'qgis-mirror' plugins with mirrored repo data |================================| 960/960
    Writing 'qgis-mirror' plugins.xml
    
    Done mirroring...
    Plugin results:
      attempted: 960
      mirrored: 960

## The `serve` subcommand

Test-serves a local QGIS static-file plugin repository, with the ability to
handle `?qgis=X.X` version-constraining queries (as is requested by QGIS
itself).

**!! THIS IS NOT FOR PRODUCTION USE !!** Only use this for testing purposes. For
production, use a robust HTTP server, like Apache or Nginx, with WSGI support
for the included Flask app that offers a means of handling `?qgis=X.X`
version-constraining queries. Such setups are outside the scope of this 
documentation.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh serve -h
    usage: plugins-xml serve [-h] [--host hostname] [--port number] [--debug]
                            (qgis | qgis-beta | qgis-dev | qgis-mirror)
    
    positional arguments:
     (qgis | qgis-beta | qgis-dev | qgis-mirror)
                           Actions apply to one of these output repositories
                           (must be defined in settings)
    
    optional arguments:
     -h, --help            show this help message and exit
     --host hostname       Host name to serve under
     --port number         Port number to serve under
     --debug               Run test server in debug mode

When using default or customized settings with non-`localhost` host names,
**you will need to update your `/etc/hosts` file**, for local previewing in
your web browser, e.g.:

    # QgisRepo
    127.0.0.1 qgis-repo.local
    127.0.0.1 dev.qgis-repo.local
    127.0.0.1 beta.qgis-repo.local
    127.0.0.1 mirror.qgis-repo.local

**Examples**

    $> ./plugins-xml.sh serve qgis-mirror
    * Running on http://mirror.qgis-repo.local:8008/ (Press CTRL+C to quit)
    
    # Go to http://mirror.qgis-repo.local:8008/plugins/plugins.xml in your
    # web browser will show HTML rendering of the plugin repo.
    
    # To replicate what your QGIS version will query:
    #   http://mirror.qgis-repo.local:8008/plugins/plugins.xml?qgis=3.10

## The `package` subcommand

Packages a repository into a compressed archive.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh package --help
    usage: plugins-xml package [-h] (qgis | qgis-beta | qgis-dev | qgis-mirror)
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
    
    optional arguments:
      -h, --help            show this help message and exit

**Examples**

    $> ./plugins-xml.sh package qgis
    Gathering 'qgis' repo directory data
     23 items to archive
    Archiving repo |================================| 23/23
    Repo 'qgis' archived: ./packaged-repos/qgis-repo_2018-01-08_07-31-36.tar.gz


## The `clear` subcommand

Clears all plugins, archives and icons from a repository, then sets up an empty
repo with default (or custom-defined) settings.

_Note: Repo names are default examples_

    $> ./plugins-xml.sh clear --help
    usage: plugins-xml clear [-h] (qgis | qgis-beta | qgis-dev | qgis-mirror)
    
    positional arguments:
      (qgis | qgis-beta | qgis-dev | qgis-mirror)
                            Actions apply to one of these output repositories
                            (must be defined in settings)
    
    optional arguments:
      -h, --help            show this help message and exit

**Examples**
    
    # with debug output on
    
    $> ./plugins-xml.sh clear qgis-dev
    Removing any existing repo contents...
    Setting up new repo...
    Copying root HTML index file: ./www/qgis-dev/index.html
    Copying root HTML favicon: ./www/qgis-dev/favicon.ico
    Making web_plugins_dir: ./www/qgis-dev
    Copying plugins HTML index file: ./www/qgis-dev/plugins/index.html
    Copying plugins.xml from template: plugins.xml
    Copying plugins.xsl from template: plugins-dev.xsl
    Making packages_dir: ./www/qgis-dev/plugins/packages
    Making packages_dir (for auth): ./www/qgis-dev/plugins/packages-auth
    Making icons_dir: ./www/qgis-dev/plugins/icons
    Copying default icon from template: default-dev.png

