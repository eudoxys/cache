"""Cache manager

The cache manager handles the data cache for all downloaded data. The cache is
necessary to enhance the overall performance of the Eudoxys packages. The cache
can be cleared using the command

    cache clear

Example
-------

    from cache import Cache
    import pandas as pd
    cache = Cache(["ST","County","file.csv"])
    if cache.exists():
        data = pd.read_csv(cache.pathname)
    else:
        data = pd.DataFrame({"test":[1,2,3]})
        data.to_csv(cache.pathname)

Archives
--------

When a cache file does not exist locally, `Cache.exists()` and `Cache.open()`
scan the archives listed in `ARCHIVES`, in order. Each archive is a URL
template whose fields are filled from the cache entry:

  - `{package}`: the cache package name

  - `{path}`: the cache path joined with `/` (URL-quoted)

Archives are not versioned: an archive is assumed to always hold the latest
version of each cache file, so the cache `version` is not used to search an
archive. A file downloaded from an archive is stored in the cache folder of
the requested version, i.e., at `pathname`, which is
`CACHEDIR/package/version/path`.

The default archive is the Eudoxys WECC data archive
(https://github.com/eudoxys/wecc), which stores files as
`wecc/{package}/{path}`, e.g., the cache entry

    Cache(["AZ","Apache","C.csv.gz"],package="loads")

is found in the archive at `wecc/loads/AZ/Apache/C.csv.gz` and downloaded to
`CACHEDIR/loads/0/AZ/Apache/C.csv.gz`. The same archive file is used for
`version=2`, and is then stored in `CACHEDIR/loads/2/AZ/Apache/C.csv.gz`.

If the file exists in an archive, `exists()` returns `True` without
downloading it, and `open()` downloads it into the cache folder (at
`pathname`) and opens the local copy. Opening for writing (`"w"` or `"x"`
modes) never downloads. Archives are not searched when `package` is `None`.

To disable archives, or to add others, change the module global, e.g.,

    import cache.cache
    cache.cache.ARCHIVES = []

Caveats
-------

  - `exists()` returning `True` for an archived file does not mean
    `pathname` exists yet; call `open()` (or `download()`) before reading
    `pathname` directly.

  - Because archives hold only the latest version, a package that reads an
    older cache `version` gets the latest archived file stored under that
    older version's folder. Packages should request the current version.

  - Network errors are treated as "not in this archive" and logged at DEBUG,
    so the cache works offline.
"""

import os
import stat
import warnings
import shutil
import logging
import tempfile
import urllib.error
import urllib.parse
import urllib.request

_logger = logging.getLogger(__file__)

PACKAGE = "cache"
"""Default package name (root of cache file tree)"""

VERSION = 0
"""Default cache schema version (root of package cache file tree)"""

ARCHIVES = [
    "https://raw.githubusercontent.com/eudoxys/wecc/main/wecc/{package}/{path}",
    ]
"""List of cache archive URL templates, scanned in order when a cache file
does not exist locally (see Archives above). The fields `{package}` and
`{path}` are filled from the cache entry. Archives are searched without the
cache version because they always hold the latest version of each file.
"""

ARCHIVE_TIMEOUT = 10
"""Timeout in seconds for each archive request"""

