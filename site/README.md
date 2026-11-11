# Landing OMR Desktop — Ready

## Livraison de la refonte 0.3.1

Le candidat produit est `fdc83fc014755b4432072fce31b8f6802cd658ed`. La nouvelle publication conserve les dix fichiers de téléchargement 0.1.0/0.3.0 relus anonymement le 6 novembre 2026. Leur manifeste de rétention est épinglé à `7c029fc2f2e72cc39bdfedb0ddb36fc2dfe58b1ab9022f604cd5c62f8399f6ae` ; les gardes de provenance, d’immutabilité et de collision restent actives. Le nouveau paquet ARM64 ne modifie pas les installateurs des autres plateformes.

Le complément texte `assets/materials/0.3.1/rebuild.patch` actualise uniquement les quatre fichiers de version de reconstruction déjà publics ; il met à jour les empreintes du manifeste du kit de base. Le pont Bun, l’extension native et la recette de remplacement ARM64 corrigée du kit 0.3.0 restent inchangés. La page locale décrit l’application du complément et les prérequis existants ; aucun historique Git, secret ou autre partie du dépôt n’est publié.

Le DMG 0.3.1 qualifié contient 147399172 octets, SHA-256 `a3c9f45362552936a465d7499f63a8e5392e214cb92154d38d8e09ea0396ae23`. Signature Developer ID, tickets app/DMG et Gatekeeper ont passé sur le runner puis sur le Mac natif. Quatre tests du moteur signé et la navigation AX des quatre pages principales ont passé dans un profil privé, en arrière-plan et sans remplacement de l’app personnelle. La génération réelle fournisseur n’a pas été réexercée : le manifeste reste `generation: synthetic-only`. La publication demeure soumise à la revue du payload exact et aux gardes existantes.

La décision courante est [LANDING-READY.md](brand/decisions/LANDING-READY.md). Elle remplace la landing v3 par les deux templates, la feuille de style, le script et le logo du ZIP `Open_Model_Router_Landing_Ready.zip`. Le manifeste qualifié du projet, et non le snapshot du ZIP, gouverne les téléchargements. La publication relève du coordinateur après revue indépendante, selon `GOAL.md` ; le constructeur ne déploie pas.

Le hero et la disponibilité partagent un seul état OS/architecture/format. La détection est indicative et réversible : un Mac générique ne permet pas de choisir sa puce, un hint ARM ou Windows 32 bits ne sélectionne pas un paquet x64. Un choix manuel n’est pas remplacé par un hint tardif. Sans manifeste qualifié, aucun téléchargement n’est activé. Les notes d’installation, hashes et métadonnées suivent le paquet choisi ; la liste statique reste accessible sans JavaScript.

Le catalogue peut présenter des versions différentes selon le système : une nouvelle version ARM64 ne renomme pas les paquets Intel, Windows ou Linux conservés. Chaque paquet porte sa version et son commit produit dans le HTML statique comme dans les panneaux interactifs. Si plusieurs versions existent pour une même architecture, leurs boutons indiquent la version en plus du format. Une même version garde une identité commune de source et de prérelease ; des identités contradictoires restent refusées.

Pour publier une nouvelle version en conservant l’historique visible, la garde reçoit `--artifacts` pour les seuls nouveaux paquets, `--historical-manifest` pour l’entrée historique épinglée et `--catalog` pour le catalogue utilisé au build. Ce dernier contient exactement les nouveaux paquets, dans leur ordre d’entrée, suivis des quatre paquets historiques augmentés de `prerelease: true`. Le nouveau tag, les notes et l’immutabilité sont vérifiés séparément de la provenance historique signée ; aucun ancien paquet n’emprunte l’identité de la nouvelle release. Ce mode exclut `--landing-only`.

## Produit et architecture

`src/templates/en.html` et `fr.html` sont les gabarits éditables issus du ZIP. `scripts/render-ready.ts` injecte les métadonnées vérifiées et normalise la sémantique HTML sans changer la composition. `src/ready.css` reprend le design fourni avec les fontes locales existantes. `dist/` contient seulement HTML, CSS, scripts locaux, logo/favicon, polices et éventuels paquets qualifiés — jamais les originaux, décisions ou preuves. React, Tailwind et leurs composants devenus inutiles sont supprimés ; aucune dépendance n’est ajoutée.

`language-routing.js` conserve la préférence EN/FR et les ancres. `src/ready.mjs`, publié sous `landing.mjs`, synchronise les scénarios, les téléchargements, le menu et la copie du checksum. Aucun framework client, backend, compte, analytics, police distante ni appel fournisseur. Les anciens choix de téléchargement stockés ne sont pas réinterprétés. Les erreurs de stockage n’empêchent pas le choix de langue.

Les quatre scénarios restent du contenu explicatif : aucun appel modèle n’est déclenché. Les boutons, flèches, Home/End et Entrée mettent à jour décision et diagramme. Sans JavaScript, le scénario initial, les liens et les détails natifs restent lisibles. La FAQ garde les limites réelles d’accès fournisseur, d’inférence distante et de consentement. Aucun statut interne de développement ou de qualification n’est ajouté à la composition fournie.

