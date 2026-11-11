# OMR Desktop — déclinaison de la direction fournie

## Direction actuelle — refonte du 6 novembre 2026

Cette révision remplace la palette citron de la direction historique ci-dessous : papier `#f7f6f2`, panneau `#fdfcf9`, encre `#202b25`, forêt `#245642`, sélection `#e8eee7`. Le sombre utilise des surfaces vert-noir et un accent sauge accessible. Un titre serif local contraste avec les contrôles sans-serif et les métadonnées monospace. Aucun changement de logo ou d’icône native.

Référence réellement générée par Codex : `image_gen.imagegen`, PNG 1568 × 1003 conservé dans `/srv/omr-private/artifacts/open-model-router/desktop-redesign-20261106/omr-desktop-concept.png`, avec prompt et reçu `receipt.json` adjacents. Le modèle d’image exact n’est pas exposé par l’outil. Composition retenue : navigation calme, fil de contexte compact, résumé de service horizontal, action Chat visible, topologie sans grille décorative, activité et connexions. Les radios de profil, connexions fictives, compteurs et raccourcis illustratifs de l’image ne sont pas transposés comme fonctions ou faits.

Les sections suivantes décrivent la provenance et les contraintes de la direction antérieure ; la palette et composition présentes ici les remplacent. Les frontières natives, de consentement, de secrets et de release restent identiques.

## Source et périmètre

Le delta visuel part du candidat figé `53af7f470a6d1a430b34f7c047a62351b274067f`. Il possède uniquement `desktop/` : aucune modification du moteur ni du socle en revue parallèle. La release compose les deux deltas finaux revus, sans remplacer les corrections du socle par cette base antérieure.

La consigne originale et les deux PNG sont conservés inchangés dans `design/originals/`. Le logo produit est `upload_3smffdyj.png`, pas le symbole décoratif de la maquette. Aucun chiffre, fournisseur, score ou test simulé de la référence ne devient une donnée produit.

## Langage visuel

| Rôle | Sombre | Clair |
| --- | --- | --- |
| Fond | `#090d0f` | `#f0f3ea` |
| Fond secondaire | `#0f1516` | `#e8ede3` |
| Panneau | `#131a1b` | `#fafcf6` |
| Surface secondaire | `#192122` | `#e4ebdf` |
| Texte | `#f0f3ea` | `#17251e` |
| Texte secondaire | `#a3afa8` | `#536458` |
| Action citron | `#cff66a` | `#cff66a` |
| Survol citron | `#ddff84` | `#ddff84` |
| Sélection texte | `#cff66a` | `#38551b` |

Le gris secondaire est éclairci par rapport au token landing `#8f9a95` pour les petites légendes desktop. Les contrôles ont des bordures distinctes, un focus visible et des libellés ; couleur seule et animation ne portent aucune information. Sans nouveaux fichiers de fontes licenciés disponibles, utiliser les fontes locales : titres/sans `Segoe UI`, `SF Pro Display`, système ; métadonnées `SFMono-Regular`, `Cascadia Code`, `Consolas`, monospace. Aucune requête de fonte externe.

Navigation latérale, contexte en en-tête, cartes de résumé, topologie et activité/politique reprennent la composition de la référence. Fournisseurs/modèles, profils, consommation, inspection, réglages, boîtes de dialogue, états vide/chargement/erreur partagent les mêmes tokens. Le thème suit le système ; le choix clair/sombre dans Réglages est temporaire jusqu’au prochain lancement et ne persiste aucune donnée web.

## Topologie et inspection

La topologie représente le catalogue local actif : trois profils, leur disponibilité liée au décideur consenti et le nombre de modèles directs autorisés. La dernière route n’est surlignée que depuis un reçu réellement observé ; elle est explicitement historique, jamais une requête animée en cours. Sans reçu, afficher « Aucune route observée ». La révision et les règles sont celles de la configuration active, pas du brouillon non enregistré.

