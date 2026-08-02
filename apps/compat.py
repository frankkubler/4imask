"""Compatibility shims that must be applied before any other import.

PySide6 (shiboken) installs an import hook that inspects the source of every
module imported after Qt, to detect ``from __feature__ import``. On the fake
modules exposed by ``six.moves`` this ends up in ``repr(module)``, which
CPython 3.12 builds from ``spec.loader._path`` -- an attribute
``six._SixMetaPathImporter`` does not have. The resulting AttributeError breaks
any import of matplotlib (and therefore ultralytics) made after PySide6.
"""

import logging

logger = logging.getLogger(__name__)


def patch_six_meta_path_importer():
    """Give six's meta path importer the ``_path`` attribute CPython expects."""
    try:
        from six import _SixMetaPathImporter
    except ImportError:
        return
    if not hasattr(_SixMetaPathImporter, "_path"):
        _SixMetaPathImporter._path = ()
        logger.debug("Patched six._SixMetaPathImporter._path for PySide6")


patch_six_meta_path_importer()
