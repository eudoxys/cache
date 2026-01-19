"""Eudoxys cache manager CLI

Syntax
------

    cache {clear,size,backup,restore} [--package PACKAGE] [--version VERSION] 
          [-P|--path PATH] [-C|--cachedir CACHEDIR] [-f|--filename FILENAME]
          [-h] [-w|--warning] [-d|--debug] 

Commands
--------

  - `clear`: clear the specified `PATH` in the `CACHEDIR`

  - `size`: shows the disk usage of the specified `PATH` in the `CACHEDIR`

  - `backup`: backup the specified cache to `FILENAME` `tar` file

  - `restore`: restore the specified cache from `FILENAME` `tar` file

Options
-------

  - `-h|--help`: show this help message and exit

  - `--package PACKAGE: package name

  - `--version VERSION: version number

  - `-C|--cachedir CACHEDIR`: cache working folder

  - `-P|--path PATH`: cache path to clear

  - `-w|--warning`: enable warning messages from python

  - `-d|--debug`: enable debug traceback on exceptions

Description
-----------

The Eudoxys cache manager allows users of Eudoxys packages to manage the data
cache used to enhance the performance of packages that makes intensive use of
online data sources.

The cache folder hierarchy is as follows

  - `package`: the root folder refers the package using the cache

  - `version`: the version number refers the package cache schema version

  - `path`: the path is an arbitrarily deep folder tree to store the file. The
    last element the path is the `name.ext`, which specifies the name and
    extension and indicates the cache file's name and type, respectively.

When using `backup` and `restore`, the `tar` file will be compressed if
`FILENAME` ends with `.gz`.

Package information
-------------------

  - Source code: https://github.com/eudoxys/cache

  - Documentation: https://www.eudoxys.com/cache

  - Issues: https://github.com/eudoxys/cache/issues

  - License: https://github.com/eudoxys/cache/blob/main/LICENSE
"""

from .cache import Cache
from .cli import main
