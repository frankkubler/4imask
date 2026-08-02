"""Tests du garde-fou d'usage.

Le controle bloquait tout demarrage hors Windows, ou USERDOMAIN n'existe pas :
ces tests verrouillent le comportement sur chaque plateforme et le cas ou
aucune liste n'est embarquee.
"""

import pytest

from apps.authorization import is_authorized, load_authorized_domains

DOMAINS = ["DOMAINE-A", "DOMAINE-B"]


@pytest.mark.parametrize("domain, attendu", [
    ("DOMAINE-A", True),
    ("DOMAINE-B", True),
    ("AUTRE", False),
    ("domaine-a", False),   # la comparaison est sensible a la casse
])
def test_domaine_compare_a_la_liste(domain, attendu):
    assert is_authorized(domain, DOMAINS) is attendu


@pytest.mark.parametrize("domain", [None, ""])
def test_domaine_indeterminable_est_autorise(domain):
    """Hors Windows, USERDOMAIN n'existe pas : l'absence de valeur ne doit pas
    empecher le demarrage sur les plateformes documentees par le README."""
    assert is_authorized(domain, DOMAINS) is True


@pytest.mark.parametrize("liste", [None, []])
def test_sans_liste_aucune_restriction(liste):
    assert is_authorized("N-IMPORTE-QUOI", liste) is True


def test_load_fichier_absent_retourne_none(tmp_path):
    assert load_authorized_domains(str(tmp_path / "absent")) is None


def test_load_fichier_vide_retourne_none(tmp_path):
    chemin = tmp_path / "vide"
    chemin.write_text("\n  \n\n", encoding="utf-8")
    assert load_authorized_domains(str(chemin)) is None


def test_load_ignore_lignes_vides_et_espaces(tmp_path):
    chemin = tmp_path / "domaines"
    chemin.write_text("DOMAINE-A\n\n  DOMAINE-B  \n\n", encoding="utf-8")
    assert load_authorized_domains(str(chemin)) == ["DOMAINE-A", "DOMAINE-B"]


def test_load_sur_un_repertoire_retourne_none(tmp_path):
    """Un chemin illisible ne doit pas faire planter le demarrage."""
    assert load_authorized_domains(str(tmp_path)) is None
