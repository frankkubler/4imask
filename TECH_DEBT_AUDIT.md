# Audit de dette technique — 4imask

**Révision 3** — 2026-08-02 (post-correction du Top 5)
Révision 2 : 2026-08-02, post-migration `uv` · Révision 1 : 2026-08-02, commit `5d61eb9`
Périmètre : intégralité du dépôt (1 278 lignes Python réparties sur 9 modules, 2 workflows CI, 24 Mo de binaires versionnés)
État audité : commit `9eea236`

> **Méthode et limites.** Audit statique par lecture intégrale des modules Python, des workflows CI et des fichiers de configuration.
> **Révision 2 :** l'environnement créé par `uv sync` a permis de vérifier empiriquement F001, F013 et F027 — les deux premiers confirmés, F027 invalidé et retiré.
> **Révision 3 :** `uv run ruff check` et `uv run pip-audit` ont été exécutés. `pip-audit` ne signale **aucune vulnérabilité connue** : la réserve des révisions précédentes sur les CVE est levée. `ruff` relève 23 signalements, tous déjà couverts par des constats existants. `vulture` et `mypy` n'ont pas été exécutés.
> **Correction de décompte.** Les révisions 1 et 2 annonçaient 58 et 68 constats pour des tableaux comptant en réalité 65 et 76 lignes. Le décompte ci-dessous est établi en comptant les lignes du tableau.

## Journal de la révision 3

Le commit `9eea236` traite le Top 5 de la révision 2. **23 constats passent à `RESOLVED`**, dont les 6 Critique.

| Statut | Constats |
|--------|----------|
| `RESOLVED` — sortie vidéo | F001, F074 |
| `RESOLVED` — gestion d'erreurs du thread | F002, F003, F004, F018, F055 |
| `RESOLVED` — masquage | F013 |
| `RESOLVED` — garde-fou d'usage | F005, F007, F021, F022, F030 |
| `RESOLVED` — chaîne de build et `uv` | F009, F010, F033, F034, F066, F070, F072, F073, F075 |
| `RESOLVED` — découvert et corrigé en cours de route | F078 |
| Requalifiés, gravité abaissée | F006 (Critique → Moyenne), F011, F014, F015, F020 (Élevée → Moyenne), F060, F064, F069 |
| **`NEW`** | F079, F080, F081 |

**Il ne reste aucun constat Critique.** Répartition des 57 constats ouverts : **0 Critique**, **9 Élevée**, **34 Moyenne**, **14 Faible**. Total du tableau : 80 constats, dont 23 `RESOLVED`.

Vérifications à l'appui des `RESOLVED` :

- **F001** — pipeline complet sur une source 4:3 : sortie 854×640, **20 frames écrites, 20 lisibles** (contre 0 avant).
- **F002/F004** — `run()` sur un fichier inexistant émet `['Ouverture du fichier video impossible : /inexistant.mp4', '__complete__']` au lieu de lever un `TypeError` silencieux.
- **F005** — `git filter-repo` a réécrit les 124 commits ; un balayage de tous les blobs du dépôt ne trouve plus aucune occurrence des domaines purgés.
- **F007** — quatre cas de démarrage vérifiés : Linux sans `USERDOMAIN` → démarre, domaine autorisé → démarre, domaine inconnu → refusé, sans liste embarquée → démarre sans restriction.
- **F013/F020** — 34 tests passants (`uv run pytest`).

---

## Synthèse

1. **Aucun constat Critique ne subsiste.** Les six de la révision 2 sont corrigés et vérifiés.
2. **Le risque résiduel principal est le workflow SLSA (F008)**, non traité : à chaque release, il publie une attestation de provenance signée niveau 3 pour `artifact1` et `artifact2`, deux fichiers texte de 10 octets. C'est désormais le constat le plus grave du dépôt, et le seul qui produise une garantie fausse plutôt qu'un simple défaut.
3. **Trois bugs de correction restent ouverts et sont tous en effort S** : `split(".")[0]` sur le chemin de sortie (F012), `self.mask_size` jamais rafraîchi après un premier traitement (F016), et `stop_anonymization` qui n'attend pas la fin du thread (F019).
4. **Les tests couvrent la primitive de masquage mais pas le pipeline.** 34 tests sur `draw_detections`, le dimensionnement et le garde-fou ; rien sur une vraie vidéo de bout en bout, et **aucun job CI ne les exécute** (F081) — le seul workflow se déclenche sur tag et ne fait que construire.
5. **Le garde-fou d'usage est désormais assumé, pas résolu (F006).** La liste ne fuite plus et le contrôle ne bloque plus les plateformes non-Windows, mais il reste contournable par construction. C'est documenté comme tel dans le README ; la gravité passe de Critique à Moyenne au titre du risque accepté.
6. **La migration `uv` est terminée côté outillage mais pas côté métadonnées** : `description = "Add your description here"` subsiste, `version = "1.0.3"` diverge du `self.version = "1.0.2"` codé en dur (F069), et ni `license` ni `authors` ne sont déclarés sur un projet AGPL-3.0 (F071).
7. **L'accélération matérielle annoncée par le README reste inatteignable (F067).** Seul `onnxruntime` CPU est déclaré ; aucun extra ne permet d'installer les variantes GPU, DirectML ou OpenVINO.
8. **Deux contournements sont désormais en place sans filet (F079).** `apps/compat.py` patche `six._SixMetaPathImporter` pour un bug d'interaction PySide6/ultralytics : aucun lien vers un ticket amont, aucune borne de version, aucun test de non-régression. Il deviendra du code mort silencieux quand l'amont corrigera.
9. **`apps/worker.py` reste le point de concentration**, mais sa densité a baissé : la gestion d'erreurs et le dimensionnement en sont sortis. Les constats restants y sont structurels (rechargement du modèle par exécution, options mutées depuis l'UI en cours de traitement).
10. **Un reliquat opérationnel après la purge d'historique** : les forks GitHub éventuels conservent les objets purgés, et GitHub garde les objets orphelins joignables par SHA après un force-push tant que son GC serveur n'a pas tourné.

---

## Modèle mental de l'architecture

