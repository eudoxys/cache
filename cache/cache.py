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
"""

import os
import stat
import warnings
import shutil
import logging

_logger = logging.getLogger(__file__)

PACKAGE = "cache"
"""Default package name (root of cache file tree)"""

VERSION = 0
"""Default cache schema version (root of package cache file tree)"""

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
        return open(self.pathname,mode,encoding=encoding)

    def exists(self):
        """Tests for existence of cache file

        Returns
        -------

          - `bool`: `True` if file exists, otherwise `False
        """
        return os.path.exists(self.pathname)

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
