"""Information RGPD / GDPR présentée à l'utilisateur dans l'interface.

Le texte affiché ici est le résumé opérationnel de `docs/RGPD.md` (fr) et
`docs/GDPR.md` (en) : toute modification de fond doit être répercutée dans les
deux langues et dans les deux documents, puis s'accompagner d'une
incrémentation de NOTICE_VERSION afin que les utilisateurs ayant masqué la
notice la revoient une fois.
"""

import logging
import os

from PySide6.QtCore import QLocale, QSettings, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextBrowser, QVBoxLayout)

from apps.utils import resource_path

logger = logging.getLogger(__name__)

ORGANISATION_NAME = "4iTEC"
APPLICATION_NAME = "4iMask Anonymizer"
SETTINGS_ACK_KEY = "privacy/notice_acknowledged_version"
SETTINGS_LANG_KEY = "privacy/language"

# À incrémenter à chaque modification de fond de la notice.
NOTICE_VERSION = 1

# Langues disponibles pour l'information RGPD : (code, libellé affiché).
LANGUAGES = (("fr", "Français"), ("en", "English"))
FALLBACK_LANGUAGE = "en"

DOCUMENT_FILENAMES = {"fr": "RGPD.md", "en": "GDPR.md"}

# Bandeau permanent de la fenêtre principale.
SHORT_NOTICE = {
    "fr": (
        "4iMask masque uniquement les visages, et les têtes vues de dos lorsque l'option "
        "« Back-facing (pose) » est activée. Aucun autre élément identifiant — silhouette, "
        "plaque d'immatriculation, badge, écran, document — n'est traité. Traitement "
        "100 % local, aucune donnée ne quitte ce poste. Contrôlez la vidéo produite avant "
        "toute diffusion."
    ),
    "en": (
        "4iMask masks faces only, plus heads seen from behind when the \"Back-facing "
        "(pose)\" option is enabled. No other identifying element — silhouette, licence "
        "plate, badge, screen, document — is processed. Everything runs locally, no data "
        "leaves this machine. Review the produced video before releasing it."
    ),
}

