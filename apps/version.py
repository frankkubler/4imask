"""Version et mentions legales de l'application.

`pyproject.toml` est la source unique : la version n'est ecrite nulle part
ailleurs dans le code. Le fichier est lu au demarrage, aussi bien depuis les
sources qu'depuis un bundle PyInstaller, ou il est embarque par l'option
--add-data "pyproject.toml:." (voir pyinstaller_cmd.txt).

importlib.metadata ne convient pas ici : le projet n'est pas installe comme
paquet et PyInstaller n'embarque pas les metadonnees de distribution.
"""

import sys
import tomllib
from datetime import date
from pathlib import Path

# Annee de premiere publication, figee : seule la fin de la plage evolue.
FIRST_RELEASE_YEAR = 2025

VERSION_UNKNOWN = "inconnue"


def _pyproject_path() -> Path:
    """Chemin de pyproject.toml, dans le bundle comme depuis les sources."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "pyproject.toml"
    # Depuis les sources : remonter depuis ce fichier plutot que depuis le
    # repertoire courant, pour rester correct quel que soit le dossier de lancement.
    return Path(__file__).resolve().parent.parent / "pyproject.toml"


def get_version() -> str:
    """Version declaree dans pyproject.toml.

    Ne leve pas : une version illisible ne doit pas empecher l'application de
    demarrer, elle s'affiche alors comme inconnue.
    """
    try:
        with _pyproject_path().open("rb") as handle:
            return tomllib.load(handle)["project"]["version"]
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return VERSION_UNKNOWN


def get_copyright_years(today: date = None) -> str:
    """Plage d'annees du copyright, de la premiere publication a aujourd'hui."""
    current = (today or date.today()).year
    if current <= FIRST_RELEASE_YEAR:
        return str(FIRST_RELEASE_YEAR)
    return f"{FIRST_RELEASE_YEAR}-{current}"
