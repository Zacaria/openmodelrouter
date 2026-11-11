# Fournisseurs, fichier et sélecteurs — vérification Linux

> Rapport historique r1 : le candidat `cf8007209c75404721bf35a6525b5cfad07a34af` a reçu **CHANGES_REQUESTED** pour la réintroduction d’UUID et l’authentification Hermes. Les corrections, régressions et résultats actuels sont dans [PROVIDERS-REVIEW-R2-20261104.md](PROVIDERS-REVIEW-R2-20261104.md). Les contrôles ci-dessous ne sont pas une approbation de r1.

## Candidat et composition

Code vérifié : `3dd6634df1684b60c29639014fa9a0bb6a7c83cd`, arbre **`601b0eb61f437771278846b8a52deb0ebc7589cf`**. Le commit de ce compte rendu est documentaire ; le SHA final soumis à revue est indiqué dans la remise Kanban et le manifeste des preuves.

- Base produit : `a5677fd2f08eac7dd06b5272f6545bf0fd8fe317`.
- Tranche fournisseur/catalogue : `0e857513c6eb17b969cae28432f4766ecc0b7383`.
- Dépendance UI revue : `1c1095865fc5113219d59f382f4b46a479cda90d` (contient `d7314946`). Merge de consommation signé : `23c197c7626122321e8f9f39421854b1649005b5`.
- Raccord des appelants et correction de la garde de destination : `3dd6634df1684b60c29639014fa9a0bb6a7c83cd`.

Tous ces commits ont une signature vérifiée. Les fichiers CSS, primitive `ui.tsx`, icônes et Rust sont **identiques à la dépendance UI**, sans édition auteur dans cette tranche. Les appelants métier onboarding/stratégies ne changent que leurs sélecteurs. `desktop/src/App.tsx` est le hotspot coordonné avec t_86d5d3a4.

Après approbation, t_0fcc8c66 peut consommer la branche complète (la dépendance UI est déjà ancêtre). S’il a déjà intégré la dépendance UI, les seuls commits fonctionnels de cette tranche à appliquer sont `0e857513` puis `3dd6634d` ; ne pas rejouer le merge comme un patch de fichiers partagés. Le compte rendu accompagne ces sources.

## Résultats exercés

| Frontière | Résultat observé |
|---|---|
| Fichier ↔ UI | Brave Linux, vrai sidecar JSONL : preset Ollama enregistré dans `providers.json`, édition externe réellement chargée dans l’App, conflit et JSON invalide refusés sans écraser l’édition ni la dernière valide, récupération. |
| Sélecteur dans l’App | Bundle de production réellement chargé : `assets/index-DtPz9WkO.js`. Popup fournisseur ouvert avec les quatre types, fond/surlignage des tokens OMR en clair/sombre, largeurs 640/1440, clavier/Escape/focus et pas de débordement du popup. Aucun sélecteur natif visible dans les pages exercées ; les contrôles natifs cachés de Radix restent présents pour le comportement formulaire. |
| Valeurs des appelants | Qualité enregistrée comme nombre, effort vide enregistré `null`, référence UUID puis `null`, choix Jev assignant `jev-1.13.0`, autre protocole vidant le modèle, trois modes décideur et retour direct, filtres de reçus. Aucun accord de coût donné. |
| Catalogue observé | Rejeu hors réseau des 454 IDs OpenRouter réellement collectés par t_0598018b : **454 directs + 3 profils = 457**, sans troncature. Les **19 IDs commençant par `~`** sont conservés littéralement. Ce n’est ni un accès authentifié ni une génération OpenRouter. |
| Native Linux | OMP 18.14.2 `models ls` et Codex 0.159.0 `model/list` paginé : **604 IDs visibles exacts chacun**, trois profils et 601 directs synthétiques. Vrai OMP → proxy authentifié → Desktop → SSE synthétique : une requête, modèle `~synthetic/model:exact`, effort `high`, aucun appel au décideur. |