L’activité ouvre les reçus réels dans un inspecteur lisible : route, modèle confirmé ou inconnu, usage, motif structuré, contraintes et métadonnées complètes dépliables. Les valeurs manquantes restent non mesurées ; aucun prompt ni réponse n’est introduit. Tous les contrôles existants et commandes IPC restent raccordés.

## Adaptations natives et marque

Les décorations de fenêtre restent fournies par l’OS. Aucun feu macOS, faux titre système, sélecteur d’OS ou chrome web n’est ajouté. Le minimum existant reste 800 × 640 ; les colonnes se replient sans masquer les actions et les tableaux peuvent défiler dans leur propre zone.

Les PNG desktop, ICO Windows et ICNS macOS sont dérivés du logo fourni, proportions conservées. Une extraction du signe de routage avec son entrée et ses trois destinations sert au template monochrome macOS ; le tray Windows/Linux emploie un dérivé compact du même signe, citron sur plaque sombre. Aucun symbole redessiné. Génération reproductible et provenance : `scripts/build_brand.py` et `design/BRAND.md`. Pas de formats mobile/Store.

Menus, tray, fermeture, arrêt confirmé, coffre OS, consentement aux générations et à l’envoi de contexte restent inchangés. La barre de menus macOS utilise le template natif ; Windows/Linux gardent l’icône contrastée. Les nouveaux réglages d’apparence ne déclenchent aucune commande moteur.

## Composition avec le socle corrigé

`desktop/src/App.tsx` est un hotspot avec `t_01bf8649`. Ce delta ne modifie pas `changeConnection`, le consentement du décideur ni les handlers `setQuitting` / `setForce` de la base. Il ajoute le thème en mémoire, déplace l’autostart dans Réglages, remplace le hero décoratif, traduit les statuts des reçus et ouvre leur détail structuré. `components/ui.tsx` rend le focus au déclencheur après fermeture ; cette restauration ne doit pas remplacer l’invalidation de l’accord d’arrêt forcé dans le socle corrigé.

La base `53af7f4` n’est **pas livrable seule** : le reviewer du socle (commentaire 182) a reproduit le consentement réutilisé après changement de destination/décideur, l’accord d’arrêt forcé retenu après annulation et un changement concret de route pendant un cycle d’outils après hot-config. Leur correction appartient au candidat socle. Release doit préserver ses handlers et sa continuité moteur, intégrer seulement ce delta visuel, puis revoir/tester les octets composés. Les tests verts du restylage ne constituent pas une levée de ces trois réserves.

`src-tauri/src/main.rs` ne change que l’image et le flag template du tray. `scripts/native_replay.py` se déplace vers Réglages pour l’autostart et appelle le replay visuel optionnel ; conserver aussi les nouvelles régressions du socle lors de la composition. Aucun fichier moteur, IPC, capability ou manifeste de sécurité n’est modifié ici.

## Vérification et frontière release

Tests frontend de la topologie et des reçus sans valeurs inventées ; contrôles de provenance/formats et de contraste. Rejouer les parcours natifs Linux existants sur profil isolé avec API synthétique locale effectivement appelée, puis parcourir tous les écrans clair/sombre et le minimum de fenêtre. Comparer les captures fraîches avec la référence et les icônes aux tailles 16/24/32/64 px sur les deux fonds. Une capture WebKit Linux ne qualifie ni macOS ni Windows : build, installation et surfaces système de ces OS restent dans `t_a3a76415`. Le mandat ultérieur [DESKTOP-DELIVERY.md](design/delivery/DESKTOP-DELIVERY.md), avec sa [distribution mise à jour](design/delivery/DESKTOP-DISTRIBUTION-20261031-public.md), autorise les installateurs/checksums publics depuis le site existant. La chaîne continue jusqu’au téléchargement anonyme et à l’installation réelle dans `t_29098b54`, sans nouvel accord public et sans rendre le dépôt public.
