# Installation — préversion privée candidate.3

La préversion `v0.1.0-candidate.3` est publiée dans le dépôt privé. Elle contient le commit signé `63e517c25caa503b02eb38b2be994f8e2c32e142`. Son téléchargement puis sa certification isolée ont été reproduits : 114 tests réussis, un test d'inférence ignoré et contrôle landing réussi. Ce n'est pas une validation des quatre intégrations : oh-my-pi reste non qualifié. Voir `DELIVERY-STATUS.md` pour les preuves et limites.

Python 3.11+ et Git sont nécessaires pour construire et certifier ; Python 3.11+ suffit pour utiliser le cœur extrait. Les outils peuvent se trouver à la racine du commit candidat et, s'ils y sont suivis, font partie de l'archive. Ne pas employer `python -O`, `-OO` ni `PYTHONOPTIMIZE` pour construire ou certifier.

## Construire, vérifier, certifier

Depuis ce dossier, pour un commit **complet existant** et une version choisie :

```sh
python3 build_release.py build --repo /chemin/vers/depot --revision COMMIT_SHA_COMPLET --version VERSION --output /chemin/nouveau-bundle
python3 build_release.py certify --repo /chemin/vers/depot-de-confiance --revision COMMIT_SHA_COMPLET_ATTENDU --bundle /chemin/nouveau-bundle --scratch /chemin/nouveau-scratch
python3 -m unittest -v test_build_release
```

Le bundle et le scratch ne doivent pas exister ; choisir les deux hors de tout dépôt. Le build lit uniquement les blobs Git du commit, refuse les liens/sous-modules et certains noms de caches, poids ou secrets, et ne touche pas à l'index ni aux fichiers de travail. Les fichiers réguliers, y compris binaires, sont inclus sans omission jusqu'à 5 Mo chacun ; au-delà le build échoue. Les filtres de noms ne garantissent pas l'absence de secrets : **auditer tous les contenus du commit, y compris les binaires, avant toute publication**. L'archive est déterministe ; `manifest.json` lie version, commit, tree, membres et leurs SHA-256, ainsi que celui de l'archive. `SHA256SUMS` contient ce dernier.

La certification exige un dépôt Git de confiance et le SHA complet attendu fournis séparément : elle compare commit et tree aux objets Git et les chemins, modes et contenus aux blobs de cette révision avant extraction. Elle vérifie aussi empreinte, membres et chemins, refuse liens et types non réguliers, puis extrait dans le nouveau scratch et lance `omr.py --help`, la découverte `unittest` à la racine, les tests `host-adapters/test_launch.py` si `host-adapters` existe et le script `tests/test_landing.py` directement s’il existe et la découverte des autres modules `test*.py` dans `tests`, dans un venv isolé sans dépendances additionnelles. Les tests démarrent des serveurs synthétiques sur loopback ; ils ne testent aucun fournisseur réel. `SHA256SUMS` et manifest ne sont pas des signatures : comparer l'empreinte à une valeur obtenue séparément par un canal fiable. Le dépôt et la révision attendue doivent provenir d’une autorité de confiance indépendante ; le manifeste ne les authentifie pas. Ils ne prouvent ni authenticité ni absence de secrets. La certification est une vérification locale, pas une publication ni la validation des quatre hôtes.

## Récupérer la préversion GitHub privée

Avec un compte ayant accès au dépôt, utiliser l'authentification native de `gh` si nécessaire (ne jamais copier de clé), puis choisir un nouveau dossier de téléchargement :

```sh
gh release download v0.1.0-candidate.3 --repo Zacaria/open-model-router --dir dossier-telecharge
cd dossier-telecharge
shasum -a 256 -c SHA256SUMS
```

SHA-256 attendu de l'archive candidate.3 : `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`. Vérifier aussi la provenance du dépôt de confiance et le tag signé ; les trois fichiers téléchargés seuls ne constituent pas une autorité indépendante. Pour un contrôle des chemins et une extraction sûre, utiliser `build_release.py` depuis la révision de confiance et la commande `certify` ci-dessus avec le SHA complet `63e517c25caa503b02eb38b2be994f8e2c32e142`, le dossier téléchargé comme `--bundle` et un nouveau scratch externe. Employer ensuite son répertoire `source` comme installation. Ne pas extraire une archive non fiable directement par `tar`. Candidate.2 reste un brouillon avec un échec de test conservé ; ne pas la confondre avec cette préversion.

## Configuration locale

Lire `GATEWAY-SPEC.md` dans la source extraite et créer **hors de la source** un JSON de configuration avec `routes`, `default_route`, les URL/modèles/protocoles autorisés et la décision explicite ; aucune route de repli inter-familles/local implicite. Lancer `python3 omr.py serve --config /chemin/local/config.json --port PORT`. Éviter les identifiants dans ce fichier ; ne jamais copier les clés ou sessions des hôtes. La transmission d'authentification reçue est opt-in sur la route exacte. Le serveur est en loopback, destiné aux clients locaux de confiance.

La baseline s1d1 est optionnelle : voir `INSTALL-S1D1.md` et `requirements-s1d1.txt` dans le commit pour les versions épinglées et la récupération explicite des poids vérifiés, hors Git et hors archive. Aucun poids n'est inclus. La disponibilité des versions, des wheels et des poids sur un système donné n'est pas garantie.

## Limites

La certification est hors ligne et ne prouve aucun parcours fournisseur réel. Des preuves distinctes sur le runtime candidate.3 couvrent Hermes VM, Claude Code VM et Codex Mac ; elles ne valident pas oh-my-pi ni tous les fournisseurs/modèles. L'installation téléchargée décrite ici a été reproduite sur Linux, pas sur tous les systèmes et dépendances optionnelles. Aucun service/daemon automatique ni poids n'est fourni. Cette préversion privée et les résultats bornés ne constituent pas une livraison finale du contrat `GOAL.md`.
