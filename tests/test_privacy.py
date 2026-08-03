"""Verifie l'information RGPD affichee a l'utilisateur.

Deux classes d'erreur sont visees, qu'aucun autre test ne rattrape et qui ne
produisent aucun message a l'execution :

- une traduction oubliee, qui n'apparait qu'en changeant de langue dans l'interface ;
- un document embarque manquant, qui ne se voit que dans l'executable distribue,
  ou le bouton "document complet" ouvre alors le vide.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from apps import privacy

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture
def reglages(tmp_path, monkeypatch):
    """Isole les preferences du test : ne pas ecrire dans celles de l'utilisateur."""
    fichier = tmp_path / "settings.ini"
    monkeypatch.setattr(
        privacy, "_settings", lambda: QSettings(str(fichier), QSettings.IniFormat))


# --- Parite des traductions -------------------------------------------------

def test_toutes_les_langues_ont_les_memes_cles():
    reference = set(privacy.UI_TEXT[privacy.FALLBACK_LANGUAGE])
    for code, _ in privacy.LANGUAGES:
        assert set(privacy.UI_TEXT[code]) == reference, f"Cles manquantes en {code}"


@pytest.mark.parametrize("code", [code for code, _ in privacy.LANGUAGES])
def test_chaque_langue_fournit_bandeau_et_notice(code):
    assert privacy.SHORT_NOTICE[code].strip()
    assert privacy.FULL_NOTICE_HTML[code].strip()


@pytest.mark.parametrize("code", [code for code, _ in privacy.LANGUAGES])
def test_le_bandeau_annonce_le_perimetre_du_masquage(code):
    """Le point le plus lourd de consequences doit rester visible sans ouvrir la notice."""
    bandeau = privacy.SHORT_NOTICE[code].lower()
    assert "pose" in bandeau
    assert "badge" in bandeau


def test_repli_sur_l_anglais_si_une_cle_manque(monkeypatch):
    monkeypatch.setitem(privacy.UI_TEXT, "fr", {})
    assert privacy.text("close", "fr") == privacy.UI_TEXT[privacy.FALLBACK_LANGUAGE]["close"]


# --- Choix de la langue -----------------------------------------------------

def test_langue_systeme_toujours_geree():
    assert privacy.system_language() in dict(privacy.LANGUAGES)


def test_langue_stockee_prioritaire_sur_la_locale(reglages):
    privacy.set_language("fr")
    assert privacy.current_language() == "fr"


def test_langue_stockee_invalide_ignoree(reglages):
    privacy._settings().setValue(privacy.SETTINGS_LANG_KEY, "de")
    assert privacy.current_language() == privacy.system_language()


def test_langue_non_geree_refusee(reglages):
    with pytest.raises(ValueError):
        privacy.set_language("de")


# --- Acquittement de la notice ----------------------------------------------

def test_notice_affichee_au_premier_lancement(reglages):
    assert privacy.should_show_notice()


def test_notice_masquee_apres_acquittement(reglages):
    privacy.acknowledge_notice()
    assert not privacy.should_show_notice()


def test_notice_reaffichee_apres_evolution_du_texte(reglages):
    privacy._settings().setValue(privacy.SETTINGS_ACK_KEY, privacy.NOTICE_VERSION - 1)
    assert privacy.should_show_notice()


def test_acquittement_illisible_ne_fait_pas_planter(reglages):
    """Une preference corrompue reaffiche la notice plutot que d'interrompre l'app."""
    privacy._settings().setValue(privacy.SETTINGS_ACK_KEY, "n/a")
    assert privacy.should_show_notice()


# --- Documents complets -----------------------------------------------------

@pytest.mark.parametrize("code, fichier", privacy.DOCUMENT_FILENAMES.items())
def test_document_present_pour_chaque_langue(code, fichier):
    assert (RACINE / "docs" / fichier).is_file()
    assert Path(privacy.privacy_document_path(code)).name == fichier


def test_repli_sur_l_autre_langue_si_le_document_manque(monkeypatch):
    """Un document non livre ne doit pas laisser l'utilisateur sans information."""
    monkeypatch.setattr(
        privacy.os.path, "isfile",
        lambda chemin: Path(chemin).name == privacy.DOCUMENT_FILENAMES["en"])
    assert Path(privacy.privacy_document_path("fr")).name == \
        privacy.DOCUMENT_FILENAMES["en"]


def test_documents_embarques_dans_le_bundle():
    """Sans --add-data docs, le bouton "document complet" est mort dans l'executable."""
    workflow = (RACINE / ".github/workflows/pyinstaller.yml").read_text(encoding="utf-8")
    assert '--add-data "docs:docs"' in workflow
    assert '--add-data "LICENSE:."' in workflow
