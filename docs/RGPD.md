# Volet RGPD — 4iMask Anonymizer

**Version du document :** 1.0
**Version applicative couverte :** 4iMask Anonymizer 1.1.0
**Textes de référence :** Règlement (UE) 2016/679 (RGPD), loi n° 78-17 « Informatique et Libertés » modifiée
**English version:** [GDPR.md](./GDPR.md)

---

## 1. Objet

4iMask Anonymizer est un logiciel de bureau qui détecte les visages présents dans un
fichier vidéo et les masque (floutage, mosaïque ou pavé opaque) afin de produire une
copie moins identifiante de la vidéo d'origine. Une option complémentaire
(*Back-facing (pose)*) permet de masquer également les têtes des personnes vues de dos,
qu'aucun détecteur de visage ne peut trouver.

> **Périmètre du masquage : les visages et les têtes, rien d'autre.**
> 4iMask masque les visages détectés, et les têtes lorsque l'option de pose est activée.
> Il ne recherche, ne détecte et ne masque aucun autre élément identifiant : silhouette,
> plaque d'immatriculation, badge, écran, document, tatouage, signe distinctif restent
> visibles dans la vidéo produite. Cette limite est structurelle, pas un défaut de
> réglage : elle conditionne l'ensemble de l'analyse qui suit, et en particulier la
> section 6.

Ce document décrit :

- les traitements de données à caractère personnel réalisés **par le logiciel lui-même** ;
- ce que le logiciel ne fait pas ;
- les **limites** de l'anonymisation produite, qui conditionnent la qualification
  juridique du fichier de sortie ;
- les obligations qui restent à la charge de l'organisation utilisatrice.

Il ne constitue pas un conseil juridique et ne remplace pas l'analyse à mener par le
responsable de traitement ou son délégué à la protection des données (DPO).

---

## 2. Rôles et responsabilités

| Acteur | Rôle | Justification |
|---|---|---|
| Organisation qui installe et utilise 4iMask | **Responsable de traitement** (art. 4.7) | Elle détermine les finalités (pourquoi ces vidéos sont anonymisées) et les moyens (quel poste, quelles vidéos, quelle conservation). |
| 4iTEC, éditeur du logiciel | **Fournisseur d'outil** | L'éditeur ne reçoit, n'héberge et ne consulte aucune donnée. Il ne traite pas de données pour le compte du responsable de traitement : la relation ne relève donc pas de l'article 28 (sous-traitance) au titre de l'usage du logiciel. |
| Personne filmée | **Personne concernée** (art. 4.1) | Elle exerce ses droits auprès du responsable de traitement, pas auprès de l'éditeur. |

Le traitement s'exécute **intégralement sur le poste de l'utilisateur**. Aucune
convention de sous-traitance n'est requise pour le seul usage du logiciel.

---

## 3. Données traitées par l'application

| Catégorie | Contenu | Emplacement | Conservation | Finalité |
|---|---|---|---|---|
| Contenu vidéo source | Images pouvant comporter des personnes physiques identifiables (art. 4.1) | Fichier choisi par l'utilisateur, laissé **inchangé** | Sous le contrôle exclusif de l'utilisateur | Détection puis masquage des visages et des têtes |
| Vidéo de sortie | Copie redimensionnée, visages et têtes détectés masqués, **sans piste audio** | Même dossier que la source, suffixe `_anonymized_<format>` | Sous le contrôle exclusif de l'utilisateur | Livrable du traitement |
| Points de posture (option *pose*) | Coordonnées de points corporels servant à situer la tête d'une personne vue de dos | Mémoire vive uniquement | Le temps du traitement de l'image | Placer le masque là où le visage n'est pas visible |
| Journaux techniques | Horodatage, **chemin complet** du fichier traité, modèle de détection, option de masquage, taille de masque, erreurs | Sous-dossier `logs/` du répertoire de lancement | Rotation automatique : les 5 fichiers les plus récents sont conservés, les autres supprimés à chaque démarrage | Diagnostic technique |
| Nom de domaine Windows | Variable d'environnement `USERDOMAIN`, lue au démarrage | Mémoire vive uniquement, **non journalisée, non transmise** | Durée d'exécution | Garde-fou d'usage (voir section 11) |
| Préférences d'affichage | Langue choisie et indicateur « notice de confidentialité lue » | Registre Windows / fichier de configuration utilisateur (`QSettings`) | Jusqu'à désinstallation ou effacement manuel | Afficher l'information dans la bonne langue et ne pas la répéter à chaque lancement |

