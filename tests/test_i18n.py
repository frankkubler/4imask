"""Verifie les traductions de l'interface et la bascule de langue.

Ces defauts ne produisent aucune erreur a l'execution et ne se voient qu'en
basculant le drapeau, ecran par ecran :

- une cle presente dans une langue et absente dans l'autre, qui laisse un libelle
  anglais au milieu d'une interface francaise ;
- un champ de formatage renomme dans une seule langue, qui affiche le gabarit brut
  ({error}) au lieu du message ;
- un libelle en dur oublie dans le code, qui ne change jamais de langue.
"""

import importlib
import re
from pathlib import Path

import pytest
from PySide6.QtGui import QPixmap

from apps import i18n

RACINE = Path(__file__).resolve().parent.parent
CODES = [code for code, _ in i18n.LANGUAGES]
CHAMPS = re.compile(r"\{(\w+)")


# --- Parite des tables ------------------------------------------------------

@pytest.mark.parametrize("code", CODES)
def test_toutes_les_langues_ont_les_memes_cles(code):
    reference = set(i18n.TRANSLATIONS[i18n.FALLBACK_LANGUAGE])
    assert set(i18n.TRANSLATIONS[code]) == reference, f"Cles divergentes en {code}"


@pytest.mark.parametrize("code", CODES)
def test_aucune_chaine_vide(code):
    vides = [cle for cle, valeur in i18n.TRANSLATIONS[code].items() if not valeur.strip()]
    assert not vides, f"Traductions vides en {code} : {vides}"


@pytest.mark.parametrize("code", CODES)
def test_memes_champs_de_formatage_dans_toutes_les_langues(code):
    """Un champ renomme d'un cote afficherait le gabarit brut a l'utilisateur."""
    reference = i18n.TRANSLATIONS[i18n.FALLBACK_LANGUAGE]
    for cle, gabarit in i18n.TRANSLATIONS[code].items():
        assert set(CHAMPS.findall(gabarit)) == set(CHAMPS.findall(reference[cle])), \
            f"Champs differents pour {cle!r} en {code}"


@pytest.mark.parametrize("code", CODES)
def test_chaque_langue_a_son_invitation_a_basculer(code):
    assert i18n.SWITCH_HINT[code].strip()


# --- Restitution des chaines ------------------------------------------------

def test_formatage_des_champs():
    assert "boum" in i18n.tr("failed", language="fr", error="boum")


def test_repli_sur_l_anglais_si_une_cle_manque(monkeypatch):
    monkeypatch.setitem(i18n.TRANSLATIONS, "fr", {})
    attendu = i18n.TRANSLATIONS[i18n.FALLBACK_LANGUAGE]["stop"]
    assert i18n.tr("stop", language="fr") == attendu


def test_gabarit_incompatible_ne_leve_pas(monkeypatch):
    """Une traduction fautive degrade l'affichage, elle n'interrompt pas l'interface."""
    monkeypatch.setitem(i18n.TRANSLATIONS["fr"], "failed", "Echec : {raison}")
    assert i18n.tr("failed", language="fr", error="boum") == "Echec : {raison}"


# --- Choix de la langue -----------------------------------------------------

def test_langue_systeme_toujours_geree():
    assert i18n.system_language() in dict(i18n.LANGUAGES)


def test_langue_stockee_prioritaire_sur_la_locale(reglages):
    i18n.set_language("fr")
    assert i18n.current_language() == "fr"


def test_langue_stockee_invalide_ignoree(reglages):
    i18n.settings().setValue(i18n.SETTINGS_LANG_KEY, "de")
    assert i18n.current_language() == i18n.system_language()


def test_langue_non_geree_refusee(reglages):
    with pytest.raises(ValueError):
        i18n.set_language("de")


def test_ancien_reglage_de_langue_repris(reglages):
    """La langue choisie du temps ou elle ne pilotait que la notice reste honoree."""
    i18n.settings().setValue(i18n.LEGACY_SETTINGS_LANG_KEY, "fr")
    assert i18n.current_language() == "fr"


def test_reglage_courant_prioritaire_sur_l_ancien(reglages):
    i18n.settings().setValue(i18n.LEGACY_SETTINGS_LANG_KEY, "fr")
    i18n.settings().setValue(i18n.SETTINGS_LANG_KEY, "en")
    assert i18n.current_language() == "en"


# --- Bascule ----------------------------------------------------------------

def test_bascule_alterne_entre_les_deux_langues(reglages):
    i18n.set_language("fr")
    assert i18n.toggle_language() == "en"
    assert i18n.toggle_language() == "fr"


def test_bascule_notifiee_a_l_interface(reglages):
    # Ecriture directe : le point de depart doit etre le meme quelle que soit la
    # locale du poste qui execute les tests, et sans emettre de signal.
    i18n.settings().setValue(i18n.SETTINGS_LANG_KEY, "fr")
    recues = []
    i18n.notifier.language_changed.connect(recues.append)
    try:
        i18n.set_language("en")
        i18n.set_language("fr")
    finally:
        i18n.notifier.language_changed.disconnect(recues.append)
    assert recues == ["en", "fr"]


