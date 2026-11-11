# Sessions natives dans OMR Desktop

## Périmètre intégré

Entrées exactes : socle livré `74695fbbd290f8875dbf569254ede228bdfc4150` (arbre `cbfe26bfd7fda1ccefa3f503366d7818dc232226`) et adapters acceptés `983b7c5c7df7762b54f2c3ce0c0d66cc16219680` (arbre `ad05f2e8be60f6e437a6ea3d51a88b343001973b`). Les 26 fichiers advanced sont repris sans modification. Les preuves expurgées du parent sont la référence historique, pas une validation de cette intégration.

La page **Stratégies natives** pilote une nouvelle session Codex appartenant à OMR, jamais une session importée. Le proxy HTTP et sa configuration ne changent pas : aucune compaction ni délégation automatique sur les requêtes directes ou les profils. Les commandes sont explicites et asynchrones ; l'annulation reste accessible pendant un tour. Une seule session, un seul travail actif. Fermer la fenêtre ne ferme pas la session ; fermer la session la détruit. Quitter sans interruption refuse les travaux actifs.

## Disponibilité

- Codex 0.159.0 sur Linux x86_64 : intégration du protocole app-server qualifié. Requiert le binaire natif et son helper dans l'installation npm utilisateur standard, `/usr/bin/bwrap` et l'authentification ChatGPT native préexistante. L'app ne fournit pas ces dépendances et ne lance aucune connexion au démarrage. La présence locale ne prouve pas l'accès fournisseur ; **Connecter** vérifie le compte et le catalogue avant tout tour.
- Claude Code : non disponible dans Desktop ; qualification sémantique de délégation partielle et permissions enfant non attestées.
- OMP : non disponible dans Desktop ; compaction/changement observés sur macOS, préservation des paires outils non qualifiée, délégation non vérifiée.
- Hermes et autres OS/versions Codex : non disponibles. Aucun remplacement par une fixture ou par un appel HTTP.

## Isolation et permissions

Le clic **Connecter une session isolée** consent à l'utilisation de la souscription native pour les opérations suivantes, chacune déclenchée explicitement et susceptible de consommer son quota. Aucun achat ni repli API. Bubblewrap construit une racine vide : seuls certificats publics/DNS, binaire natif avec son helper, HOME temporaire et fichier d'authentification monté en lecture seule à son chemin natif sont exposés. Aucun montage de la racine hôte, des workspaces ou des sockets utilisateur. Ni lecture Python, ni copie de credential. Le nouveau HOME privé et ses rollouts sont temporaires, supprimés à la fermeture. Les processus reçoivent un environnement minimal sans clés API héritées. Aucun shell n'est lancé.

Le thread est read-only, approval=never, effort=low, plugins/MCP/skills/shell/web désactivés, profondeur enfant limitée à un. Toutes les demandes serveur sont refusées sauf l'outil déterministe `read_context`, réservé au thread créé et retournant uniquement le contexte saisi dans l'app. Ce contexte est une donnée non fiable, jamais une permission. L'app ne lit aucun projet utilisateur. Une compaction exige un item natif terminé et la terminaison du même tour ; une délégation exige un enfant natif terminé, pas une affirmation textuelle. Les refus, erreurs et timeouts ne deviennent pas des réussites ; un timeout ferme le transport propriétaire.

## Commandes et données

IPC privé `native` : `connect`, `maintain`, `switch`, `compact`, `delegate`, `cancel`, `close`. Aucun chemin, commande shell, identifiant de thread existant ni flag de permission fourni par le WebView. `connect` exige `consent=true`. Les **instructions de session** saisies explicitement dans ce contrôle sont transmises comme `developerInstructions` natifs à la création et restent distinctes du contexte non fiable. Elles ne changent ni sandbox, ni permissions, ni outils. Une préférence écrite seulement dans un ancien message utilisateur n'est pas une politique persistante garantie : un replay avec gpt-6-luna a conservé les données mais perdu le préfixe demandé. Le replay des instructions persistantes doit donc exercer ce véritable réglage natif sans effacer ce résultat négatif. Les modèles proviennent du catalogue natif ; `switch` transmet le choix au prochain tour, sans prétendre changer le modèle enfant. Les textes et le résultat restent en mémoire de l'app (et dans le HOME natif temporaire pendant la session), jamais dans les reçus ou leurs exports.

Chaque opération produit un reçu `mode=native`, avec identifiant local, action, statut, durée, compteurs numériques et événements bornés sans contenu. Les snapshots Codex de contexte et de dernier appel ne sont pas des totaux de tour : ils sont séparés, non additionnés aux consommations API. Un snapshot natif peut annoncer un total non nul avec des sous-compteurs à zéro après compaction : les valeurs brutes sont conservées, mais l'inspecteur signale l'écart et n'en déduit jamais une consommation nulle. Coût auxiliaire, coût total et facture restent inconnus. Les identifiants natifs sont hachés ; aucun prompt, réponse, argument d'outil, adresse de compte ou erreur brute persisté. Le résultat est affiché uniquement sur la page de session ; l'inspecteur montre la preuve structurelle et les limites comptables.

## Vérification

Version du candidat : **0.2.0**, distincte du socle public 0.1.0 ; aucune publication depuis cette carte. Sous Linux, l'installation npm attendue est `npm install --global --prefix "$HOME/.local" @openai/codex@0.159.0`, avec Bubblewrap fourni par la distribution et `codex login` effectué par l'utilisateur. Ces étapes ne sont jamais lancées par l'app. Le montage d'authentification est read-only : une rotation nécessitant une écriture peut échouer et exige une reconnexion native hors OMR ; aucun repli n'est tenté.

Tests de contrat hors ligne : `python3 -B -m unittest test_desktop_native -v`. Ils ne prouvent aucune capacité native. Replay réel intégré : `OMR_NATIVE_REPLAY_CONSENT=1 python3 -B desktop/scripts/replay_native_strategies.py`. Fournir `OMR_TEST_ENGINE=/chemin/omr-engine` pour le sidecar gelé. Le consentement ne vaut que pour les prompts synthétiques de ce script sur la souscription existante. Le replay utilise une session neuve et n'enregistre que validations et reçus sans transcript.

Pour les vrais boutons Tauri/WebKit, utiliser le harnais `desktop/scripts/run_native_replay.sh` avec `OMR_NATIVE_UI_REPLAY=1`, `OMR_NATIVE_REPLAY_CONSENT=1`, les chemins `OMR_TEST_APP`, `OMR_TAURI_DRIVER`, `OMR_WEBKIT_DRIVER` et un `OMR_EVIDENCE` isolé. Sans ce flag, le replay historique du socle reste synthétique et ne lance aucune génération native. Les hôtes non rejoués ne sont pas revendiqués.

La fermeture normale attend l'arrêt du processus natif et la suppression du HOME temporaire **avant** d'accuser réception à Tauri. Un crash brutal de l'OS ou du processus ne garantit pas ce nettoyage ; les fichiers temporaires restent privés, mais ne sont pas chiffrés par OMR.
