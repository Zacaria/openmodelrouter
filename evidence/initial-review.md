# Revue indépendante initiale — 27 octobre 2026

## Verdict exact
- **GO préservation seulement**, conditionné à la création du premier commit depuis l'arbre EXACT `134cf0df11385856063c90ed5c774abc8bc35707`, avec libellé explicite « prototype historique, non livré ». Ce n'est ni une validation produit ni une autorisation de release. Comparer l'arbre immédiatement avant signature ; tout changement invalide cet avis. Aucun push ou signature exécuté par cette revue.
- **GO correctif provenance de l'archive pour intégration ultérieure**, pas GO livraison : le chemin local construit `status: unknown` et `real-local-identity-unknown`; empreintes avant/après et politique sont exposées, sans revendiquer l'authenticité des poids. Tests unitaires sur simulation seulement ; aucune inférence réelle refaite. Les empreintes ne prouvent ni identité amont ni immuabilité concurrente.
- **Attention conflit majeur** : l'arbre de préservation NE CONTIENT PAS le correctif du candidat. `demo-t_a3c46d97/demo.py:98` y étiquette arbitrairement `real-local-s1d1`, et `README.md:21` affirme « vrai s1d1 » sans preuve ; le correctif devra être intégré séparément avant usage ou publication revendiquant cette provenance. Préserver ne signifie pas valider ces affirmations historiques.

## Identités et périmètre
- Archive SHA256 `f7fdabb4c2ab5e3c5c40d9f0dba73c28850b82348e7419b5dfd86e6aaaf0c8bc`, ses 15 fichiers comparés octet par octet à l'extrait stable ; aucune divergence et extrait inchangé après tests.
- Index comparé directement à l'arbre Git demandé : mêmes noms, modes et objets ; 54 fichiers, tous identiques aux fichiers de travail. Aucun cache, pyc ou GOAL-SESSION.json inclus. Aucun autre fichier source/docs non suivi constaté au moment du contrôle. `staged-files.txt` contient la liste exacte `git diff --cached --name-only` ; `canonical-manifest.json` donne SHA256, blob Git, taille et mode de chaque fichier ; `candidate-manifest.json` idem SHA256/taille/mode de tous les fichiers du candidat.
- Manifest canonique SHA256 `a152f76ac02e2f08131eb38291e2794f891bf0501d617901451a7aeb2814dae4` ; manifest candidat SHA256 `0a4910064d39107aacc6c8c0f29f7885190b3514ac70c2f51689721b41e7de32`. GOAL.md SHA256 `b48a4d1cd41bc479b7c3854e2b2f72f79a49258dcd97b678037a97a6f8c7d83b`.
- Trois fichiers communs divergent entre archive et index : `demo-t_a3c46d97/demo.py`, `test_demo.py`, `README.md`; empreintes exactes dans les manifests. Ne pas confondre archive corrigée et arbre de préservation.

## Preuves des tests
Copie intégrale du candidat dans `test-copy/`, sans modification de l'original ; exécution dans chaque dossier avec `env -i`, HOME et TMPDIR isolés, `PYTHONDONTWRITEBYTECODE=1`, et `sitecustomize.py` interdisant les connexions socket Python. `python3 -m unittest -v` : démonstration 6/6 OK et boucle 6/6 OK, codes 0. Journaux complets `demo-t_a3c46d97-tests.log` et `loop-t_daf181c7-tests.log`. Aucun fournisseur, modèle, poids ou carte invoqué. L'interdiction socket est un garde-fou Python, pas une sandbox système générale ; les commandes exécutées par ces tests sont synthétiques et inspectées.

## Confidentialité et limites
Scan de tous les 54 blobs indexés : aucune correspondance aux signatures ciblées de clés privées, jetons OpenAI/GitHub/AWS et affectations littérales de secrets ; cela ne prouve pas l'absence de tout secret. Les deux JSONL inclus sont étiquetés ou documentés simulés ; cas JSON synthétique. Commandes de génération fiables mais non sandboxées ; passerelle loopback sans authentification ; aucun usage données privées ni exposition réseau. Le contrat GOAL exige quatre intégrations réelles, identité s1d1 prouvée, benchmarks reproductibles et livraison vérifiée : non démontrés par cette revue. Documents historiques peuvent avoir hypothèses ou instructions dépassées par GOAL.md ; conserver comme historique, pas comme preuve actuelle.

Aucun Git write, aucune carte, aucun fournisseur. Les sorties de revue sont limitées à ce répertoire de scratch durable.
