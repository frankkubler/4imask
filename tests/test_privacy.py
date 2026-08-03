"""Verifie l'information RGPD affichee a l'utilisateur.

Deux classes d'erreur sont visees, qu'aucun autre test ne rattrape et qui ne
produisent aucun message a l'execution :

- une notice non traduite, qui n'apparait qu'en changeant de langue dans l'interface ;
- un document embarque manquant, qui ne se voit que dans l'executable distribue,
  ou le bouton "document complet" ouvre alors le vide.

Les libelles de la fenetre et le choix de la langue relevent de tests/test_i18n.py.
"""

from pathlib import Path

import pytest

from apps import i18n, privacy

RACINE = Path(__file__).resolve().parent.parent


# --- Parite des traductions -------------------------------------------------

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


@pytest.mark.parametrize("code", [code for code, _ in privacy.LANGUAGES])
def test_la_notice_cite_le_libelle_reel_de_l_option_de_pose(code):
    """Une notice qui nomme une option introuvable a l'ecran n'informe personne."""
    libelle = i18n.TRANSLATIONS[code]["pose_option"]
    assert libelle in privacy.SHORT_NOTICE[code]
    assert libelle in privacy.FULL_NOTICE_HTML[code]


# --- Acquittement de la notice ----------------------------------------------

def test_notice_affichee_au_premier_lancement(reglages):
    assert privacy.should_show_notice()


def test_notice_masquee_apres_acquittement(reglages):
    privacy.acknowledge_notice()
    assert not privacy.should_show_notice()


def test_notice_reaffichee_apres_evolution_du_texte(reglages):
    i18n.settings().setValue(privacy.SETTINGS_ACK_KEY, privacy.NOTICE_VERSION - 1)
    assert privacy.should_show_notice()


def test_acquittement_illisible_ne_fait_pas_planter(reglages):
    """Une preference corrompue reaffiche la notice plutot que d'interrompre l'app."""
    i18n.settings().setValue(privacy.SETTINGS_ACK_KEY, "n/a")
    assert privacy.should_show_notice()


def test_notice_suivie_dans_la_langue_courante(reglages):
    i18n.set_language("fr")
    assert privacy.short_notice() == privacy.SHORT_NOTICE["fr"]
    i18n.set_language("en")
    assert privacy.short_notice() == privacy.SHORT_NOTICE["en"]


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
