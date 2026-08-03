"""Bouton drapeau qui bascule la langue de l'interface.

Les drapeaux sont dessinés à l'exécution plutôt que chargés depuis des fichiers :
un SVG dépendrait du greffon Qt `imageformats/qsvg` dans le bundle PyInstaller,
et un PNG serait flou sur les écrans à forte densité. Le tracé fournit ici
plusieurs tailles dans un même QIcon, Qt choisissant celle qui convient à
l'écran.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QToolButton

from apps import i18n

# Hauteurs pré-rendues : couvre l'affichage standard et les écrans HiDPI.
ICON_HEIGHTS = (16, 24, 32, 48)

# Ratio commun aux deux drapeaux. L'Union Jack est officiellement en 2:1, mais un
# jeu d'icônes homogène prime ici sur l'exactitude des proportions.
FLAG_RATIO = 3 / 2

BORDER_COLOR = QColor("#8a8a8a")

FRENCH_BLUE = QColor("#002654")
FRENCH_RED = QColor("#ce1126")
UNION_BLUE = QColor("#012169")
UNION_RED = QColor("#c8102e")
WHITE = QColor("#ffffff")


def _painter(pixmap):
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    return painter


def _draw_border(painter, rect):
    painter.setPen(QPen(BORDER_COLOR, 1))
    painter.setBrush(Qt.NoBrush)
    # Le rectangle est réduit d'un demi-pixel pour que le trait tombe dans l'image.
    painter.drawRect(rect.adjusted(0, 0, -1, -1))


def _draw_french_flag(painter, rect):
    third = rect.width() / 3
    painter.setPen(Qt.NoPen)
    for index, color in enumerate((FRENCH_BLUE, WHITE, FRENCH_RED)):
        painter.setBrush(color)
        painter.drawRect(QRect(
            rect.x() + round(index * third), rect.y(),
            round((index + 1) * third) - round(index * third), rect.height()))


def _draw_union_flag(painter, rect):
    width, height = rect.width(), rect.height()
    painter.setPen(Qt.NoPen)
    painter.setBrush(UNION_BLUE)
    painter.drawRect(rect)

    # Les diagonales débordent du drapeau : on les confine à son rectangle.
    painter.save()
    painter.setClipRect(rect)
    top_left = QPoint(rect.left(), rect.top())
    top_right = QPoint(rect.right(), rect.top())
    bottom_left = QPoint(rect.left(), rect.bottom())
    bottom_right = QPoint(rect.right(), rect.bottom())
    # Croix de saint André, puis croix de saint Patrick posée par-dessus. Le
    # décalage des bandes rouges du drapeau réel n'est pas reproduit : il
    # mesurerait moins d'un pixel aux tailles utilisées ici.
    for color, thickness in ((WHITE, height / 3), (UNION_RED, height / 6)):
        painter.setPen(QPen(color, max(1.0, thickness), Qt.SolidLine, Qt.FlatCap))
        painter.drawLine(top_left, bottom_right)
        painter.drawLine(top_right, bottom_left)
    painter.restore()

    # Croix de saint Georges : bande blanche large, bande rouge à l'intérieur.
    painter.setPen(Qt.NoPen)
    for color, ratio in ((WHITE, 1 / 3), (UNION_RED, 1 / 5)):
        band_v = max(1, round(height * ratio))
        band_h = max(1, round(height * ratio))
        painter.setBrush(color)
        painter.drawRect(QRect(
            rect.x() + round((width - band_v) / 2), rect.y(), band_v, height))
        painter.drawRect(QRect(
            rect.x(), rect.y() + round((height - band_h) / 2), width, band_h))


_PAINTERS = {"fr": _draw_french_flag, "en": _draw_union_flag}


def flag_pixmap(language, height=16, device_pixel_ratio=1.0):
    """Drapeau de la langue, dessiné à la hauteur logique demandée."""
    draw = _PAINTERS.get(language)
    if draw is None:
        raise ValueError(f"Aucun drapeau pour la langue {language!r}")
    width = round(height * FLAG_RATIO)
    pixmap = QPixmap(QSize(round(width * device_pixel_ratio),
                           round(height * device_pixel_ratio)))
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    painter = _painter(pixmap)
    rect = QRect(0, 0, width, height)
    draw(painter, rect)
    _draw_border(painter, rect)
    painter.end()
    return pixmap


def flag_icon(language):
    """QIcon multi-résolution : Qt y puise la taille adaptée à l'écran."""
    icon = QIcon()
    for height in ICON_HEIGHTS:
        icon.addPixmap(flag_pixmap(language, height))
    return icon


class LanguageFlagButton(QToolButton):
    """Drapeau cliquable qui fait basculer toute l'interface d'une langue à l'autre.

    Le drapeau affiché est celui de la langue **active** ; l'infobulle annonce,
    dans la langue cible, ce que produira le clic. Le bouton se resynchronise sur
    `i18n.notifier` : deux boutons ouverts en même temps restent cohérents, quel
    que soit celui que l'utilisateur actionne.
    """

    def __init__(self, parent=None, height=16):
        super().__init__(parent)
        self._height = height
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setIconSize(QSize(round(height * FLAG_RATIO), height))
        self.clicked.connect(i18n.toggle_language)
        i18n.notifier.language_changed.connect(self._on_language_changed)
        self.retranslate()

    def _on_language_changed(self, _language):
        self.retranslate()

    def retranslate(self):
        language = i18n.current_language()
        self.setIcon(flag_icon(language))
        hint = i18n.switch_hint(language)
        self.setToolTip(hint)
        # Sans texte visible, l'infobulle est la seule information : elle doit
        # aussi être exposée aux technologies d'assistance.
        self.setAccessibleName(hint)
