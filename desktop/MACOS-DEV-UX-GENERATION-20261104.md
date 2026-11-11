# macOS DEV — autosave, catalogue et génération (4 novembre 2026)

## État livré

Le candidat **546ef5e3d680469e9b03a4f543d66527975f6432**, arbre
**da047c657f649d1548c3c14cf9037111d5dd813c**, est construit en ARM64,
inspecté et ouvert sur le Mac du propriétaire. Ce document post-build ne change
pas le pin source du binaire. **L’essai GUI propriétaire reste à recueillir** :
ne pas assimiler la preuve fournisseur du moteur à cet essai manuel.

Le propriétaire a autorisé l’usage de son profil DEV sans sauvegarde imposée,
puis l’arrêt/relance normal de la seule app OMR DEV. Lors de la bascule, aucune
instance OMR n’était présente ; aucun processus personnel n’a donc été arrêté.
Aucune installation existante remplacée, aucune valeur de clé lue/exportée,
aucune nouvelle dépense, aucun nouveau service, aucune nouvelle notarisation.
Le refus du harnais GUI automatique historique reste intact ; cette remise
emploie l’ouverture normale de l’app autorisée, pas ce harnais.

## Provenance exacte

- UX approuvée : **6c635d558968e2f0d867e82d6034af38126b1db5**,
  arbre `9a0d0eea4ad21e9799e320103d9c1db20c58ffee`, revue t_6625b229.
- Moteur approuvé : **4f2a28707b08a401578679d5adb04a50652deb35**,
  arbre `2005e81b7c9ca736f9a2053974587e5fa6ff787e`, revue t_3a935a9c.
- Base commune `8cf9a7f02a9c8bb77cc7cd6c505ab8f6b7a94795` ; le précédent
  tip release `80864f99bc437957af40231022b257105775010d` n’ajoutait que la
  documentation de l’ancien build.
- Merge signé sans conflit des deux tips corrigés, pas des tips refusés :
  **21 chemins UX et 4 chemins moteur disjoints**. Les 25 blobs composés sont
  exactement ceux de leurs sources approuvées, sans delta de résolution.
  `approved-union-proof.json` conserve les IDs Git par chemin. Signatures et
  refs privées vérifiées ; conservation poussée et relue sur
  `origin/work/omr-macos-compose-20261104`.
- Aucun Chat ajouté, aucun refus Codex séparé intégré, aucun fichier produit
  modifié par l’opérateur. Le Chat suit t_820b8958 et sa revue propre.

## Build et vérifications exécutées

Linux : 52 tests frontend, types, format, `test:build`, build et 71 tests Python
ciblés réussis. Replay Brave 153 du frontend compilé avec vrai Runtime isolé :
11 groupes réussis, 604 IDs, autosave sérialisé (une écriture simultanée max),
CAS/refus/rechargement et barrière abandon/chargement. Catalogue, coffre et
réponse de ce replay sont **synthétiques**.

Mac : recette existante adaptée aux pins et chemins, worktree explicite
`~/.cache/hermes-omr-t_0fcc8c66-546ef5e3/worktree-546ef5e3`, hors checkout
personnel ; lock `~/Library/Caches/native-pacing.lock`, aucun build concurrent.
macOS 15.6.1 ARM64, Python 3.13.5, Node 24.21.0, Rust 1.91.1,
wheelhouse verrouillé, venv neuf, `CARGO_BUILD_JOBS=2`.
Début **12:01:51Z**, fin **12:29:36Z**, code **0**.

La recette conservée `build-compose.sh` exécute contrat CI, installations
verrouillées, types runtime, 52 tests frontend/types/format/stabilité/build,
71 tests Python (génération/Desktop/sécurité/CI/fichier/revue), gel du moteur,
tests pi-ai et pi-ai empaqueté avec `OMR_TEST_ENGINE`, Rust fmt/test/Clippy,
puis `native:build -- --ci --target aarch64-apple-darwin --bundles dmg
--config '{"bundle":{"macOS":{"hardenedRuntime":false}}}'` avec
`APPLE_SIGNING_IDENTITY=-`, et collecte `ci/desktop.py collect`.
Le log exact est conservé. État source Mac propre en fin de recette.
Les quatre fichiers frontend Linux/Mac sont SHA256-identiques.

DMG inspecté via montage read-only puis détaché : bundle
`io.havesomecode.omr` 0.3.0, app et moteur ARM64, signature ad hoc
`codesign --verify --deep --strict` valide, inventaire **875 entrées**, DMG
inchangé. Son moteur embarqué passe **17 contrôles** IPC/fichier/CAS/catalogue
604/génération loopback/refus bearer/redémarrage/arrêt, sans Python sur PATH,
dans un état explicitement privé. Aucun coffre réel dans ces contrôles.

## Fournisseur réel — moteur empaqueté

