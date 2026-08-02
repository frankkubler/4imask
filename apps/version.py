"""Version de l'application.

Source unique de verite. `pyproject.toml` doit porter la meme valeur ; le test
tests/test_version.py verifie que les deux ne divergent pas.

Le projet n'est pas installe comme paquet (voir pyproject.toml), et PyInstaller
n'embarque pas les metadonnees de distribution : importlib.metadata ne peut donc
pas servir de source, d'ou cette constante.
"""

__version__ = "1.1.0"
