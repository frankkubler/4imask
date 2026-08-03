"""Tests de la primitive de masquage et du regroupement des boites.

``draw_detections`` est le point de passage oblige des trois detecteurs
(YOLO, CenterFace, YuNet) : ce qui est verifie ici couvre la totalite de la
logique d'anonymisation, sans dependance a Qt ni a un modele.

La fusion, elle, n'intervient que lorsque la detection de pose est combinee a un
detecteur de visage : deux boites mal regroupees donnent deux masques sur la meme
tete, ce qui se voit immediatement a l'ecran mais ne fait echouer aucun traitement.
"""

import ast
from pathlib import Path

import numpy as np
import pytest

from apps.utils import (
    ALREADY_SCALED, draw_detections, mask_boxes, merge_boxes, merge_scaled_boxes,
    scale_bb)

RACINE = Path(__file__).resolve().parent.parent


def blank_frame(value=255, size=100):
    return np.full((size, size, 3), value, dtype=np.uint8)


def test_solid_couvre_la_boite():
    out = draw_detections(blank_frame(), 20, 20, 60, 60,
                          replacewith='solid', mask_size=1.0)
    assert out[40, 40].tolist() == [0, 0, 0]


def test_solid_ne_deborde_pas_sur_le_reste_de_la_frame():
    out = draw_detections(blank_frame(), 20, 20, 60, 60,
                          replacewith='solid', mask_size=1.0)
    assert out[5, 5].tolist() == [255, 255, 255]


@pytest.mark.parametrize("replacewith", ['solid', 'blur', 'mosaic'])
def test_boite_degeneree_ne_leve_pas(replacewith):
    """Une boite de 1 px faisait echouer cv2.blur sur un ksize nul, ce qui tuait
    le thread de traitement en plein milieu d'une video."""
    draw_detections(blank_frame(), 50, 50, 51, 51,
                    replacewith=replacewith, mask_size=1.0)


@pytest.mark.parametrize("replacewith", ['solid', 'blur', 'mosaic'])
def test_boite_hors_cadre_est_clippee(replacewith):
    draw_detections(blank_frame(), -30, -30, 130, 130,
                    replacewith=replacewith, mask_size=2.0)


def test_boite_entierement_hors_cadre_laisse_la_frame_intacte():
    frame = blank_frame()
    out = draw_detections(frame, 200, 200, 260, 260,
                          replacewith='solid', mask_size=1.0)
    assert np.array_equal(out, blank_frame())


def test_blur_modifie_la_zone_ciblee():
    # Moitie gauche noire, moitie droite blanche : le flou doit faire apparaitre
    # des valeurs intermediaires a la frontiere.
    frame = blank_frame()
    frame[:, :50] = 0
    out = draw_detections(frame, 30, 30, 70, 70,
                          replacewith='blur', mask_size=1.0, ellipse=False)
    zone = out[30:70, 30:70]
    assert np.any((zone > 0) & (zone < 255))


def test_mask_size_agrandit_la_zone_masquee():
    petite = draw_detections(blank_frame(), 40, 40, 60, 60,
                             replacewith='solid', mask_size=1.0)
    grande = draw_detections(blank_frame(), 40, 40, 60, 60,
                             replacewith='solid', mask_size=2.0)
    assert (grande == 0).sum() > (petite == 0).sum()


def test_scale_bb_est_symetrique():
    x0, y0, x1, y1 = scale_bb(40, 40, 60, 60, mask_scale=2.0)
    assert (x0, y0, x1, y1) == (20, 20, 80, 80)


def test_scale_bb_neutre_a_1():
    assert scale_bb(10, 20, 30, 40, mask_scale=1.0).tolist() == [10, 20, 30, 40]


# --- Regroupement des boites de plusieurs detecteurs ------------------------

def test_les_boites_qui_se_recouvrent_donnent_une_englobante():
    # 36 % de la plus petite, au-dessus du seuil de 30 %.
    assert merge_boxes([(0, 0, 50, 50), (20, 20, 70, 70)]) == [(0, 0, 70, 70)]


