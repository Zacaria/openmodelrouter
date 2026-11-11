# Premier démarrage — candidat Linux

**Rapport historique du candidat `dd2e02e` — non approuvé.** Les défauts R1/R2 constatés en revue sont corrigés et requalifiés dans [`../20261101-linux-r1-r2/VERIFICATION.md`](../20261101-linux-r1-r2/VERIFICATION.md). Les empreintes ci-dessous décrivent exclusivement l’ancien sidecar.

**Prochaine action :** revue indépendante de la frontière signée remise sur `t_75dfa842`, puis composition par le chantier distribution `t_7f883b61`. Aucun déploiement ni publication dans ce travail.

## Périmètre livré

L’assistant reprend après interruption, conserve ses étapes sans conserver de clé/brouillon dans le WebView et ne s’impose pas à une configuration valide préexistante. Il connecte les répondants avec Responses, choisit le décideur, règle le routage et expose des tests distincts avec coût API possible. L’accès direct ne dépend pas d’un décideur.

Trois modes sont raccordés : BYOK avec coffre OS et pi-ai, serveur existant par URL (dont le point d’entrée OpenAI d’Ollama), et s1d1 ONNX INT8 téléchargé/géré explicitement. Chat JSON passe par pi-ai pour les nouvelles connexions. Jev et Imajev utilisent leur contrat SystemOne propre ; une abstention ne devient pas une décision chat de remplacement. Imajev exige un serveur avec son vrai readout, non des poids chargés dans un générateur chat.

Le mode géré vérifie six SHA-256 épinglés avant publication atomique et avant/après chargement. Le téléchargement et l’inférence ont des processus isolés et bornés ; annulation/arrêt nettoient aussi les descendants du bootloader gelé. Aucun démarrage automatique ni poids dans Git ou dans l’archive du sidecar. Les limites de prompt, seuils expérimentaux et OS indisponibles sont visibles dans l’interface et `desktop/ONBOARDING.md`.

## Exécution vérifiée

| Contrôle | Résultat réel |
|---|---|
| `OMR_TEST_ENGINE=<sidecar> python3 -B -m unittest discover -v` | 216 tests, OK, aucun skip dans le passage final ; inclut le transport pi-ai gelé sans PATH de runtime |
| Suites historiques de `.github/workflows/tests.yml`, `host-adapters/test_launch.py`, `tests/test_landing.py` | Toutes sorties 0 |
| `npm run check`, `npm test`, `npm run format:check`, `npm run test:build`, `npm run build` dans `desktop` | OK ; 23 tests UI ; reconstruction JS/CSS indépendante identique |
| `npm run check --prefix desktop/provider-runtime` | OK |
| `cargo fmt --check`, `cargo test --locked --release --features tauri/custom-protocol` | OK ; 1 test Rust |
| `cargo clippy --locked --release --features tauri/custom-protocol -- -D warnings` | OK |
| Black sur les huit fichiers Python changés, compilation Python, `git diff --check` | OK ; pas de linter Python séparé configuré dans ce dépôt |
| Build sidecar existant avec les trois dépendances ONNX installées, puis `npm run native:build -- --no-bundle` | Réussi sur Linux x86_64, Python 3.13.5, WebKitGTK/WebKitWebDriver 2.54.0, tauri-driver 2.1.0 |

Le replay du **vrai Tauri** compte **41 assertions réussies** : départ vide, coffre Secret Service jetable, reprise après relance, absence d’appel automatique, Responses via pi-ai, BYOK, serveur URL, refus HTTP sans retry et reprise explicite, Jev/SystemOne, Imajev/SystemOne synthétique, annulation et reprise de téléchargement, lancement ONNX CPU gelé, décision non constante, arrêt du groupe complet et relance sans auto-démarrage. HOME, XDG, D-Bus, coffre et ports étaient isolés. Aucun processus natif de ce workspace ne subsistait après fermeture.

Le premier replay a détecté une erreur du harnais : sa recherche de `config.json` comptait aussi le fichier du checkpoint. La recherche cible désormais le dossier d’application ; le replay complet suivant est celui conservé. Les trois défauts de la revue adverse interne — reprise incomplète, abstention Jev, DNS/téléchargement non réapable — ont été reproduits et corrigés avant ce candidat.

## Checkpoint et identité des artefacts

- Checkpoint réel : `scombat/s1d1-router-6src-tiny-onnx-int8`, révision `dac13b5c0356864ea4501fa151d74dcd8b3ea22a`, **61 157 560 octets**. Empreintes et tailles réellement lues : `checkpoint.json`.
- Deux décisions natives donnent les exigences **1 puis 2**, avec le vrai tokenizer/ONNX. Un contexte de plus de 1024 tokens est refusé sans troncature ; le worker survit et la requête publique suivante réussit (`local-boundaries.json`). Ce n’est pas une qualification de qualité générale.
- Application native : `45f50c4f57661d09b6cf0a7c7c3f0110f42a80c902a1b2755e7ca49b7f7136e5`.
- Sidecar : `a8264b37b325a79f31d2492cbe42007c88bcc7c0b08faf35f73d27c3de0e6b4e`.
- `desktop/scripts/verify_onboarding_artifact.py` compare les huit modules Python gelés au code courant (seul `co_filename` est normalisé), les deux entrées pi-ai natives à leurs inputs et l’absence de poids embarqués. Les quatre fichiers frontend reconstruits correspondent à ceux de la qualification native. Détails : `artifact-integrity.json` ; compte rendu natif : `results.json`.

Archive de preuves : `omr-onboarding-linux-evidence-20261101.zip`, **17 membres vérifiés**, SHA-256 `897658b3c4678214ad17f8614161c1703ce90c5226b67133059af71077151024`. Elle conserve captures natives, texte réellement affiché, résultats, empreintes et journaux à `/srv/omr-private/artifacts/open-model-router/t_75dfa842/omr-onboarding-linux-evidence-20261101.zip`. Le reçu `HANDOFF.md` est joint à la tâche ; l’archive historique n’est pas une pièce jointe. Les modules source restent dans Git, pas dans une seconde copie d’arbre.

## Limites et prochaine frontière

**Non qualifiés :** fournisseur API réel/payant, vraie installation Ollama, poids/serveur Imajev et service Jev réels, macOS et Windows. Le mode géré est refusé hors Linux ; les autres modes ne sont pas présentés comme nouvellement qualifiés sur ces OS. Aucun achat, secret réel, session utilisateur activée ou appel de génération externe.

Le script packaging/runtime et ses locks/notices n’ont pas été modifiés. Le build de qualification contenait `numpy 2.5.4`, `tokenizers 0.23.3`, `onnxruntime 1.31.1`, `PyInstaller 6.16.0` et `certifi 2026.10.23`. **Avant distribution**, le propriétaire de `t_7f883b61` doit composer ces dépendances et leurs licences dans son lock/notices, puis vérifier le paquet composé. Les avertissements PyInstaller concernant notamment imports Windows, alias numpy et utilitaires optionnels torch/tensorflow sont conservés dans l’archive ; le chemin ONNX CPU réellement exercé fonctionne, pas les utilitaires GPU/transformers non qualifiés.

**Suppression :** ancien formulaire décideur Chat-seul et helper d’identité dupliqué remplacés par le composant partagé ; aucun fichier source supprimé, aucune donnée utilisateur réinitialisée. Les fichiers de staging appartiennent exclusivement aux tests/opérations gérées.

Base de ce travail : `b55ce49aec2025c8a7c029275c961dde7acee151`. La revue doit utiliser le commit signé indiqué dans la transition Kanban, pas une branche générale ni les changements d’un autre worker.
