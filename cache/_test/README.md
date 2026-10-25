# Tests

Run from the repository root:

    pip install -e . pytest
    pytest

| File | Checks | Network |
| ---- | ------ | ------- |
| `test_archive.py` | `ARCHIVES` lookup in `Cache.exists()`, `Cache.open()`, and `Cache.download()` against a temporary local `file://` archive; one test (`network` marker) downloads one small file from the WECC archive | one test |

Skip networked tests with `pytest -m "not network"`. All tests use a
temporary cache folder and never write to the package's `.cache` folder.
