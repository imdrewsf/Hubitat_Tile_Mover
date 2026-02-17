import os
import sys

# When running a package directory as a script (e.g. `python hubitat_tile_mover ...`),
# the package directory can become sys.path[0] and shadow stdlib modules.
# Remove it and prepend the parent directory.
pkg_dir = os.path.dirname(__file__)
if sys.path and os.path.abspath(sys.path[0]) == os.path.abspath(pkg_dir):
    sys.path.pop(0)
parent = os.path.dirname(pkg_dir)
if parent and (not sys.path or os.path.abspath(sys.path[0]) != os.path.abspath(parent)):
    sys.path.insert(0, parent)

from .main import main

if __name__ == '__main__':
    raise SystemExit(main())