FULL_NOTICE_HTML = {
    "fr": """
<h3>Ce que fait 4iMask sur ce poste</h3>
<ul>
  <li>Il lit la vidéo que vous sélectionnez, image par image, <b>sans jamais la modifier
      ni la supprimer</b>.</li>
  <li>Un modèle de détection embarqué localise les <b>visages</b> présents dans chaque
      image.</li>
  <li>Si l'option <i>Back-facing (pose)</i> est activée, un second modèle repère les
      personnes et leur posture afin de situer <b>la tête même de dos</b>, là où aucun
      détecteur de visage ne voit quoi que ce soit. Les points de posture servent
      uniquement à placer le masque : ils sont calculés en mémoire et ne sont jamais
      enregistrés.</li>
  <li>Les zones détectées — <b>et elles seules</b> — sont masquées selon l'option choisie
      (flou, mosaïque ou pavé opaque).</li>
  <li>Une nouvelle vidéo est écrite <b>dans le dossier de la vidéo source</b>, avec le
      suffixe <code>_anonymized_&lt;format&gt;</code>. La piste audio n'est pas reprise.</li>
</ul>

<h3>Le masquage porte uniquement sur les visages et les têtes</h3>
<p>C'est la limite la plus importante à connaître. 4iMask masque les visages, et les têtes
lorsque l'option de pose est activée. Il ne recherche, ne reconnaît et ne masque
<b>rien d'autre</b>. Restent intacts dans la vidéo produite :</p>
<ul>
  <li>silhouette, démarche, corpulence, coiffure, vêtements distinctifs ;</li>
  <li>tatouages, cicatrices, prothèses, signes religieux visibles ;</li>
  <li>plaques d'immatriculation, badges, écrans, documents, courriers, étiquettes ;</li>
  <li>éléments de contexte permettant une ré-identification par recoupement : lieu, date,
      poste de travail, effectif restreint.</li>
</ul>
<p>Si l'un de ces éléments doit être masqué, il faut le faire <b>manuellement</b> dans un
logiciel de montage : 4iMask ne le fera pas.</p>

<h3>Ce qui est écrit sur le disque</h3>
<ul>
  <li>La vidéo produite, à l'emplacement décrit ci-dessus.</li>
  <li>Un journal technique dans le sous-dossier <code>logs/</code> : horodatage,
      <b>chemin du fichier traité</b>, modèle et options utilisés, erreurs éventuelles.
      Les 5 journaux les plus récents sont conservés, les plus anciens sont supprimés
      automatiquement au démarrage.</li>
  <li>Votre langue d'affichage et votre choix « ne plus afficher cette information ».</li>
</ul>
<p>Aucune image intermédiaire, aucune vignette et aucune coordonnée de visage ne sont
enregistrées.</p>

<h3>Ce que 4iMask ne fait pas</h3>
<ul>
  <li><b>Aucune connexion réseau</b> : pas d'envoi de vidéo, pas de télémétrie, pas de
      statistiques d'usage, pas de compte utilisateur.</li>
  <li><b>Aucune reconnaissance faciale</b> : les modèles repèrent l'emplacement des
      visages, ils n'identifient personne, ne calculent aucun gabarit biométrique et ne
      conservent aucune empreinte.</li>
  <li><b>Aucun apprentissage</b> : vos vidéos ne servent pas à entraîner les modèles et
      ne sont transmises à personne.</li>
</ul>

<h3>Autres limites</h3>
<p>Le fichier produit <b>ne peut pas être considéré comme anonyme sans contrôle</b> :</p>
<ul>
  <li>La détection n'est jamais exhaustive : visages de profil, éloignés, flous ou
      partiellement cachés peuvent être manqués. Une résolution de sortie plus élevée
      améliore la détection des personnes en arrière-plan.</li>
  <li>Le flou et la mosaïque atténuent l'information sans la détruire ; le pavé opaque
      (<i>Mask</i>) est l'option la plus robuste pour une diffusion externe.</li>
  <li>L'option de pose déduit la position de la tête ; lorsque la posture ne permet pas
      de la situer, c'est la partie haute de la personne qui est masquée. Le masque peut
      donc être plus large que la tête — un excès volontaire, préférable à une tête
      laissée visible.</li>
</ul>
<p><b>Visionnez la vidéo produite avant de la diffuser.</b></p>

<h3>Vos responsabilités</h3>
<p>Votre organisation reste responsable du traitement : base légale, information des
personnes filmées, durée de conservation des vidéos d'origine, sécurité des fichiers et
suppression des sources devenues inutiles. Le document RGPD complet détaille ces points.</p>
""",
    "en": """
<h3>What 4iMask does on this machine</h3>
<ul>
  <li>It reads the video you select, frame by frame, <b>without ever modifying or
      deleting it</b>.</li>
  <li>A bundled detection model locates the <b>faces</b> present in each frame.</li>
  <li>If the <i>Back-facing (pose)</i> option is enabled, a second model locates people
      and their posture in order to place <b>the head even from behind</b>, where no face
      detector can see anything. The posture points are used solely to position the mask:
      they are computed in memory and never stored.</li>
  <li>The detected areas — <b>and only those</b> — are masked using the selected option
      (blur, mosaic or solid box).</li>
  <li>A new video is written <b>in the source video's folder</b>, with the
      <code>_anonymized_&lt;format&gt;</code> suffix. The audio track is not carried over.</li>
</ul>

<h3>Masking applies to faces and heads only</h3>
<p>This is the most important limitation to understand. 4iMask masks faces, and heads when
the pose option is enabled. It looks for, recognises and masks <b>nothing else</b>. The
following remain fully visible in the produced video:</p>
<ul>
  <li>silhouette, gait, build, hairstyle, distinctive clothing;</li>
  <li>tattoos, scars, prostheses, visible religious symbols;</li>
  <li>licence plates, badges, screens, documents, letters, labels;</li>
  <li>contextual elements allowing re-identification by cross-referencing: location,
      date, workstation, small headcount.</li>
</ul>
<p>If any of these must be hidden, it has to be done <b>manually</b> in a video editor:
4iMask will not do it for you.</p>

<h3>What is written to disk</h3>
<ul>
  <li>The produced video, at the location described above.</li>
  <li>A technical log in the <code>logs/</code> subfolder: timestamp, <b>path of the
      processed file</b>, model and options used, any errors. The 5 most recent logs are
      kept, older ones are deleted automatically at startup.</li>
  <li>Your display language and your "do not show again" choice.</li>
</ul>
<p>No intermediate frame, no thumbnail and no face coordinates are stored.</p>

<h3>What 4iMask does not do</h3>
<ul>
  <li><b>No network connection</b>: no video upload, no telemetry, no usage statistics,
      no user account.</li>
  <li><b>No facial recognition</b>: the models locate where faces are, they identify
      nobody, compute no biometric template and store no signature.</li>
  <li><b>No training</b>: your videos are not used to train the models and are not sent
      to anyone.</li>
</ul>

<h3>Other limitations</h3>
<p>The produced file <b>cannot be considered anonymous without review</b>:</p>
<ul>
  <li>Detection is never exhaustive: faces in profile, far away, blurred or partially
      hidden may be missed. A higher output resolution improves detection of people in
      the background.</li>
  <li>Blur and mosaic attenuate information without destroying it; the solid box
      (<i>Mask</i>) is the most robust option for external release.</li>
  <li>The pose option infers the position of the head; when posture does not allow it to
      be located, the upper part of the person is masked instead. The mask may therefore
      be wider than the head — deliberate over-masking, preferable to leaving a head
      visible.</li>
</ul>
<p><b>Watch the produced video before releasing it.</b></p>

<h3>Your responsibilities</h3>
<p>Your organisation remains the data controller: lawful basis, information of the people
filmed, retention of the original videos, file security and deletion of sources that are
no longer needed. The full GDPR document covers these points.</p>
""",
}