**Traitement en mémoire :** chaque image est décodée, analysée puis réécrite image par
image. Aucune image intermédiaire, aucune vignette, aucune coordonnée de visage et aucun
point de posture ne sont écrits sur le disque.

---

## 4. Ce que l'application ne fait pas

- **Aucune connexion réseau.** Ni envoi de vidéo, ni télémétrie, ni statistiques
  d'usage, ni recherche de mise à jour, ni compte utilisateur.
- **Aucune identification de personne.** Les modèles embarqués (YOLOv11n-face,
  CenterFace, YuNet, et le modèle de pose YOLO11n) *localisent* des visages, des
  personnes et des points de posture dans l'image. Ils ne calculent aucun gabarit
  biométrique, ne comparent aucun visage à une base de référence et ne conservent aucune
  empreinte. Voir la section 5.
- **Aucun apprentissage.** Les modèles sont figés et exécutés localement ; vos vidéos
  ne servent ni à les entraîner, ni à les améliorer, et ne sont transmises à aucun
  éditeur de modèle.
- **Aucune suppression automatique.** Le fichier source n'est ni modifié ni effacé :
  sa suppression relève de la politique de conservation du responsable de traitement.

---

## 5. Détection de visages ≠ traitement biométrique

La qualification de l'article 9.1 du RGPD (« données biométriques aux fins d'identifier
une personne physique de manière unique ») repose sur la **finalité d'identification**.

4iMask réalise une **détection** : le modèle répond à la question « y a-t-il un visage à
cet endroit de l'image ? ». Il ne produit pas de gabarit, ne réalise aucune comparaison
et ne permet pas de reconnaître qui est la personne. Le traitement réalisé par le
logiciel **ne relève donc pas de l'article 9.1**, et sa finalité — réduire
l'identifiabilité — va dans le sens de la minimisation (art. 5.1.c).

Le même raisonnement vaut pour l'option de pose. Les points de posture qu'elle calcule
pourraient, dans un autre usage, servir à identifier une personne à sa démarche ; ce
n'est pas le cas ici. Ils sont calculés image par image, exploités uniquement pour placer
un masque, jamais agrégés en séquence, jamais comparés et jamais conservés. La finalité
d'identification unique, qui seule déclencherait l'article 9.1, est absente.

Les **images sources**, elles, restent des données à caractère personnel au sens de
l'article 4.1 dès qu'une personne y est identifiable, et le traitement consistant à les
lire relève pleinement du RGPD.

À toutes fins utiles : 4iMask n'est pas un système d'identification biométrique à
distance au sens du règlement (UE) 2024/1689 sur l'intelligence artificielle.

---

## 6. Portée et limites de l'anonymisation produite

> ⚠️ **Point central.** Le fichier produit par 4iMask ne peut pas être présumé
> « anonyme » au sens du considérant 26 du RGPD sans contrôle préalable.

### 6.1 La détection n'est pas exhaustive

Aucun modèle de détection n'atteint 100 % de rappel. Sont fréquemment manqués :

- les visages de profil ou de dos partiel ;
- les visages très petits (personne éloignée, vidéo redimensionnée en 360p) ;
- les visages flous, sous-exposés, en contre-jour ou en mouvement rapide ;
- les visages partiellement occultés (masque, casque, main, reflet).

L'option *Back-facing (pose)* couvre spécifiquement les personnes de dos, que les trois
détecteurs de visage ne peuvent pas trouver. Elle s'ajoute au détecteur de visage sans le
remplacer, et ralentit le traitement. **Elle est désactivée par défaut** : si la scène
comporte des personnes filmées de dos, elle doit être activée explicitement.

Le redimensionnement appliqué avant détection (360p à 1080p) dégrade mécaniquement la
détection des visages lointains : **privilégier la résolution la plus élevée** lorsque
la scène comporte des personnes en arrière-plan.

### 6.2 Le masquage n'est pas également robuste selon l'option

| Option | Robustesse | Remarque |
|---|---|---|
| **Mask** (pavé opaque) | La plus élevée | L'information sous le pavé est détruite. |
| **Mosaic** (pixellisation) | Moyenne | Une pixellisation grossière conserve des informations exploitables par reconstruction. |
| **Blur** (flou) | La plus faible | Un flou léger peut être partiellement inversé ; augmenter la taille de masque renforce l'effet sans le garantir. |