4imask est une application de bureau **PySide6 mono-processus** qui floute les visages d'un fichier vidéo. La structure tient en quatre couches : `4imask_anonymizer.py` porte la totalité de l'interface (une `QMainWindow` dont le constructeur instancie chaque widget à la main, sans fichier `.ui` ni séparation vue/état) ; `apps/worker.py` porte un `QThread` unique qui exécute la boucle de traitement de bout en bout ; `apps/{yolo,centerface,yunet}.py` sont trois adaptateurs de détecteurs qui convergent tous vers une unique primitive de dessin, `apps/utils.py::draw_detections` — le seul point d'abstraction propre du projet, et il est bien utilisé. Depuis la révision 3 s'ajoutent deux modules transverses : `apps/authorization.py` (garde-fou d'usage, fonctions pures testables) et `apps/compat.py` (correctif d'ordre d'import, appliqué depuis `apps/__init__.py`).

Le flux de données est une chaîne linéaire : `QFileDialog` → `cv2.VideoCapture` → boucle `while` dans `run()` → détecteur → `draw_detections` → `cv2.VideoWriter` + `Signal(np.ndarray, int)` vers l'UI. Il n'existe **toujours aucune couche de configuration** : les options (modèle, mode de remplacement, taille de masque) sont écrites directement dans des attributs publics du worker depuis l'UI, sous forme de chaînes magiques, y compris pendant l'exécution du thread (F024). Le même `AnonymizationWorker` sert à l'anonymisation réelle et à la prévisualisation, la seule différence étant le drapeau `write_output`.

**Ce que la révision 3 a changé dans ce modèle.** Le worker communique désormais ses échecs par signal (`error_occurred`) au lieu de tenter de construire des widgets depuis un thread non-GUI, et libère ses ressources dans un `finally`. Le `VideoWriter` n'est plus ouvert sur des dimensions supposées mais sur celles que le pipeline produit réellement, ce qui supprime la classe de bugs la plus coûteuse du projet. Ces deux changements font de `run()` une fonction qui échoue proprement — condition préalable à tout le reste.

**Contradictions avec le README** — deux des quatre écarts sont levés. Restent : le répertoire `res/ffmpeg/` et le commit `c56d0b3 V1.0.2 ffmpeg conversion` laissent croire à une étape de conversion ffmpeg qui n'existe nulle part dans le code (F048), et la section Prerequisites omet quatre dépendances déclarées dans `pyproject.toml` (F054).

---

## Constats

| ID | Catégorie | Fichier:Ligne | Gravité | Effort | Description | Recommandation |
|----|-----------|---------------|---------|--------|-------------|----------------|
| ~~F001~~ | Correction | `apps/worker.py:118-131` | `RESOLVED` | — | *Le writer était ouvert sur `(new_width, new_height)` alors qu'`imutils.resize` conserve le ratio source : toute vidéo non 16:9 produisait un fichier sans frame lisible.* Le writer est désormais ouvert paresseusement sur `frame.shape` à la première frame produite. Vérifié : source 4:3 → 854×640, 20 frames écrites, 20 lisibles. | — |
| ~~F002~~ | Gestion d'erreurs | `apps/worker.py:44` | `RESOLVED` | — | *`QMessageBox.critical(self, …)` avec `self` = `QThread` levait un `TypeError`.* Remplacé par `error_occurred.emit(...)`, affiché par `on_worker_error` dans le thread GUI. L'import `QMessageBox` a été retiré du worker. | — |
| ~~F003~~ | Gestion d'erreurs | `apps/worker.py:123` | `RESOLVED` | — | *Même défaut sur l'échec d'ouverture du writer.* Idem F002. | — |
| ~~F004~~ | Gestion d'erreurs | `apps/worker.py:37-149` | `RESOLVED` | — | *`run()` n'avait aucun `try/except/finally` : toute exception figeait l'UI.* Corps enveloppé dans `try/except Exception` avec `logger.exception` + signal, et `finally` qui libère `cap` et `out` puis émet `anonymization_complete`. | — |
| ~~F005~~ | Hygiène de sécurité | `res/.dummy` | `RESOLVED` | — | *Quatre domaines Windows d'entreprise versionnés en clair dans un dépôt public AGPL.* Fichier retiré du suivi, ajouté au `.gitignore`, écrit au build depuis le secret `AUTHORIZED_DOMAINS`. Historique purgé par `git filter-repo` sur 124 commits ; balayage de tous les blobs : plus aucune occurrence. **Reliquat opérationnel : voir la première question ouverte.** | — |
| F006 | Hygiène de sécurité | `apps/authorization.py:30-44` | Moyenne | M | **Requalifié (Critique → Moyenne).** Le contrôle reste fondé sur `os.getenv("USERDOMAIN")`, variable modifiable, comparée à une liste embarquée dans le binaire : il demeure contournable par construction. La différence est qu'il est désormais documenté comme garde-fou d'usage et non comme mesure de sécurité (`README.md`, docstring du module), et que la liste ne fuite plus. | Risque accepté en connaissance de cause. À rouvrir seulement si une vraie restriction devient nécessaire — auquel cas seule une vérification signée côté serveur tiendrait. |
| ~~F007~~ | Correction | `apps/authorization.py:30-44` | `RESOLVED` | — | *`USERDOMAIN` n'existant pas hors Windows, l'application s'y fermait systématiquement.* `is_authorized` autorise explicitement le domaine indéterminable et l'absence de liste. Quatre cas de démarrage vérifiés. | — |
| **F008** | Hygiène de sécurité | `.github/workflows/generator-generic-ossf-slsa3-publish.yml:33-37` | Élevée | S | Template SLSA non modifié : chaque release construit `artifact1`/`artifact2` (`echo "artifact1" > artifact1`) et publie une attestation de provenance signée niveau 3 pour ces fichiers factices. **Constat le plus grave restant** : il produit une garantie fausse, pas seulement un défaut. | Remplacer `Build artifacts` par le téléchargement de l'artefact du workflow PyInstaller et pointer `sha256sum` dessus, ou supprimer le workflow. |
| ~~F009~~ | Dépendances et configuration | `.github/workflows/pyinstaller.yml:1-6` | `RESOLVED` | — | *Aucune clé `on:` : workflow invalide, jamais exécuté.* Ajout de `name:` et `on: {push: {tags: ['v*']}, workflow_dispatch:}`. | — |
| ~~F010~~ | Dépendances et configuration | `.github/workflows/pyinstaller.yml:36-48` | `RESOLVED` | — | *Le workflow exigeait un `.spec` exclu par `.gitignore`.* Le build passe par les options CLI, sans `.spec`. | — |
| F011 | Décomposition architecturale | `4imask_anonymizer.py:233-235`, `:365-390`, `:322-338`, `:421-455` | Moyenne | M | **Requalifié (Élevée → Moyenne) : le symptôme est corrigé, la cause demeure.** `anonymization_complete` réactive désormais Blur/Mask/Mosaic et `format_combo`, qui restaient grisés jusqu'au redémarrage. Mais la logique d'activation reste dupliquée sur cinq méthodes aux ensembles divergents, et rien n'empêche une nouvelle divergence. | Extraire `_set_ui_state(state)` avec `state ∈ {IDLE, RUNNING, PREVIEW, PAUSED}` et un seul tableau widget→état. |
| **F012** | Correction | `apps/worker.py:66` | Élevée | S | `(self.video_path).split(".")[0]` tronque au **premier** point du chemin complet. `/home/j.dupont/video.mp4` produit `/home/j_anonymized_480p.avi` — écriture hors du dossier attendu, voire écrasement. | `base, _ = os.path.splitext(self.video_path)` puis `f"{base}_anonymized_{self.output_format.lower()}.avi"`. |
| ~~F013~~ | Correction | `apps/utils.py:31-36`, `:44-46` | `RESOLVED` | — | *`cv2.blur` levait `cv2.error` sur un `ksize` nul pour toute boîte de moins de 2 px, tuant le thread.* Sortie anticipée sur boîte dégénérée, `ksize` borné à 1, et rayon d'ellipse nul traité (supprime aussi un `RuntimeWarning` de skimage). Trois tests paramétrés verrouillent le comportement. | — |
| F014 | Correction | `apps/worker.py:134` | Moyenne | S | **Requalifié (Élevée → Moyenne) :** `progress = (frame_count / total_frames) * 100` lève toujours `ZeroDivisionError` quand `CAP_PROP_FRAME_COUNT` n'est pas renseigné, mais l'exception est désormais capturée, journalisée et affichée à l'utilisateur au lieu de figer l'UI. | Tester `total_frames > 0` ; sinon barre en mode indéterminé. |
| F015 | Correction | `apps/worker.py:140` | Moyenne | S | **Requalifié (Élevée → Moyenne)**, même raison que F014. `frames_per_second = frame_count / elapsed_time` avec `elapsed_time` possiblement nul à la première itération. | Garder `if elapsed_time > 0`. |
| **F016** | Correction | `4imask_anonymizer.py:285-291` | Élevée | S | `update_mask_size` écrit dans `self.worker.mask_size` si un worker existe, sinon dans `self.mask_size`. Dès qu'un worker a existé, `self.mask_size` n'est plus mis à jour — or c'est cette valeur qui est passée au worker suivant (lignes 217 et 427). Toute modification faite après un premier traitement est perdue. | Toujours écrire `self.mask_size = value`, puis propager au worker s'il existe. |
| **F017** | Gestion d'erreurs | `4imask_anonymizer.py:522-525` | Élevée | S | `os.mkdir('logs')` ne capture que `FileExistsError`. En installation packagée sous `C:\Program Files\`, `PermissionError` remonte non gérée avant tout affichage — et avant que le gestionnaire d'exceptions ne soit installé. | `os.makedirs(log_dir, exist_ok=True)` dans un `try/except OSError`, repli sur `%LOCALAPPDATA%` / `~/.local/share`. |
| ~~F018~~ | Correction | `apps/worker.py:143-149` | `RESOLVED` | — | *`cap.release()` / `out.release()` n'étaient atteints que par la sortie normale de la boucle.* Déplacés dans le `finally` de F004. | — |
| **F019** | Correction | `4imask_anonymizer.py:322-338` | Élevée | S | `stop_anonymization` positionne le drapeau puis réactive immédiatement l'UI, sans `self.worker.wait()`. L'utilisateur peut relancer un traitement pendant que le précédent écrit encore dans le même fichier. | Ajouter `self.worker.wait()` après `stop()`, comme le font `closeEvent` et `stop_preview`. |
| F020 | Dette de tests | `tests/` | Moyenne | M | **Requalifié (Élevée → Moyenne).** 34 tests couvrent `draw_detections` (boîtes limites, clipping, mask_size), le dimensionnement de sortie sur trois ratios, et le garde-fou d'usage. Restent non couverts : le pipeline de bout en bout sur une vraie vidéo, `correct_orientation`, et les trois adaptateurs de détecteurs. | Ajouter un test d'intégration sur une vidéo de 10 frames vérifiant nombre de frames et différence sur les zones de visage. Voir F081 pour l'exécution en CI. |
| ~~F021~~ | Dérive documentaire | `README.md` (section *Usage restriction*) | `RESOLVED` | — | *Le README ne mentionnait pas le verrou qui fermait l'application pour tout utilisateur hors des domaines listés.* Section dédiée ajoutée, précisant qu'il s'agit d'un garde-fou d'usage et non d'une mesure de sécurité. | — |
| ~~F022~~ | Dérive documentaire | `README.md:13-16` | `RESOLVED` | — | *Le README documentait une installation Linux impossible en pratique.* Corrigé par F007 : l'application démarre hors Windows. | — |
| **F023** | Performance | `apps/worker.py:70`, `:74`, `:78` | Élevée | M | Le modèle est instancié dans `run()` : chaque bascule prévisualisation ↔ anonymisation recharge YOLO+torch (plusieurs secondes) ou re-sérialise le modèle ONNX de CenterFace. Un aller-retour Play/Stop répété rend l'application inutilisable. | Instancier les détecteurs dans `VideoAnonymizer`, les mettre en cache par nom, les injecter dans le worker. |
| **F024** | Dette de typage | `apps/worker.py:30-32` | Élevée | M | `model` et `replacewith` sont des attributs publics mutés depuis l'UI **pendant** l'exécution du thread (`get_model_option:269`, `get_replacewith_option:294`), avec des chaînes magiques non validées. `'none'` est accepté et produit une vidéo intégralement non anonymisée, sous un nom de fichier contenant `_anonymized_`. | Passer les deux en paramètres du constructeur, typés par `enum.StrEnum`. Bloquer le démarrage si rien n'est sélectionné. |
| F025 | Décomposition architecturale | `4imask_anonymizer.py:198`, `:443-444` | Moyenne | S | `self.timer.timeout.connect(self.update_frame)` s'exécute à **chaque** appel de `play_preview` : les connexions s'accumulent. Le timer appelle `update_frame()` sans argument → `frame=None` → no-op. Le `QTimer` est intégralement inutile, et également démarré sans connexion dans `select_video`. | Supprimer `self.timer`, `timer.start(30)` et cette connexion : l'affichage est piloté par `frame_emited`. |
| F026 | Correction | `apps/centerface.py:34-37`, `:52-54` | Moyenne | S | `import onnx` / `import onnxruntime` n'ont lieu que dans la branche `backend == 'auto'`, mais sont utilisés dans la branche `backend == 'onnxrt'`. `CenterFace(backend='onnxrt')` lève `NameError`. Latent : le seul appelant passe `'auto'`. | Remonter les deux imports en tête de module. |
| F028 | Correction | `4imask_anonymizer.py:194-200` | Moyenne | S | `self.video_label.setText(os.path.basename(self.video_path))` s'exécute **avant** le test d'annulation : sur annulation le label est vidé, un avertissement s'affiche, et `self.video_path` est écrasé à `""` — perdant la sélection précédente. | Déplacer le `setText` dans la branche `if self.video_path:`. |
| F029 | Correction | `apps/worker.py:53` vs `:154` | Moyenne | S | `rotate_code` est lu deux fois : en `float` ligne 53 (émis sur un `Signal(np.ndarray, int)`) et en `int` ligne 154 par frame dans `correct_orientation`. Deux sources de vérité pour la même métadonnée, relue à chaque frame. | Lire l'orientation une fois avant la boucle, la caster en `int`, la passer en paramètre. |
| ~~F030~~ | Hygiène de sécurité | `apps/authorization.py:16-27` | `RESOLVED` | — | *`open(...).read()` sans `with` ni `try`, et `FileNotFoundError` non gérée si `res/.dummy` manquait au bundle.* Remplacé par `load_authorized_domains`, qui utilise un gestionnaire de contexte et retourne `None` sur `OSError`. Quatre tests couvrent fichier absent, vide, répertoire et lignes parasites. | — |
| F031 | Gestion d'erreurs | `4imask_anonymizer.py:541-560` | Moyenne | S | `file_handler.close()` ferme le handler **immédiatement après** l'avoir enregistré dans `basicConfig(handlers=[...])`. Le fichier de log ne fonctionne que grâce à la réouverture implicite de `FileHandler.emit` en mode `'a'` — comportement non intentionnel dont dépend toute la journalisation. | Supprimer les deux dernières lignes de `logs_settings`. |
| F032 | Gestion d'erreurs | `apps/centerface.py:22`, `apps/yunet.py:16` | Moyenne | S | `logging.getLogger(self.__class__.__name__).getChild(self.__class__.__name__)` produit `CenterFace.CenterFace` / `YuNet.YuNet`, alors que les autres modules utilisent `getLogger(__name__)`. Filtrage par module impossible. | Uniformiser sur `logging.getLogger(__name__)`. |
| ~~F033~~ | Dépendances et configuration | `pyproject.toml`, `uv.lock` | `RESOLVED` | — | *Aucune version épinglée, build non reproductible.* `uv.lock` fige l'arbre complet, `.python-version` fixe 3.12. Réserves reportées sur F068. | — |
| ~~F034~~ | Dépendances et configuration | `pyproject.toml:7-18` | `RESOLVED` | — | *Variantes `onnxruntime` commentées dans `requirements.txt`.* Les lignes commentées ont disparu ; le fond est traité par F067. | — |
| F035 | Dépendances et configuration | `pyproject.toml:7-18` | Moyenne | M | Quatre runtimes d'inférence coexistent pour trois modèles : `torch` (YOLO/CUDA), `openvino` (YOLO/CPU), `onnxruntime` (CenterFace), OpenCV DNN (YuNet). Coût d'installation et surface de bugs disproportionnés — `uv.lock` fait 283 Ko. | Décider si CenterFace et YuNet apportent encore quelque chose face à YOLO ; à défaut exporter les trois modèles en ONNX et ne garder qu'`onnxruntime`. |
| F036 | Décomposition architecturale | `4imask_anonymizer.py:28-169` | Moyenne | L | Constructeur de 140 lignes : garde-fou, configuration ffmpeg, et construction manuelle de 20 widgets, sans séparation entre disposition, état et raccordement des signaux. | Extraire `_build_ui()` et `_connect_signals()` — `check_authorization()` a déjà été sortie en révision 3. |
| F037 | Décomposition architecturale | `4imask_anonymizer.py:241-283` | Moyenne | M | Trois `QCheckBox` mutuellement exclusives avec exclusion réimplémentée à la main (cascade `if sender ==`), là où Qt fournit `QButtonGroup(exclusive=True)`. Duplication ×2 (modes et modèles), 43 lignes pour deux choix. | Remplacer par deux `QButtonGroup` exclusifs, ou par des `QComboBox` — la sémantique « un seul parmi trois » est celle d'un combo. |
| F038 | Décomposition architecturale | `4imask_anonymizer.py:269-283`, `:294-308` | Moyenne | S | `get_model_option` et `get_replacewith_option` mélangent lecture et effet de bord : elles retournent une valeur **et** mutent `self.worker`. Les handlers `toggled` les appellent uniquement pour l'effet de bord, en ignorant le retour. | Séparer en un accesseur pur et une méthode `_push_options_to_worker()`. |
| F039 | Décomposition architecturale | `apps/worker.py:69-88` | Moyenne | S | Cascade `if/elif` qui instancie un détecteur et force les deux autres à `None`, suivie de la cascade symétrique lignes 99-117. Ajouter un modèle demande de toucher deux endroits. | Interface commune `detect_and_mask(frame, mask_size, replacewith) -> np.ndarray` + dictionnaire `{'yolo': YOLOModel, …}`. |
| F040 | Décomposition architecturale | `apps/yunet.py:88-95` | Moyenne | S | `YuNet.scale_bb` duplique `apps/utils.py:67-74` et n'est appelée nulle part : code mort qui laisse croire à un second mécanisme de mise à l'échelle. | Supprimer. |
| F041 | Dette de typage | `apps/yolo.py:26` | Moyenne | S | `def detect_faces(self, image_path: str, ...)` reçoit en réalité un `np.ndarray` (`apps/worker.py:100`). L'annotation et le nom mentent tous deux sur le contrat. Signalé aussi par `ruff` (UP006 sur `List`). | Renommer en `frame: np.ndarray` et passer à `list[...]`. |
| F042 | Dette de typage | `apps/yunet.py:60-68` | Moyenne | S | `visualize` déclare `draw_scores`, `ovcolor`, `replaceimg`, `box_color`, `text_color` — aucun n'est utilisé (seul `fps` l'est, et n'est jamais passé). Cinq paramètres fantômes dans une signature publique. | Supprimer les paramètres inutilisés, ou les implémenter. |
| F043 | Dette de typage | `apps/worker.py:190-204` | Moyenne | S | `yunet_mechanism` reçoit `ellipse`, `draw_scores`, `replaceimg`, `mosaicsize` puis les **écrase** par des littéraux identiques dans l'appel à `visualize`. Les paramètres reçus sont ignorés. | Transmettre les paramètres reçus, ou les retirer de la signature. |
| F044 | Dette de typage | `apps/yolo.py:26`, `:47` | Moyenne | S | `max_width`/`max_height` (filtrage implémenté lignes 41-42) ne sont jamais renseignés par l'appelant ; `radius: int = 30` de `mask_faces` est reçu (valeur `20`) et jamais utilisé. | Câbler à l'UI si le filtrage est voulu, sinon supprimer les trois paramètres. |
| F045 | Performance | `apps/worker.py:132` | Moyenne | M | `frame_emited.emit(frame, rotate_code)` est émis pour **chaque** frame, y compris quand `pause_updates` est vrai côté UI : `update_frame` filtre à l'arrivée, mais la frame a déjà traversé la file inter-threads. Pendant une anonymisation avec écriture, `pause_updates` vaut `True` — 100 % des émissions sont jetées. | Tester un drapeau `emit_frames` côté worker, ou limiter à ~10 fps. |
| F046 | Performance | `apps/yolo.py:30` | Moyenne | S | `half=True` est passé inconditionnellement, y compris quand `self.device is None` (chemin OpenVINO/CPU) où la demi-précision n'est pas supportée. | `half=(self.device == "cuda")`. |
| F047 | Performance | `apps/yunet.py:69` | Moyenne | S | `output = image.copy()` par frame, alors que YOLO et CenterFace modifient en place. Une copie complète 1080p par frame là où les deux autres n'en font aucune. | Travailler en place, ou aligner les trois sur la copie explicite. |
| F048 | Dérive documentaire | `res/ffmpeg/bin/`, `4imask_anonymizer.py:340-341`, `:488-505` | Moyenne | S | Le répertoire nommé `res/ffmpeg/bin` ne contient **aucun** binaire ffmpeg — uniquement `libopenh264-1.8.0-linux64.4.so` et `openh264-1.8.0-win64.dll`, que `FFmpegPathManager` ajoute au `PATH`. Sous Windows cela sert à OpenCV pour H264 ; sous Linux, une bibliothèque partagée dans `PATH` (au lieu de `LD_LIBRARY_PATH`) n'a aucun effet. Le nommage et le message `"FFmpeg path in environment"` induisent en erreur. | Renommer `res/openh264/` et la classe en `OpenH264PathManager` ; utiliser `LD_LIBRARY_PATH` hors Windows. |
| F049 | Dérive documentaire | `4imask_anonymizer.py:533-536` | Moyenne | S | Le commentaire `# Keep only the last 10 files` surplombe un code qui en conserve 5. | Corriger le commentaire, ou extraire `MAX_LOG_FILES = 5`. |
| F050 | Incohérences | `apps/utils.py:13-21` vs `4imask_anonymizer.py:341`, `:477` | Moyenne | S | Deux mécanismes concurrents de résolution des chemins : `resource_path()` (basé sur `sys._MEIPASS`) et `os.path.dirname(os.path.abspath(__file__))` pour ffmpeg et la licence. Les deux fonctionnent sous PyInstaller *onefile* par coïncidence, mais divergeront en *onedir*. | Router les trois usages par `resource_path()`. |
| F051 | Incohérences | `apps/utils.py:19` | Moyenne | S | Hors PyInstaller, `resource_path` retombe sur `os.path.abspath(".")` : les modèles ne sont trouvés que si l'application est lancée depuis la racine du dépôt. `uv run 4imask_anonymizer.py` depuis un autre répertoire échoue au chargement du modèle. Également signalé par `ruff` (BLE001 sur le `except Exception` de la fonction). | Repli sur `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` et `except AttributeError` au lieu du blanket catch. |
| F052 | Décomposition architecturale | `4imask_anonymizer.py:370-383`, `:205-208`, `:346-347`, `:180-181`, `apps/yunet.py:70-76`, `apps/utils.py:7-10` | Faible | S | Six blocs de code commenté conservés, dont une implémentation alternative de 14 lignes au milieu de `update_frame`. L'historique git couvre ce besoin. | Supprimer. |
| F053 | Dérive documentaire | `README.md:35` | Faible | S | `git clone https://github.com/your-username/4imask.git` — placeholder du modèle jamais remplacé. | Mettre l'URL réelle. |
| F054 | Dérive documentaire | `README.md:13-21` | Faible | S | La section Prerequisites omet `ultralytics`, `torch`, `openvino` et `pyqtdarktheme`, tous présents dans `pyproject.toml` — dont `ultralytics`, seul contributeur AGPL et donc à l'origine de la licence du projet. | Renvoyer vers `pyproject.toml` plutôt que dupliquer la liste. |
| ~~F055~~ | Incohérences | `apps/worker.py:127`, `:147` | `RESOLVED` | — | *`out.write(frame) if self.write_output else None` : expression conditionnelle utilisée comme instruction, deux fois.* Remplacées par des `if` explicites lors de la réécriture de `run()`. | — |
| F056 | Incohérences | `apps/worker.py:69-88` | Faible | S | `self.yunet` est un attribut d'instance alors que `yolo_` et `centerface` sont des variables locales — asymétrie dictée par `yunet_mechanism` qui y accède via `self`. | Passer l'instance en paramètre et faire des trois des variables locales. |
| F057 | Incohérences | `4imask_anonymizer.py:493-496` | Faible | S | `set_ffmpeg_env_path` : branche `if platform.system() == "Windows"` dont les deux corps sont rigoureusement identiques. | Supprimer la condition. |
| F058 | Incohérences | `4imask_anonymizer.py:34` et `:44` | Faible | S | `setWindowTitle("4iMask Anonymizer")` appelé deux fois avec la même valeur. | Supprimer le second. |
| F059 | Incohérences | `apps/yunet.py` (ensemble) vs reste du code | Faible | S | Trois conventions coexistent : `snake_case`, `camelCase` (hérité d'OpenCV Zoo), et des commentaires alternant français et anglais. Depuis la révision 3, `pyproject.toml` exclut les deux fichiers vendored de `ruff`. | Ne **pas** uniformiser `yunet.py` (voir section dédiée) ; uniformiser la langue des commentaires. |
| F060 | Décomposition architecturale | `apps/yolo.py:24` | Faible | S | **Partiellement résolu :** `cv2.destroyAllWindows()` a disparu de `worker.py` lors de la réécriture de `run()`. Reste le `pass` orphelin en fin de `YOLOModel.__init__`, signalé par `ruff` (PIE790). | Supprimer. |
| F061 | Dépendances et configuration | `res/models/` | Faible | M | 23,4 Mo de modèles binaires versionnés sans Git LFS, dont `yolov11n-face.pt` (5,5 Mo) et son export OpenVINO (10,7 Mo) — le même réseau stocké deux fois. | Passer `res/models/` sous Git LFS, ou générer l'export OpenVINO au build depuis le `.pt`. La purge d'historique de la révision 3 était l'occasion idéale ; elle est passée. |
| F062 | Dépendances et configuration | `check_licenses.py:7` | Faible | S | Script orphelin : déclenche `pip install pip-licenses` dans l'environnement courant à l'exécution — en contradiction directe avec la migration `uv`, où l'environnement est géré par le lock. Référencé ni par le README ni par la CI. | Remplacer par `uv run --with pip-licenses piplicenses` dans un job de conformité, ou supprimer. |
| F063 | Dépendances et configuration | `pyinstaller_cmd.txt:1-7` | Faible | S | Quatre commandes de build empilées par ordre chronologique, sans indication de celle qui fait foi, et toutes invoquant `pyinstaller` hors de l'environnement `uv`. Le fichier fait maintenant doublon avec le workflow et la section *Compilation* du README, qui sont à jour. | Supprimer le fichier. |
| F064 | Dépendances et configuration | `*.py` (permissions) | Faible | S | **Requalifié :** les fichiers `.py` sont en mode 755 sans shebang (9 signalements `ruff` EXE002). Le dépôt étant sur un montage `fuseblk`, `chmod` est inopérant — la recommandation de la révision 2 ne fonctionnait pas. | `git update-index --chmod=-x <fichiers>` pour corriger le mode côté index, ou désactiver la règle EXE002 dans `[tool.ruff.lint]` si le montage rend le point sans objet. |
| F065 | Dérive documentaire | `apps/` (ensemble) | Faible | M | Aucune docstring dans `centerface.py`, `yunet.py`, `yolo.py` ni sur `AnonymizationWorker.run`. `authorization.py`, `compat.py` et `utils.py::resource_path` en ont. | Une docstring d'une ligne sur les quatre fonctions les plus denses, précisant le format de boîtes attendu (xyxy vs xywh — source d'erreur réelle, cf. `apps/yunet.py:84`). |
| ~~F066~~ | Dépendances et configuration | `.github/workflows/pyinstaller.yml:9-19` | `RESOLVED` | — | *Le workflow référençait `requirements.txt`, supprimé par la migration.* Remplacé par `astral-sh/setup-uv` + `uv sync --frozen --group dev`. | — |
| **F067** | Dépendances et configuration | `pyproject.toml:10` | Élevée | M | Seul `onnxruntime` (CPU) est déclaré. Les variantes `onnxruntime-gpu` / `-directml` / `-openvino` que le README annonce ont disparu **y compris à l'état de commentaire** : plus aucune trace n'indique comment activer l'accélération matérielle. CenterFace tourne systématiquement sur CPU ; la seule accélération restante est le chemin CUDA de `torch` pour YOLO. | Déclarer des extras `[project.optional-dependencies]` (`gpu`, `directml`, `openvino`) et documenter `uv sync --extra gpu`. |
| F068 | Dépendances et configuration | `pyproject.toml:8-17` | Moyenne | S | Les dix dépendances utilisent `>=` sans borne supérieure, avec des planchers alignés sur les toutes dernières versions. `uv.lock` protège la reproductibilité, mais tout `uv lock --upgrade` acceptera silencieusement une majeure suivante — sur `ultralytics` et `opencv-python`, historiquement porteurs de ruptures. Le cas est concret : l'ImportError de F078/F079 vient précisément d'un tel saut. | Passer les dépendances sensibles en `~=` (`opencv-python~=5.0`, `ultralytics~=8.4`, `pyside6~=6.11`). |
| F069 | Dérive documentaire | `pyproject.toml:3-4` vs `4imask_anonymizer.py:30` | Moyenne | S | **Mis à jour :** `version` est passée à `1.0.3` mais `self.version = "1.0.2"` reste codé en dur dans l'UI — les deux sources de vérité divergent désormais activement. `description = "Add your description here"` subsiste. | Renseigner `description`, et lire la version via `importlib.metadata.version("4imask")` au lieu de la coder en dur. |
| ~~F070~~ | Dette de tests | `pyproject.toml:20-37` | `RESOLVED` | — | *Aucun groupe de dépendances de développement.* Ajout de `[dependency-groups] dev` avec `pytest`, `ruff`, `pip-audit`, `pyinstaller`, plus `[tool.pytest.ini_options]` et `[tool.ruff]` excluant le code vendored. | — |
| F071 | Hygiène de sécurité | `pyproject.toml` | Moyenne | S | Ni `license` ni `authors` déclarés, alors que le projet est sous AGPL-3.0 par transitivité d'`ultralytics`. Un paquet construit depuis ce `pyproject.toml` ne porterait aucune métadonnée de licence — précisément ce que l'AGPL exige de propager. | `license = "AGPL-3.0-only"`, `license-files = ["LICENSE"]`, plus `authors`. |
| ~~F072~~ | Dépendances et configuration | `pyproject.toml`, `uv.lock`, `.python-version` | `RESOLVED` | — | *Les trois fichiers de la migration étaient untracked et la suppression de `requirements.txt` non indexée : `git clone` donnait un projet sans moyen d'installer ses dépendances.* Committés dans `9eea236`. | — |
| ~~F073~~ | Dérive documentaire | `README.md:32-56` | `RESOLVED` | — | *Les instructions référaient à `requirements.txt` et à `python 4imask_anonymizer.py`.* Remplacées par `uv sync` / `uv run`, avec une section Développement et une section Compilation à jour. | — |
| ~~F074~~ | Gestion d'erreurs | `apps/worker.py:127-131` | `RESOLVED` | — | *La valeur de retour de `out.write()` était jetée, laissant un fichier vide passer pour un succès.* Testée explicitement (`is False`) et convertie en `RuntimeError` détaillant les dimensions en cause. | — |
| ~~F075~~ | Dépendances et configuration | `.github/workflows/pyinstaller.yml:12-16` | `RESOLVED` | — | *`python_ver: '3.11.9'` contredisait `requires-python = ">=3.12"`.* La version vient désormais de `.python-version` via `setup-uv` : la divergence est structurellement impossible. | — |
| F076 | Dépendances et configuration | `pyproject.toml:16` | Moyenne | M | `torch>=2.13.0` sans `[[tool.uv.index]]` ni `[tool.uv.sources]` : `uv sync` installe la variante par défaut de PyPI — sous Linux, la roue CUDA complète (plusieurs Go) même sur une machine sans GPU, alors que `apps/yolo.py:14-21` bascule sur OpenVINO dans ce cas. | Déclarer l'index PyTorch CPU par défaut, avec un extra `gpu` pointant sur `cu126` (à combiner avec F067). |
| F077 | Dépendances et configuration | `pyproject.toml` | Faible | S | Ni `[build-system]` ni `[project.scripts]` : le projet n'est pas installable et n'expose pas de commande. `uv run 4imask` n'existe pas, ce qui contraint à `uv run 4imask_anonymizer.py` — donc à dépendre du répertoire courant, ce qui déclenche F051. | Ajouter `[project.scripts]` et un `[build-system]` hatchling, ou déclarer explicitement `[tool.uv] package = false`. |
| ~~F078~~ | Décomposition architecturale | `apps/__init__.py:10` | `RESOLVED` | — | **`NEW` puis résolu en révision 3.** `apps/compat.py` n'était importé que depuis la première ligne de `4imask_anonymizer.py` : comme `apps/worker.py` importe PySide6 avant `apps.yolo`, tout point d'entrée autre que le fichier principal échouait sur `ImportError: cannot import name 'YOLO' from 'ultralytics'`. Découvert en écrivant les tests, qui ne pouvaient pas être collectés. L'import a été déplacé dans `apps/__init__.py`, ce qui le rend inconditionnel. | — |
| **F079** `NEW` | Dépendances et configuration | `apps/compat.py:16-27` | Moyenne | S | Le correctif `six._SixMetaPathImporter._path` est un contournement d'un bug d'interaction entre PySide6 (hook d'import shiboken), `six` et CPython 3.12. Il n'est **borné à aucune version**, ne référence **aucun ticket amont**, et n'a **aucun test de non-régression** : le jour où PySide6 ou `six` corrigera, rien ne signalera que le patch est devenu inutile, et il restera indéfiniment dans un chemin d'import critique. Le lien avec F068 est direct : c'est une conséquence des bornes de version ouvertes. | Ajouter en commentaire le lien vers le ticket amont, et un test qui importe `apps.worker` dans un sous-processus **sans** `apps.compat` — il échoue tant que le bug amont existe, et signalera sa disparition. |
| **F080** `NEW` | Gestion d'erreurs | `4imask_anonymizer.py:171-187`, `:31-32` | Moyenne | S | `check_authorization` affiche une `QMessageBox.warning` **modale et bloquante** depuis le constructeur, avant que la fenêtre principale ne soit affichée, puis `__init__` appelle `sys.exit()` — une `SystemExit` levée depuis un constructeur, que rien n'attrape. Comportement hérité, mais mis en évidence en révision 3 : un test automatisé du refus se bloque indéfiniment sur la boîte modale. | Remonter la décision dans `mainloop()` : construire la fenêtre, tester `window.check_authorization()`, afficher le message et sortir proprement avant `window.show()`. Rend aussi le chemin de refus testable. |
| **F081** `NEW` | Dette de tests | `.github/workflows/` | Élevée | S | Les 34 tests ajoutés en révision 3 **ne sont exécutés par aucun workflow**. Le seul workflow de build se déclenche sur tag `v*` et ne fait que construire l'exécutable ; le workflow SLSA ne teste rien. Une régression sur `draw_detections` ou le dimensionnement de sortie ne serait détectée par personne. | Ajouter un workflow `on: [push, pull_request]` : `setup-uv`, `uv sync --frozen --group dev`, puis `uv run pytest` et `uv run ruff check`. C'est le complément indispensable de F020. |

---

## Top 5 — si vous ne corrigez rien d'autre

Le Top 5 de la révision 2 est traité par le commit `9eea236`. Voici le suivant, recalculé.

### 1. F081 — Faire exécuter les tests par la CI

Les 34 tests écrits en révision 3 ne servent à rien tant que personne ne les lance. C'est le constat au meilleur rapport effort/valeur du rapport, et il conditionne tous les autres : sans exécution automatique, chaque correction qui suit repose sur la discipline manuelle.

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - run: uv run ruff check
      - run: uv run pytest
```

Note : les tests actuels n'ont besoin ni de GPU ni d'affichage — `apps/utils.py` et `apps/authorization.py` n'importent pas Qt, et `tests/test_worker.py` n'instancie pas de `QApplication`. Un runner `ubuntu-latest` standard suffit.

### 2. F008 — Le workflow SLSA signe des artefacts factices

C'est désormais le constat le plus grave du dépôt, et le seul qui produise une garantie **fausse** plutôt qu'un défaut. Un utilisateur qui vérifie la provenance SLSA d'une release obtient une attestation valide pour deux fichiers texte contenant « artifact1 » et « artifact2 ».

Deux issues, aucune intermédiaire acceptable : soit le workflow récupère l'artefact réellement produit par `pyinstaller.yml` et calcule son empreinte, soit il est supprimé. Vu que le build tourne sur `windows-latest` et le SLSA sur `ubuntu-latest`, la première option demande de chaîner les deux workflows via `workflow_run` ou de fusionner les jobs. Si cet effort n'est pas prévu à court terme, **supprimez le fichier** : une attestation mensongère est pire que pas d'attestation.

### 3. F012 + F016 + F019 — Les trois bugs restants, tous en effort S

Aucun n'est structurel, tous ont un correctif d'une à deux lignes, et ils sont indépendants.

```diff
--- a/apps/worker.py
+++ b/apps/worker.py
-                output_name = (self.video_path).split(".")[0] + "_anonymized_" + self.output_format.lower() + ".avi"
+                base, _ = os.path.splitext(self.video_path)
+                output_name = f"{base}_anonymized_{self.output_format.lower()}.avi"
```

```diff
--- a/4imask_anonymizer.py
+++ b/4imask_anonymizer.py
     def update_mask_size(self, value):
         value = round(value, 2)
         self.logger.info(value)
+        self.mask_size = value
         if hasattr(self, 'worker'):
             self.worker.mask_size = value
-        else:
-            self.mask_size = round(value, 2)
```

```diff
     def stop_anonymization(self):
         if hasattr(self, 'worker'):
             self.worker.stop()
+            self.worker.wait()
```

`os` est déjà importé dans `apps/worker.py`. Le troisième correctif rend `stop_anonymization` cohérent avec `closeEvent` et `stop_preview`, qui appellent déjà `wait()`.

### 4. F023 + F024 — Sortir la configuration et le chargement du modèle de `run()`

Les deux constats Élevée restants sur `apps/worker.py` ont la même racine : le worker se configure lui-même à partir d'attributs publics que l'UI mute quand elle veut, y compris pendant l'exécution. En conséquence il recharge le modèle à chaque démarrage, et rien ne garantit la cohérence des options d'une frame à l'autre.

```python
# apps/detectors.py
class Detector(Protocol):
    def detect_and_mask(self, frame: np.ndarray, mask_size: float,
                        replacewith: ReplaceWith) -> np.ndarray: ...

DETECTORS = {'yolo': YOLOModel, 'centerface': CenterFace, 'yunet': YuNet}
```

```diff
-        self.worker = AnonymizationWorker(self.video_path, output_format, self.mask_size, write_output=True)
-        self.worker.model = model
-        self.worker.replacewith = replacewith
+        detector = self._get_cached_detector(model)      # instancie une fois, réutilise ensuite
+        self.worker = AnonymizationWorker(
+            self.video_path, output_format, self.mask_size,
+            detector=detector, replacewith=ReplaceWith(replacewith), write_output=True)
```

Effet secondaire utile : le worker devient testable sans modèle réel, via un détecteur factice. C'est ce qui débloque le test d'intégration manquant de F020.

### 5. F067 + F076 — Rendre l'accélération matérielle atteignable

Aujourd'hui, une installation standard donne `onnxruntime` CPU **et** la roue CUDA complète de PyTorch — le pire des deux mondes : plusieurs gigaoctets téléchargés, et CenterFace comme YuNet tournant malgré tout sur CPU. Le README promet trois modes d'accélération dont aucun n'est atteignable.

```toml
[project.optional-dependencies]
gpu       = ["onnxruntime-gpu>=1.28"]
directml  = ["onnxruntime-directml>=1.28"]
openvino  = ["onnxruntime-openvino>=1.28"]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cpu" }
```

Puis documenter `uv sync --extra gpu` dans le README, en face de chaque profil matériel.

---

## Gains rapides

Effort S, gravité Moyenne ou supérieure, sur les constats **ouverts**.

- [ ] **F081** — Workflow `tests.yml` sur `push`/`pull_request` (le plus rentable).
- [ ] **F008** — Réparer ou supprimer le workflow SLSA.
- [ ] **F012** — `os.path.splitext` au lieu de `split(".")[0]` (`apps/worker.py:66`).
- [ ] **F016** — Toujours écrire `self.mask_size` (`4imask_anonymizer.py:285-291`).
- [ ] **F019** — Ajouter `self.worker.wait()` (`4imask_anonymizer.py:324`).
- [ ] **F017** — `os.makedirs(exist_ok=True)` dans un `try/except OSError` (`4imask_anonymizer.py:522`).
- [ ] **F014 / F015** — Garder les deux divisions (`apps/worker.py:134`, `:140`).
- [ ] **F026** — Remonter `import onnx` / `import onnxruntime` en tête de `apps/centerface.py`.
- [ ] **F028** — Déplacer `setText(basename(...))` dans la branche de succès (`4imask_anonymizer.py:194`).
- [ ] **F031** — Supprimer `file_handler.close()` (`4imask_anonymizer.py:560`).
- [ ] **F032** — Uniformiser les loggers sur `getLogger(__name__)`.
- [ ] **F040** — Supprimer `YuNet.scale_bb`, code mort (`apps/yunet.py:88-95`).
- [ ] **F041** — Renommer `image_path: str` en `frame: np.ndarray` (`apps/yolo.py:26`).
- [ ] **F046** — `half=(self.device == "cuda")` (`apps/yolo.py:30`).
- [ ] **F049** — Corriger le commentaire « last 10 files » (`4imask_anonymizer.py:533`).
- [ ] **F025** — Supprimer le `QTimer` mort et sa reconnexion cumulative.
- [ ] **F069** — Renseigner `description`, lire la version via `importlib.metadata`.
- [ ] **F071** — Déclarer `license = "AGPL-3.0-only"` et `license-files`.
- [ ] **F068** — Passer `opencv-python`, `ultralytics` et `pyside6` en `~=`.
- [ ] **F079** — Ajouter un test de non-régression sur le shim `apps/compat.py`.
- [ ] **F080** — Remonter la décision d'autorisation dans `mainloop()`.

---

## Ce qui semble mauvais mais ne l'est pas

**`QFileDialog.Options()` (`4imask_anonymizer.py:193`) — constat F027 de la révision 1, invalidé.** J'avais signalé cette API Qt5 comme supprimée des PySide6 récents. Vérification sur PySide6 6.11.1 : `QFileDialog.Options()` retourne `<Option: 0>` et l'appel passe sans erreur. L'argument est redondant, mais il ne casse rien. C'est le type de constat que seule l'exécution permet de trancher.

**`res/.dummy` reste sur le disque après la purge, et c'est voulu.** Le fichier est untracked et gitignoré : il sert de liste locale pour le développement, et sa présence ne réintroduit aucune fuite. Le supprimer ferait basculer l'environnement de développement en mode « aucune restriction », ce qui est le comportement par défaut mais rendrait le chemin de refus impossible à exercer localement.

**Le garde-fou autorise le domaine indéterminable, ce qui « désactive » le contrôle hors Windows.** C'est délibéré et documenté dans la docstring de `apps/authorization.py`. La notion de domaine Windows n'a pas d'équivalent Linux ou macOS ; bloquer par défaut y rendrait l'application inutilisable, ce qui était précisément le bug F007. Le contrôle vise un parc Windows d'entreprise, pas une frontière de sécurité.

**`apps/centerface.py` et `apps/yunet.py` sont du code tiers vendored.** `yunet.py` porte son en-tête de copyright OpenCV Zoo et `centerface.py` est dérivé de ORB-HD/deface (crédité dans le README). Leur `camelCase`, leur NMS en Python pur, leur boucle de décodage par pixel sont autant de choses qu'un audit isolé signalerait — et qu'il ne faut pas corriger : les uniformiser supprime la traçabilité avec l'amont. La révision 3 a formalisé ce choix en les excluant de `ruff` dans `pyproject.toml`.

**Le NMS en O(n²) n'est pas un problème de performance.** `n` est le nombre de visages par frame — typiquement 1 à 10. Le coût réel est trois ordres de grandeur sous celui de l'inférence. Les vrais goulots sont F023 (rechargement du modèle) et F045 (émissions jetées).

**`@lru_cache` sur `shape_transform` (`apps/centerface.py:127`) semble inutile** — les arguments sont identiques à chaque frame, donc le cache « ne fait rien ». C'est l'intérêt : il évite deux `ceil` et deux divisions par frame, et `maxsize=128` empêche toute fuite.

**La coexistence de trois détecteurs n'est pas de l'indécision.** YOLO (torch/CUDA), CenterFace (onnxruntime) et YuNet (OpenCV DNN) couvrent trois profils matériels distincts. Sur un parc hétérogène, c'est une redondance justifiée. F035 questionne le coût d'installation, pas le principe.

**Sous-classer `QThread` avec `run()` surchargé est l'anti-pattern Qt classique.** Il ne s'applique pas ici : le worker ne reçoit aucun signal entrant, seulement deux drapeaux booléens lus dans sa propre boucle. La refonte en `moveToThread` ajouterait une boucle d'événements pour zéro bénéfice. La révision 3 a d'ailleurs conforté ce choix : ajouter `error_occurred` en signal sortant a suffi à rendre les erreurs visibles.

**La faute d'orthographe dans `frame_emited` (`apps/worker.py:20`)** touche quatre sites d'appel pour un gain nul. La révision 3 aurait été l'occasion, mais mélanger un renommage à une réécriture de `run()` aurait rendu le diff illisible. À faire seule, plus tard.

**`imutils` pour un unique appel à `resize`** ressemble à une dépendance superflue. Elle est désormais load-bearing d'une manière non évidente : c'est son comportement de préservation du ratio qui définit les dimensions de sortie, et `tests/test_worker.py` verrouille cet invariant. La remplacer par `cv2.resize` change le contrat de sortie — ce n'est plus un nettoyage, c'est une décision produit sur le recadrage.

**Le mode d'écriture en `.avi` avec un fourcc `h264`/`mp4v`** semble incohérent et n'a volontairement pas été retenu comme constat. AVI accepte ces deux codecs, et le choix évite les problèmes de finalisation d'atome MP4 en cas d'arrêt brutal — ce qui, vu F019, reste prudent.

---

## Questions ouvertes pour le mainteneur

1. **`NEW` — La purge d'historique doit-elle être complétée côté GitHub ?** Le dépôt local est propre, mais le force-push n'a pas été fait, et trois points subsistent : les forks éventuels conservent les objets purgés ; GitHub garde les objets orphelins joignables par URL de SHA tant que son GC serveur n'a pas tourné (un ticket au support est nécessaire pour un dépôt public) ; et le secret `AUTHORIZED_DOMAINS` doit être créé avant la prochaine release, sinon le binaire sera construit sans restriction (le workflow émet un `::warning::` mais n'échoue pas).

2. **Le garde-fou d'usage doit-il rester ?** Maintenant qu'il est externalisé et documenté comme non-sécuritaire, sa valeur est essentiellement dissuasive. S'il n'a pas d'utilité contractuelle réelle, le supprimer retirerait F006 et F080 d'un coup.

3. **Le commit `c56d0b3 V1.0.2 ffmpeg conversion` référence une conversion introuvable dans le code.** Binaire ffmpeg jamais committé (`res/ffmpeg/` ne contient que openh264), étape abandonnée, ou le terme désigne-t-il le backend `CAP_FFMPEG` d'OpenCV ?

4. **La sortie en `.avi` est-elle un choix ou un contournement ?** Un commentaire conservait une version `.mkv` désactivée, et le commit `61e4824 try mp4v` suggère plusieurs tentatives. Y a-t-il un problème connu avec MP4 à documenter plutôt qu'à « corriger » ?

5. **`NEW` — Quelle est la sortie attendue pour une source non 16:9 ?** Depuis la correction de F001, une source 4:3 en « 480p » produit du 854×640 : la largeur est respectée, la hauteur suit le ratio. C'est cohérent et sans perte, mais « 480p » ne décrit alors plus la sortie. Faut-il renommer le sélecteur (« largeur cible »), ou recadrer/letterboxer pour obtenir exactement la définition annoncée ?

6. **La prévisualisation doit-elle réexécuter le pipeline complet ?** `play_preview` crée un `AnonymizationWorker` avec `write_output=False` : inférence intégrale à pleine résolution pour un affichage 720×480.

7. **Que doit faire l'application quand aucun modèle ou aucun mode n'est coché ?** Les accesseurs retournent `'none'`, que `run()` traite en produisant une vidéo **redimensionnée mais non anonymisée**, sous un nom contenant `_anonymized_`. Mode « transcodage seul » voulu, ou situation à bloquer ? Le risque est réel pour un outil RGPD.

8. **CenterFace et YuNet servent-ils encore ?** L'UI coche YOLO par défaut et les commits récents ne touchent que ce chemin. Leur retrait supprimerait `onnxruntime`, `onnx` et 7,5 Mo de modèles — et réglerait une partie de F067.

9. **`NEW` — Le shim `apps/compat.py` a-t-il un ticket amont ?** S'il vient d'un bug déjà signalé chez PySide6, `six` ou `ultralytics`, le lien permettrait de borner sa durée de vie. Sinon, vaut-il la peine de le remonter — c'est un bug d'interaction qui touchera d'autres projets Qt + ultralytics sur Python 3.12.

10. **Le projet doit-il être installable comme paquet ?** F077 en dépend : `[project.scripts]` réglerait aussi F051, mais impose un `[build-system]` et un renommage du module d'entrée (`4imask_anonymizer` commence par un chiffre — importable, mais inhabituel).
