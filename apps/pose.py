from typing import List

import numpy as np
from ultralytics import YOLO
from torch.cuda import (is_available as cuda_is_available,
                        device_count as cuda_device_count)

from apps.utils import resource_path, openvino_device
import logging

# Indices des keypoints COCO utilises pour situer la tete.
HEAD_KEYPOINTS = (0, 1, 2, 3, 4)  # nez, oeil G, oeil D, oreille G, oreille D
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6

# En dessous de ce score, un keypoint est considere comme devine plutot que vu.
# C'est le cas de tous les keypoints du visage quand la personne est de dos.
KEYPOINT_CONF = 0.5


class PoseModel:
    """Detecte les tetes sous n'importe quel angle, y compris de dos.

    Les detecteurs de visage (YOLO face, CenterFace, YuNet) ne voient rien quand
    la personne tourne le dos : il n'y a pas de visage dans l'image. Ce modele
    detecte des personnes et leurs keypoints, puis en deduit la position de la
    tete, ce qui reste possible de dos.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        if cuda_is_available() and cuda_device_count() > 0:
            self.device = "cuda"
            self.model_path = resource_path("res/models/yolo11n-pose.pt")
            self.logger.info("Using CUDA for pose model")
        else:
            self.device = openvino_device()
            self.model_path = resource_path("res/models/yolo11n-pose_openvino_model/")
            self.logger.info(f"Using openvino for pose model on {self.device or 'auto'}")

        self._model = YOLO(self.model_path, task="pose", verbose=False)

    def detect_heads(self, image_path, conf: float, iou: float,
                     max_width: int = None, max_height: int = None) -> List[tuple[int, ...]] | None:
        results = self._model.predict(image_path, conf=conf, iou=iou,
                                      verbose=False, device=self.device,
                                      quantize=16)

        head_boxes = []
        for result in results:
            if result.keypoints is None:
                continue
            for box, keypoints in zip(result.boxes, result.keypoints):
                xy = keypoints.xy[0].cpu().numpy()
                scores = keypoints.conf[0].cpu().numpy()
                person_box = [float(v) for v in box.xyxy[0]]
                x0, y0, x1, y1 = self._head_box(xy, scores, person_box)
                if (max_width is None or (x1 - x0) <= max_width) and \
                   (max_height is None or (y1 - y0) <= max_height):
                    head_boxes.append((x0, y0, x1, y1))

        return head_boxes or None

    def _head_box(self, xy: np.ndarray, scores: np.ndarray,
                  person_box: List[float]) -> tuple[int, ...]:
        """Deduit la boite de la tete des keypoints, du plus fiable au plus grossier."""
        x0p, y0p, x1p, y1p = person_box

        head = [xy[i] for i in HEAD_KEYPOINTS if scores[i] >= KEYPOINT_CONF]
        shoulders = [xy[i] for i in (LEFT_SHOULDER, RIGHT_SHOULDER)
                     if scores[i] >= KEYPOINT_CONF]

        # Les boites produites ici sont calibrees pour rester comparables a celles
        # d'un detecteur de visage : c'est le meme reglage "Mask Size" qui les
        # agrandit ensuite, il doit donner un rendu homogene entre les modeles.

        # 1. Visage lisible : boite centree sur les keypoints vus. L'ecart entre
        #    les epaules donne une echelle stable quel que soit l'eloignement.
        if len(head) >= 2:
            points = np.array(head)
            cx, cy = points[:, 0].mean(), points[:, 1].mean()
            if len(shoulders) == 2:
                half = np.linalg.norm(shoulders[0] - shoulders[1]) * 0.42
            else:
                spread = max(points[:, 0].max() - points[:, 0].min(),
                             points[:, 1].max() - points[:, 1].min())
                half = max(spread * 1.1, (y1p - y0p) * 0.05)
            return self._as_box(cx - half, cy - half, cx + half, cy + half)

        # 2. Personne de dos : le visage n'est pas lisible mais les epaules le
        #    restent. La tete se trouve juste au-dessus de leur milieu. La boite
        #    reste un peu plus large qu'au cas 1, ou la position etait vue et non
        #    deduite.
        if len(shoulders) == 2:
            center = (shoulders[0] + shoulders[1]) / 2
            width = np.linalg.norm(shoulders[0] - shoulders[1])
            half = width * 0.5
            cy = center[1] - width * 0.5
            return self._as_box(center[0] - half, cy - half, center[0] + half, cy + half)

        # 3. Aucun keypoint credible. Leurs positions restent malgre tout mieux
        #    placees que le centre de la boite personne : de dos, le nez predit
        #    tombe du bon cote de la silhouette meme avec un score tres bas. On
        #    s'en sert pour le centre, et la hauteur du corps donne l'echelle
        #    (une tete vaut environ un septieme de la stature).
        guessed = np.array([xy[i] for i in HEAD_KEYPOINTS])
        guessed = guessed[(guessed[:, 0] > 0) | (guessed[:, 1] > 0)]
        height = y1p - y0p
        if len(guessed):
            cx, cy = guessed[:, 0].mean(), guessed[:, 1].mean()
            half = max(height / 14.0, 8.0)
            return self._as_box(cx - half, cy - half, cx + half, cy + half)

        # 4. Modele muet sur la tete : on masque la bande haute de la personne.
        #    C'est grossier, mais laisser passer une tete est pire qu'en masquer
        #    un peu trop.
        return self._as_box(x0p, y0p, x1p, y0p + height * 0.22)

    @staticmethod
    def _as_box(x0, y0, x1, y1) -> tuple[int, ...]:
        return tuple(np.round([x0, y0, x1, y1]).astype(int))
