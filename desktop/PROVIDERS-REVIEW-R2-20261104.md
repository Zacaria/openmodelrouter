# Fournisseurs — correctifs de revue r2

## Candidat et périmètre

Correctifs de F1/P1 et F2/P2 de la revue indépendante du candidat `cf8007209c75404721bf35a6525b5cfad07a34af` ; ce candidat n’a pas été approuvé. Source corrigée et signée : **`b93e81bb2ac820dfd2f73401b50b8f6f64d5e185`**, arbre **`ace67ca64eac2bf74288bf702aef5f16a40abcee`**. Le commit documentaire suivant ne change aucun octet du code vérifié ; le manifeste de la nouvelle archive donne le candidat final exact pour revue.

Delta source : `desktop_engine.py`, `host-adapters/launch.py`, les régressions `test_desktop_provider_file.py`, `test_desktop_review.py`, `host-adapters/test_desktop_catalogue.py`, `host-adapters/test_hermes_auth.py`, ainsi que les deux contrats `PROVIDERS-FILE.md` et `host-adapters/README.md`. Aucun changement frontend, CSS, contrôle partagé, icône, Rust ou autre worktree. Les quatre fichiers du build frontend sont SHA-256 identiques au candidat r1 et à l’export propre r2.

## F1 — identité de coffre et destination durable

L’état interne `config.json` conserve `connection_destinations`, une table UUID→URL exacte, distincte du fichier partageable et de l’historique de dix révisions. Chaque sauvegarde acceptée conserve les entrées supprimées. Le chargement du fichier comme la sauvegarde UI refuse toute autre URL pour un UUID déjà accepté, avant écriture ou émission de credentials. Le contrôle ne dépend plus de la présence d’une clé en mémoire. La remise des valeurs natives sur l’IPC `secrets` ne change jamais cette table. Un état interne dont la configuration contredit sa propre liaison échoue au démarrage.

La table est initialisée depuis la configuration interne et son historique si elle n’existe pas encore ; aucun secret n’est lu ou transféré pour cela. Ce correctif ne peut pas reconstituer des destinations déjà oubliées par une ancienne version ni annuler une divulgation antérieure. Ne pas éditer `config.json` pour modifier la confiance ; utiliser `providers.json` et un nouvel UUID pour une autre URL.

Régressions réellement exécutées :

- suppression dans le fichier puis réintroduction du même UUID avec une autre URL ; refus aussi après éviction de plus de dix révisions et redémarrage ; sauvegarde UI refusée sans clé chargée ; restauration de l’URL d’origine permise ;
- vrai sidecar JSONL : suppression, remise intégrale des valeurs comme le fait Rust, tentative refusée ; fichier hostile laissé sur disque, redémarrage, remise des valeurs natives, `discover` refusé et **zéro requête** à la destination hostile ;
- nouvelle identité + enregistrement explicite d’une nouvelle clé : découverte locale réussie ; le serveur reçoit exclusivement le nouveau canari, jamais l’ancien ;
- consentement exact et continuité des outils conservés : les fixtures de changement de serveur créent désormais une nouvelle identité, après avoir vérifié le refus de l’ancienne. Les changements de transport UI à URL identique restent possibles.

`f1-red.log` conserve les échecs avant correction. `f1-sidecar-old-red.log` rejoue le nouveau test d’IPC contre les fichiers du candidat r1 exportés depuis Git : l’ancienne version accepte la destination, donc RED confirmé. `f1-sidecar-green.log` donne le passage corrigé sous namespace réseau isolé. Aucun coffre OS réel n’a été ouvert : ce test reproduit son message IPC, pas son implémentation native.

## F2 — clé du proxy reconnue par Hermes

Le launcher fournit maintenant **`OPENAI_BASE_URL` égal au `--base-url` du proxy** avec `OPENAI_API_KEY` égal à sa clé locale éphémère. Le bearer Desktop reste séparé et retiré de l’environnement enfant. Aucun réglage Hermes persistant n’est écrit. Un ancien `OPENAI_BASE_URL` sans rapport est explicitement remplacé dans ce seul enfant.

`host-adapters/test_hermes_auth.py` exécute le launcher réel et le proxy réel. Un processus de test à la place du CLI interactif importe ensuite le **résolveur Hermes installé**, avec configuration, fournisseur nommé, propriétaire et pool vides/synthétiques ; il n’exécute aucune conversation ni inférence. Il vérifie la clé résolue et effectue un GET authentifié `/v1/models` : **HTTP200**, trois profils et une route directe. Le profil sentinelle isolé reste inchangé, sans `.env` ni `auth.json`. Les imports Hermes peuvent créer leurs répertoires de support dans ce HOME jetable, jamais dans le profil utilisateur.

Le RED réel échoue sur la sélection de clé du résolveur avant le changement ; le GREEN utilise le même résolveur et le même protocole de test. Source Hermes observée : `bf0203a794a07aac3ff764972ab9087baa4e4f4e` ; SHA-256 de `runtime_provider_custom.py` : `8744c52b92cf84b1a5e57077c3e6fcaffacaa2799e46cd9149809aba7211847c`. Ce résultat ne qualifie toujours pas le sélecteur interactif Hermes.

## Vérification fraîche