Le dernier rejeu natif complet tourne dans Bubblewrap avec réseau externe désactivé et système hôte en lecture seule. Un probe préalable retourne `ENETUNREACH` (101) vers une adresse externe et autorise loopback. Les répertoires natifs d’auth/configuration sont isolés ; HOME/XDG isolent aussi la comptabilité des daemons OMP. Ni token personnel ni service fournisseur réel utilisé.

## Checks frais

| Commande / portée | Résultat |
|---|---|
| `uv run --python 3.13.5 --with-requirements desktop/sidecar-requirements.txt python -B -m unittest discover -v` | **277 tests**, succès, **3 skips** de chemins empaquetés nécessitant un moteur figé. |
| Suites de `.github/workflows/tests.yml` dans `pilot-t_f21a25b3`, `loop-t_daf181c7`, `comparator-t_14313d5b`, `integrated-t_dab1958b`, `demo-t_a3c46d97` | 16 / 6 / 5 / 9 / 6 tests, succès ; un skip de pilote. |
| `python -B tests/test_landing.py` dans le même environnement uv | Succès : 8 fragments, 6 IDs uniques et divulgations françaises/prototype. |
| `npm run format:check`, `npm run check`, `npm test` dans `desktop/` | Succès ; **34 tests frontend**. |
| `npm run build`, `npm run test:build` dans `desktop/` | Succès ; 93 notices collectées, JS/CSS identiques avec sources étrangères et sans règles Git ignore. |
| `npm run check`, `npm run build` dans `desktop/provider-runtime/` | Succès ; runtime pi-ai Linux compilé avec les dépendances épinglées. |
| `scripts/test_controls_render.py --evidence .evidence/controls-production` avec Playwright 1.56.0 | **225/225 contrôles** verts de la primitive, distincts du rejeu App complet. |
| `unittest discover -s host-adapters -v`, avec les deux binaires natifs opt-in, sous Bubblewrap | **16 tests**, succès sans skips ; inclut génération OMP synthétique, refus d’auth proxy et registres natifs. |
| Ruff 0.14.5, `check --select F` sur les Python touchés ; `format --check` sur le moteur/sidecar et nouveaux tests | Succès. Le launcher conserve le format historique du dépôt. |

**Fermeture des entrées :** export propre de l’arbre `601b0eb6…`, sans `.evidence`, dépendances ni fichiers ignorés hérités. Installation des deux lockfiles, compilation pi-ai, **277 tests Python**, **34 tests frontend**, format/type/build/stabilité répétés dans cet export : succès. Ses **quatre fichiers frontend produits** sont identiques par SHA-256 à ceux du bundle exercé dans Brave.

## Reproduction des probes supplémentaires

Les diagnostics non produit, logs, captures et manifeste par membre sont dans l’archive jointe `t_702b81af-providers-linux-evidence.zip`. Extraire les scripts `browser_bridge.py` et `browser_probe.py` sous `desktop/.evidence/` dans un worktree jetable ; ils n’opèrent que sur `desktop/.evidence/browser-state`. Ils ne sont pas des points d’entrée livrés à l’utilisateur.

1. Construire le frontend. Lancer `npm exec -- vite preview --host 127.0.0.1 --port 18741 --strictPort` depuis `desktop/`.
2. Depuis la racine, lancer `python3 -B desktop/.evidence/browser_bridge.py` (port loopback 18742, sidecar réel, requêtes limitées à snapshot/save_config et origine du preview).
3. Lancer `OMR_REPLAY_PRODUCTION=1 uv run --python 3.13.5 --with playwright==1.56.0 python desktop/.evidence/browser_probe.py`. Le script utilise `/usr/bin/brave-browser`, des données synthétiques et aucune API fournisseur. Arrêter les deux processus propres après le test.

Pour les registres/transport natifs : installer OMP 18.14.2 dans un préfixe jetable ignoré, exposer Bun 1.4.4 dans PATH, définir `OMR_TEST_CODEX_BIN` et `OMR_TEST_OMP_BIN` avec des **chemins d’exécutables réels**, puis :

