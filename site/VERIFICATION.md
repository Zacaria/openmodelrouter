# Vérification — direction artistique de la landing OMR

## Candidat et périmètre

Carte `t_ef5e93f2`, base publiée `b7bcf68eccb4e6426d4af9722bfbb11f43e5b71a`, branche `work/art-direction-landing-20261031`. Le SHA signé exact, l’arbre candidat, les empreintes du build et le readback distant sont dans le handoff Kanban. Modifications limitées à `site/` et `tests/test_landing.py` ; aucun changement moteur, app, workflow ou worktree tiers.

Les originaux fournis sont conservés sous `brand/originals/`, vérifiés par SHA-256. Les décisions de composition et le mandat public actualisé sont dans `ART-DIRECTION.md` et `brand/decisions/`. Le build ne publie aucun de ces documents ni le ZIP de référence.

## Tests exécutés

- RED : le contrat du logo échoue d’abord (`0` occurrence au lieu de deux), puis le contrat de composition échoue sur l’ancienne séquence de sections. Après implémentation, les six tests du contrat passent sur l’HTML construit.
- L’inspection de capture a détecté le texte clair sur le CTA citron. Une assertion navigateur reproduit l’échec (`rgb(240, 243, 234)` au lieu de `rgb(17, 26, 17)`). La règle globale des liens est replacée dans la couche CSS de base ; le test passe ensuite, sans contourner le thème shadcn.
- Installation fraîche `npm ci --ignore-scripts --no-audit --no-fund`, puis `npm run check`, `npm run format:check`, `npm run build`, `npm test`, `npm run test:browser` : PASS. Node 24.21.0, npm 11.19.0, Python 3.13.5. `npm audit --audit-level=moderate` : zéro vulnérabilité signalée. Les suites canoniques Python 3.13 sont exécutées localement, pas présentées comme une exécution GitHub Actions.
- Suites canoniques de `.github/workflows/tests.yml` : 64 tests racine, 16 pilot, 6 loop, 5 comparator, 9 integrated, 6 demo et 9 host-adapters ; 115 découverts, tous passent sauf un test pilot explicitement sauté faute de modèle d’inférence locale configuré. Aucun modèle ni accès fournisseur réel n’est utilisé pour la landing.
- Le build public est une allowlist exacte : HTML, CSS, favicon ICO, deux PNG du logo, trois polices et leurs trois licences. Un rebuild nettoie uniquement `site/dist/` pour ne pas conserver d’anciens fichiers. Les sources, captures et documents privés sont exclus. La reconstruction depuis l’arbre Git exporté et ses résultats sont joints au handoff final.

## Navigateur et accessibilité

Brave headless 153.0.8010.37, serveur loopback du vrai build, sans JavaScript client et avec mouvement réduit. Douze largeurs : 320, 359, 360, 390, 767, 768, 769, 1024, 1100, 1101, 1440, 1920 px. Aucun débordement horizontal ni texte hors viewport. Seize liens vérifiés par clic vers leur fragment ; 21 cibles de tabulation avec focus visible, skip-link effectif et quatre FAQ ouvertes/fermées par Entrée/Espace.

Le groupe radio natif s’utilise aux flèches du clavier. Douze interactions tactiles/souris couvrent les quatre choix à 320, 390 et 1440 px : un seul panneau explicatif visible, sélection cohérente, aucun appel IA ni modèle inventé. Zéro erreur console/réseau et zéro requête tierce ; les polices sont locales.

Axe WCAG A/AA, 2.1/2.2 et bonnes pratiques à 390 et 1440 px, FAQ ouvertes : **zéro violation détectée**, avec un résultat de contraste incomplet sur les fonds en dégradé (`bgGradient`, sélecteurs conservés dans le rapport). Ce n’est pas décrit comme un audit automatique sans réserve.

Le contrôle complémentaire remplace temporairement les fonds dégradés par des enveloppes unies volontairement moins contrastées : `#304235` pour les fonds sombres et `#b8d956` pour le citron. Les bornes RGB calculées du hero sont au plus `(37.69, 50.25, 43.76)` et le fond citron au moins `(199.02, 237.76, 102.68)` ; les enveloppes sont donc conservatrices. Axe contraste passe sans violation ni résultat incomplet sur les quatre profils aux deux largeurs. Les captures restent celles des vrais dégradés, pas de cette sonde.

## Inspection visuelle

Neuf captures fraîches produites par `tests/browser.mjs` : desktop complet et viewport 1440 px ; mobile complet, viewport 320/390 px, diagramme, profils, disponibilité et FAQ. Deux planches juxtaposent les références du ZIP et le candidat à dimensions comparables. La composition est reprise : hero monumental gauche / graphe droit, quadrillage, accent serif italique, manifeste clair, exploration et quatre cartes sombres, parcours clair, FAQ sombre et grand CTA citron.

Les captures complètes mobiles très hautes ont aussi été inspectées par crops ciblés : aucun chevauchement de sections. La navigation mobile reste exposée sur deux colonnes plutôt qu’un menu JavaScript ; elle prend plus de hauteur mais garde ses liens lisibles et directement accessibles. Aucun défaut visuel bloquant relevé dans les dernières captures comparées.

Le logo est dérivé exclusivement du PNG fourni. Le cadrage retire la marge noire extérieure, sans couper la plaque ni ses branches. La planche clair/sombre vérifie les tailles réelles 16/32/48/128 px. À 16 px, l’identité est surtout une signature colorée : les reflets et toutes les ramifications ne sont pas lisibles individuellement. À 32 px, la silhouette est identifiable ; à 48/128 px, le symbole et les trois sorties sont reconnaissables. Les coins noirs de l’original sont conservés, sans détourage ni nouveau dessin.

Ces preuves qualifient la landing locale, pas l’application native. Firefox, WebKit, lecteur d’écran, appareils physiques, publication Vercel et installateurs ne sont pas testés par cette carte.

## Nettoyage et livraison

L’ancienne composition et son ancien favicon SVG de branchement sont remplacés. Les PNG intermédiaires inutilisés 48/256 px sont retirés ; seuls 32/128 px et les tailles ICO utiles restent. Aucun fichier de données n’est supprimé. Dépendances, replay, build et captures restent ignorés ; preuves et payload sont joints à la carte, pas committés comme builds.

Le candidat passe par la revue indépendante demandée, puis `t_5c4e05b7` publie depuis la source exacte acceptée et vérifie l’alias existant avec rollback. `t_a3a76415` livre les paquets ; `t_29098b54` active les vrais liens versionnés et vérifie téléchargements anonymes, checksums et installations. Le mandat autorise déjà cette distribution des installateurs/checksums ; aucun nouvel accord public n’est requis. Aucun déploiement, activation de téléchargement, changement de visibilité ou achat n’a été effectué ici.
