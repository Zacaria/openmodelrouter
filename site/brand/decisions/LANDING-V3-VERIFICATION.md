# Landing v3 — vérification du candidat local

## Limite de livraison

Carte `t_e047617c`, branche locale `work/landing-v3-20261101`, base signée `c9954673d9da71f93d60bd39c957a7238efa0f2c`. Le commit contenant ce document est le candidat ; son SHA exact et l’inventaire de preuves sont remis avec la demande de revue. Aucun déploiement, publication, tag ni push n’a été exécuté. Le canonique sale, les autres worktrees et les données de release n’ont pas été modifiés.

Le correctif réutilise React au build, shadcn, les fontes et le logo existants. L’original de logo livré dans l’archive v3 est identique pixel par pixel RGBA à `brand/originals/upload_3smffdyj.png` (les fichiers PNG ont des encodages différents). SHA-256 de l’archive de spécification : `8142a3211ddaf1dcb5ac729bafcfcdf0602df936c68f8764bd0a463cc1caf362`.

## Comportements livrés

- Un composant de téléchargement dans le hero et la disponibilité ; état OS/architecture/format unique. Le SHA, les notes et avertissements suivent exactement le paquet. Un Mac générique reste sans puce choisie. Un Windows/Linux ARM ou un Windows explicitement x86/32 bits ne sélectionne pas implicitement le build x64. Le choix manuel gagne contre les hints tardifs ; aucun stockage de téléchargement n’est lu.
- Diagramme natif sans cadre en perspective, quatre catégories activables et reliées aux radios, à la branche, à l’explication et à l’inspecteur. Aucun score ni appel fournisseur. Les scénarios sont des tâches illustratives, pas des profils ou le mode direct.
- Récit conservé : routage local sur fournisseurs configurés, profils et mode direct distincts, éligibilité, inspection, usage observé/estimé/non mesuré, clients visés et limites. La répétition de la carte Inspector a été supprimée au profit de l’inspecteur intégré et de l’usage.
- EN/FR indexables, notes et FAQ natives, menu fermé par lien/Échap/clic extérieur avec JS, sélection de langue avec ancre et stockage refusé, focus visible, défilement réduit, grille mobile lisible. Sans JS : liste complète des vrais liens/checksums, navigation, menu natif, radios, explications et inspecteur fonctionnent encore.

## Source publique et téléchargements réels

Les HTML publics correspondent au payload historique, pas à un checkout propre identifiable par son seul HEAD. Les empreintes publiques avant/après l’intégration initiale `4939038` sont restées identiques ; ce relevé distant n’a pas été répété pendant la correction R1 :

| Route | SHA-256 public |
| --- | --- |
| `/en/` | `0e43d9facdcaf1fba5f051cf1940afb72f8dfe4c3f31513356294c8b57573388` |
| `/fr/` | `af8b829b989d8da4c8ade9cb03505101e1b41a8ef75f98336503f9e94cb6a496` |

L’input de preview est `site/artifacts/v3/input/manifest.json`, copie séparée du manifest historique avec `prerelease: true` conservateur, justifié par le draft GitHub de même source. Ni la garde ni l’input historique ne sont affaiblis. Ce fichier n’est **pas** un manifest de nouvelle release approuvée. La release privée 0.2.0 n’a pas été substituée aux téléchargements publics 0.1.0.

Pendant l’intégration initiale, les quatre URL publiques ont été intégralement lues, avec statut 200, longueur exacte et hash des octets concordant avec les sidecars et les binaires locaux ; il ne s’agit pas d’un simple HEAD. Pendant R1, les quatre paquets et sidecars locaux ont été revérifiés ; aucun nouveau téléchargement distant n’est revendiqué :

| Paquet 0.1.0 | Octets | SHA-256 |
| --- | ---: | --- |
| macOS arm64 DMG | 12993046 | `7068e309d31fc0d5851bcc5d7360a2c11ac9e2d4c41e35fb5baa15713563a691` |
| macOS x64 DMG | 13747988 | `7c2a7efdfa70450206019cb49a5e7c8e693a87761abbb1d930cd61235eda6c81` |
| Windows x64 EXE | 10945241 | `caa933c6b07df21963428f11fd50cc63ad01e844bd8b2384db2f68ce5519f9c8` |
| Linux x64 DEB | 26091712 | `8e9e3d19bf95a6271f20a956ffa5e8b22c7f2c9801e0f2bfb8dd1ec85f37d9b8` |

La vérification des octets ne prouve pas l’installation ni la génération réelle. Les avertissements synthétiques, macOS/Rosetta/onboarding et Windows non signé restent visibles.

## Commandes exécutées et résultats

Depuis `site/`, Node 24.21.0, Brave Linux via Playwright :

```sh
npm ci
OMR_DOWNLOADS_MANIFEST="$PWD/artifacts/v3/input/manifest.json" npm run build
npm run check
npm run format:check
OMR_PRODUCT_CHECKOUT=/srv/omr-private/workspaces/open-model-router/t_b8abbd3c-product npm test
npx html-validate dist/en/index.html dist/fr/index.html
OMR_TEST_EVIDENCE_DIR=artifacts/v3-r1/browser npm run test:browser
npm run test:staging
npx tsx scripts/verify-landing.tsx artifacts/v3/input/manifest.json dist
# Invocation locale de check_static_payload, pas de publish().
git diff --check
```

