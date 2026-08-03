"""Traductions de l'interface et gestion de la langue courante.

Ce module est la source unique des chaînes affichées : aucun libellé visible par
l'utilisateur ne doit être écrit en dur ailleurs dans le code. Ajouter une clé
suppose de la renseigner dans **toutes** les langues de LANGUAGES — la parité
est vérifiée par tests/test_i18n.py, y compris celle des champs de formatage.

Le choix de langue est mémorisé dans les préférences du poste et notifié aux
fenêtres ouvertes par `notifier.language_changed`, ce qui permet de retraduire
l'interface sans redémarrer l'application.

Qt Linguist (.ts/.qm) n'est volontairement pas utilisé : il imposerait une étape
de compilation (lrelease) dans la chaîne de build PyInstaller pour deux langues
et quelques dizaines de chaînes.
"""

import logging

from PySide6.QtCore import QLocale, QObject, QSettings, Signal

logger = logging.getLogger(__name__)

ORGANISATION_NAME = "4iTEC"
APPLICATION_NAME = "4iMask Anonymizer"

SETTINGS_LANG_KEY = "ui/language"
# Clé utilisée avant que la langue ne pilote toute l'interface : relue une fois
# pour ne pas perdre le choix des utilisateurs qui avaient déjà basculé la notice.
LEGACY_SETTINGS_LANG_KEY = "privacy/language"

# Langues disponibles : (code, libellé affiché dans sa propre langue).
LANGUAGES = (("fr", "Français"), ("en", "English"))
FALLBACK_LANGUAGE = "en"

# Invitation à basculer, indexée par la langue *cible* : elle est donc toujours
# écrite dans la langue vers laquelle le clic emmène, ce qui reste compréhensible
# quelle que soit la langue affichée.
SWITCH_HINT = {
    "fr": "Passer en français",
    "en": "Switch to English",
}

TRANSLATIONS = {
    "fr": {
        # --- Écran de démarrage ---
        "splash_loading_models": "Chargement des modèles de détection…",
        "splash_starting": "Démarrage…",

        # --- Sélection de la vidéo ---
        "select_video": "Sélectionner une vidéo",
        "select_video_dialog": "Sélectionner une vidéo",
        "video_filter": "Fichiers vidéo (*.mp4 *.avi *.mov *.mkv)",
        "no_video_selected": "Aucune vidéo sélectionnée.",

        # --- Format de sortie ---
        "output_format": "Format de sortie :",

        # --- Méthode de masquage ---
        "mosaic": "Mosaïque",
        "blur": "Flou",
        "solid_mask": "Pavé opaque",
        "mask_size": "Taille du masque :",

        # --- Détection ---
        "pose_option": "Personnes de dos (pose)",
        "pose_tooltip": (
            "Ajoute la détection des têtes vues de dos. Ralentit le traitement."),

        # --- Commandes ---
        "start": "Démarrer l'anonymisation",
        "pause": "Pause",
        "resume": "Reprendre",
        "stop": "Arrêter",
        "play_preview": "Lancer l'aperçu",
        "stop_preview": "Arrêter l'aperçu",

        # --- Progression et résultat ---
        "time_remaining_unknown": "Temps restant estimé : --",
        "time_remaining": "Temps restant estimé : {hours} h {minutes} min {seconds} s",
        "original_video": "Vidéo d'origine",
        "complete": "Anonymisation terminée.",
        "failed": "Échec de l'anonymisation : {error}",

        # --- Boîtes de dialogue ---
        "warning_title": "Avertissement",
        "error_title": "Erreur",
        "warn_in_progress": "Une anonymisation est en cours. Arrêtez-la d'abord.",
        "warn_select_first": "Sélectionnez d'abord une vidéo.",
        "warn_not_authorized": "Vous n'êtes pas autorisé à utiliser cette application.",

        # --- Erreurs remontées par le traitement ---
        "err_open_input": "Ouverture du fichier vidéo impossible : {path}",
        "err_open_output": "Ouverture du fichier de sortie impossible : {path}",
        "err_frame_rejected": (
            "Image {frame} refusée par l'encodeur : {width}x{height} "
            "au lieu de {expected_width}x{expected_height}"),

        # --- Pied de fenêtre ---
        "license_link": "Licence AGPL",
        "version_label": "{years} 4iMask Anonymizer — version {version}",
        "version_unknown": "inconnue",

        # --- Information RGPD ---
        "privacy_dialog_title": "Confidentialité et protection des données",
        "privacy_dont_show": (
            "J'ai lu cette information, ne plus l'afficher au démarrage"),
        "privacy_open_document": "Ouvrir le document RGPD complet",
        "privacy_close": "J'ai compris",
        "privacy_missing_title": "Document indisponible",
        "privacy_missing_body": (
            "Le document RGPD complet n'a pas été trouvé sur ce poste.\n"
            "Il est consultable dans le dépôt du projet, fichier docs/RGPD.md."),
        "privacy_link": "Confidentialité / RGPD",
    },
    "en": {
        # --- Splash screen ---
        "splash_loading_models": "Loading detection models…",
        "splash_starting": "Starting…",

        # --- Video selection ---
        "select_video": "Select Video",
        "select_video_dialog": "Select Video",
        "video_filter": "Video Files (*.mp4 *.avi *.mov *.mkv)",
        "no_video_selected": "No video selected.",

        # --- Output format ---
        "output_format": "Output format:",

        # --- Masking method ---
        "mosaic": "Mosaic",
        "blur": "Blur",
        "solid_mask": "Solid box",
        "mask_size": "Mask size:",

        # --- Detection ---
        "pose_option": "Back-facing (pose)",
        "pose_tooltip": (
            "Also detects heads seen from behind. Slows processing down."),

        # --- Commands ---
        "start": "Start Anonymization",
        "pause": "Pause",
        "resume": "Resume",
        "stop": "Stop",
        "play_preview": "Play Preview",
        "stop_preview": "Stop Preview",

        # --- Progress and outcome ---
        "time_remaining_unknown": "Estimated time remaining: --",
        "time_remaining": "Estimated time remaining: {hours}h {minutes}m {seconds}s",
        "original_video": "Original Video",
        "complete": "Anonymization complete.",
        "failed": "Anonymization failed: {error}",

        # --- Dialogs ---
        "warning_title": "Warning",
        "error_title": "Error",
        "warn_in_progress": "Anonymization is in progress. Please stop it first.",
        "warn_select_first": "Please select a video first.",
        "warn_not_authorized": "You are not authorized to use this application.",

        # --- Errors raised by the processing thread ---
        "err_open_input": "Cannot open the video file: {path}",
        "err_open_output": "Cannot open the output file: {path}",
        "err_frame_rejected": (
            "Frame {frame} rejected by the encoder: {width}x{height} "
            "instead of {expected_width}x{expected_height}"),

        # --- Window footer ---
        "license_link": "AGPL License",
        "version_label": "{years} 4iMask Anonymizer — version {version}",
        "version_unknown": "unknown",

        # --- GDPR information ---
        "privacy_dialog_title": "Privacy and data protection",
        "privacy_dont_show": (
            "I have read this information, do not show it at startup again"),
        "privacy_open_document": "Open the full GDPR document",
        "privacy_close": "I understand",
        "privacy_missing_title": "Document unavailable",
        "privacy_missing_body": (
            "The full GDPR document was not found on this machine.\n"
            "It is available in the project repository, file docs/GDPR.md."),
        "privacy_link": "Privacy / GDPR",
    },
}


