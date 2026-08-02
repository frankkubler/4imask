"""Package applicatif de 4iMask.

``compat`` est importe ici, et non seulement depuis le point d'entree, pour que
le correctif s'applique quel que soit le module charge en premier : ``worker``
importe PySide6 avant ``ultralytics``, ordre qui declenche l'ImportError decrit
dans ``apps/compat.py``. Sans cet import, ``import apps.worker`` echoue depuis
les tests ou tout autre point d'entree que ``4imask_anonymizer.py``.
"""

from apps import compat  # noqa: F401  must stay first
