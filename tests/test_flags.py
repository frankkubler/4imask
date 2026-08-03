"""Verifie le bouton drapeau qui bascule la langue de l'interface.

Ce que ces tests attrapent, et qu'aucun autre ne verrait : un drapeau qui ne suit
pas la langue apres un clic, et deux boutons ouverts en meme temps -- fenetre
principale et notice RGPD -- qui afficheraient des langues differentes.

Les widgets sont construits hors ecran : aucune fenetre ne s'ouvre pendant les tests.
"""

import pytest

from apps import i18n
from apps.flags import LanguageFlagButton, flag_pixmap


@pytest.fixture
def depart_fr(reglages):
    """Langue initiale connue : les tests de bascule attendent fr puis en."""
    i18n.settings().setValue(i18n.SETTINGS_LANG_KEY, "fr")


# --- Dessin des drapeaux ----------------------------------------------------

@pytest.mark.parametrize("code", [code for code, _ in i18n.LANGUAGES])
def test_chaque_langue_a_son_drapeau(application, code):
    pixmap = flag_pixmap(code, height=16)
    assert not pixmap.isNull()
    assert pixmap.width() > pixmap.height()


def test_les_deux_drapeaux_different(application):
    """Un dessin identique laisserait l'utilisateur sans indication de langue."""
    assert flag_pixmap("fr", 32).toImage() != flag_pixmap("en", 32).toImage()


def test_langue_sans_drapeau_refusee(application):
    with pytest.raises(ValueError):
        flag_pixmap("de")


# --- Bascule ----------------------------------------------------------------

def test_le_clic_bascule_la_langue(application, depart_fr):
    bouton = LanguageFlagButton()
    bouton.click()
    assert i18n.current_language() == "en"
    bouton.click()
    assert i18n.current_language() == "fr"


def test_le_drapeau_suit_la_langue(application, depart_fr):
    bouton = LanguageFlagButton()
    avant = bouton.icon().pixmap(32).toImage()
    bouton.click()
    assert bouton.icon().pixmap(32).toImage() != avant


def test_l_infobulle_annonce_la_langue_cible(application, depart_fr):
    bouton = LanguageFlagButton()
    assert bouton.toolTip() == i18n.SWITCH_HINT["en"]
    bouton.click()
    assert bouton.toolTip() == i18n.SWITCH_HINT["fr"]


def test_deux_boutons_restent_synchronises(application, depart_fr):
    """La notice RGPD porte son propre drapeau : il doit suivre celui de la fenetre."""
    fenetre = LanguageFlagButton()
    notice = LanguageFlagButton()
    notice.click()
    assert fenetre.toolTip() == notice.toolTip()
    assert fenetre.icon().pixmap(32).toImage() == notice.icon().pixmap(32).toImage()
