import os
import sys
# import skimage.draw
from skimage.draw import ellipse as skimage_ellipse
import cv2
import numpy as np
# def resource_path(relative_path):
#     """ Get absolute path to resource, works for dev and for PyInstaller """
#     base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
#     return os.path.join(base_path, relative_path)


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def draw_detections(frame, x1, y1, x2, y2,
                    replacewith: str = 'blur', mask_size: float = 1.3,
                    ellipse: bool = True,
                    mosaicsize: int = 15):
    # Scale bb coordinates to mask size
    x1, y1, x2, y2 = scale_bb(x1, y1, x2, y2, mask_size)
    # Clip bb coordinates to valid frame region
    y1, y2 = max(0, y1), min(frame.shape[0] - 1, y2)
    x1, x2 = max(0, x1), min(frame.shape[1] - 1, x2)
    # Une boite degeneree apres clipping n'a rien a masquer : cv2.blur leverait
    # une erreur sur un ksize nul, et le rectangle solide serait invisible.
    if x2 <= x1 or y2 <= y1:
        return frame
    if replacewith == 'solid':
        ovcolor = (0, 0, 0)  # Couleur noire pour masquer
        cv2.rectangle(frame, (x1, y1), (x2, y2), ovcolor, -1)
    elif replacewith == 'blur':
        bf = 2  # blur factor (number of pixels in each dimension that the face will be reduced to)
        # ksize doit valoir au moins 1 : une boite de moins de 2 px fait echouer cv2.blur
        # sur une assertion, ce qui tuait le thread de traitement.
        ksize = (max(1, abs(x2 - x1) // bf), max(1, abs(y2 - y1) // bf))
        blurred_box = cv2.blur(frame[y1:y2, x1:x2], ksize)
        r_rad, c_rad = (y2 - y1) // 2, (x2 - x1) // 2
        # Un rayon nul fait diviser par zero dans skimage : sur une boite trop
        # petite pour porter une ellipse, on floute le rectangle entier.
        if ellipse and r_rad > 0 and c_rad > 0:
            roibox = frame[y1:y2, x1:x2]
            # Get y and x coordinate lists of the "bounding ellipse"
            ey, ex = skimage_ellipse(r_rad, c_rad, r_rad, c_rad)
            roibox[ey, ex] = blurred_box[ey, ex]
            frame[y1:y2, x1:x2] = roibox
        else:
            frame[y1:y2, x1:x2] = blurred_box
    elif replacewith == 'mosaic':
        for y in range(y1, y2, mosaicsize):
            for x in range(x1, x2, mosaicsize):
                pt1 = (x, y)
                pt2 = (min(x2, x + mosaicsize - 1), min(y2, y + mosaicsize - 1))
                color = (int(frame[y, x][0]), int(frame[y, x][1]), int(frame[y, x][2]))
                cv2.rectangle(frame, pt1, pt2, color, -1)
    return frame


def openvino_device():
    """Device a passer a ultralytics pour l'inference OpenVINO.

    Renvoie 'intel:gpu' quand un GPU Intel est expose par OpenVINO, sinon None
    pour laisser ultralytics choisir. Sans cette precision, ultralytics compile
    le modele en mode 'AUTO', qui retombe sur le CPU : le GPU integre reste
    inutilise alors qu'il decharge nettement le processeur.
    """
    try:
        import openvino as ov
        devices = ov.Core().available_devices
    except Exception:
        return None
    has_gpu = any(d == "GPU" or d.startswith("GPU.") for d in devices)
    return "intel:gpu" if has_gpu else None


def merge_boxes(boxes, overlap: float = 0.3):
    """Regroupe les boites qui designent la meme tete et renvoie leur englobante.

    Quand plusieurs detecteurs tournent ensemble, une meme tete est trouvee
    plusieurs fois. Masquer chaque boite separement floute la zone deux fois et
    superpose deux ellipses, ce qui se voit. On fusionne donc avant de masquer.

    Le recouvrement est rapporte a la plus petite des deux boites, et non a leur
    union : une boite de visage serree est souvent incluse dans une boite de tete
    plus large, un IoU classique les separerait a tort.
    """
    boxes = [tuple(int(v) for v in b) for b in boxes]
    if len(boxes) < 2:
        return boxes

    # Groupes fusionnes de proche en proche : deux boites qui ne se touchent pas
    # se retrouvent ensemble si une troisieme recouvre les deux.
    groups = []
    for box in boxes:
        merged = box
        rest = []
        for group in groups:
            if _overlaps(merged, group, overlap):
                merged = (min(merged[0], group[0]), min(merged[1], group[1]),
                          max(merged[2], group[2]), max(merged[3], group[3]))
            else:
                rest.append(group)
        rest.append(merged)
        groups = rest
    return groups


def _overlaps(a, b, threshold):
    """Vrai si l'intersection couvre assez de la plus petite des deux boites."""
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return False
    smallest = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return smallest > 0 and (ix * iy) / smallest >= threshold


# Facteur neutre pour draw_detections : la boite est masquee telle qu'elle est
# fournie. A passer apres merge_scaled_boxes, qui a deja applique le gabarit.
ALREADY_SCALED = 1.0


def merge_scaled_boxes(boxes, mask_size: float, overlap: float = 0.3):
    """Fusionne les boites telles qu'elles seront dessinees, gabarit compris.

    merge_boxes decide sur les boites brutes, alors que le masquage les agrandit
    ensuite de mask_size -- soit un facteur 2,2 au reglage par defaut. Deux
    boites jugees distinctes a ce stade, typiquement un visage detecte et la tete
    deduite de la posture, decales l'un par rapport a l'autre, se recouvrent
    largement une fois agrandies : la meme tete recevait alors deux ellipses
    superposees, bien visibles. En agrandissant avant de fusionner, la decision
    porte sur ce que l'utilisateur voit.

    Les boites renvoyees sont deja au gabarit final : elles doivent etre masquees
    avec ALREADY_SCALED, sans quoi l'agrandissement s'appliquerait deux fois.
    """
    scaled = [tuple(scale_bb(*box, mask_size)) for box in boxes]
    return merge_boxes(scaled, overlap)


def mask_boxes(boxes, frame, replacewith: str = 'blur', mask_size: float = 1.3,
               ellipse: bool = True, mosaicsize: int = 15):
    """Applique le masquage a une liste de boites, quel que soit le detecteur.

    Utilise pour combiner plusieurs modeles sur une meme frame : chaque modele
    fournit ses boites, le masquage est applique une seule fois par boite.
    """
    for x1, y1, x2, y2 in boxes:
        frame = draw_detections(frame, x1, y1, x2, y2, replacewith, mask_size,
                                ellipse, mosaicsize)
    return frame


def scale_bb(x0, y0, x1, y1, mask_scale=1.3):
    s = mask_scale - 1.0
    h, w = y1 - y0, x1 - x0
    y0 -= h * s
    y1 += h * s
    x0 -= w * s
    x1 += w * s
    return np.round([x0, y0, x1, y1]).astype(int)
