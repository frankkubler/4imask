"""Écran de démarrage affiché pendant le chargement des modèles.

Il remplace le splash natif de PyInstaller (`--splash` / `pyi_splash`), qui ne
fonctionnait que dans le binaire distribué : lancée depuis les sources,
l'application restait plusieurs secondes sans aucun retour visuel.

Le temps à couvrir est celui de l'import de torch, ultralytics et openvino par
`apps.worker` — environ quatre secondes. C'est pourquoi `4imask_anonymizer.py`
diffère cet import jusqu'à ce que cet écran soit visible : affiché après, il
n'aurait plus rien à montrer.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from apps.utils import resource_path

logger = logging.getLogger(__name__)

# Même image en deux définitions : la seconde évite un rendu flou sur les écrans
# à forte densité. Ordre décroissant, la première dont le facteur convient gagne.
SPLASH_IMAGES = ((1.5, "res/icons/splash@1.5x.png"), (1.0, "res/icons/splash.png"))

# Dimensions de repli, celles de l'image nominale : un livrable incomplet doit
# donner un écran sobre, pas une fenêtre de taille nulle.
FALLBACK_SIZE = (800, 380)

MESSAGE_COLOR = QColor("#5a5a5a")
# Marges relatives (gauche, haut, droite, bas). La moitié gauche de l'image
# porte le logo et son bas un bandeau rouge : le message se pose sous le bloc
# de texte, à droite. La marge haute reste nulle pour laisser un message long
# passer à la ligne vers le haut plutôt que de déborder de l'image.
MESSAGE_MARGINS = (0.44, 0.0, 0.05, 0.09)
MESSAGE_HEIGHT_RATIO = 0.035


def screen_ratio():
    screen = QApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def splash_pixmap(ratio=None):
    """Image de démarrage, dans la définition la plus proche de l'écran."""
    ratio = screen_ratio() if ratio is None else ratio
    for image_ratio, path in SPLASH_IMAGES:
        if ratio < image_ratio:
            continue
        pixmap = QPixmap(resource_path(path))
        if not pixmap.isNull():
            pixmap.setDevicePixelRatio(image_ratio)
            return pixmap
        logger.warning("Image de démarrage illisible : %s", path)
    logger.warning("Aucune image de démarrage disponible, écran uni.")
    fallback = QPixmap(*FALLBACK_SIZE)
    fallback.fill(Qt.white)
    return fallback


class Splash(QSplashScreen):
    """Écran de démarrage, avec l'étape en cours écrite sur l'image."""

    def __init__(self, ratio=None):
        # Pas de WindowStaysOnTopHint : le type de fenêtre Qt.SplashScreen place
        # déjà l'écran au-dessus, et forcer davantage ferait passer une boîte de
        # dialogue ouverte pendant le démarrage derrière lui.
        super().__init__(splash_pixmap(ratio))

    @staticmethod
    def close_all():
        """Ferme les écrans de démarrage encore ouverts.

        Utile avant tout dialogue affiché pendant le démarrage : sans cela, le
        message se retrouverait sous l'écran, sans moyen d'y répondre.
        """
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QSplashScreen):
                widget.close()

    def drawContents(self, painter):
        message = self.message()
        if not message:
            return
        left, top, right, bottom = MESSAGE_MARGINS
        rect = self.rect()
        zone = rect.adjusted(
            round(rect.width() * left), round(rect.height() * top),
            -round(rect.width() * right), -round(rect.height() * bottom))
        font = painter.font()
        font.setPointSizeF(max(8.0, rect.height() * MESSAGE_HEIGHT_RATIO))
        painter.setFont(font)
        painter.setPen(MESSAGE_COLOR)
        painter.drawText(
            zone, Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap, message)

    def show_message(self, text):
        """Annonce l'étape en cours. Le texte arrive déjà traduit.

        La boucle d'évènements ne tourne pas encore pendant le chargement :
        sans le repaint et le traitement des évènements forcés ici, l'écran
        resterait vide jusqu'à l'ouverture de la fenêtre principale.
        """
        self.showMessage(text)
        self.repaint()
        QApplication.processEvents()
