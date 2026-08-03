"""Outillage commun aux tests d'interface.

Les widgets ont besoin d'une QApplication, mais aucun test n'ouvre de fenetre :
la plateforme Qt est forcee hors ecran pour que la suite tourne aussi bien en
local que sur une machine sans serveur d'affichage.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from apps import i18n  # noqa: E402


@pytest.fixture(scope="session")
def application():
    """QApplication unique pour toute la session : Qt n'en admet pas deux."""
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def reglages(tmp_path, monkeypatch):
    """Isole les preferences du test : ne pas ecrire dans celles de l'utilisateur.

    Les preferences sont vides au depart. Un test qui a besoin d'une langue
    initiale precise l'ecrit lui-meme, sans quoi le resultat dependrait de la
    locale du poste qui execute la suite.
    """
    fichier = tmp_path / "settings.ini"
    monkeypatch.setattr(
        i18n, "settings", lambda: QSettings(str(fichier), QSettings.IniFormat))