À **12:30:48Z**, les mêmes octets moteur que ceux du DMG ont réellement
traversé **IPC OMR → gateway authentifiée → pi-ai embarqué → tunnel loopback
existant → Ollama réel** sur `http://127.0.0.1:11434/v1`.

Modèle exact **omr-hermes-qwen3-4b:ctx8192** : découverte des six IDs,
`generation_verified`, texte utile non vide validé par le moteur, identité
confirmée, `finish_reason=stop`, **12 tokens entrée / 2 sortie**, **3,966 s**,
reçu `completed`, transport `pi-ai`, sans décideur. Ce succès n’est pas déduit
d’un HTTP200 seul. Le contenu fournisseur n’a pas été retenu.

Le probe n’a utilisé qu’un répertoire de données temporaire privé et un bearer
synthétique local. Processus probe sorti code0, son port fermé ; données jetables
nettoyées. Aucun état utilisateur ou coffre OS lu. Le tunnel possédé PID17930
est conservé pour l’essai propriétaire et t_820b8958 ; ne pas le fermer ni
l’autodémarrer implicitement. Son handoff est attaché à t_a4c82b0a.

## Présentation DEV

À **12:31:05Z**, ouverture normale par `/usr/bin/open -a` du bundle du nouveau
DMG monté read-only :

`~/.cache/hermes-omr-t_0fcc8c66-546ef5e3/presentation-qualified/OMR Desktop.app`

NSRunningApplication confirme PID **23274**, bundle et exécutable exacts,
lancement fini, app active/premier plan. CoreGraphics observe une fenêtre OMR
layer0 de **1180×820**. Aucun clic automatique, réglage OS ou accès de capture
contourné. `providers.json` a conservé son hash avant/après lancement.
L’agent n’a pas inspecté son contenu ni lu les clés. La filiation fraîche est
23274 → bootloader23289 → moteur23293, listener **127.0.0.1:60561**.
Ne pas démonter/retirer cette entrée tant que l’app ou son consommateur reste actif.

**Action propriétaire restante :** observer autosave/sélecteur dans Fournisseurs,
sélectionner un modèle et cliquer **Tester** ; relever résultat ou message exact.
OpenRouter réutilise la clé saisie localement ; la preuve ci-dessus ne qualifie
pas son accès réel. Ollama offre une alternative locale sans frais nouveaux.
Le coffre, tray/échelles et parcours GUI complet ne sont pas indépendamment
qualifiés par les observations de fenêtre.

## Octets et conservation privée

- DMG : **145316931 octets**, SHA256
  **ec0b692080798c22342ad7866d135272b65115190a10ec5f186f65709480451d**.
- Moteur : **a22a611b63a47ea11bd882181daced21830bf5df86380bb5832838724ab7abb6**.
- Exécutable app : **8de2a747a7f8c80c776cf5726fd3ddaff9031f07825c0c87f95f6966ddbfb383**.
- Draft privé existant `desktop-v0.3.0-candidate.1`, release **431721137** :
  asset DMG **709440317**, nom `input-compose-546ef5e3-aarch64-apple-darwin.dmg` ;
  reçu collecteur **709443685**, nom `input-compose-546ef5e3-verification.json`,
  1672 octets, SHA256 **4f406415b4b80d2d53138caa032bee88d491808bb949218cffbea6d065f4936d**.
  API : `https://api.github.com/repos/Zacaria/open-model-router/releases/assets/709440317`
  et `https://api.github.com/repos/Zacaria/open-model-router/releases/assets/709443685`.
  Métadonnées et flux retéléchargés vérifiés ; dépôt privé, release draft et
  cinq anciens assets inchangés. Aucun remplacement ou publication publique.
- Preuves durables :
  `/srv/omr-private/artifacts/open-model-router/t_0fcc8c66/compose-546ef5e3/`.
  Reçu opérateur `MACOS-DEV-546ef5e3-RECEIPT.json` et archive manifeste
  `MACOS-DEV-546ef5e3-EVIDENCE.zip` distincts du reçu collecteur original.

## Limites et suppressions

Pas de nouvelle qualification Developer ID, notarisation/Gatekeeper de
distribution, Intel, macOS14, installation publique, vrai OpenRouter, coffre OS
ou parcours GUI propriétaire. Suite Python racine complète et Pyright non rejoués
par release : preuves amont séparées, 16 erreurs Pyright préexistantes rapportées.
Avertissements npm : configuration locale `minimum-release-age`, scripts
fsevents/Bun non explicitement approuvés ; les builds correspondants réussissent.
93 notices de dépendances générées. Le premier probe fournisseur visait un chemin
`.app` non présent après collecte ; corrigé vers le moteur dont la parité SHA256
avec le DMG a été démontrée, sans changer le produit.

Aucun fichier source, base ou donnée utilisateur supprimé. Seuls les états
synthétiques jetables de vérification sont nettoyés automatiquement. Worktrees,
montage de présentation et tunnel restent des entrées actives des consommateurs,
pas des copies finies à retirer pendant cet essai.