class Cache:
    """Cache manager class implementation"""
    CACHEDIR = os.path.join(os.path.dirname(__file__),".cache")
    """Specifies the default folder for cache files constructed by this class"""

    def __init__(self,
        path:str|list[str],
        package:str=PACKAGE,
        version:int|str|float=VERSION,
        ):
        """Construct a cache file handler

        Arguments
        ---------

          - `path`: cache file tree path

          - `package`: cache package name (default is `"cache"`)

          - `version`: cache version number (default `0`)
        """

        # check path
        assert isinstance(package,str) or package is None, f"{package=} must be a string"
        assert package is None or isinstance(version,(int,str,float,type(None))), f"{version=} must be a string or number"

        self.package = package
        """Package name"""

        self.version = version
        """Cache schema version number"""

        if isinstance(path,str):
            path = [path]
        elif isinstance(path,list):
            path = [str(x) for x in path]

        if package is None:
            self.root = self.CACHEDIR
        else:
            self.root = os.path.join(self.CACHEDIR,package,str(version))
        """Specifies the root folder of the cache, which includes the package
        name and the version number
        """

        self.path = [x.replace(" ","_") for x in path]
        """Specifies the path to the cache file"""
        self.name = self.path[-1]
        """Specifies the name of the cache file
        """
        self.pathname = os.path.join(self.root,*self.path)
        """Specifies the full path and name of the cache file
        """
        self.dirname = os.path.dirname(self.pathname)
        """Specifies the folder name of the cache file
        """

        self.archive = None
        """URL of the archived copy of the cache file, if one was found by
        `exists()`, `open()`, or `download()`, otherwise `None`
        """

        _logger.debug(f"Cache({package=},{version=},{path=}) --> '{self.pathname}'")
        os.makedirs(self.dirname,exist_ok=True)

    @classmethod
    def cachedir(cls,*args,makedirs=True):
        """Get/set cache directory

        Arguments
        ---------

          - `*args`: path to directory

        Returns
        -------

          - `path`: path to directory if `*args` is empty, path to old
            directory if `*args` is not empty
        """
        if not args:
            return cls.CACHEDIR
        olddir = cls.CACHEDIR
        cls.CACHEDIR = os.path.join(*args)
        if makedirs:
            os.makedirs(cls.CACHEDIR,exist_ok=True)
        return olddir

    def open(self,mode="r",encoding="utf-8"):
        """Open cache file

        Arguments
        ---------

          - `mode`: file open mode (see `open`)

          - `encoding`: file encoding (see `open`)

        Returns
        -------

          - `io.IOBase`: file handle
        """
        assert isinstance(mode,str), f"{mode=} must be a string"
        assert isinstance(encoding,str), f"{encoding=} must be a string"
        if mode[:1] not in "wx" and not os.path.exists(self.pathname):
            self.download()
        return open(self.pathname,mode,encoding=encoding)

    def exists(self):
        """Tests for existence of cache file locally or in an archive

        Returns
        -------

          - `bool`: `True` if the file exists in the cache folder or in one
            of the `ARCHIVES`, otherwise `False`
        """
        return os.path.exists(self.pathname) or self._find_archive() is not None

    def download(self):
        """Download the cache file from the first archive that has it

        The archived file (always the latest version) is stored in the cache
        folder of this entry's version, at `pathname`. Does nothing if the
        file already exists there.

        Returns
        -------

          - `bool`: `True` if the file exists in the cache folder afterward,
            otherwise `False`
        """
        if os.path.exists(self.pathname):
            return True
        url = self._find_archive()
        if url is None:
            return False
        try:
            with urllib.request.urlopen(url,timeout=ARCHIVE_TIMEOUT) as response:
                # write atomically so a failed download never leaves a partial file
                fd,tmpname = tempfile.mkstemp(dir=self.dirname,prefix=".download-")
                try:
                    with os.fdopen(fd,"wb") as fh:
                        shutil.copyfileobj(response,fh)
                    os.replace(tmpname,self.pathname)
                except BaseException:
                    os.remove(tmpname)
                    raise
        except (urllib.error.URLError,OSError) as err:
            _logger.debug(f"download {url=} failed: {err}")
            return False
        _logger.debug(f"downloaded {url=} to {repr(self.pathname)}")
        return True

    def _urls(self):
        """@private Generate the candidate archive URLs for this cache file

        Archives always hold the latest version of a file, so the cache
        version is not part of the archive URL.
        """
        if self.package is None:
            return
        path = "/".join(urllib.parse.quote(x) for x in self.path)
        for archive in ARCHIVES:
            yield archive.format(
                package=urllib.parse.quote(self.package),
                path=path,
                )

    def _find_archive(self):
        """@private Find the first archive URL that has this cache file

        Returns
        -------

          - `str|None`: archive URL, or `None` if no archive has the file
        """
        if self.archive is not None:
            return self.archive
        for url in self._urls():
            try:
                request = urllib.request.Request(url,method="HEAD")
                with urllib.request.urlopen(request,timeout=ARCHIVE_TIMEOUT):
                    pass
                _logger.debug(f"found {url=}")
                self.archive = url
                return url
            except (urllib.error.URLError,OSError,ValueError) as err:
                _logger.debug(f"not found {url=}: {err}")
        return None

    def delete(self,ignore_errors:bool=True):
        """Delete the cache file

        Arguments
        ---------

          - `ignore_errors`: enables ignoring of `FileNotFoundError` exceptions
        """
        assert isinstance(ignore_errors,bool), f"{ignore_errors=} must be a Boolean value"
        try:
            os.remove(self.pathname)
            _logger.debug(f"deleted {repr(self.pathname)}")
        except FileNotFoundError:
            if not ignore_errors:
                raise
            _logger.debug(f"deleted {repr(self.pathname)} file not found")

    def backup(self,
        file="cache.zip",
        path:str|list[str]=None,
        package:str="cache",
        version:int|str|float=0,
        ):
        """@private Backup a cache to file
        
        Arguments
        ---------

          - `file`: the filename 

          - `path`: the cache path to backup

          - `package`: the package from which cache is being backed u

          - `version`: the version of the cache data to backup
        """
        _logger.error(f"backup {repr(self.pathname)} not implemented")
        raise NotImplementedError("TODO")

    def restore(self,
        file:str="cache.zip",
        ):
        """@private Restore a backup of cache 

        Arguments
        ---------

          - `file`: the backup file to restore from
        """
        _logger.error(f"restore {repr(self.pathname)} not implemented")
        raise NotImplementedError("TODO")

    def __str__(self):
        return self.pathname

    def __repr__(self):
        return f"Cache(package='{self.package}',version={self.version},path={self.path})"

    @classmethod
    def clear(cls,
        path:list[str]=None,
        package:str=PACKAGE,
        version:int|str|float=VERSION,
        clear_ro:bool=True,
        ):
        """Clears the cache at the specified level

        Arguments
        ---------

          - `path`: specifies the path to clear, e.g., `["CA","Alameda"]`

          - `clear_ro`: enable clearing of read-only files
        """
        if path is None:
            path = []
        assert isinstance(path,list), f"{path=} must be a list"
        for name in path:
            assert isinstance(name,str), f"{name=} must be a string"
        assert isinstance(clear_ro,bool), f"{clear_ro=} must be a Boolean"
        def rm_ro(remove_call,path,_):
            os.chmod(path,stat.S_IWRITE)
            remove_call(path)
            _logger.debug(f"cleared read-only file {path=}")
        shutil.rmtree(
            path=os.path.join(cls.CACHEDIR,*path),
            ignore_errors=True,
            onexc=rm_ro if clear_ro else None,
            )
        _logger.debug(f"cleared {repr(cls.CACHEDIR)}")

def cache_clear(path=None):
    """Clear cache files

    Arguments

      - `path`: the path to clear, e.g., `["CA","Alameda"]`
    """
    Cache.clear(path)

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    cache = Cache(["TEST","Test county","test name.csv"])
    Cache.clear()