Le pied de page EN/FR donne accès aux sources et licences du paquet macOS ARM64 0.3.0 sur l’alias public dédié. Ce lien ne suppose aucun compte GitHub et ne présente pas ce compagnon comme les sources des anciens installateurs. Le contrôle général de tous les attributs src/href accepte uniquement les chemins locaux propres et fragments, sans caractères de contrôle ni antislash. Son unique exception externe est l’ancre source-materials, dans un footer et vers l’URL exacte ; jamais un chargement iframe, script ou preload.

Palette et rythme suivent le ZIP ; Space Grotesk, DM Sans, IBM Plex Mono et leurs licences restent locaux. `assets/logo.webp` est copié à l’identique depuis le ZIP, les favicons existants sont conservés. Le diagramme se recompose sur mobile ; `prefers-reduced-motion` désactive transitions, animations et défilement fluide.

## Vérifier localement

Depuis `site/`, Node 24 et npm :

```sh
npm ci
npm run check
npm run format:check
# Sans manifest : état indisponible honnête, aucun paquet inventé.
npm run build
npm test
npm run test:browser
npm run test:staging
```

Pour un build avec téléchargements, fournir explicitement `OMR_DOWNLOADS_MANIFEST=/chemin/manifest.json` à `npm run build`. Le [contrat d’entrée](brand/decisions/DOWNLOAD-HANDOFF.md) exige notamment taille, SHA-256, source, `prerelease` et qualification. Les octets sont vérifiés avant copie. Les binaires, manifests privés, fixtures et captures restent hors Git. Le manifest historique public 0.1.0 omet `prerelease` : la préparation de prévisualisation séparée est documentée dans LANDING-V3 ; elle ne qualifie pas une nouvelle release.

`npm test` contrôle le HTML construit, la traduction, le staging et les gardes. Pour exécuter les trois intégrations de garde supplémentaires, fournir `OMR_PRODUCT_CHECKOUT=/chemin/checkout-produit-accepte` ; sans lui, elles sont explicitement ignorées. La commande Python historique `python3 tests/test_landing.py` depuis la racine reste disponible.

`test:browser` utilise Brave via Playwright (`BROWSER_PATH`, défaut `/usr/bin/brave-browser`) et un serveur loopback temporaire, ou `OMR_TEST_ORIGIN` pour une destination déjà autorisée. EN/FR sont exercés à 320, 390, 768, 1280 et 1534 px : scénarios, synchronisation, clavier, menu, SHA, absence de JS, détection conservative, ressources et axe. `OMR_TEST_BUILT_DIR` sélectionne un build isolé ; `OMR_BROWSER_OUTPUT` désigne le dossier de preuves. Ces contrôles Brave/Linux ne certifient ni les autres navigateurs ni l’application Desktop ; zéro violation axe n’est pas une certification WCAG.

`test:staging` utilise des octets synthétiques isolés pour deux formats Linux et des paquets refusés. Il n’écrase pas le `dist/` principal et ne qualifie aucun installateur réel. Les rapports v3 et antérieurs sont historiques ; les scripts et composants qu’ils décrivent ne sont plus la version courante.

## Revue et release

La revue porte sur l’arbre exact. Le coordinateur sélectionne les paquets approuvés, reconstruit le candidat accepté, exécute la garde existante et relit le déploiement exact. Les dix fichiers historiques 0.1.0/0.3.0 sont conservés en taille et SHA-256. Le projet reste `open-model-router.vercel.app` : aucun nouveau projet ni remplacement silencieux d’un tag ou d’une release existants. Une nouvelle version conserve sa propre identité sans réétiqueter les anciens paquets. Les métadonnées de qualification et limites des essais restent dans le handoff privé, pas dans le texte produit.

## Release status without a GitHub release

A numeric-version download may explicitly set `prerelease` to `null` when no
GitHub release status exists. The landing then shows no release-status label;
this does not admit publication. The existing publication guard still requires
verified provenance and rejects this status until a separately reviewed no-tag
identity path is provided. Missing `prerelease` remains unavailable.

# GitHub availability

The footer presents GitHub as unavailable without linking to a private repository.
Activation is a separate change after the owner changes visibility and verifies
the exact destination anonymously. Existing source and license links remain active.

## R15 source delta preparation

The R15 source delta is staged only when `OMR_R15_SOURCE_DELTA` names the exact
pinned archive. It contains the changed engine source inputs and notices, not an
installer. The existing 0.3.0 source base and WebKit parts are referenced rather
than copied or replaced. The old base's `omr-pi` is not the R15 binary; its old
manifest does not validate the updated tree. A source delta and static comparison
are not evidence of a successful rebuild or new runtime qualification. Release
remains subject to the R15 publication guard and review of the exact payload.
The private-evidence integration tests accept `OMR_R15_TEST_ARCHIVE`,
`OMR_R15_TEST_SOURCE_MANIFEST` and `OMR_R15_TEST_PREVIOUS_CATALOG`; without
those inputs they report skips rather than reading machine-specific locations.

The retained read-only `ci/check_immutable_releases.py` checks the repository setting
through GitHub; a missing helper, unavailable API, or unconfirmed setting refuses
publication. It does not modify the setting or establish release immutability.