class _LanguageNotifier(QObject):
    """Porte le signal de changement de langue.

    Un QObject de module plutôt qu'un signal par fenêtre : le bouton drapeau
    existe à plusieurs endroits (fenêtre principale, notice RGPD) et tous
    doivent se retraduire, quel que soit celui qui a été cliqué.
    """

    language_changed = Signal(str)


notifier = _LanguageNotifier()


def settings():
    """Préférences du poste. Point unique, pour que les tests puissent l'isoler."""
    return QSettings(ORGANISATION_NAME, APPLICATION_NAME)


def available_languages():
    return LANGUAGES


def is_supported(language):
    return language in dict(LANGUAGES)


def system_language():
    """Langue déduite de la locale du poste, repli sur l'anglais."""
    code = QLocale.system().name().split("_")[0].lower()
    return code if is_supported(code) else FALLBACK_LANGUAGE


def current_language():
    store = settings()
    stored = store.value(SETTINGS_LANG_KEY)
    if is_supported(stored):
        return stored
    legacy = store.value(LEGACY_SETTINGS_LANG_KEY)
    if is_supported(legacy):
        return legacy
    return system_language()


def set_language(language):
    """Mémorise la langue et notifie l'interface si elle change réellement.

    Le choix est écrit dans tous les cas, y compris quand il coïncide avec la
    locale du poste : il devient explicite et ne suivra plus une locale modifiée
    par la suite. Le signal, lui, n'est émis que sur un changement effectif —
    sans quoi chaque ouverture de fenêtre retraduirait toute l'interface.
    """
    if not is_supported(language):
        raise ValueError(f"Langue non gérée : {language!r}")
    changed = language != current_language()
    settings().setValue(SETTINGS_LANG_KEY, language)
    if changed:
        notifier.language_changed.emit(language)


def next_language(language=None):
    """Langue vers laquelle bascule le bouton drapeau."""
    language = language or current_language()
    codes = [code for code, _ in LANGUAGES]
    return codes[(codes.index(language) + 1) % len(codes)]


def toggle_language():
    """Bascule vers la langue suivante et renvoie celle qui devient active."""
    language = next_language()
    set_language(language)
    return language


def language_label(language=None):
    """Nom de la langue, écrit dans cette langue."""
    language = language or current_language()
    return dict(LANGUAGES).get(language, language)


def switch_hint(language=None):
    """Invitation à basculer, rédigée dans la langue cible."""
    return SWITCH_HINT[next_language(language)]


def tr(key, language=None, **kwargs):
    """Chaîne traduite, avec repli sur l'anglais quand la clé manque.

    Les champs de formatage sont passés en mots-clés. Un gabarit incohérent est
    journalisé et renvoyé tel quel : une traduction fautive ne doit pas
    interrompre l'interface, et tests/test_i18n.py verrouille déjà leur parité.
    """
    language = language or current_language()
    table = TRANSLATIONS.get(language, TRANSLATIONS[FALLBACK_LANGUAGE])
    template = table.get(key)
    if template is None:
        template = TRANSLATIONS[FALLBACK_LANGUAGE].get(key)
        if template is None:
            # Clé inconnue partout : la renvoyer telle quelle rend la faute
            # visible à l'écran sans interrompre l'interface.
            logger.error("Clé de traduction inconnue : %r", key)
            return key
        logger.warning("Clé de traduction absente en %s : %r", language, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        logger.error("Gabarit %r incompatible avec %r en %s", key, kwargs, language)
        return template
