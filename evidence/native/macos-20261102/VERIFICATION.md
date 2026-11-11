# OMR Desktop macOS ARM64 — candidat privé

**Prochaine action :** revoir le code du candidat `5737f77f8a05f8a87301a0dfd139f1a31834f7b1`, puis les preuves et le reçu du DMG. Cette remise qualifie le portage privé ; elle ne vaut pas admission publique Apple ni réussite d’une génération Qwen.

## Identité du candidat exercé

| Élément | Identité |
|---|---|
| Source signée | `5737f77f8a05f8a87301a0dfd139f1a31834f7b1` ; arbre `6033bf7337d792d550981b5f7f3720074af14cb3` |
| Base non approuvée globalement | `d619cd75d069a616ad33605a77e720c878528247` ; aucun PASS hérité |
| Export source vérifié sur mac-worker | SHA-256 `9ae30dbb2fbb5386f229a97322061aa5f03205fd1e0a26b89923fa1bcb2c9b41` ; 765 fichiers suivis comparés |
| Paquet privé | `OMR-Desktop-0.2.0-macos-arm64-5737f77-private.dmg` ; 144639221 octets ; SHA-256 `8f7aef8c166bf92dc560999df94e31ead763686f9e8c57eafdaa541c2b8666af` |
| Exécutables réellement exercés | App scellée `9e6e8e8fad62e3f48b45946e3f596cfbb0b64c106a7190e720af3fb6f2ba03e9` ; moteur embarqué `12fdf1e5e6048f4d16c5a32822da069bda16143fa2545d363752c35526ab2f5b` |

Hôte : mac-worker, macOS 15.6.1, ARM64/M1 Pro, 16 Gio. Cible `aarch64-apple-darwin`, version produit et badge **0.2.0**, minimum macOS **14.0**. Aucun build Intel ni essai Rosetta revendiqué. Le minimum 14.0 est déclaré ; le seul hôte physique exercé ici tourne sous 15.6.1.

Outils observés : Python de build 3.13.3, PyInstaller 6.16.0, certifi 2026.10.23, numpy 2.5.4, tokenizers 0.23.3, onnxruntime 1.31.1, Node 22.23.2, npm 10.9.8, Rust 1.91.1, Bun 1.4.4 ; CLI Tauri 2.12.4 et bibliothèque Rust Tauri 2.12.5 verrouillées. Ces outils sont ceux du constructeur : l’app a été lancée avec `PATH` vide, pas avec un Python/Node utilisateur.

## Changements bornés

1. Installation des dépendances du décideur depuis le wheelhouse natif, hors réseau, avec le lock/hashes existants. Aucun second lock macOS conservé ; minimum OS explicite issu de la roue ARM ONNX.
2. Worker macOS activé sur le chemin de groupes POSIX. Le cas Darwin « second kill d’un groupe zombie → EPERM » est reproduit puis corrigé : réaper le leader terminé, toujours nettoyer les descendants ; un refus de permission sur un worker vivant reste une erreur. Windows reste désactivé sur cette branche.
3. Cible Bun `aarch64` distinguée de l’addon npm `arm64`. Une spec macOS empêche PyInstaller de réécrire/re-signer seulement les deux assets pi-ai déjà compilés ; leurs hashes gelés doivent toujours être strictement identiques. Les autres bibliothèques restent traitées normalement. Le helper et la spec accompagnent les inputs de reconstruction.
4. L’alias système `/var → /private/var` ne fait plus échouer les matériaux valides : seuls les parents de la racine sélectionnée sont canonisés. Racine symlinkée, liens internes et chemins traversants restent refusés, avec régressions.
5. Disponibilité du mode géré affichée depuis l’état natif ; reprise du petit correctif de badge `1c78b77`, sans retirer le bouton du nouvel onboarding. Aucun workflow commun modifié, aucun fichier source supprimé, aucune base réinitialisée, aucun secret personnel importé/exporté.

## Vérifications fraîches

| Portée | Résultat |
|---|---|
| Python macOS, `OMR_TEST_ENGINE=<moteur natif> ... -m unittest discover -v` | **252 tests**, zéro échec/erreur, **8 skips** : sept anciens tests explicitement Linux et une provenance de bibliothèques Debian. Les six nouveaux tests de cycle macOS passent ; le transport pi-ai gelé est effectivement exercé. |
| Python Linux et suites historiques | **252 tests**, zéro échec/erreur, trois skips faute de moteur Linux gelé ; **51 tests supplémentaires**, un skip historique faute de générateur/poids configurés. Les trois tests gelés skippés sous Linux sont exercés sur le moteur Mac quand applicables ; aucune preuve Debian n’est inventée. |
| Frontend et Rust natifs | **25 tests UI** ; types, format, inputs/notices, provider-runtime types et build de production OK. `cargo test --locked --release --features tauri/custom-protocol` : un test OK ; Clippy même cible avec `-D warnings`, Rustfmt et build Tauri natif : sorties 0. |
| Parcours réel de l’app finale | **48 assertions** et **11 captures AX** : état vierge, saisie UI avec notifications natives, sauvegarde sans seed, téléchargement/empreintes des six fichiers, démarrage ONNX, consentement, tests explicites, direct et trois profils, refus HTTP 401 sans clé, inspecteur/détail, stop/restart, fermer/rouvrir, annuler puis confirmer Quitter. |
| Octets et paquet | Huit modules Python gelés identiques au source compilé, seul `co_filename` normalisé ; deux assets pi-ai identiques ; aucun poids embarqué. DMG vérifié par hdiutil ; 17 fichiers/liens de l’app montée et recopiée identiques à l’app exercée. Copie extraite du DMG réellement relancée : même configuration, aucune inférence ni démarrage géré automatique, arrêt 0. Paquet inchangé après les parcours. |

