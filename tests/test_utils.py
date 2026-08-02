"""Tests de la primitive de masquage.

``draw_detections`` est le point de passage oblige des trois detecteurs
(YOLO, CenterFace, YuNet) : ce qui est verifie ici couvre la totalite de la
logique d'anonymisation, sans dependance a Qt ni a un modele.
"""

import numpy as np
import pytest

from apps.utils import draw_detections, scale_bb


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
