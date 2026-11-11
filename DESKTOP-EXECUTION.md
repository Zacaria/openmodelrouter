# OMR Desktop — contrat d'exécution parallèle

## Autorisation et résultat

Zacaria a autorisé, dans Desktop `20261030_224613_eb22ab`, les deux travaux en parallèle et choisi shadcn/ui avec https://github.com/agmmnn/tauri-ui comme base. `DESKTOP-SCOPE.md` contient les besoins et parcours de vérification ; `GOAL.md` conserve ses limites de coût, données et activation. Livrer le socle sans attendre compaction/délégation ; ces deux capacités restent un chantier indépendant, pas abandonné.

Base source des nouveaux worktrees : `c9fbada2f2392a3e5db27a70c84e4f685081586c`. Le canonique contient README.md modifié, ROADMAP.md et DESKTOP-SCOPE.md non suivis au départ ; ne pas le nettoyer ni y écrire depuis les workers. Les copies du cadrage attachées aux cartes sont les entrées figées. Les branches natives Codex/OMP contiennent d'autres candidats : ne pas les intégrer ou les activer sur la seule foi d'un ancien rapport, et ne pas lancer de réparation concurrente de leurs cartes existantes.

## Répartition de propriété

- **App / socle** : `desktop/`, passerelle et tests nécessaires au catalogue mixte, politiques, configuration et reçus ; documentation d'installation. Propriétaire exclusif de l'intégration du moteur actuel. Préserver les fonctions et garde-fous existants, sans réécriture Rust du routeur.
- **Stratégies avancées** : modules/additions dans `advanced/`, preuves et tests dédiés, contrat d'intégration. Lire le moteur mais ne pas modifier `omr.py`, `desktop/` ou les sources d'un autre worktree. Fournir l'interface minimale réellement justifiée par une compaction ou délégation exécutable, pas un framework de plugins spéculatif.
- **Release socle** : consommer uniquement le candidat exact revu de l'app, préparer les paquets et vérifier chaque plateforme disponible. Aucun parent sur les stratégies avancées.
- **Intégration avancée** : consommer le socle effectivement livré et le candidat avancé revu ; appliquer les raccords nécessaires dans son propre worktree, puis revue exacte avant activation/release.

Chaque carte builder emploie `request_review(reviewer="reviewer")` après checks et préservation, plutôt que `complete`. Sur la même carte, le reviewer reste en lecture seule, complète uniquement sur PASS et utilise `request_changes` pour une correction. Les preuves/captures doivent être attachées durablement avant passage en revue. Les releases vérifient le verdict exact et ne prennent jamais un statut seul pour une approbation.

## Socle à produire

App autonome Tauri v2, React/TypeScript/Vite, shadcn ; tauri-ui inspecté à `8eb86d894c19b6df04ff883ab28b412b1e5f23ea`. Réutiliser les seuls éléments utiles et leurs mentions de licence ; épingler ce qui est exécuté. Ne pas activer ses workflows de publication optionnels. Ne pas confondre un starter compilé avec l'application demandée.

Brancher les écrans sur de vrais états locaux : état/service, fournisseurs et modèles, profils/règles, consommation et inspecteur. Pas de chiffres de démonstration présentés comme usage réel. Le moteur est embarqué sans demander Python à l'utilisateur ; menu macOS, fenêtre accessible sur Windows/Linux, arrêt explicite et fermeture sans interruption implicite. Stockage de secrets adapté à l'OS, aucun secret dans le frontend persistant, JSON exporté ou logs. Interface de contrôle locale authentifiée ou IPC natif minimal ; pas de nouveau service public.

Les trois modèles virtuels et routes directes partagent l'observation, pas la décision : direct contourne le décideur. Les politiques automatiques sélectionnent seulement parmi les routes autorisées/compatibles, considèrent effort et coût de transition, respectent le budget tokens et messages et conservent le modèle quand changer n'est pas justifié. Le décideur reste interchangeable. Toute transmission de contexte à un décideur externe exige une configuration explicitement consentie ; le chantier lui-même utilise uniquement des exemples publics/synthétiques autorisés. Ne pas livrer un classifieur constant ou des heuristiques arbitraires comme preuve de qualité.

## Stratégies avancées à produire

Établir les capacités réellement exposées par Hermes, Codex, Claude Code et OMP pour compacter et déléguer. Réutiliser les mécanismes natifs sans modifier Hermes core. Développer et exécuter le plus petit parcours supporté avec contexte synthétique, puis comparer maintien/switch/compaction/délégation avec leurs coûts complets. Préserver les permissions, instructions, couples outils/résultats et annulation. Aucun appel d'outil à partir de contenu non fiable sans les permissions du client. Un proxy ne peut déclarer une action native réussie sans preuve.

Produire une matrice supporté/non supporté/non vérifié, les adapters réellement utilisables et leurs tests. Un client inaccessible ne bloque que son essai ; les fixtures qualifient les contrats hors ligne, pas l'intégration native. Si aucune stratégie native n'est accessible, conserver le candidat et remonter le blocage précis sans marquer le chantier fonctionnellement livré.

## Préservation, revue et livraison

Docs puis tests RED, implémentation minimale et vérification. Préserver les deltas source et docs utiles sur les branches de travail avec les conventions de signature/revue établies ; push privé autorisé par GOAL.md, jamais force-push ou release automatique issue du starter. Avant une mutation Git vérifier l'état exact et l'absence d'un autre propriétaire. Ne pas committer dépendances, builds, secrets ou transcripts. Inclure la copie autorisée de DESKTOP-SCOPE.md et ce contrat dans le candidat app.

Exercer les parcours UI réels, inspecter le rendu et joindre captures lisibles. Tester l'app native au moins sur l'hôte disponible, puis fournir les builds/replays par OS ; ne pas appeler une compilation croisée une validation native. Les accès Mac/Windows utilisent les voies déjà autorisées, sans inventer de compte ou toucher une session active pour obtenir une preuve. Le manque de signature/notarisation ou d'accès d'un OS se rapporte exactement, sans achat ni simulation de signature.

Continuer les étapes éligibles jusqu'au résultat demandé, pas seulement au scaffold. Pas de décomposition récursive concurrente. Les pauses, erreurs et limites sont consignées sur la carte propriétaire ; utiliser le cycle natif de revue/correction et les dépendances, pas de nouveau scheduler. `t_5228779f` reste l'acceptation globale historique et ses gates restent intacts. L'extension desktop ne transforme pas une intégration Codex/OMP bloquée en réussite.

## Suivi

Board : `open-model-router` ; tenant : `omr-desktop-v1`. Cartes et identités figées attachées dans `desktop-task-map.json`. Ce fichier est un contrat, pas une seconde liste de progression. Source de la demande et réception des événements : session Desktop `20261030_224613_eb22ab` ; continuité de coordination via le canal projet déjà abonné, sans relancer le goal historique.