UI_TEXT = {
    "fr": {
        "dialog_title": "Confidentialité et protection des données",
        "language_label": "Langue :",
        "dont_show": "J'ai lu cette information, ne plus l'afficher au démarrage",
        "open_document": "Ouvrir le document RGPD complet",
        "close": "J'ai compris",
        "missing_title": "Document indisponible",
        "missing_body": (
            "Le document RGPD complet n'a pas été trouvé sur ce poste.\n"
            "Il est consultable dans le dépôt du projet, fichier docs/RGPD.md."),
        "link": "Confidentialité / RGPD",
    },
    "en": {
        "dialog_title": "Privacy and data protection",
        "language_label": "Language:",
        "dont_show": "I have read this information, do not show it at startup again",
        "open_document": "Open the full GDPR document",
        "close": "I understand",
        "missing_title": "Document unavailable",
        "missing_body": (
            "The full GDPR document was not found on this machine.\n"
            "It is available in the project repository, file docs/GDPR.md."),
        "link": "Privacy / GDPR",
    },
}


def _settings():
    return QSettings(ORGANISATION_NAME, APPLICATION_NAME)


def available_languages():
    return LANGUAGES


def system_language():
    """Langue de l'information déduite de la locale du poste."""
    code = QLocale.system().name().split("_")[0].lower()
    return code if code in dict(LANGUAGES) else FALLBACK_LANGUAGE


def current_language():
    stored = _settings().value(SETTINGS_LANG_KEY)
    if stored in dict(LANGUAGES):
        return stored
    return system_language()


def set_language(language):
    if language not in dict(LANGUAGES):
        raise ValueError(f"Langue non gérée : {language!r}")
    _settings().setValue(SETTINGS_LANG_KEY, language)


