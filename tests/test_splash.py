"""Verifie l'ecran de demarrage Qt.

Ce qui est verrouille ici ne se voit qu'au lancement de l'application, et pas du
tout depuis les tests fonctionnels :

- l'image de demarrage absente du livrable, qui donnerait un ecran vide ;
- le retour de l'import de apps.worker au niveau module, qui ferait apparaitre
  l'ecran une fois le chargement termine -- donc pour rien ;
- la reapparition du splash PyInstaller, qui s'afficherait en double avec celui-ci.
"""

import ast
import importlib
import re
from pathlib import Path

import pytest

from apps import splash as splash_module
from apps.splash import FALLBACK_SIZE, SPLASH_IMAGES, Splash, splash_pixmap

RACINE = Path(__file__).resolve().parent.parent
POINT_ENTREE = RACINE / "4imask_anonymizer.py"


# --- Image ------------------------------------------------------------------

@pytest.mark.parametrize("ratio, chemin", SPLASH_IMAGES)
def test_les_images_de_demarrage_sont_livrees(ratio, chemin):
    assert (RACINE / chemin).is_file()


def test_ecran_normal(application):
    pixmap = splash_pixmap(ratio=1.0)
    assert not pixmap.isNull()
    assert pixmap.devicePixelRatio() == 1.0


def test_ecran_haute_densite(application):
    """Sur un ecran dense, l'image 1.5x evite un demarrage flou."""
    pixmap = splash_pixmap(ratio=2.0)
    assert pixmap.devicePixelRatio() == 1.5
    assert pixmap.width() > splash_pixmap(ratio=1.0).width()


def test_repli_si_aucune_image(application, monkeypatch):
    """Un livrable incomplet doit donner un ecran sobre, pas une fenetre vide."""
    monkeypatch.setattr(splash_module, "resource_path", lambda chemin: "/introuvable")
    pixmap = splash_pixmap(ratio=1.0)
    assert not pixmap.isNull()
    assert pixmap.size().toTuple() == FALLBACK_SIZE


# --- Message ----------------------------------------------------------------

def test_le_message_est_affiche(application):
    ecran = Splash(ratio=1.0)
    ecran.show_message("Chargement…")
    assert ecran.message() == "Chargement…"
    ecran.close()


def test_le_message_est_dessine_sur_l_image(application):
    """Un message qui ne serait pas peint laisserait l'ecran identique a l'image."""
    ecran = Splash(ratio=1.0)
    ecran.show()
    vide = ecran.grab().toImage()
    ecran.show_message("Chargement des modèles de détection…")
    assert ecran.grab().toImage() != vide
    ecran.close()


# --- Ordonnancement du demarrage --------------------------------------------

def imports_de_niveau_module():
    arbre = ast.parse(POINT_ENTREE.read_text(encoding="utf-8"))
    noms = set()
    for noeud in arbre.body:
        if isinstance(noeud, ast.Import):
            noms.update(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.module:
            noms.add(noeud.module)
    return noms


def test_le_moteur_reste_charge_a_la_demande():
    """Importe au niveau module, il s'ouvrirait avant que l'ecran soit affiche."""
    assert "apps.worker" not in imports_de_niveau_module()


def commande_pyinstaller_courante():
    """Derniere ligne active de pyinstaller_cmd.txt : les precedentes sont l'historique."""
    lignes = (RACINE / "pyinstaller_cmd.txt").read_text(encoding="utf-8").splitlines()
    actives = [ligne for ligne in lignes
               if ligne.strip() and not ligne.strip().startswith("#")]
    return actives[-1]


# L'option porte toujours une image : la reconnaitre ainsi evite de confondre une
# commande active avec un commentaire qui explique pourquoi elle a ete retiree.
OPTION_SPLASH = re.compile(r"--splash[=\s]+[\"']?[\w./\\-]+\.(?:png|jpg|jpeg|bmp)")


def test_le_splash_pyinstaller_a_bien_ete_retire():
    """Les deux ecrans s'afficheraient l'un sur l'autre s'ils coexistaient."""
    assert "pyi_splash" not in POINT_ENTREE.read_text(encoding="utf-8")
    assert not OPTION_SPLASH.search(commande_pyinstaller_courante())
    # Le workflow construit le binaire, le README documente la construction locale :
    # les deux doivent suivre, sinon les builds divergent.
    for fichier in (".github/workflows/pyinstaller.yml", "README.md"):
        contenu = (RACINE / fichier).read_text(encoding="utf-8")
        assert not OPTION_SPLASH.search(contenu), f"--splash encore actif dans {fichier}"


def test_l_image_de_demarrage_reste_embarquee():
    """Sans --add-data res, l'executable afficherait l'ecran de repli uni."""
    assert '--add-data "res:res"' in commande_pyinstaller_courante()


def test_l_ecran_se_ferme_avant_un_dialogue(application):
    """Un avertissement au demarrage doit rester lisible, pas passer sous l'ecran."""
    ecran = Splash(ratio=1.0)
    ecran.show()
    assert ecran.isVisible()
    Splash.close_all()
    assert not ecran.isVisible()


def test_l_ecran_ne_force_pas_le_premier_plan():
    """Force au-dessus, il masquerait les dialogues ouverts pendant le demarrage."""
    source = (RACINE / "apps/splash.py").read_text(encoding="utf-8")
    actives = [ligne for ligne in source.splitlines()
               if "WindowStaysOnTopHint" in ligne and not ligne.strip().startswith("#")]
    assert not actives


def test_le_moteur_est_charge_une_seule_fois():
    module = importlib.import_module("4imask_anonymizer")
    premier = module.load_processing()
    assert premier is module.load_processing()
    assert premier.__name__ == "AnonymizationWorker"
