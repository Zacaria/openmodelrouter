# Itération macOS UI/config — remise du 4 novembre 2026

## État et prochaine action

**DMG de développement privé construit et relu ; livraison utilisable complète non qualifiée.**
La suite GUI/fichier/tray/coffre requiert une voie de replay Mac à isolation effective : le refus de filiation/identité déjà établi dans `t_4a149763` reste actif. Aucun lancement GUI personnel n'a été substitué à cette preuve. Le build, le moteur synthétique et la remise privée ci-dessous sont acquis indépendamment de ce verrou.

- Qualification/publication historique : `t_c350e5cc` ; consommer les nouveaux pins, pas build-400.
- Admission des nouveaux octets dans la chaîne Apple existante : `t_0317aadc` (builder, sans parent).
- Raccord Codex comme fournisseur amont Desktop Mac : `t_f567df08` (builder, sans parent). Ce n'est pas le chantier Codex comme client GUI.

## Source exacte

- Candidat produit signé et revu : `8cf9a7f02a9c8bb77cc7cd6c505ab8f6b7a94795`.
- Arbre : `7062a43a8829c0207ec4efe1694136abba4fae4c`.
- Le candidat contient déjà le parent UI `1c1095865fc5113219d59f382f4b46a479cda90d` ; composition par avance rapide, sans nouveau delta produit ni double application.
- Revues indépendantes réconciliées : `t_702b81af` r2 et `t_86d5d3a4` r2. Signatures, ascendance et refs privées relues immédiatement avant consommation ; aucun PASS transféré à des octets modifiés.
- Branche privée de conservation : `work/omr-macos-compose-20261104`. Le présent compte rendu est un ajout documentaire post-build : son éventuel SHA n'est pas le SHA compilé.
- Mac : dépôt existant `/Users/operator/repos/open-model-router`, worktree détaché neuf `~/.cache/hermes-omr-t_0fcc8c66/worktree-8cf9a7f0`. Aucun clone ni remplacement du checkout personnel.

## Artefact et preuves durables

Dossier : `/srv/omr-private/artifacts/open-model-router/t_0fcc8c66/compose-8cf9a7f0/`.

| Objet | Identité SHA-256 |
| --- | --- |
| DMG ARM64, 145314054 octets | `453384ecfb766b8a63b4b2a48475261c6e34535c9f3ec02c07a7a781f05ed6a6` |
| `verification.json` | `804e38c8e31d64f8cb3665ab882f92e8f324e5cf37ff7d47023154908442baff` |
| Moteur embarqué | `f5de16628ce8fcc0ad2cc47f5ba7b25f09eab727b600f252fd4173f3587ac212` |
| Exécutable app | `76f0122db3638121b239f07c2434d7f1c2de4a89b13263a7f408a80408a2e561` |
| `composed-native-inventory.json`, 875 entrées | `b5faac867910a6080cfb76da54002fcf9100acc95fdbc0dad2edc9abed25c510` |
| `native-app-inspection.json` | `a53eff0aff93ee46119de0116cd9709831979f950c82121908f2021174e18a8e` |
| `build-compose.log` | `8261139e1a68788f23d3c594e6908c0e3e043024d90b74113b53abad888b9c6f` |
| `build-compose.sh` | `5bb33a89df09634d2b66fd756e6ee0c44b919cd1df6e187c67f562526e4605da` |

Le DMG n'entre pas dans la petite archive de preuves Kanban (limite 25 Mo). Les scripts exacts, logs, inventaire, manifeste et readbacks y sont conservés séparément. Le DMG est aussi disponible dans le **draft privé existant** `desktop-v0.3.0-candidate.1` du dépôt `Zacaria/open-model-router` :

- Asset API `708328785`, `input-compose-8cf9a7f0-aarch64-apple-darwin.dmg`.
- Asset API `708328787`, `input-compose-8cf9a7f0-verification.json`.
- Ajout entre 05:16:10Z et 05:16:36Z ; repo privé, draft maintenu, trois anciens assets préservés. Aucun tag ou asset remplacé, aucune publication publique.
- Métadonnées relues et deux flux retéléchargés par API : empreintes identiques au stockage durable.

Téléchargement authentifié du DMG de développement :

```sh
gh release download desktop-v0.3.0-candidate.1 --repo Zacaria/open-model-router \
  --pattern input-compose-8cf9a7f0-aarch64-apple-darwin.dmg
```

## Exécutions natives réalisées

Mac-worker : macOS 15.6.1 ARM64. Recette existante réutilisée en série avec Node 24.21.0, Python 3.13.5, Rust 1.91.1, wheelhouse verrouillé existant, venv neuf et `CARGO_BUILD_JOBS=2`. Aucun build concurrent observé avant lancement. Début 05:02:14Z, fin 05:13:43Z, code 0.

