# Onboarding — correction R1/R2 et nouvelle qualification Linux

**Prochaine action :** relire le nouveau commit signé indiqué dans la remise Kanban de `t_75dfa842`. Le candidat précédent `dd2e02e265efd44ea015d7f1ab87d2244a2c5987` n’est pas approuvé ; ses preuves restent historiques. Aucun déploiement ni publication.

## Frontière corrigée

- **R1 — tout l’échange IPC est borné.** Le watchdog démarre avant la première écriture et couvre les écritures partielles, `flush()` et la lecture, avec le même deadline et signal d’annulation. Il vise le groupe capturé. Le nettoyage réape ce groupe puis ferme tous les canaux et retire son HOME, même si `BufferedWriter.close()` rencontre un pipe cassé après une interruption de flush.
- **R2 — le nettoyage reste attaché au processus capturé.** Sous le verrou de cycle de vie, une ancienne classification en erreur ne nettoie et ne change l’état que si ce processus est toujours celui du manager. Après un vrai arrêt/redémarrage, le nouveau worker reste prêt, vivant et capable de répondre.
- Aucun formulaire, provider, poids, protocole ou packaging modifié dans cette correction. Aucun fichier source supprimé, aucune donnée utilisateur réinitialisée. L’ancien write/flush non surveillé a été remplacé, pas conservé comme repli.

## Régressions exécutées

`test_desktop_onboarding.ManagedWorkerLifecycleTest` utilise de vrais processus isolés et les vraies commandes `start`/`stop`. Les seules substitutions concernent les petits poids de fixture et le processus de calcul synthétique.

1. Worker qui ne lit jamais stdin : charge UTF-8 de 28 000 octets, JSON de 84 014 octets, pipe réduit à 4 096 octets. Deadline de 0,15 s puis annulation séparée. L’appel doit finir avant le contrôle à 0,8 s ; processus réapé, deux canaux fermés, HOME supprimé, état arrêté.
2. Petit write bufferisé devant un pipe plein : mêmes contrôles pour le blocage dans **flush**, avec deadline et annulation séparées. Ce test a révélé puis fermé le défaut de cleanup sur `BrokenPipeError`.
3. Écritures volontairement limitées à trois octets : le vrai enfant reçoit exactement une requête JSON complète et répond ; le worker reste prêt.
4. Lecture de l’ancien worker retenue par une barrière : vrais stop/start, nouveau processus prêt, puis ancienne erreur libérée. Le nouveau processus et son HOME restent intacts, statut prêt ; une nouvelle classification réussit.

Les trois nouveaux tests, rejoués contre le **blob Git exact** `dd2e02e:desktop_managed.py`, produisent cinq assertions en échec et une erreur, puis réussissent sur la correction. Les tests de cycle de vie ont aussi été répétés **20 fois : 120 tests, zéro erreur, échec ou skip**. Le log RED initial antérieur au correctif, le replay RED complet et les logs GREEN sont conservés avec le harnais de replay dans l’archive de cette remise.

## Gates frais

