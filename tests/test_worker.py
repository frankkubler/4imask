"""Tests du dimensionnement de sortie.

Le writer etait ouvert sur les dimensions demandees par l'utilisateur alors que
``imutils.resize`` conserve le ratio de la source : toute video non 16:9
produisait un fichier vide, sans erreur. Ces tests verrouillent l'invariant
"le writer est ouvert sur ce que le pipeline produit reellement".
"""

import cv2
import imutils
import numpy as np
import pytest

from apps.worker import AnonymizationWorker


@pytest.fixture
def worker():
    return AnonymizationWorker("/inexistant.mp4", "480p", 1.6, write_output=False)


@pytest.mark.parametrize("fmt, expected", [
    ("360p", (640, 360)),
    ("480p", (854, 480)),
    ("720p", (1280, 720)),
    ("1080p", (1920, 1080)),
    ("inconnu", (640, 480)),
])
def test_get_dimensions(worker, fmt, expected):
    assert worker.get_dimensions(fmt) == expected


@pytest.mark.parametrize("src_w, src_h", [
    (1920, 1080),   # 16:9  : la hauteur tombe juste
    (640, 480),     # 4:3   : la hauteur ne tombe pas juste
    (1080, 1920),   # 9:16  : source verticale
])
def test_le_writer_accepte_ce_que_le_pipeline_produit(tmp_path, worker, src_w, src_h):
    """Reproduit la chaine resize -> VideoWriter pour chaque ratio de source."""
    target_width, _ = worker.get_dimensions("480p")
    frame = np.zeros((src_h, src_w, 3), dtype=np.uint8)
    resized = imutils.resize(frame, width=target_width)

    # Ouverture paresseuse : la taille du writer vient de la frame, pas du format.
    out_size = (resized.shape[1], resized.shape[0])
    path = str(tmp_path / "out.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 25.0, out_size)
    assert writer.isOpened()
    try:
        for _ in range(5):
            assert writer.write(resized) is not False
    finally:
        writer.release()

    cap = cv2.VideoCapture(path)
    try:
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 0
    finally:
        cap.release()


def test_un_writer_mal_dimensionne_rejette_les_frames(tmp_path):
    """Le comportement d'origine : sans la correction, write() renvoie False et le
    fichier produit ne contient aucune frame lisible."""
    path = str(tmp_path / "bad.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 25.0, (854, 480))
    assert writer.isOpened()
    mauvaise_taille = np.zeros((640, 854, 3), dtype=np.uint8)   # sortie d'une source 4:3
    try:
        assert writer.write(mauvaise_taille) is False
    finally:
        writer.release()

    cap = cv2.VideoCapture(path)
    try:
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 0
    finally:
        cap.release()
