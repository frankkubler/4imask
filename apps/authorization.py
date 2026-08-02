"""Garde-fou d'usage : restreint l'application a une liste de domaines Windows.

Ce n'est pas une mesure de securite. La liste est embarquee dans le binaire et
la variable d'environnement lue est modifiable par l'utilisateur : le but est
d'eviter un usage hors du perimetre prevu, pas de l'empecher.

La liste n'est pas versionnee. Elle est ecrite au moment du build depuis le
secret ``AUTHORIZED_DOMAINS`` (voir ``.github/workflows/pyinstaller.yml``), et
``res/.dummy`` est exclu par ``.gitignore``.
"""

DOMAIN_ENV_VAR = "USERDOMAIN"
AUTHORIZED_DOMAINS_FILE = "res/.dummy"


def load_authorized_domains(path):
    """Lit la liste des domaines autorises.

    Retourne ``None`` quand aucune liste n'est disponible -- fichier absent,
    illisible ou vide -- ce qui correspond a une execution depuis les sources.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            domains = [line.strip() for line in handle if line.strip()]
    except OSError:
        return None
    return domains or None


def is_authorized(domain, authorized_domains):
    """Determine si l'application peut demarrer.

    Deux cas autorisent inconditionnellement :

    - aucune liste embarquee : execution depuis les sources, aucune restriction ;
    - domaine indeterminable : ``USERDOMAIN`` n'existe que sous Windows, et son
      absence ne doit pas empecher le demarrage sur les plateformes que le
      README documente.
    """
    if not authorized_domains:
        return True
    if not domain:
        return True
    return domain in authorized_domains