def test_un_recouvrement_sous_le_seuil_ne_fusionne_pas():
    """25 % de la plus petite : deux tetes proches restent deux masques."""
    boites = [(0, 0, 50, 50), (25, 25, 75, 75)]
    assert sorted(merge_boxes(boites)) == sorted(boites)


def test_les_boites_distinctes_restent_separees():
    """Deux personnes cote a cote doivent garder chacune leur masque."""
    boites = [(0, 0, 40, 40), (200, 0, 240, 40)]
    assert sorted(merge_boxes(boites)) == sorted(boites)


def test_une_boite_incluse_est_absorbee():
    """Un IoU classique separerait a tort un visage serre d'une tete plus large."""
    assert merge_boxes([(10, 10, 20, 20), (0, 0, 100, 100)]) == [(0, 0, 100, 100)]


def test_le_regroupement_est_transitif():
    """Deux boites disjointes se rejoignent si une troisieme couvre les deux."""
    assert merge_boxes([(0, 0, 10, 10), (20, 0, 30, 10), (5, 0, 25, 10)]) \
        == [(0, 0, 30, 10)]


# --- Fusion au gabarit du masque --------------------------------------------

# Visage detecte et tete deduite de la posture pour une meme personne, decales
# comme ils le sont sur une tete penchee ou de trois-quarts : 12 % de
# recouvrement brut, 75 % une fois le gabarit applique.
VISAGE, TETE = (500, 300, 540, 352), (505, 345, 585, 425)


def test_deux_masques_qui_se_superposeront_sont_fusionnes():
    """Le defaut visible corrige ici : deux ellipses dessinees sur une seule tete."""
    assert len(merge_boxes([VISAGE, TETE])) == 2
    assert len(merge_scaled_boxes([VISAGE, TETE], mask_size=1.6)) == 1


def test_des_personnes_distinctes_ne_sont_pas_regroupees_par_le_gabarit():
    """Le gabarit elargit les boites : il ne doit pas coller deux personnes."""
    boites = [(0, 0, 40, 40), (400, 0, 440, 40)]
    assert len(merge_scaled_boxes(boites, mask_size=1.6)) == 2


def test_les_boites_renvoyees_sont_deja_au_gabarit():
    """Elles sont masquees sans nouvel agrandissement : leur taille est la finale."""
    (x0, y0, x1, y1), = merge_scaled_boxes([VISAGE], mask_size=1.6)
    assert [x0, y0, x1, y1] == scale_bb(*VISAGE, 1.6).tolist()


def test_sans_gabarit_le_comportement_est_celui_de_merge_boxes():
    boites = [VISAGE, TETE]
    assert merge_scaled_boxes(boites, mask_size=1.0) == merge_boxes(boites)


def test_la_zone_masquee_est_celle_de_la_boite_fusionnee():
    frame = np.full((600, 700, 3), 255, dtype=np.uint8)
    boites = merge_scaled_boxes([VISAGE, TETE], mask_size=1.6)
    out = mask_boxes(boites, frame, 'solid', ALREADY_SCALED, ellipse=False)
    (x0, y0, x1, y1) = boites[0]
    assert out[(y0 + y1) // 2, (x0 + x1) // 2].tolist() == [0, 0, 0]
    # Un pixel juste au-dela du bord doit rester intact : sans ALREADY_SCALED,
    # le gabarit serait applique une seconde fois et deborderait largement.
    assert out[(y0 + y1) // 2, min(x1 + 5, 699)].tolist() == [255, 255, 255]


def test_le_worker_ne_reapplique_pas_le_gabarit():
    """Un self.mask_size rendu a mask_boxes agrandirait les masques deux fois."""
    arbre = ast.parse((RACINE / "apps/worker.py").read_text(encoding="utf-8"))
    appels = [n for n in ast.walk(arbre)
              if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "mask_boxes"]
    assert appels, "L'appel a mask_boxes a disparu du worker"
    for appel in appels:
        facteurs = [a for a in appel.args if isinstance(a, ast.Attribute)]
        assert not [a for a in facteurs if a.attr == "mask_size"]
