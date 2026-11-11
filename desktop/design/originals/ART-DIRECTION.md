# Open Model Router — direction artistique fournie par Zacaria

## Autorité et sources

Demande Desktop du 31 octobre 2026 : « Voilà la direction artistique de la landing page ainsi que son logo à adapter et insérer, et l'UI de l'application à décliner sur chaque plateforme ».

Cette direction remplace les choix graphiques précédents, pas le périmètre fonctionnel de DESKTOP-SCOPE.md, DESKTOP-EXECUTION.md, DESKTOP-DISTRIBUTION.md et GOAL.md. Implémenter dans les surfaces existantes, pas un prototype parallèle. Conserver les données réelles, les limites d'accès et la revue indépendante avant livraison.

Originaux fournis, à joindre durablement aux cartes et conserver inchangés :
- `Open_Model_Router_Landing_Page.zip` : index.html autonome, README et quatre captures desktop/mobile. Source `/home/operator/.hermes/attachments/Open_Model_Router_Landing_Page.zip`.
- `upload_2anlrouf.png` : référence de l'interface desktop. Source `/home/operator/.hermes/images/upload_2anlrouf.png`.
- `upload_3smffdyj.png` : logo/icône 3D. Source `/home/operator/.hermes/images/upload_3smffdyj.png`.

## Landing

Reprendre la composition fournie, pas uniquement sa couleur : hero typographique monumental à gauche, diagramme de routage à droite, fond quadrillé subtil, contraste noir-vert / blanc cassé / citron, alternance de sections sombres et claires, démonstration explicative, cartes de capacités, FAQ et grand CTA citron final. Conserver le contraste typographique de l'accent italique à empattements, les titres sans-serif serrés et les métadonnées monospace.

Tokens exacts du HTML : fond #090d0f, fond secondaire #0f1516, surface #131a1b, surface secondaire #192122, blanc #f0f3ea, muted #8f9a95, citron #cff66a, citron lumineux #ddff84, bleu #94caff. Typographies proposées par la référence : Space Grotesk, DM Sans, IBM Plex Mono ; utiliser des fichiers locaux licenciés si disponibles, sinon les replis documentés. Éviter les requêtes externes non nécessaires.

Réutiliser le frontend shadcn/statique existant et ses contrôles accessibles. Français par défaut comme convenu. Adapter les textes à OMR réellement disponible : le SDK TypeScript et l'API du ZIP sont conceptuels, les métriques et choix du simulateur ne sont pas des mesures. Ne pas copier ces promesses ou exemples non implémentés. Remplacer la section d'intégration conceptuelle par le vrai parcours disponible. La référence ne change ni les trois profils Économie/Équilibré/Qualité, ni les limites de distribution privée. Les téléchargements restent désactivés tant que leurs artefacts ne sont pas vérifiés.

## Logo

Employer l'image fournie plutôt qu'un nouveau symbole. Conserver le module central chevron/Y vert lumineux, le flux entrant de gauche et les trois sorties menthe, violet, orange. Préserver les proportions, ne pas étirer ni retracer approximativement le logo.

Adapter cadrage, marges et tailles pour header/footer, favicon et icône d'application. Conserver l'original ; dériver les formats desktop utiles seulement (.ico, .icns, PNG selon packaging existant), sans familles mobile/Store non demandées. À petite taille, une variante monochrome pour tray/menu peut simplifier le symbole central, en gardant son identité et en vérifiant réellement sa lisibilité sur clair/sombre. Documenter le dérivé et son usage ; ne pas confondre le symbole de routage décoratif du ZIP avec le nouveau logo de produit.

## Application macOS, Windows, Linux

Reprendre la structure de la référence : navigation latérale, en-tête de contexte, résumé en cartes, topologie/trace de décision, activité et politique. Même langage visuel sur fournisseurs/modèles, profils, consommation, inspecteur, réglages et états vide/erreur/chargement, pas seulement l'accueil.

Fond presque noir verdâtre, panneaux vert sombre, bordures fines, accent citron réservé aux actions/sélections, légendes techniques monospace, sans-serif lisible. Conserver le thème système/clair demandé ; décliner ce thème sans sacrifier le contraste. Les contrôles et décorations de fenêtre restent natifs par OS : pas de faux feux macOS sous Windows/Linux, ni de sélecteur d'OS du concept dans le produit. Menu macOS, tray et icônes respectent le cycle de vie existant.

La capture est une référence visuelle de simulateur, pas une spécification de télémétrie. Ne pas introduire 12 840 requêtes, 99,2 %, 420 ms, $0.003, scores 85/68/74, confidence HIGH ou faux providers. Brancher les composants sur les états locaux existants ; afficher absence de données/inconnu au lieu d'inventer. Ne pas exposer un prompt à un service pour reproduire la démo. Pas de nouveau moteur ni de nouvelle surface réseau.

## Vérification et propriété

Landing : posséder seulement site/, tests associés et documentation/ressources de marque nécessaires. App : posséder desktop/, ses tests et documentation visuelle ; ne pas réécrire le moteur. Ne pas modifier le canonique sale ni le worktree d'un autre worker. Chaque worker consigne cette décision dans son candidat et préserve les changements selon les conventions déjà autorisées.

Tester parcours existants, clavier, focus, réduction des animations, contraste et débordements ; captures fraîches comparées aux références à dimensions comparables. Landing : desktop et mobile 390/320 px. App : tous les écrans, thèmes clair/sombre, minimum de fenêtre et lecture des petites icônes ; distinguer aperçu du chrome par OS et véritable exécution native. Les builds/replays macOS, Windows, Linux restent dans la release existante et ne doivent pas être déclarés réussis depuis une capture web.

Builder : candidat exact, checks et captures durables, puis request_review vers reviewer. Reviewer : PASS exact seulement, sinon request_changes. Publication landing par sa continuation ; installateurs par t_a3a76415 avec le candidat app restylé et les éventuelles corrections du socle. Aucune dépense, publication sociale, activation fournisseur ni modification de session utilisateur.