| Commande / portée | Résultat |
|---|---|
| `OMR_TEST_ENGINE=<sidecar exact> .venv/bin/python -B -m unittest discover -v` | **219 tests**, zéro échec/erreur/skip ; transport pi-ai gelé inclus |
| `.venv/bin/python -B -m unittest -v test_desktop_onboarding` | **20 tests**, zéro skip |
| Export du tree Git candidat, build pi-ai depuis ses manifests, même suite onboarding | **20 tests**, zéro skip ; aucune fixture ignorée du workspace utilisée |
| Suites supplémentaires de `.github/workflows/tests.yml`, adaptateurs hôtes, landing | Sorties 0 ; **un skip explicite** de génération locale historique, faute de `OMR_GENERATOR_PYTHON`/`OMR_GENERATOR_WEIGHTS` ; ce test n’est pas la classification ONNX de ce produit |
| `npm run check`, `npm test`, `npm run format:check`, `npm run test:build`, `npm run build` dans `desktop` ; `npm run check --prefix desktop/provider-runtime` | OK ; **23 tests UI** ; build indépendant identique |
| `cargo fmt --check`, `cargo test --locked --release --features tauri/custom-protocol`, `cargo clippy --locked --release --features tauri/custom-protocol -- -D warnings` | OK ; **1 test Rust** |
| Black `--check` sur les deux Python changés, compilation et `git diff --check` | OK ; pas de linter Python distinct configuré pour ces fichiers |
| `.venv/bin/python desktop/scripts/build_sidecar.py`, puis `npm run native:build -- --no-bundle` | Sidecar et vrai Tauri Linux reconstruits sans changer les scripts du propriétaire distribution |
| `sh desktop/scripts/run_onboarding_replay.sh` avec chemins explicites, HOME/XDG/D-Bus/Secret Service isolés | **41 assertions réussies**, de l’état vide à la reprise persistée ; aucune clé réelle ni session utilisateur |

## Inférence et identité réelles

Le replay natif télécharge et vérifie à nouveau le checkpoint s1d1 épinglé, exerce annulation/reprise et fait deux décisions réellement non constantes de qualités **1 puis 2**. BYOK/URL/Jev/Imajev passent par les fixtures loopback déclarées : elles ne qualifient pas leurs fournisseurs réels. Les trois captures et leur texte affiché ont été régénérés ; aucun texte d’interface n’a changé dans le correctif.

Une sonde complémentaire, avec le **worker du sidecar gelé**, refuse un prompt de plus de 1024 tokens sans troncature, garde le worker vivant et réussit les deux questions publiques suivantes en environ **6 ms chacune**, sous leurs deadlines de deux secondes. Les scores observés sont `0.09088727831840515` et `0.45224321261048317`. L’arrêt et la suppression du HOME sont confirmés. Valeurs précises dans `local-boundaries.json` ; ce n’est pas une qualification de qualité générale.

- Application : `45f50c4f57661d09b6cf0a7c7c3f0110f42a80c902a1b2755e7ca49b7f7136e5` (inchangée : aucun code Rust/frontend changé).
- **Nouveau sidecar** : `02511db18bd2749ce8e2a51f92b4fda602e2accf55ba0d61808e32684809e0d6`.
- `artifact-integrity.json` : huit modules Python gelés identiques au source, deux entrées pi-ai identiques aux inputs, quatre fichiers frontend, aucun poids embarqué. Six fichiers du checkpoint réellement hachés dans `checkpoint.json`.
- Versions : Python 3.13.5, numpy 2.5.4, tokenizers 0.23.3, onnxruntime 1.31.1, PyInstaller 6.16.0, certifi 2026.10.23. Les scripts runtime/packaging et leurs locks/notices restent hors de cette modification.

Les JSON synthétiques et ce rapport sont conservés dans Git. L’archive `omr-onboarding-linux-r1-r2-evidence-20261101.zip` contient captures, textes, résultats, logs et sondes ; son empreinte, son nombre de membres et son stockage durable sont indiqués dans le reçu de remise. Les binaires reconstruisibles restent dans le workspace actif pour la revue ; les poids restent hors Git et hors archive.

## Limites et relais

**Non qualifiés :** API réelles/payantes, vraies installations Ollama/Jev/Imajev, macOS, Windows, installateurs et paquet final recomposé. Le mode géré reste Linux uniquement. Le skip historique et les avertissements npm install-script / imports optionnels PyInstaller restent visibles dans les logs ; le chemin ONNX CPU gelé exercé fonctionne, sans promesse GPU/transformers.

Après approbation du nouveau commit, le propriétaire distribution `t_7f883b61` peut composer ses dépendances et licences ONNX, reconstruire puis qualifier le paquet résultant. Son candidat de distribution reste distinct : aucun PASS ne se transfère implicitement à cette composition. Aucun achat, génération externe, tag, release ou déploiement n’a été effectué.
