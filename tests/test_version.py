"""Empeche la version de l'UI et celle du paquet de diverger a nouveau.

Les deux avaient deja derive (1.0.2 dans l'UI contre 1.0.3 dans pyproject.toml) :
la valeur affichee a l'utilisateur ne correspondait plus a celle du projet.
"""

import re
import tomllib
from pathlib import Path

from apps.version import __version__

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_identique_a_pyproject():
    declaree = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert declaree == __version__, (
        f"pyproject.toml annonce {declaree} alors que apps/version.py porte "
        f"{__version__}. Mettre les deux a jour ensemble."
    )


def test_version_respecte_le_format_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), (
        f"Version '{__version__}' attendue au format MAJEUR.MINEUR.CORRECTIF."
    )
