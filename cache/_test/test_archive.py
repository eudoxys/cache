"""Tests for cache archive support (`ARCHIVES`)"""

# pylint: disable=redefined-outer-name,unused-argument # pytest fixtures

import os
import pathlib

import pytest

import cache.cache as cachemod
from cache import Cache

@pytest.fixture
def archive(tmp_path,monkeypatch):
    """Local file:// archive holding `pkg/ST/County_Name/data.csv`"""
    root = tmp_path / "archive"
    (root / "pkg" / "ST" / "County_Name").mkdir(parents=True)
    (root / "pkg" / "ST" / "County_Name" / "data.csv").write_text("a,b\n1,2\n")
    monkeypatch.setattr(cachemod,"ARCHIVES",[root.as_uri() + "/{package}/{path}"])
    olddir = Cache.cachedir(str(tmp_path / "cache"))
    yield root
    Cache.cachedir(olddir)

def test_default_archive():
    """The WECC archive is the only default archive"""
    assert len(cachemod.ARCHIVES) == 1
    assert "eudoxys/wecc" in cachemod.ARCHIVES[0]

def test_exists_in_archive(archive):
    """exists() is True for an archived file and does not download it"""
    cache = Cache(["ST","County Name","data.csv"],package="pkg")
    assert cache.exists()
    assert not os.path.exists(cache.pathname)
    assert cache.archive.endswith("/pkg/ST/County_Name/data.csv")

def test_open_downloads(archive):
    """open() downloads an archived file into the cache folder"""
    cache = Cache(["ST","County Name","data.csv"],package="pkg")
    with cache.open() as fh:
        assert fh.read() == "a,b\n1,2\n"
    assert os.path.exists(cache.pathname)
    assert not [x for x in os.listdir(cache.dirname) if x.startswith(".download-")]

def test_missing_everywhere(archive):
    """exists() is False and open() raises when no archive has the file"""
    cache = Cache(["ST","County Name","missing.csv"],package="pkg")
    assert not cache.exists()
    assert not cache.download()
    with pytest.raises(FileNotFoundError):
        cache.open()

def test_open_write_does_not_download(archive):
    """open() for writing creates the file locally and ignores archives"""
    cache = Cache(["ST","County Name","data.csv"],package="pkg")
    with cache.open("w") as fh:
        fh.write("local\n")
    assert pathlib.Path(cache.pathname).read_text(encoding="utf-8") == "local\n"

def test_local_file_preferred(archive):
    """A local cache file is used without consulting archives"""
    cache = Cache(["ST","County Name","data.csv"],package="pkg")
    pathlib.Path(cache.pathname).write_text("local\n",encoding="utf-8")
    assert cache.exists()
    assert cache.archive is None
    with cache.open() as fh:
        assert fh.read() == "local\n"

def test_archive_scan_order(archive,tmp_path,monkeypatch):
    """Archives are scanned in order; an archive without the file is skipped"""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(cachemod,"ARCHIVES",[
        empty.as_uri() + "/{package}/{path}",
        archive.as_uri() + "/{package}/{path}",
        ])
    cache = Cache(["ST","County Name","data.csv"],package="pkg")
    assert cache.exists()
    assert cache.archive.startswith(archive.as_uri())

def test_version_not_searched(archive):
    """Archives are searched without the version; downloads go to the version folder"""
    for version in [0,2,"1.5"]:
        cache = Cache(["ST","County Name","data.csv"],package="pkg",version=version)
        assert cache.exists()
        assert "/pkg/ST/County_Name/data.csv" in cache.archive
        assert str(version) not in cache.archive.split("/pkg/",1)[1]
        assert cache.download()
        assert cache.pathname == os.path.join(Cache.cachedir(),"pkg",str(version),
            "ST","County_Name","data.csv")
        with open(cache.pathname,encoding="utf-8") as fh:
            assert fh.read() == "a,b\n1,2\n"

def test_version_field_rejected(archive,monkeypatch):
    """Archive templates cannot use a {version} field"""
    monkeypatch.setattr(cachemod,"ARCHIVES",[archive.as_uri() + "/{package}/{version}/{path}"])
    with pytest.raises(KeyError):
        Cache(["ST","County Name","data.csv"],package="pkg").exists()

def test_no_archives(archive,monkeypatch):
    """An empty ARCHIVES list disables archive lookup"""
    monkeypatch.setattr(cachemod,"ARCHIVES",[])
    assert not Cache(["ST","County Name","data.csv"],package="pkg").exists()

def test_no_package(archive):
    """Archives are not searched when package is None"""
    assert not Cache(["pkg","ST","County Name","data.csv"],package=None).exists()

@pytest.mark.network
def test_wecc_archive(tmp_path):
    """A file in the WECC archive is found and downloaded"""
    olddir = Cache.cachedir(str(tmp_path))
    try:
        cache = Cache(["AZ","Apache","W_2018.csv.gz"],package="weather",version=7)
        assert cache.exists()
        assert cache.archive.endswith("/wecc/weather/AZ/Apache/W_2018.csv.gz")
        assert cache.download()
        assert os.path.exists(os.path.join(str(tmp_path),"weather","7","AZ","Apache","W_2018.csv.gz"))
        with open(cache.pathname,"rb") as fh:
            assert fh.read(2) == b"\x1f\x8b" # gzip magic number
        assert not Cache(["AZ","Apache","nonexistent.csv"],package="weather").exists()
    finally:
        Cache.cachedir(olddir)