Les nouveaux tests SSR/sélection ont été observés rouges avant l’implémentation, puis verts. Après R1, `npm test` : **60 tests**, zéro échec ni skip ; les onze tests de garde incluent les trois intégrations au candidat produit signé. Build, TypeScript, Prettier et validation HTML passent. L’inventaire exact du payload vérifie **24 fichiers / 64 583 152 octets**, y compris les quatre paquets et sidecars. La garde a reconstruit les scripts/CSS/assets et comparé le HTML au manifest sans appeler sa fonction de publication. Les messages de refus et erreurs de mismatch imprimés par les tests négatifs de garde sont attendus ; le résultat final des onze tests est `OK`.

Brave : **16 layouts EN/FR**, **64 états de scénarios**, **18 cas de détection**, **4 scans axe sans violation**, **32 captures**. Largeurs 320, 390, 768, 1024, 1280, 1440, 1534 et 1920 ; le viewport 1534 est en 1534×960. Clavier et focus, synchronisation des deux panneaux dans les deux sens, checksum copié et refus de clipboard, vrai clic de téléchargement avec hash du fichier reçu, no-JS, stockage refusé, langue racine et ancre sont exercés. Aucune requête tierce du site ni erreur console/page/réseau n’a été relevée.

Le staging synthétique vérifie DEB/AppImage et garde le focus sur le format choisi ; il refuse les paquets non qualifiés et nettoie les paquets périmés. Ses preuves sont séparées dans `artifacts/downloads-active/`. Une assertion garantit qu’il ne remplace ni `dist/index.html` ni le rapport réel du candidat. Les captures livrées viennent du build réel 0.1.0, jamais des fixtures.

## Preuves et limites

Les preuves initiales de `4939038`, hashes publics et archive restent intacts dans `site/artifacts/v3/`. Les preuves courantes de R1 (logs rouges/verts, rapports JSON, inventaire, 32 captures, manifest du candidat et archive) sont séparées dans `site/artifacts/v3-r1/`. Les viewports ordinaires hero/scénarios/inspecteur/disponibilité ont été inspectés visuellement en français et en anglais. Une analyse initiale d’image mobile très haute a signalé de faux chevauchements ; les crops des pixels et les viewports ordinaires ont confirmé leur absence. Ne pas juger une capture de 11 000 px uniquement sur sa miniature réduite.

Axe laisse le contraste des fonds à gradients en état incomplet (100 cibles par scan) : aucun certificat WCAG n’est revendiqué. Seize paires explicites de couleurs/tokens et extrémités de gradients ont été calculées séparément ; toutes passent leur seuil AA (4,5 normal, 3 grand texte). Il ne s’agit pas d’une mesure exhaustive de chaque pixel rendu.

Safari, Firefox, appareils physiques, installation native et génération avec fournisseurs ne sont pas vérifiés ici. Les UA/hints sont des états navigateur émulés. Aucun benchmark Lighthouse ni gain de performance n’est annoncé. `npm ci` a signalé deux scripts d’installation non approuvés (esbuild et @parcel/watcher), sans empêcher les builds ; audit npm : zéro vulnérabilité déclarée.

L’ancien cadre/perspective et les règles CSS rendues inutiles ont été remplacés, ainsi que l’ancien hero à doubles CTA. Aucun fichier ni donnée de release n’a été supprimé. Le nettoyage facultatif des anciens scripts `tests/bilingual-browser.mjs` et `tests/motion.mjs` a rencontré une règle de refus de suppression ; ils restent intacts, explicitement historiques dans le README, et ne sont plus des commandes npm courantes. Aucun contournement n’a été tenté.

## Correction R1 après revue de `4939038`

La revue a reproduit un hint `{platform: "Windows", architecture: "x86", bitness: "32"}` activant à tort x64. Le test unitaire ajouté et le navigateur sur le build précédent échouent sur cette sélection ; logs `v3-r1/logs/red-unit.log` et `red-browser.log`. La correction conserve l’architecture détectée `x86` sans paquet sélectionné, ajoute un avertissement EN/FR d’incompatibilité et interdit le rétablissement implicite de x64 par le seul choix Windows, y compris après un aller-retour vers un autre OS. Un choix x64 explicite pour une autre machine reste possible avec l’avertissement visible et le bon checksum.

Les nouveaux cas couvrent x86/32 EN desktop et FR mobile, x86/64 avec UA x86, `Win32` générique, hints 32/64 bits retardés et hints 32 bits après choix manuel. Les cas ARM Windows/Linux et Mac ainsi que le choix manuel avant hint Mac restent verts. Les quatre captures `*-windows32-*` ont été examinées : avertissement lisible, aucun clipping dans l’état bloqué et après choix explicite. La détection reste indicative : sans hint fiable, `Win32` ne démontre pas un OS 32 bits. Aucune installation Windows réelle n’a été effectuée.

Aucun fichier supprimé pour R1 ; seuls détection, traitement du choix OS, textes EN/FR, régressions et documentation ont changé. Les données de release, le manifest historique et les autres worktrees sont inchangés. L’export propre de l’arbre candidat reconstruit un payload identique octet pour octet ; son arbre, commit signé et résultats frais sont liés au manifest de remise hors Git.

**Étape suivante exacte :** nouvelle revue indépendante du commit R1 remis sur cette carte. Pas de déploiement. Une éventuelle release ultérieure exige un manifest explicitement approuvé, un rebuild de ce commit et la garde de publication au dernier moment.