def text(key, language=None):
    """Chaîne d'interface, avec repli sur l'anglais si une clé manque."""
    language = language or current_language()
    return UI_TEXT.get(language, UI_TEXT[FALLBACK_LANGUAGE]).get(
        key, UI_TEXT[FALLBACK_LANGUAGE][key])


def short_notice(language=None):
    language = language or current_language()
    return SHORT_NOTICE.get(language, SHORT_NOTICE[FALLBACK_LANGUAGE])


def full_notice_html(language=None):
    language = language or current_language()
    return FULL_NOTICE_HTML.get(language, FULL_NOTICE_HTML[FALLBACK_LANGUAGE])


def should_show_notice():
    """Vrai tant que l'utilisateur n'a pas acquitté la version courante."""
    try:
        acknowledged = int(_settings().value(SETTINGS_ACK_KEY, 0))
    except (TypeError, ValueError):
        acknowledged = 0
    return acknowledged < NOTICE_VERSION


def acknowledge_notice():
    _settings().setValue(SETTINGS_ACK_KEY, NOTICE_VERSION)


def privacy_document_path(language=None):
    """Document complet dans la langue courante, en développement comme packagé.

    Repli sur l'autre langue si la traduction demandée n'est pas livrée.
    """
    language = language or current_language()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ordered = [language] + [code for code, _ in LANGUAGES if code != language]
    for code in ordered:
        filename = DOCUMENT_FILENAMES[code]
        candidates = [
            resource_path(os.path.join("docs", filename)),
            os.path.join(project_root, "docs", filename),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
    return None


class PrivacyDialog(QDialog):
    """Notice d'information RGPD, affichée au premier lancement et à la demande."""

    language_changed = Signal(str)

    def __init__(self, parent=None, startup=False):
        super().__init__(parent)
        self.setMinimumSize(680, 560)
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.language = current_language()

        layout = QVBoxLayout(self)

        language_line = QHBoxLayout()
        self.language_label = QLabel()
        language_line.addWidget(self.language_label)
        self.language_combo = QComboBox()
        for code, label in LANGUAGES:
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        language_line.addWidget(self.language_combo)
        language_line.addStretch(1)
        layout.addLayout(language_line)

        self.header = QLabel()
        self.header.setWordWrap(True)
        self.header.setTextFormat(Qt.PlainText)
        layout.addWidget(self.header)

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        layout.addWidget(self.body)

        self.dont_show_checkbox = None
        if startup:
            self.dont_show_checkbox = QCheckBox()
            layout.addWidget(self.dont_show_checkbox)

        buttons = QHBoxLayout()
        self.document_button = QPushButton()
        self.document_button.clicked.connect(self.open_document)
        buttons.addWidget(self.document_button)
        buttons.addStretch(1)
        self.close_button = QPushButton()
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(text("dialog_title", self.language))
        self.language_label.setText(text("language_label", self.language))
        self.header.setText(short_notice(self.language))
        self.body.setHtml(full_notice_html(self.language))
        self.document_button.setText(text("open_document", self.language))
        self.close_button.setText(text("close", self.language))
        if self.dont_show_checkbox is not None:
            self.dont_show_checkbox.setText(text("dont_show", self.language))

    def on_language_changed(self, index):
        language = self.language_combo.itemData(index)
        if not language or language == self.language:
            return
        self.language = language
        set_language(language)
        self.retranslate()
        self.language_changed.emit(language)

    def open_document(self):
        path = privacy_document_path(self.language)
        if path is None:
            self.logger.warning("Document RGPD introuvable dans le livrable.")
            QMessageBox.information(
                self, text("missing_title", self.language),
                text("missing_body", self.language))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def accept(self):
        if self.dont_show_checkbox is not None and self.dont_show_checkbox.isChecked():
            acknowledge_notice()
        super().accept()
