"""Cache manager CLI"""

import os
import sys
import argparse
import warnings

from cache import Cache

E_OK = 0
"""Exit code on success"""

E_FAILED = 1
"""Exit code on failure"""

E_SYNTAX = 2
"""Exit code on syntax error"""

def main(*args:list[str],**kwargs:dict[str,str]) -> int:
    """Cache manager main command line processor

    # Argument

    - `*args`: command line arguments (`None` is `sys.argv`)

    # Returns

    - `int`: return/exit code
    """
    try:

        # support direct call to main
        if args:
            sys.argv = [__file__] + list(args)
        if kwargs:
            sys.argv += [f"--{x}={y}" for x,y in kwargs.items()]

        # setup command line parser
        parser = argparse.ArgumentParser(
            prog="cache",
            description="Eudoxys cache manager CLI",
            epilog="See https://www.eudoxys.com/cache for documentation. ",
            )

        parser.add_argument("command",
            choices=["clear","size"]
            )
        parser.add_argument("--package",
            default="cache",
            help="package name")
        parser.add_argument("--version",
            default="0",
            help="version number")
        parser.add_argument("-C","--cachedir",
            default=Cache.CACHEDIR,
            help="cache working folder")
        parser.add_argument("-P","--path",
            default="",
            help="cache path to clear")
        parser.add_argument("-w","--warning",
            action="store_true",
            help="enable warning messages from python")
        parser.add_argument("-d","--debug",
            action="store_true",
            help="enable debug traceback on exceptions")

        # parse arguments
        args = parser.parse_args()

        # setup warning handling
        if not args.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )

        match args.command:

            case "clear":

                Cache.clear(args.package)
                return E_OK

            case "size":
                Cache.CACHEDIR = args.cachedir
                cache = Cache(
                    path=args.path.split("/"),
                    package=args.package,
                    version=args.version,
                    )
                size = os.path.getsize(cache.pathname)
                if size < 1000:
                    size = f"{size:.0f} B"
                elif size < 1e6:
                    size = f"{size/1000:.3f} kB"
                elif size < 1e9:
                    size = f"{size/1e6:.3f} MB"
                elif size < 1e12:
                    size = f"{size/1e9:.3f} GB"
                else:
                    size = f"{size/1e12:.3f} TB"
                print(cache.pathname.replace(Cache.CACHEDIR,"~"),size)

            case "viewer":

                return os.system(f"marimo run {os.path.join(os.path.dirname(__file__),'viewer.py')}")

            case "test":

                return os.system(f"python3 {os.path.join(os.path.dirname(__file__),'tests.py')}")

            case "_":

                raise RuntimeError(f"command={args.command} is invalid")

        return E_FAILED

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug"):
            raise

        print(f"ERROR [cache]: {err}")
        return E_FAILED

if __name__ == "__main__":
    main("size","-d")