Pour une diffusion externe ou une publication, l'option **Mask** est recommandée.

L'option de pose déduit la position de la tête à partir de la posture. Lorsque celle-ci
ne permet pas de la situer, c'est la partie haute de la personne qui est masquée : le
masque peut alors couvrir plus que la tête. Ce sur-masquage est volontaire — laisser une
tête visible est plus dommageable qu'en masquer un peu trop.

### 6.3 Le masquage ne porte que sur les visages et les têtes

**4iMask ne masque que les visages détectés, et les têtes lorsque l'option de pose est
activée.** Aucun autre élément identifiant n'est recherché ni traité — ni
automatiquement, ni par option de configuration. Restent intacts dans la vidéo de
sortie :

- silhouette, démarche, corpulence, coiffure, vêtements distinctifs ;
- tatouages, cicatrices, prothèses, signes religieux visibles ;
- plaques d'immatriculation, badges, écrans, documents, courriers, étiquettes ;
- éléments de contexte permettant une ré-identification par recoupement (lieu, date,
  effectif restreint, poste de travail identifiable).

Le masquage de ces éléments, lorsqu'il est nécessaire, doit être réalisé **manuellement**
dans un logiciel de montage : aucune évolution de réglage de 4iMask ne le fera.

La piste audio, en revanche, **n'est pas reprise** dans le fichier de sortie : les voix
sont de fait supprimées.

### 6.4 Conséquence juridique

Le résultat constitue, en l'état, une **réduction du risque de ré-identification** et
non une anonymisation irréversible au sens du considérant 26. Tant qu'une
ré-identification reste raisonnablement possible compte tenu des moyens disponibles, le
fichier de sortie **demeure une donnée à caractère personnel** et reste soumis au RGPD :
base légale, durée de conservation, sécurité, droits des personnes.

**Procédure recommandée avant toute diffusion :**

1. visionner intégralement la vidéo produite ;
2. vérifier l'absence de visage ou de tête non masqués, en particulier lors des
   changements de plan, des entrées de champ, des mouvements rapides et pour les
   personnes filmées de dos ;
3. vérifier les éléments identifiants listés au 6.3 ;
4. en cas de doute, retraiter en résolution supérieure ou en option **Mask**, ou
   compléter par un masquage manuel dans un logiciel de montage ;
5. tracer ce contrôle si la vidéo est destinée à une diffusion large.

---

## 7. Obligations de l'organisation utilisatrice

Le logiciel est un moyen technique ; la conformité relève du responsable de traitement.
Points à couvrir :

- **Base légale** (art. 6) du traitement initial des vidéos *et* de leur anonymisation :
  intérêt légitime, obligation légale, mission d'intérêt public ou consentement selon le
  contexte. L'anonymisation est le plus souvent une mesure de minimisation adossée au
  traitement principal.
- **Information des personnes filmées** (art. 12 à 14) : au moment de la captation, par
  affichage sur site, note de service ou mention contractuelle.
- **Registre des traitements** (art. 30) : y décrire l'usage de 4iMask comme mesure
  technique du traitement concerné.
- **Analyse d'impact — AIPD** (art. 35) : requise notamment en cas de vidéosurveillance
  systématique d'une zone accessible au public, de traitement à grande échelle ou de
  surveillance de salariés. L'usage de 4iMask constitue alors une mesure de réduction du
  risque à documenter dans l'AIPD.
- **Limitation de conservation** (art. 5.1.e) : définir une durée pour les vidéos
  sources et **supprimer les originaux** une fois la version masquée validée, si la
  finalité ne justifie plus leur conservation.
- **Sécurité** (art. 32) : les fichiers source et de sortie résident sur le poste de
  travail. Chiffrement du disque, contrôle d'accès au poste et aux dossiers de travail,
  et nettoyage périodique du dossier `logs/` (il contient les chemins et donc les noms
  des fichiers traités).
- **Violation de données** (art. 33-34) : la diffusion d'une vidéo insuffisamment
  masquée constitue une violation de données à caractère personnel et doit être traitée
  comme telle.

---

## 8. Droits des personnes concernées

Les droits d'accès, de rectification, d'effacement, de limitation et d'opposition
(art. 15 à 22) s'exercent **auprès du responsable de traitement**, c'est-à-dire de
l'organisation qui détient les vidéos.