def test_langue_inchangee_ne_notifie_pas(reglages):
    """Sans ce garde-fou, chaque ouverture de fenetre retraduirait toute l'interface."""
    i18n.set_language("fr")
    recues = []
    i18n.notifier.language_changed.connect(recues.append)
    try:
        i18n.set_language("fr")
    finally:
        i18n.notifier.language_changed.disconnect(recues.append)
    assert recues == []


def test_invitation_redigee_dans_la_langue_cible(reglages):
    i18n.set_language("fr")
    assert i18n.switch_hint() == i18n.SWITCH_HINT["en"]


def test_cle_inconnue_ne_fait_pas_planter():
    """Une faute de frappe doit se voir a l'ecran, pas interrompre l'interface."""
    assert i18n.tr("cle_qui_n_existe_pas") == "cle_qui_n_existe_pas"


# --- Cohérence entre le code et les tables ----------------------------------

SOURCES = [RACINE / "4imask_anonymizer.py"] + sorted((RACINE / "apps").glob("*.py"))


def cles_utilisees():
    cles = set()
    for source in SOURCES:
        texte = source.read_text(encoding="utf-8")
        cles.update(re.findall(r"\btr\(\s*[\"'](\w+)[\"']", texte))
    return cles


def test_toutes_les_cles_appelees_existent():
    """Une cle mal orthographiee afficherait son propre nom a l'utilisateur."""
    inconnues = cles_utilisees() - set(i18n.TRANSLATIONS[i18n.FALLBACK_LANGUAGE])
    assert not inconnues, f"Cles appelees mais absentes des traductions : {inconnues}"


def test_aucune_traduction_morte():
    """Une cle qui n'est plus appelee alourdit la relecture des traductions."""
    declarees = set(i18n.TRANSLATIONS[i18n.FALLBACK_LANGUAGE])
    assert not declarees - cles_utilisees()


# --- Absence de libelles en dur ---------------------------------------------

def test_aucun_libelle_en_dur_dans_la_fenetre_principale():
    """Un setText("...") litteral echapperait a la bascule de langue."""
    source = (RACINE / "4imask_anonymizer.py").read_text(encoding="utf-8")
    litteraux = re.findall(r"set(?:Text|ToolTip|WindowTitle)\(\s*[\"']([^\"']+)[\"']",
                           source)
    # Seule exception admise : la remise a blanc du bandeau de notification.
    assert [texte for texte in litteraux if texte] == []


def test_aucun_message_en_dur_dans_les_boites_de_dialogue():
    """Titres et corps des QMessageBox passent tous par tr()."""
    source = (RACINE / "4imask_anonymizer.py").read_text(encoding="utf-8")
    for ligne in source.splitlines():
        if "QMessageBox." not in ligne:
            continue
        reste = re.sub(r"tr\([^)]*\)", "", ligne)
        assert not re.search(r"[\"'][^\"']+[\"']", reste), f"Texte en dur : {ligne.strip()}"


# --- Retraduction de la fenetre principale ----------------------------------

@pytest.fixture
def fenetre(application, reglages, monkeypatch):
    """Fenetre principale isolee : ni controle de domaine, ni notice au demarrage."""
    module = importlib.import_module("4imask_anonymizer")
    monkeypatch.setattr(module.VideoAnonymizer, "check_authorization", lambda self: True)
    i18n.settings().setValue(i18n.SETTINGS_LANG_KEY, "fr")
    fenetre = module.VideoAnonymizer()
    yield fenetre
    fenetre.close()


def test_la_bascule_retraduit_la_fenetre(fenetre):
    assert fenetre.start_button.text() == i18n.TRANSLATIONS["fr"]["start"]
    i18n.set_language("en")
    assert fenetre.start_button.text() == i18n.TRANSLATIONS["en"]["start"]


def test_la_bascule_preserve_l_image_de_l_apercu(fenetre):
    """setText sur ce label effacerait l'image en cours de lecture."""
    image = QPixmap(4, 4)
    image.fill()
    fenetre.original_label.setPixmap(image)
    i18n.set_language("en")
    assert not fenetre.original_label.pixmap().isNull()


def test_la_bascule_conserve_le_fichier_choisi(fenetre):
    fenetre.video_path = "/videos/reunion.mp4"
    i18n.set_language("en")
    assert fenetre.video_label.text() == "reunion.mp4"


def test_la_bascule_traduit_le_resultat_affiche(fenetre):
    fenetre._worker_error = "disque plein"
    fenetre.anonymization_complete()
    i18n.set_language("en")
    assert fenetre.notification_label.text() == \
        i18n.TRANSLATIONS["en"]["failed"].format(error="disque plein")
