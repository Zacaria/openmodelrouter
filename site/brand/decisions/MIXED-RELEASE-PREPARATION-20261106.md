# Catalogue multi-version — préparation du 6 novembre 2026

## Résultat local

La source visuelle acceptée `e643d4ac6dc83d5b2d02a5bc3949ce62009a4501` est intégrée dans la branche Chat, sans changement du backend ni des octets des installateurs. La composition initiale sans modification donnait l’arbre `83c35ba1502ab8be25128684e706617cea51e4e6`.

Le successeur conserve version, source et prérelease par paquet. Le staging refuse encore des identités contradictoires au sein d’une même version. Les panneaux, détails, liens et lignes statiques ne reprennent plus l’identité du premier paquet. Lorsque deux versions existent pour une architecture, les boutons distinguent leur version en plus du format.

Trois échecs ont été observés avant correction : rejet du manifeste mixte, affichage `vundefined` après passage aux métadonnées par paquet, puis deux boutons `.dmg` identiques. Les tests correspondants passent après correction.

## Vérifications

- Types, format, build et suite `npm test` passent. Cette dernière ignore par défaut trois intégrations exigeant les outils de release produit ; l’exécution finale avec les entrées acceptées ci-dessous passe sans ces ignores.
- Les 12 tests de garde, sans ignore, passent avec les quatre outils matérialisés depuis le commit signé `b5a80f3215b28e772f8af19ad467ea923370def7` et vérifiés par identité de blob. Les fixtures Git/GitHub et Vercel sont synthétiques : cela ne constate pas l’immutabilité du dépôt réel ni une publication.
- Brave sandboxé : EN/FR, 10 layouts et 40 scénarios de base ; sélection ARM64/Intel, versions 0.3.0/0.1.0 et conservation de deux DMG ARM64 aux largeurs 320, 390 et 1280. Métadonnées, source et liens des deux panneaux restent cohérents. Les captures synthétiques EN/FR ont été relues, sans clipping observé ; leur taille `0.0 MB` provient des octets de fixture, pas d’un véritable installateur.
- Staging isolé avec fichiers synthétiques : téléchargement/checksum/clipboard et nettoyage des anciens paquets passent sans modifier le `dist/` principal. Les captures et reçus sont sous `/srv/omr-private/artifacts/open-model-router/chat-400-20261105/landing-retained-version-green/` ; les témoins négatifs sont conservés dans les dossiers `landing-mixed-red/` et `landing-retained-version-red/`.

L’essai initial des intégrations avec le checkout Chat a échoué faute de `ci/release_preflight.py` ; ces outils appartiennent à la branche de release acceptée. Les quatre entrées de test ont été extraites dans `accepted-release-tools-b5a80f3/`, sans modifier le worktree produit historique, qui contient encore des modifications locales.

## Raccord du catalogue à la garde

La préparation UI a reçu un PASS indépendant sur l’arbre `2b194c9564876f1c290021f5077aaf1aa43a9ee3`, puis a été signée et poussée dans `e81e9ace8005d4c3e2fdd6f7f789782dd1f2574f`. L’alias public est resté sur son déploiement initial après ce push de source.

Le successeur ajoute `--catalog` avec `--historical-manifest` : `--artifacts` reste limité à la nouvelle release. Le catalogue est lié exactement aux nouvelles entrées puis aux quatre entrées historiques épinglées, avec leur statut de prérelease explicite. La signature et l’identité de la nouvelle release ne remplacent pas la provenance historique ; les deux contrôles restent exécutés. Le HTML est comparé au catalogue complet, les collisions ne concernent que les nouveaux chemins, et la conservation des anciens octets et sidecars reste imposée. Les modes précédents ne changent pas et `--landing-only` est incompatible avec ce catalogue mixte.

Avant correction, le test de provenance historique refusait ce mode et le véritable rendu mixte échouait à la comparaison HTML avec le seul manifeste nouveau. Après correction, le test historique avec tag SSH réellement signé et les 13 tests de garde passent. L’entrée de publication est exercée avec Vercel inerte ; les lecteurs d’identité/immutabilité du scénario mixte sont des doublures dont l’invocation et les refus sont vérifiés. Les autres intégrations de la suite exercent séparément les outils réels sur des fixtures Git signées. Ce n’est pas une qualification d’une release GitHub réelle.

## Action restante avant publication 0.3.0

Faire revoir le raccord exact, puis composer le payload réel avec le DMG signé et les quatre installateurs conservés. Refaire les contrôles de signature, notes, provenance historique épinglée, identité distante, immutabilité, collisions et conservation exacte des anciens octets immédiatement avant publication.

Le DMG signé ARM64 0.3.0 n’est pas publié par cette préparation. Sa revue/admission finale reste distincte des tests UI synthétiques et de la disponibilité des matériaux documentée dans [SOURCE-MATERIALS-20261106.md](SOURCE-MATERIALS-20261106.md).