Builds lourds sérialisés sous le lease existant, concurrence Rust 1. Aucun processus personnel arrêté, aucune app personnelle remplacée. Les connexions sont locales et sans clé : les identifiants et états de test sont dédiés ; le coffre personnel et sa liste de recherche n’ont pas été reconfigurés. Un aller-retour de stockage de clé BYOK n’est **pas** qualifié par cette remise.

### Inférence : trois niveaux séparés

- **Répondant synthétique : réussi.** Le harnais réutilise la vraie fixture Responses existante, réellement appelée par le pont pi-ai. Ce n’est pas une réponse de LLM.
- **Classifieur local réel : réussi.** Le checkpoint s1d1 épinglé tourne dans le worker CPU gelé. Les deux questions publiques de contrôle donnent les qualités **1 puis 2** ; tokenizer et usage proviennent de l’inférence, pas d’une fixture constante. Aucun prompt ni réponse conservé dans les reçus.
- **Générateur Qwen existant : non qualifié.** Deux essais bornés avec les poids `qwen3:1.7b` déjà présents, copiés dans notre espace, sont arrêtés par le même garde de swap. Variante GPU : delta global 52188 pages de 16384 octets ; variante CPU, zéro couche sur 29 déportée au GPU : 30092 pages. Le seuil était 16384 pages ; minimum de mémoire libre observé 27 % puis 30 %. Zéro génération complète et HTTP 502 conservés comme échecs, pas comme PASS. Les groupes de serveur possédés sont arrêtés et les poids originaux re-hachés inchangés. Les métriques sont globales : aucune causalité exclusive attribuée à OMR. Pas de troisième retry, de nouveaux poids, de dépense ni de relèvement du seuil. Prérequis du prochain essai : une capacité permettant l’inférence sans franchir ce garde, ou un autre répondant existant autorisé par la continuation de livraison.

## Signature, captures et distribution

Le build Tauri local sans identité fournissait un seal incomplet. Commandes privées explicites après build :

```sh
codesign --force --deep --sign - "OMR Desktop.app"
codesign --verify --deep --strict --verbose=2 "OMR Desktop.app"
```

Le seal **ad hoc privé** passe, y compris sur l’app montée depuis le DMG. Aucune identité Developer ID n’a été exportée ou remplacée par un faux PASS ; le DMG n’est pas signé, aucune notarisation et aucun parcours Gatekeeper/public download qualifiés. La continuation de livraison possède ces actions, avec ses contrôles existants et une nouvelle qualification des octets finaux.

Le préflight de capture écran renvoie `false`. Aucune permission demandée, préférence changée ou capture synthétisée. Les captures sont des **arbres Accessibility natifs réels**, pas des images ; géométrie, couleurs et Dock ne sont pas attestés par ces fichiers.

### Dépendances réellement observées

`native-payload-inventory.json` décrit les 80 entrées natives/liens observées, hashes et commandes Mach-O ; aucun chemin de chargement non système n’est absolu hors paquet. NumPy charge **Accelerate** du système : aucune bibliothèque GNU `libgfortran`/`libquadmath` de la roue Linux n’est héritée. L’inventaire distingue `LC_ID_DYLIB` des véritables chargements.

Les matériaux Bun/WebKit/TinyCC préparés pour **ce Mac** sont vérifiés : **260 fichiers**, cible `aarch64-apple-darwin`. Ils restent sous `~/Library/Caches/omr-native-t_5c86c079/source/desktop/.sidecar-build/pi-ai-distribution/` ; le manifeste et le reçu de vérification sont dans l’archive de preuves. Ni reconstruction historique du runtime ni publication approuvée ne sont attestées. Le refus `verify_worker_corresponding_sources()` du kit Linux reste intact.

**Avant publication :** conserver les textes et matériaux des composants effectivement distribués et compléter leur collecte dans le paquet final. Les 31 chemins de notices gelés ne sont pas une clôture générale : notamment `onnxruntime/LICENSE` et `onnxruntime/ThirdPartyNotices.txt` du wheel ne sont pas collectés à ces chemins. Vérifier aussi les mentions des autres extensions et bibliothèques observées, sans importer une attestation NumPy/GCC Linux ni demander une reconstruction générale de toolchain pour rejouer des tests privés. Une recomposition des ressources impose de re-sceller et vérifier le nouveau paquet.

## Stockage et relais

- DMG durable Debian : `/home/operator/.hermes/profiles/builder/artifacts/open-model-router/t_5c86c079/OMR-Desktop-0.2.0-macos-arm64-5737f77-private.dmg`.
- DMG durable Mac : `~/omr-native-candidates/t_5c86c079/OMR-Desktop-0.2.0-macos-arm64-5737f77-private.dmg` ; profil et harnais de qualification sous `~/Library/Caches/omr-native-t_5c86c079/final/`.
- Archive de preuves : `omr-macos-native-5737f77-evidence.zip`, conservée dans le même dossier durable Debian et jointe à la remise. Elle comprend captures AX, scripts utilisés, logs frais, reçus et échecs de génération. Pas de poids, d’état de coffre, de clé de signature ou de transcript client.

Le code source produit est le commit `5737f77…`. Le commit documentaire descendant conserve ce rapport et les petits JSON de preuve ; il ne change pas les octets produits. Revue indépendante d’abord ; la continuation macOS peut ensuite traiter mentions concrètes, identité de version de livraison, signature/notarisation et vraie réponse autorisée, sans attendre Windows ni le kit Linux. Aucune publication, nouveau tag, achat, utilisation d’un abonnement ou modification de forwarding n’a été faite.
