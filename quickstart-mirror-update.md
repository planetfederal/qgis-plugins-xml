# QGIS Python Plugin Repository Generation and Updater Utility

## Quickstart for Mirroring and Updating

> See README.md for complete details on the utility.

Clone this code repo or download the latest archive. Then run:

    $> cd <path/to/code/repo>/scripts
    
Generally, you will want to use the **`plugins-xml.sh`** script, as it is a
wrapper for `plugins-xml.py` and ensures that a proper Python `virtualenv` is
set up prior to running any subcommands. The [`virtualenv` utility is
required][ve] and must be found on PATH.

[ve]: https://virtualenv.pypa.io/en/stable/

### Optionally clear the output repository (repo)

    $> ./plugins-xml.sh clear qgis-mirror
    
    # Ensure uploads directory is clear (example here uses default setup)
    $> rm -R uploads/*

### Mirror **plugins.qgis.org** to 'qgis-mirror' repo
    
    $> time ./plugins-xml.sh mirror  \
       --qgis-versions "3.4,3.8,3.10,3.12" \
       qgis-mirror http://plugins.qgis.org/plugins/plugins.xml

    Downloading/merging xml |================================| 6/6
    Sorting merged plugins
    Writing merged plugins to 'mirror-temp/merged.xml'
    Downloading plugins |================================| 960/960
    Adding plugins to 'qgis-mirror' |================================| 960/960
    Sort plugins in 'qgis-mirror'
    Updating 'qgis-mirror' plugins with mirrored repo data |================================| 960/960
    Writing 'qgis-mirror' plugins.xml
    
    Done mirroring...
    Plugin results:
      attempted: 960
      mirrored: 960

    real    72m22.574s  <-- `time` ouput of command
    user    0m56.382s
    sys     0m19.886s

_Note: See README.md for alternative method of breaking up mirroring operation
into two steps: downloading and processing._

### Add extra plugins to your mirror

First, add any plugin .zip archives to the `scripts/uploads` directory. 

Then run the `update` command for your repo:

    $> ./plugins-xml.sh update --remove-version 'none' --sort-xml qgis-mirror all
    Updating plugins in 'qgis-mirror' |================================| #/#

### Test-serve your repo

    $> ./plugins-xml.sh serve qgis-mirror --host localhost --port 8008
    * Running on http://localhost:8008/ (Press CTRL+C to quit)

Test the following URL in your web browser (should see HTML listing of plugins):

    http://localhost:8008/plugins/plugins.xml?qgis=3.10

If that worked, add the following repo setup to your Plugin Manager (under 
`Settings > Plugin repositories`) in QGIS:

    Name:    A local mirror
    URL:     http://localhost:8008/plugins/plugins.xml
    Enabled: checked

Click `Reload all repositories` button, if they did not automatically reload.

Since you are locally mirroring the QGIS official repo, you will want to
_temporarily_ **disable the 'QGIS Official Plugin Repository' repo setting** 
during the test of the locally served mirror.

### Package your repo for deployment elsewhere

    $> ./plugins-xml.sh package qgis-mirror
    Gathering 'qgis-mirror' repo directory data
     960 items to archive
    Archiving repo |================================| 960/960
    Repo 'qgis-mirror' archived: ./packaged-repos/qgis-mirror-repo_2020-03-03_12-00-00.tar.gz
