# Landing — décision de composition

> Historique : les choix de copie, de langue, de visualisation et de contrôle du mouvement ci-dessous sont remplacés, en cas de contradiction, par [BILINGUAL-REFERENCE-REPAIR.md](brand/decisions/BILINGUAL-REFERENCE-REPAIR.md). Cette décision impose la correspondance EN/FR avec le HTML fourni, sans supprimer les limites réelles du produit.

## Sources et autorité

Direction de Zacaria du 31 octobre 2026 : [original](brand/originals/ART-DIRECTION.md). Les trois références sont conservées sans modification dans `brand/originals/` : ZIP de landing, capture de l'app et logo PNG. Ces sources ne sont jamais copiées dans `dist/`.

| Original                           | SHA-256                                                          |
| ---------------------------------- | ---------------------------------------------------------------- |
| ART-DIRECTION.md                   | 76b1cbd628a181a4f37819794e79d8ac902773244c3dd9bd9d25d48a5109e9f6 |
| Open_Model_Router_Landing_Page.zip | 71c59a4592cf8ac7b37ea04b125ef43ddb8b90e3c5e8455af8613a41733c456d |
| upload_2anlrouf.png                | 24425ea597068d0c9f9ca601d8a36bdcbe0de6ed7480d1b463bc49f9c21b60a0 |
| upload_3smffdyj.png                | e07bb3cfb80edc8e5be8ec2f74959330784a934bf9f850ae08450c86ee8bfd05 |

## Comparaison avant modification

Base publiée : `b7bcf68`. Le frontend existant prérend React/shadcn et Tailwind en HTML/CSS sans JavaScript client. Sa composition claire, ses petites cartes arrondies, sa typographie système et son schéma vertical diffèrent du ZIP. Le ZIP est un HTML autonome anglais avec polices Google distantes, simulateur de quatre tâches, API TypeScript conceptuelle et métriques de politique fictives. Il ne devient pas une nouvelle application.

## Adaptation retenue

1. Conserver le frontend existant et les primitives shadcn. Hero monumental à gauche, accent serif italique citron, graphe horizontal à droite, quadrillage et halo discrets.
2. Reprendre la séquence : hero sombre, manifeste clair, explication des profils sombre, quatre cartes graphiques, parcours Desktop clair, FAQ sombre, grand CTA citron, footer sombre.
3. Remplacer le simulateur par une exploration native des trois profils et du mode direct, sans résultat simulé ni appel réseau. Chaque préférence explique son rôle ; aucune mesure ni recommandation de modèle n'est inventée. Remplacer le code SDK par les étapes de configuration réelles.
4. Garder disponibilité, limites locales, clients visés et distinctions consommation/coût/facture de la page existante. Les installateurs restent en préparation et sans lien. La publication appartient à la continuation dédiée.

## Livraison autorisée

Le mandat reçu pendant cette carte autorise la chaîne jusqu’aux installateurs et checksums téléchargeables anonymement depuis le site existant, puis installation et parcours réel sur chaque OS. Il ne reste aucun nouvel accord public à demander : [DESKTOP-DELIVERY.md](brand/decisions/DESKTOP-DELIVERY.md) et [distribution mise à jour](brand/decisions/DESKTOP-DISTRIBUTION-20261031-public.md). Le dépôt et les sources restent privés. Le présent candidat conserve les états en préparation tant que les paquets ne sont pas vérifiés. `t_5c4e05b7` publie cette landing revue ; `t_a3a76415` livre les paquets ; `t_29098b54` active les liens réels et vérifie les téléchargements anonymes/installations, sans exposer les originaux de marque ni les archives sources.

## Ressources

Logo : dérivés PNG carrés du logo fourni, sans étirement ni nouveau dessin. Le cadrage carré `(96, 92, 1156, 1152)` retire seulement la marge noire extérieure de l’original 1254 × 1254 : la plaque, le flux entrant et les trois sorties restent intacts. Ce cadrage augmente leur place utile dans le header et les petites icônes. Usage header/footer (48 px CSS sur desktop, source 128 px), nœud central du graphe et favicon 32 px + ICO multi-tailles (16/32/48 px). Reproduction : `python3 scripts/derive-logo.py` depuis `site/`, Pillow requis uniquement pour régénérer les dérivés, pas pour construire le site. Aucun dérivé app/tray n'est produit par cette carte. Les fichiers de taille favicon conservent les branches colorées ; le test visuel porte sur leur silhouette à taille réelle sur clair et sombre.

Polices : Space Grotesk (titres), DM Sans (texte), IBM Plex Mono (métadonnées), fichiers locaux sous licence OFL et notices conservées. Replis : Arial/sans-serif, system-ui/sans-serif, SFMono-Regular/Consolas/monospace. Accent italique : Georgia/Times New Roman/serif, comme le ZIP. Aucune requête de police distante à l'exécution.

## Vérification

Tests sur l'artefact construit, liens d'ancre, navigation clavier et contrôles natifs sans JavaScript. Captures comparées aux références à 1440 px et 390 px, contrôle additionnel 320 px et largeurs intermédiaires ; audit axe, mouvement réduit, absence de requêtes tierces et erreurs. Voir `VERIFICATION.md` pour les résultats du candidat exact.
