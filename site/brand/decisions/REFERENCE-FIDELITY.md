# Landing OMR — fidélité au pack de référence

> Décision historique : le nouveau contrat [bilingue](BILINGUAL-REFERENCE-REPAIR.md) prime sur le titre et les autres prescriptions contradictoires ci-dessous.

## Décision propriétaire

Le propriétaire rejette les écarts encore importants entre la landing publiée et le ZIP fourni. L'équipe doit inventorier elle-même les différences et les corriger ; aucun questionnaire ou inventaire manuel n'est demandé au propriétaire. Le héros doit porter exactement : **Pour chaque requête, le bon modèle**. Des critiques et une revue indépendantes sont obligatoires. Claudio peut participer ; il ne remplace pas la référence par une nouvelle direction.

## Sources et périmètre

- Référence : `site/brand/originals/Open_Model_Router_Landing_Page.zip` ; SHA-256 `71c59a4592cf8ac7b37ea04b125ef43ddb8b90e3c5e8455af8613a41733c456d`.
- Extraction durable identique : `/home/operator/.hermes/artifacts/open-model-router/reference-pack/` ; six fichiers : HTML autonome, README, captures desktop et mobile.
- Production à comparer : `https://open-model-router.vercel.app/`, publication issue de `7184b0f6564d7188ac686b597e652cf5d8b5b86e`.
- Source de départ : même commit ; writer isolé dans `landing-reference-fidelity-v2`. Aucun changement de l'application Desktop ni des installateurs.
- Réutiliser les composants, polices locales, assets et outils présents. Ne pas remplacer la page par une image, introduire un framework ou créer une nouvelle identité.

## Travail demandé

Comparer **toute la page** : navigation/logo, héros et schéma, section claire de constat, démonstration interactive, quatre cartes d'architecture et leurs illustrations, intégration/code, FAQ, CTA final et footer. Le titre signalé est un exemple concret, pas le périmètre complet de la correction.

Pour chaque section, vérifier l'ordre, les hauteurs, la largeur de contenu, les espacements, la palette, le quadrillage/lueurs, les bordures/angles, les familles/poids/tailles de police, les retours à la ligne, le contraste, les icônes et illustrations, ainsi que les états animés, sélectionnés, au survol et au focus. La référence utilise notamment DM Sans, Space Grotesk, IBM Plex Mono et Georgia en italique : inspecter ses valeurs effectives, ne pas deviner les polices sur une vignette.

Conserver un registre concis de tous les écarts : section, preuve référence/production, gravité, correction et validation. Distinguer les écarts à réparer des adaptations nécessaires au français, aux capacités réelles et aux téléchargements. Les critiques examinent d'abord le rendu sans reprendre les verdicts PASS antérieurs. Une parité entre staging et production ne prouve pas la fidélité au ZIP.

## Vérité produit et copie

Conserver les données réelles, chiffres justifiés, disponibilités et avertissements matériels. Le README du ZIP demande lui-même d'adapter les promesses, modèles et API conceptuelle aux capacités réelles. Ne pas réintroduire de statistiques fictives, SDK inexistant, compatibilité ou disponibilité non prouvée pour ressembler à la maquette. Les adaptations doivent conserver sa composition, pas devenir des paragraphes de justification.

Employer un français naturel sur toute la page. Utiliser la phrase du héros verbatim, avec une mise en emphase et des coupures de ligne cohérentes avec la référence. Retirer les commentaires de fabrication, sans retirer la distinction de démonstration synthétique ou les limites nécessaires à l'installation. Conserver les téléchargements anonymes et leurs empreintes.

## Vérifications indépendantes

1. Critique visuelle indépendante : référence et production rendues à largeur identique, desktop1440 et mobile390 au minimum ; inspection réelle des images, section par section. Les PNG du pack sont des références utiles, son HTML permet de vérifier les comportements et éventuels artefacts de capture.
2. Critique éditoriale et comportementale indépendante, avec Claudio : français, promesse, correspondance des contrôles et états à la référence, animations, navigation, FAQ, copie et cohérence des CTA. Pas d'exécution facturée supplémentaire ni de copie d'identifiants.
3. Builder corrige le registre entier, y compris ses propres constats ; les critiques ne modifient pas son workspace. Le travail de préparation/hero/rendu peut commencer pendant les audits, mais les deux rapports doivent être consommés avant remise finale.
4. Reviewer distinct du writer : candidat exact, captures référence/candidat aux mêmes dimensions et états, avant/après complets et détails. Un PASS fonctionnel seul ne suffit pas ; tous les écarts matériels restent ouverts jusqu'à correction ou justification factuelle précise.
5. Clavier/tactile, petits écrans, menu, FAQ, copier, changement de scénario, pause/réduction du mouvement, sans JavaScript et téléchargements restent vérifiés. Exécuter les contrôles existants pertinents sans réécrire leurs assertions pour cacher les écarts.

## Publication et continuité

Release seule publie après PASS exact. Relire le manifeste courant pour conserver tous les binaires, checksums et OS disponibles, y compris ceux éventuellement ajoutés entre-temps. Payload public minimal, sans ZIP de source ni preuves privées. Vérifier anonymement les octets et le comportement publié puis transmettre le nouveau commit et manifeste à `t_29098b54`. Les chantiers natifs macOS/Windows restent indépendants ; ne pas publier un installateur non qualifié.

L'accord du propriétaire couvre l'ajout des compétences nécessaires aux profils concernés. Avant de forcer un skill sur une carte, vérifier son chargement dans le profil réel ; ne pas reproduire la panne de préchargement release. Ne pas modifier Hermes core, les garde-fous, les secrets, les limites de dépenses ou les workers existants.