- Frontend : types, format, build et **34 tests** verts ; provider-runtime vérifié. Les quatre assets frontend produits sur Mac sont SHA-256-identiques au `build-parity.json` de la revue r2.
- Python natif : `test_desktop test_desktop_security test_desktop_ci test_desktop_provider_file test_desktop_review` : **59 tests** verts. `test_pi_ai test_pi_ai_packaged` sur le moteur gelé : **33 tests** verts.
- Rust : format, **1 test**, clippy avec `-D warnings`, build Tauri/DMG et collecteur existant réussis. Aucun fichier source suivi modifié avant/après.
- Inspection native read-only 05:14:38Z–05:14:47Z : app unique, lien Applications correct, bundle `io.havesomecode.omr` 0.3.0/minimum déclaré 14.0, app/moteur ARM64, hashes exacts, `codesign --verify --deep --strict` réussi. Signature **ad hoc**, pas Developer ID. Inventaire 875 entrées, volume détaché, DMG inchangé.
- **17 contrôles** sur le moteur gelé de travail puis sur celui extrait du DMG monté : données privées explicitement dédiées, sauvegarde IPC→fichier mode 0600, édition/rechargement, invalidité et conflit sans perte, récupération, redémarrage ; `/v1/models` = **604 IDs exacts** (3 profils + 601 directs) ; génération réellement exécutée vers un répondant loopback synthétique, identité amont `synthetic/model:600`, décideur absent ; refus sans bearer et arrêts propres. `PATH` vide, aucun runtime utilisateur nécessaire. Ceci exerce l'IPC utilisé par l'UI, **pas des clics dans l'app Mac** et pas un fournisseur LLM réel.

Les commandes exactes et sorties sont dans les scripts et logs du dossier durable. Premier `sha256sum -c` lancé depuis le mauvais répertoire : échec de résolution de chemin, aucun artefact déclaré valide ; relance dans le dossier durable réussie. Avertissements conservés : configuration npm `minimum-release-age`, avis install-scripts fsevents/Bun, PyInstaller `ntdll` absent sur macOS. Des diagnostics de typage statique concernent seulement les scripts de sonde jetables ; leur exécution réelle est verte, ils ne sont pas du code produit.

## Fournisseurs : constat depuis le véritable Mac

Relevé read-only frais à 05:03:09Z (`providers-readonly.json`), sans génération ni clé lue/importée :

| Fournisseur | État réel / limite |
| --- | --- |
| OpenRouter | Catalogue public HTTP200, **455** entrées (454 au relevé antérieur). Pas d'authentification OMR ni gratuité totale établie ; aucun modèle arbitrairement activé. |
| Ollama | `.211:11434` reste non joignable depuis Mac. Les six modèles observés depuis Windows dans `t_0598018b` ne valent pas accès Mac. Aucun tunnel/service/réseau modifié. |
| LiteLLM | `.211:4000` et `.211:18443` non joignables ; endpoint alternatif inconnu. Aucun redéploiement, cette indisponibilité n'a pas retardé le build. |
| Codex | Login natif et dix modèles établis par la découverte durable `t_0598018b`, pas de génération réexécutée. Le preset Desktop ouvre le contrôleur avancé Linux-only. Le relais Responses existant attend l'auth du client natif et un modèle concret ; l'URL backend n'est pas une connexion Desktop valide. Raccord minimal routé vers `t_f567df08`, pas de token copié ni d'URL élargie en release. Cette carte a produit le refus explicite revu `e5cb26600c9343c634d02070337ed293cf70283d` (arbre `942f0e64752b3b448e696ad6bd518ec01380aaff`), pas un fournisseur fonctionnel. Sa prochaine intégration reste distincte : il n'est pas inclus dans le DMG `8cf9a7f` ici identifié. |

**Aucun fournisseur personnel n'a été configuré ou présenté comme vérifié.** Les sauvegardes/readbacks du parcours fichier ont concerné les données synthétiques propres. En l'absence d'une connexion effective admissible, créer une connexion personnelle inactive et la qualifier comme accès aurait été trompeur.

## Préservation et limites restantes

Readback final 05:18:13Z : app personnelle installée toujours 0.1.0, exécutable `f9493ac68177aa302d0b48664d06792433ebc310f0b07e8f7bd89dd31811dcec` ; dossier personnel OMR toujours limité à `engine.lock`. Trois processus Codex préexistants 44181/48449/59939 présents. Empreinte du statut Git personnel inchangée `5b9fb196ad4ad6832a1e80678eb6e178872b3fee1f9ac7f751b9b884863b67ef` (784 suppressions déjà indexées, laissées intactes). Candidat Mac propre.

Non exécutés : installation/remplacement de l'app personnelle ; vrais formulaires et popup/tray clair-sombre Mac ; coffre OS ; menus hôtes Mac/Hermes/Claude ; génération fournisseur authentifiée ; Developer ID/notarisation/Gatekeeper du nouveau DMG ; Intel physique et exécution macOS 14 ; publication et parcours publics. Le PASS Apple de build-400 ne couvre pas ces octets. La réserve connue de densité du signe à 16–18 px reste à observer nativement.

Aucun fichier produit, base ou donnée personnelle supprimé. Seuls les dossiers synthétiques créés par les probes ont été retirés par leur contexte temporaire, et les volumes détachés. Worktrees et inputs encore consommés restent conservés. Aucun achat, export de clé, TCC, arrêt personnel ou contournement du verrou historique.