```sh
bwrap --die-with-parent --unshare-net --ro-bind / / \
  --bind "$TMPDIR" "$TMPDIR" --proc /proc --dev /dev \
  -- python3 -B -m unittest discover -s host-adapters -v
```

Les variables des deux binaires doivent être exportées avant cette commande. Les tests sans ces variables sautent explicitement la qualification native. Ne pas traiter ce saut comme un PASS natif. Les exemples du launcher utilisateur sont dans [host-adapters/README.md](../host-adapters/README.md).

## Refus, limites et continuation

- **Sécurité du fichier :** aucune clé dans le JSON partageable ; consentement externe du décideur remis à `false`. Le chargement refuse un changement d’URL/transport sous un UUID de connexion existant ; créer une nouvelle identité. Une ancienne clé d’une connexion réintroduite après le lancement nécessite réenregistrement explicite ou redémarrage. Pas de delta Rust requis pour charger le fichier ; l’IPC utilise `save_config` existant. Format/limites/CAS détaillés dans [PROVIDERS-FILE.md](PROVIDERS-FILE.md).
- **Concurrence :** comparaison de révision et de SHA-256 jusqu’immédiatement avant les remplacements, test d’une édition pendant le flush, pas de prétention à un CAS atomique contre un éditeur ignorant les verrous. Si les octets changent après la dernière comparaison, la fenêtre check/replace reste inhérente au remplacement filesystem. Les erreurs d’écriture interne préservent l’état actif et permettent une reprise du fichier public valide.
- **Clients :** OMP et Codex ont des preuves de registre natif réel ; ce n’est pas une capture exhaustive de tous leurs menus. Hermes a son catalogue GET raccordé mais son picker natif n’est pas qualifié ici. Claude accepte un ID explicite/listé par le launcher ; aucune injection universelle dans son menu propriétaire n’est revendiquée. Pas de conversion entre Chat, Responses et Messages. Les métadonnées client sont texte seul et ne déclarent aucun prix ni raisonnement réglable inventé.
- **Codex par abonnement :** le preset ouvre les stratégies existantes sans faux endpoint. Le relais déjà présent `omr.py`/`forward_auth`, son catalogue natif et son invariant d’un modèle concret restent intacts et séparés du gateway Desktop mixte. Le point de raccord Mac a été transmis à t_0fcc8c66 : ne pas convertir aveuglément la base `/backend-api/codex` en `/v1`, ni importer OAuth, ni considérer la limite Linux du contrôleur avancé comme une impossibilité du relais.
- **Non exécuté ici :** binaire Tauri/DMG, UI et coffre Mac, accès authentifié/génération réelle OpenRouter/Ollama/LiteLLM/Codex, signature Apple, notarisation, installation ou publication. Ces actions appartiennent à la continuation native après revue de ce candidat. Aucun autre worktree ni service distant édité. Les premiers probes OMP ont précédé l’isolation de sa comptabilité globale : ils ne prouvent pas l’absence d’écriture de métadonnées sous `~/.omp/run`. Le dernier rejeu utilise la garde hôte lecture seule et les racines privées explicites ; aucune session personnelle n’a été qualifiée ou arrêtée.

Tentatives rejetées documentées, avec logs de suite/replay conservés lorsqu’ils ont été capturés : environnement Python système incomplet (alternative uv réussie), ancien filtre `~` et bornes 100/500 (RED), garde transport trop large corrigée pour conserver le changement UI à URL inchangée, premier probe OMP sous garde lecture seule révélant les daemons globaux hors agent-dir (isolation HOME/XDG ajoutée), et lecture CSS immédiate avant stabilisation du focus Radix (attente observable, pas de délai arbitraire). Le navigateur distant bloquait loopback ; le rejeu a été exécuté localement avec Brave. Aucun de ces échecs n’est présenté comme un résultat natif positif.

Code supprimé/remplacé : suppression de l’import `urlsplit` inutilisé du launcher, suppression de la tranche de découverte `[:500]`, remplacement des menus HTML visibles par les appelants du Select revu. Aucun fichier source ni base de données supprimé. Les builds et dépendances de replay sont ignorés et ne font pas partie du candidat.