| Commande / portée | Résultat |
|---|---|
| `uv run --offline --python 3.13.5 --with-requirements desktop/sidecar-requirements.txt python -B -m unittest discover -v` | **280 tests**, succès, **3 skips** réservés aux chemins empaquetés avec moteur figé. |
| `PYTHONPATH=. python3 -B -m unittest discover -s host-adapters -v`, trois opt-ins natifs/résolveur, garde Bubblewrap | **18 tests**, succès, **0 skip**. Registres réels Codex 0.159.0 et OMP 18.14.2 : **604 IDs** chacun ; génération OMP strictement synthétique, modèle/effort exacts, un appel, sans décideur. |
| Suites des cinq sous-répertoires de `.github/workflows/tests.yml` et `tests/test_landing.py` | 16/6/5/9/6 tests verts, un skip de génération locale du pilote ; contrôles landing verts. |
| `npm --prefix desktop run test`, `check`, `format:check`, `build`, `test:build` | **34 tests**, types/format/build verts ; stabilité JS/CSS avec sources étrangères vérifiée. |
| `npm --prefix desktop/provider-runtime run check` puis `build` | Runtime pi-ai Linux réellement compilé, dépendances épinglées. |
| Ruff 0.17.3 `check --select F` sur les six Python touchés ; `format --check` sur les cinq au format Ruff | Vert. Le launcher garde sa présentation historique. `git diff --check` vert. |

Export propre du commit source ci-dessus, sans dépendances ni fichiers ignorés hérités : les deux installations `npm ci --offline --no-audit --no-fund`, la compilation pi-ai, les **280 tests racine / 34 frontend**, les types, le format, le build et la stabilité des sources passent à nouveau. Les caches uv/npm sont réutilisés comme caches de paquets, pas comme sources ou sorties générées. `export-source.json`, `export-setup.log`, `export-checks-final.log` et `verification-summary.json` établissent cette frontière et les quatre empreintes d’artefacts identiques.

Rejeu Brave **153.0.8010.37**, bundle de production et vrai sidecar : les quatre menus clair/sombre × 640/1440, clavier/focus, UI→fichier, fichier→UI, refus du brouillon concurrent, fichier invalide puis récupération, conversions qualité/effort/baseline et filtres passent. Aucun appel fournisseur ni clé native. Les processus propres et leurs ports sont arrêtés après le rejeu.

Tentatives de préparation non retenues : premier export minimal RED incomplet (`advanced` manquait), ensuite export Git complet du module et RED sémantique confirmé ; premier chemin de lockfile inexistant, corrigé vers le lockfile du dépôt ; premier rejeu navigateur lisait le fichier avant l’acquittement de sauvegarde parce que le statut précédent était déjà « synchronisé ». Le probe attend maintenant la disparition du bouton d’application, puis le parcours passe. Ces échecs ne sont pas revendiqués comme tests produit verts. L’installation fraîche signale le postinstall Bun épinglé ; la compilation et les tests prouvent l’exécutable effectivement utilisé. L’avertissement zip de doublon NumPy provient d’une fixture de refus volontaire.

## Reproduire les deux corrections

Depuis la racine :

```sh
python3 -B -m unittest test_desktop_provider_file test_desktop_review -v
PYTHONPATH=. python3 -B -m unittest discover -s host-adapters -p test_hermes_auth.py -v
```

Le second saute explicitement le résolveur installé sans les trois opt-ins :

```sh
export OMR_TEST_HERMES_SOURCE=/chemin/vers/hermes-agent
export OMR_TEST_HERMES_SITE_PACKAGES=/chemin/vers/site-packages-python314
export OMR_TEST_HERMES_PYTHON=/chemin/vers/python314
```

Le rejeu de cette remise utilise `/home/operator/.hermes/hermes-agent`, le site-packages de la génération `dfff6e265b4e49238c30f95a870a4fab` sous `/home/operator/.hermes/installs/019d0d114d22b7e6/pm-runtime/`, et l’exécutable `python3` 3.14.9. Les tests OMP/Codex exigent aussi les opt-ins binaires décrits dans le [rapport initial](PROVIDERS-VERIFICATION-20261104.md#reproduction-des-probes-supplémentaires). Le rejeu complet des adaptateurs utilise `bwrap --unshare-net --ro-bind / /`, HOME/XDG privés et seuls les dossiers de test/TMPDIR inscriptibles ; il n’accède à aucun fournisseur externe.

## Livraison et limites

La nouvelle archive `t_702b81af-r2-evidence.zip` contient les logs RED/GREEN, commandes, probes de navigateur, captures, résumé et manifeste SHA-256 par membre. Elle complète, sans remplacer les faits historiques, les deux archives r1 déjà attachées à la carte.

Pas de nouveau transport, de changement Rust ni de migration de données. Le contrôle de destination antérieur, limité à la configuration présente et aux clés en mémoire, est remplacé. Aucun fichier source ni base de données supprimé.

Prochaine étape exacte : revue indépendante du nouveau candidat signé sur **t_702b81af**, puis consommation de ses deux commits r2 par **t_0fcc8c66** et qualification native Mac existante. Ne pas publier ces octets comme approuvés avant le verdict. Tauri/DMG, coffre/UI Mac, signature Apple, accès/génération fournisseur réelle, picker interactif Hermes et menu propriétaire Claude restent non vérifiés ici. La limite du CAS optimiste de fichier et la séparation du relais Codex natif restent celles des contrats existants.
