"""Verifie que la version affichee provient bien de pyproject.toml.

Elle y est declaree une seule fois. Le cas fragile est le bundle PyInstaller :
pyproject.toml n'y figure que si --add-data l'embarque, et l'oubli ne se voit
pas depuis les sources, seulement dans l'executable distribue.
"""

import re
import sys
import tomllib
from datetime import date
from pathlib import Path

import pytest

from apps.version import (FIRST_RELEASE_YEAR, VERSION_UNKNOWN, get_copyright_years,
                          get_version)

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def version_declaree():
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def test_version_lue_depuis_pyproject():
    assert get_version() == version_declaree()


def test_version_respecte_le_format_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", get_version())


def test_version_absente_du_code():
    """La version ne doit etre codee en dur nulle part dans les sources."""
    attendue = version_declaree()
    for source in [Path("4imask_anonymizer.py"), *Path("apps").glob("*.py")]:
        texte = (PYPROJECT.parent / source).read_text(encoding="utf-8")
        assert f'"{attendue}"' not in texte, f"Version codee en dur dans {source}"


def test_version_lue_depuis_un_bundle_pyinstaller(tmp_path, monkeypatch):
    """Simule sys._MEIPASS : le bundle doit lire le pyproject.toml embarque."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "4imask"\nversion = "9.9.9"\n', encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert get_version() == "9.9.9"


def test_version_inconnue_si_pyproject_absent_du_bundle(tmp_path, monkeypatch):
    """Un --add-data oublie degrade l'affichage mais ne fait pas planter l'app."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert get_version() == VERSION_UNKNOWN


@pytest.mark.parametrize("annee, attendu", [
    (2025, "2025"),
    (2026, "2025-2026"),
    (2030, "2025-2030"),
])
def test_plage_de_copyright(annee, attendu):
    assert get_copyright_years(date(annee, 6, 1)) == attendu


def test_copyright_suit_l_annee_courante():
    assert get_copyright_years().endswith(str(max(date.today().year, FIRST_RELEASE_YEAR)))
