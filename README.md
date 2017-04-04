# How to add or update PyQGIS plugins

The Python updater script uses the plugin's [metadata.txt][md] (embedded in the
ZIP archive) to add a new, or update an existing, plugin in the repo's
`plugins.xml` file.

Note: the required fields in [metadata.txt][md] are validated by the updater
script. Ensure your plugin's fields are correctly annotated. The one exception
is `email` address, which is not required for a simple repository setup (since
it would expose it via plain HTML).

[md]: http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins.html#plugin-metadata

Because this is a simple `plugins.xml`-based QGIS plugin repository, the
following items are _not supported_ in QGIS's plugin manager interface:

- Rating
- Rating votes
- Number of downloads

## To upload a ZIP archive and remotely run repo updater script

_Note: `boundless.test` is a reference to an SSH config alias (see
[ssh_config][shc])._

[shc]: http://www.openssh.com/manual.html

Copy a test plugin's ZIP archive up to server:

    $> scp uploads/test_plugin_1.zip boundless.test:/opt/repo-updater/uploads/

Run remote updater script on uploaded archive:

    $> ssh boundless.test "/opt/repo-updater/plugins-xml/plugins-xml.sh update test_plugin_1.zip"

Upon updating, any existing plugin in the repo that _exactly
matches_ the plugin's name (e.g. "GeoServer Explorer") will first be removed
from the XML file. Existing download archives will not be removed.

## Updates to 'development' or 'beta' repository

By default, there is no need to package a plugin for uploading to the 'dev' or 'beta' repo
differently than one for the 'release' repo. Upon update, the `plugins-xml.sh`
script will do the following:

* Add DEV (or BETA) suffix to name
  * plugin name `GeoServer Explorer` --> `GeoServer Explorer DEV`

* Add date/time stamp to version and ZIP archive
  * version `0.1.0` --> `0.1.0-201603112146`
  * archive name `plugin_name_0.1.0.zip` --> `plugin_name_0.1.0-201603112146.zip`
  * (optionally) any `--git-hash <myhash>` short hash is appended
    * `0.1.0` --> `0.1.0-201603112146-<myhash>`
    * `plugin_name_0.1.0.zip` --> `plugin_name_0.1.0-201603112146-<myhash>.zip`

These dev (or beta) plugin-only changes ensure:

* New development/beta revisions with the same base version, e.g. `0.1.0`, will
  always be considered as _newer_ by QGIS's plugin manager.

* Users browsing the plugin manager will easily see that the name and version
  indicate a _development version_, regardless of whether the plugin is
  installed via remote connection to the plugin repo or the user directly
  downloads a plugin archive and manually installs it.

* Manually downloaded dev/beta plugin archives from the plugin repo server can easily
  be referenced by their date/time stamped file name, as well as any optionally
  supplied git short hash.

**NOTE:** These changes are _applied_ to the `metadata.txt` within the plugin's
ZIP archive as well, so they are persistent even after the user has installed
the plugin. No such changes are done for 'release' plugin repo updates.

## Help for plugins-xml.sh subcommands

Available subcommands:

    $> ./plugins-xml.sh --help
    usage: plugins-xml.py [-h] {update,remove,clear} ...

    Run commands on a QGIS plugin repository

    optional arguments:
      -h, --help            show this help message and exit

    subcommands:
      repository action to take... (see 'subcommand -h')

      {update,remove,clear}
        update              Update/add a plugin in the repository
        remove              Remove a plugin from the repository
        clear               Clear all plugins, archives and icons from repository

The `update` subcommand:

    $> ./plugins-xml.sh update --help
    usage: plugins-xml.py update [-h] [--dev] [--auth] [--git-hash HASH] zip_name

    positional arguments:
      zip_name         Name of uploaded ZIP archive in uploads directory

    optional arguments:
      -h, --help       show this help message and exit
      --dev            Actions apply to development repository
      --beta           Actions apply to beta repository
      --auth           Indicates download archive needs authentication
      --git-hash HASH  Short hash of associated git commit

The `remove` subcommand:

    $> ./plugins-xml.sh remove --help
    usage: plugins-xml.py remove [-h] [--dev] [--keep-zip] plugin_name

    positional arguments:
      plugin_name  Name of plugin (not package) in repository

    optional arguments:
      -h, --help   show this help message and exit
      --dev        Actions apply to development repository
      --beta       Actions apply to beta repository
      --keep-zip   Do not remove plugin ZIP archive

The `clear` subcommand:

    $> ./plugins-xml.sh clear --help
    usage: plugins-xml.py clear [-h] [--dev]

    optional arguments:
      -h, --help  show this help message and exit
      --dev       Actions apply to development repository
      --beta      Actions apply to beta repository