L'éditeur du logiciel ne détenant aucune donnée, il n'est en mesure de répondre à aucune
demande d'exercice de droits et ne peut ni retrouver, ni supprimer une vidéo.

---

## 9. Sécurité

- Traitement local, sans exposition réseau introduite par l'application.
- Les modèles de détection sont embarqués dans le livrable : aucun téléchargement au
  premier lancement, donc aucune dépendance à un dépôt distant à l'exécution.
- Le logiciel n'élève pas ses privilèges et n'écrit qu'aux emplacements décrits en
  section 3.
- Les journaux ne contiennent ni image, ni coordonnée de visage, ni identifiant de
  personne — mais ils contiennent le **chemin complet** des fichiers traités, lequel
  peut révéler un nom, un numéro de dossier ou un site. Ce dossier doit être traité avec
  le même niveau de protection que les vidéos elles-mêmes.

---

## 10. Sous-traitance et transferts hors Union européenne

- **Sous-traitants :** aucun.
- **Transferts hors UE :** aucun.
- **Services tiers appelés à l'exécution :** aucun.

---

## 11. Points d'attention connus

Éléments identifiés qui méritent une décision du responsable de traitement :

1. **Journalisation du chemin complet.** Le nom du fichier vidéo apparaît en clair dans
   `logs/`. Si les noms de fichiers comportent des données personnelles (nom de
   personne, numéro de dossier), envisager de ne journaliser que le nom de base ou de
   désactiver la journalisation sur les postes concernés.
2. **Emplacement du dossier `logs/`.** Il est créé dans le répertoire de lancement de
   l'application, et non dans le profil utilisateur : sa localisation dépend donc du
   raccourci utilisé. À vérifier lors du déploiement pour garantir son inclusion dans la
   politique de purge.
3. **Garde-fou d'usage par `USERDOMAIN`.** Le périmètre autorisé est défini par une liste
   de domaines Windows écrite dans le livrable au moment du build, depuis un secret du
   dépôt ; elle n'est pas versionnée. Ce mécanisme relève du contrôle d'usage interne et
   non de la sécurité des données : la liste voyage dans le binaire et la variable
   d'environnement lue est modifiable par l'utilisateur. Il ne protège pas les vidéos et
   ne doit pas être présenté comme une mesure de sécurité au sens de l'article 32.
4. **Fichier de sortie écrit à côté de la source.** Si le dossier source est un partage
   réseau ou un espace largement accessible, la vidéo produite y est déposée avec les
   mêmes droits d'accès. Prévoir un dossier de travail dédié.

---

## 12. Information affichée dans l'application

Conformément au principe de transparence (art. 5.1.a), l'application informe
l'utilisateur directement dans l'interface :

- un **bandeau permanent** en haut de la fenêtre indique que le masquage porte
  uniquement sur les visages et les têtes, que le traitement est local et que la vidéo
  produite doit être contrôlée avant diffusion ;
- une **notice détaillée** s'affiche au premier lancement (et à chaque évolution de fond
  de cette notice), reprenant ce qui est traité, le périmètre limité aux visages, ce qui
  est écrit sur le disque, ce que l'application ne fait pas et les limites du masquage ;
- le lien **« Confidentialité / RGPD »** en bas de fenêtre permet de rouvrir cette
  notice à tout moment et d'ouvrir le présent document ;
- un **sélecteur de langue** (français / anglais) permet d'afficher l'ensemble de cette
  information dans l'une ou l'autre langue. La langue initiale suit la locale du poste ;
  le choix de l'utilisateur est conservé et détermine également la version du document
  complet ouverte depuis la notice.

Le texte affiché est maintenu dans `apps/privacy.py` et doit rester cohérent avec ce
document et sa version anglaise `docs/GDPR.md` : toute modification de fond doit être
répercutée dans les deux langues et dans les deux documents, avec incrémentation de
`NOTICE_VERSION` afin que les utilisateurs revoient la notice.

---

## 13. Contact

Questions relatives au présent document ou au comportement du logiciel :
<https://github.com/frankkubler/4imask/issues>.

Demandes d'exercice de droits : à adresser au responsable de traitement détenant les
vidéos (voir section 8).

---

## 14. Historique du document

| Version | Date | Modification |
|---|---|---|
| 1.0 | 2026-08 | Création — couvre 4iMask Anonymizer 1.1.0, détection de pose comprise. Version anglaise : `GDPR.md` |
