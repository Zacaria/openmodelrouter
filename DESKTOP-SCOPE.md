# OMR Desktop — périmètre de réalisation

Statut : lancement autorisé par Zacaria dans la session Desktop `20261030_224613_eb22ab` : « Oui tu peux lancer les deux travaux en parallèle ». Le socle utilisable et les stratégies compaction/délégation avancent indépendamment ; la première livraison n'attend pas ces stratégies avancées. Cette extension ne remplace pas les critères de livraison existants de GOAL.md. Le board `open-model-router`, tenant `omr-desktop-v1`, porte l'avancement ; ce document reste le contrat de périmètre.

## Décisions utilisateur acquises

- Application autonome sous Tauri pour macOS, Windows et Linux : installer l'app doit suffire pour disposer du moteur OMR, sans installation manuelle de Python.
- Sur macOS, présence dans la barre de menus, à la manière d'Ollama.
- Configurer les différents fournisseurs et modèles disponibles.
- Voir les tokens utilisés et les économies, ainsi que les statistiques de routage par modèle.
- Inspecter et contrôler le comportement du routeur.
- Régler une échelle coût ↔ qualité des réponses. L'utilisateur a précisé que « performance » désignait la qualité, pas la vitesse.
- Un même réglage économie-qualité couvre API et abonnements : optimiser les ressources nécessaires à la tâche, sans confondre tokens, tarifs et quotas.
- Exposer les trois profils Économie, Équilibré et Qualité comme modèles virtuels sélectionnables dans les clients compatibles. Permettre également le choix direct d'un modèle d'un fournisseur connecté via OMR.
- Réévaluation pendant la conversation activée par défaut en mode automatique, avec option pour la désactiver. Comparer le coût de changement selon la longueur du contexte au coût de maintien du modèle.
- Considérer comme alternatives au changement direct une délégation à un sous-agent avec consignes ciblées, ou une compaction avant changement. Ce sont des stratégies produit demandées, pas des capacités déjà qualifiées pour tous les clients.
- Référence des économies : modèle/effort que l'utilisateur aurait utilisé sans OMR ; proposer par défaut le modèle le plus utilisé dans les conversations récentes observables, avec possibilité de le remplacer.
- Inspection : conserver les traces de décision par défaut, pas le texte intégral des conversations. L'utilisateur juge sa conservation non tenable et souhaite faciliter le retour vers l'application source lorsque ses liens de conversation le permettent.
- La quantité de contexte transmise au décideur doit être configurable : budget en tokens comme réglage principal, plafond facultatif de messages récents. Principe accepté ; valeurs par défaut à mesurer.
- S'inspirer du fonctionnement documenté d'OpenRouter Auto Router pour éviter de réinventer le parcours de décision. Cette orientation ne rend pas OMR dépendant de leur service cloud et ne suppose pas disposer de leurs données agrégées.
- Interface shadcn/ui choisie par l'utilisateur ; base proposée explicitement : https://github.com/agmmnn/tauri-ui . Référence inspectée : révision `8eb86d894c19b6df04ff883ab28b412b1e5f23ea`, scaffolder Tauri v2 + shadcn, licence MIT déclarée par GitHub/README. Vérifier la licence et le code réellement repris avant utilisation ; garder les mentions requises.

## Choix de réalisation et propositions détaillées

Deux surfaces : un menu compact pour l'état et les commandes rapides ; une fenêtre pour les fournisseurs, le routage, la consommation et l'inspection. Fermer la fenêtre laisserait OMR actif ; quitter serait une action explicite. Démarrage à la connexion configurable. Sous Linux, garder la fenêtre accessible indépendamment de la disponibilité du tray.

Réutiliser le moteur Python existant et ses validations ; qualifier son embarquement par plateforme plutôt que réécrire le routage en Rust. Les changements nécessaires au moteur restent à définir : le curseur et la gestion complète des fournisseurs ne sont pas supposés déjà implémentés.

Choix réversible de démarrage : frontend React/TypeScript/Vite et composants shadcn, avec les seuls ajouts desktop utiles de tauri-ui. Pas de serveur Next.js, backend cloud, tableau de bord de démonstration conservé ni métriques fictives dans le produit. Navigation : vue d'ensemble, fournisseurs/modèles, routage, consommation, inspecteur. Afficher les états vide, inconnu, erreur et fonctionnalité non disponible ; conserver l'accessibilité clavier et le thème système. Épingler les dépendances, limiter les permissions Tauri, et ne pas activer un workflow de publication automatique issu du scaffolder.

### Fournisseurs et modèles

Configurer les connexions et modes d'accès réellement supportés ; découvrir les modèles lorsque le fournisseur le permet et autoriser une déclaration manuelle sinon. Distinguer modèle annoncé, configuré, joignable et vérifié par génération. Activer/exclure les modèles et leurs capacités/efforts autorisés. Une souscription ne prouve pas un accès API portable. Ne pas stocker les secrets dans les exports, reçus ou journaux.

### Consommation et économies

Séparer les tokens observés d'entrée, sortie, cache et raisonnement lorsque disponibles, sans additionner des catégories qui se recouvrent. Inclure le surcoût des décisions et les appels échoués lorsque leur usage est connu ; ne pas remplacer une donnée manquante par zéro.

Séparer consommation réelle, coût API estimé et éventuelle facture réelle. Un modèle moins cher ne signifie pas moins de tokens. Une référence de comparaison doit être explicite : le repricing des tokens observés au tarif d'un modèle de référence donne une estimation monétaire à volume constant, pas des tokens économisés ni une exécution contrefactuelle. Des différences de tokens exigent des exécutions comparables ; afficher non mesuré en leur absence. Les tarifs API ne traduisent pas automatiquement les quotas d'une souscription.

Proposition de calcul du défaut historique : utiliser uniquement les métadonnées déjà observées par OMR ou explicitement autorisées, en priorité les choix directs de l'utilisateur, pour ne pas transformer les propres décisions automatiques d'OMR en préférence utilisateur. Afficher la période et la règle de fréquence ; sans historique admissible, demander une référence plutôt qu'en inventer une. Conserver la référence/version utilisée dans chaque comparaison afin qu'un nouveau défaut ne réécrive pas silencieusement les économies historiques. La fenêtre et la règle de fréquence restent à préciser.

### Catalogue unifié : profils automatiques et modèles directs

Proposition d'identifiants, non encore implémentés : `omr/economy`, `omr/balanced`, `omr/quality` pour les trois politiques. Ce sont trois préférences de routage sur les modèles admissibles, pas trois modèles fournisseurs fixes. Chaque requête désigne son profil ; un réglage global ne doit pas écraser le profil explicitement choisi par un client.

Pour les modèles directs, proposer un espace distinct `direct/<connexion>/<modele>` avec identifiants opaques stables et correspondance exacte vers le modèle amont. La connexion distingue deux accès au même fournisseur. Le choix direct court-circuite le décideur : aucun appel de classification, aucune substitution silencieuse de modèle, fournisseur ou effort. Les contrôles d'accès et capacités, le proxy et les statistiques restent actifs. Une incompatibilité ou indisponibilité produit une erreur explicite.

Présenter dans les statistiques le mode automatique/direct, le profil demandé et le fournisseur/modèle effectivement observé ; conserver inconnu quand cette dernière identité n'est pas confirmée. Ne pas présenter une requête directe comme une économie obtenue par le routage automatique.

Un catalogue ne suffit pas à garantir l'affichage dans tous les sélecteurs : qualifier chaque client et chaque contrat de protocole. Exposer uniquement les combinaisons supportées ; ne pas supposer une traduction universelle entre Chat Completions, Responses et Messages. Le code actuel ne constitue pas cette fonctionnalité : omr.py n'accepte encore que `open-model-router` comme modèle demandé.

### Inspection et contrôle

Deux notions distinctes : l'analyse du contexte pour décider du routage et l'inspecteur destiné à l'utilisateur pour comprendre les décisions. Décision acceptée : métadonnées et motifs structurés par défaut, sans conservation du texte intégral. Ne pas faire fuiter des extraits de conversation dans les motifs, titres ou erreurs. Un éventuel diagnostic avec contenu reste une proposition distincte, non autorisée par cette décision. L'accès transitoire du décideur au contexte et sa transmission éventuelle à un fournisseur doivent être cadrés séparément ; absence de journalisation ne vaut pas consentement de transmission.

Proposition de retour à la source : action « Ouvrir la conversation » si l'intégration fournit un identifiant et un lien vérifiés ; sinon afficher l'application source et un identifiant de corrélation disponible. Ne pas déduire un lien à partir d'un identifiant OMR sans correspondance établie, ni importer le transcript pour compenser l'absence de lien. Valider schéma et destination avant ouverture ; ne pas conserver de jeton ou contenu privé dans le lien. Aucun support de deeplink n'est qualifié par ce cadrage seul.

Prévoir une répartition par fournisseur/modèle, des durées, erreurs et usages ; une trace locale par décision montrant candidats admissibles, politique/version, réglage coût-qualité, choix, effort, résultat observé et motif effectivement produit. Ne pas inventer d'explication si le décideur n'en fournit pas ; ne pas enregistrer les conversations par défaut.

Les trois profils expriment une préférence de sélection, pas une garantie de qualité ni un score mesuré. La latence reste une métrique distincte. L'app configure les politiques derrière les profils ; la nécessité d'un curseur continu supplémentaire reste à confirmer, sans le présupposer pour la V1.

Proposer sélection automatique ou modèle imposé, exclusions et politique de repli explicite. Aucun changement ne doit contourner les permissions ou capacités. Le moteur actuel conserve une affinité en mémoire, perdue au redémarrage ; la réévaluation demandée reste une évolution à construire. Éviter tout redémarrage implicite interrompant les conversations.

### Réévaluation et coût de transition

Orientation acceptée : classification de la tâche, filtrage des modèles compatibles et autorisés, classement selon le profil coût-qualité, puis préférence de continuité tant qu'un changement ne justifie pas son coût. Réutiliser le décideur interchangeable ; ne pas imposer l'entraînement d'un nouveau classifieur comme préalable. Les trois profils OMR partagent ce mécanisme, avec politiques distinctes ; ne pas copier mécaniquement les bandes de prix OpenRouter comme des scores de qualité.

Différence à préserver : OpenRouter documente un classement par dépenses agrégées de ses utilisateurs. OMR ne doit pas prétendre reproduire ce signal à partir de son seul historique local. Proposition de démarrage : classement explicite fondé sur capacités, coûts documentés et évaluations disponibles par tâche, puis confrontation aux résultats locaux vérifiables. Un appel réussi ou un modèle populaire ne prouve pas la qualité d'une réponse. Les données externes de ROADMAP.md restent un enrichissement optionnel, pas une dépendance cloud obligatoire. N'activer que les replis configurés ; ne pas reprendre un ensemble par défaut non autorisé.

En mode automatique, comparer les stratégies admissibles : conserver le modèle, changer avec le contexte nécessaire, compacter puis changer, ou déléguer une sous-tâche ciblée en conservant le modèle principal. Inclure coût de décision, contexte retransmis, cache réellement connu, génération attendue, compaction et échanges de délégation ; distinguer estimations et consommation observée. Ne pas considérer le maintien comme gratuit ni un cache inter-modèles comme acquis. Éviter les changements répétitifs sans bénéfice attendu suffisant ; la qualité et la continuité font partie de la comparaison.

Proposition de point de décision : chaque nouveau message utilisateur, sans changement au milieu d'un cycle d'outils en cours. La désactivation de la réévaluation fige le choix automatique ; une sélection directe reste hors de ce mécanisme.

Qualifier séparément les capacités du client/hôte avant d'activer délégation ou compaction. Un proxy seul ne doit pas prétendre lancer les sous-agents du client ni modifier durablement son historique. Préserver les instructions, permissions, identités d'appels/résultats d'outils et état de travail ; ne pas compacter silencieusement une représentation opaque. Si une stratégie n'est pas disponible, l'indiquer et comparer les seules stratégies réellement supportées, sans fabriquer une délégation ou une compaction réussie.

## Parcours de première livraison — proposition de vérification

Ces parcours traduisent les décisions en résultats observables. L'implémentation parallèle est désormais autorisée ; l'activation sur les sessions existantes reste soumise aux garde-fous et vérifications de GOAL.md. La première livraison peut exclure l'activation de compaction/délégation, avec état visible et continuation distincte.

1. **Installer et connecter.** Sur chaque OS cible, installer l'app sans installation manuelle de Python, connecter un accès supporté et effectuer une génération de test explicite. Distinguer configuration valide, accès disponible et génération réussie ; un test consommant des ressources ne se lance pas silencieusement. Sur macOS, retrouver le menu OMR après fermeture de la fenêtre.
2. **Choisir automatique ou direct.** Dans chaque client cible qualifié, sélectionner les trois profils ou un modèle direct et vérifier le modèle/effort réellement utilisés. En direct, aucun appel au décideur ni substitution ; en automatique, seules les routes autorisées et compatibles sont candidates. Vérifier streaming, outils, erreur et annulation selon GOAL.md.
3. **Adapter sans perdre la conversation.** Exercer une conversation à difficulté variable, avec cas où conserver le modèle est préférable et cas où changer est justifié. Vérifier le coût de transition, la continuité des outils, la désactivation de la réévaluation et le respect du budget de contexte. Compaction et délégation ont chacune une preuve distincte sur les hôtes supportés ; leur absence ne doit pas être masquée par une démonstration de simple changement.
4. **Comprendre la consommation.** Retrouver dans le tableau de bord les usages des générations, décisions et opérations auxiliaires, sans double comptage ni zéro fabriqué. Modifier la référence de comparaison et distinguer les estimations des mesures ; une économie négative reste visible. Ouvrir une décision et retrouver ses contraintes, sa stratégie et son résultat sans transcript conservé.
5. **Garder la maîtrise.** Exclure un modèle, changer les limites et simuler une indisponibilité : les nouvelles décisions respectent les réglages, les opérations en cours ne sont pas interrompues silencieusement et aucun repli non autorisé n'est utilisé. Restaurer une configuration précédente sans écraser une modification concurrente ; vérifier l'absence de secrets et texte des échanges dans les traces/exportations.

## Décisions encore ouvertes

1. Contexte du décideur : budget de tokens principal et plafond de messages facultatif acceptés ; les deux limites s'appliquent ensemble lorsqu'activées. Détails de conception proposés : prioriser la demande courante et les échanges nécessaires à sa compréhension ; ne pas couper arbitrairement une structure d'outil. Comptabiliser séparément l'extrait conversationnel et l'enveloppe du décideur (politique, catalogue, métadonnées), avec un plafond total explicite. Estimation signalée si le tokenizer exact n'est pas disponible. Signaler la réduction de contexte et définir un comportement explicite si la demande courante seule dépasse le budget ; aucune extension ou synthèse payante silencieuse. Cette sélection ne réduit pas le contexte transmis au modèle qui répond. Valeurs par défaut à mesurer ; consentement de transmission externe et éventuelle escalade restent à préciser.
2. Profondeur du contrôle avancé, modes d'accès fournisseurs prioritaires et portée des changements de politique. Préciser notamment le changement explicite de profil/modèle au sein d'une conversation sans réutiliser une affinité contradictoire.
3. Qualifier les mécanismes de délégation et compaction par hôte dans le chantier indépendant ; leur disponibilité ne bloque pas la première livraison du socle, décision désormais acceptée. Ne pas les retirer du besoin ni prétendre à une qualification native obtenue uniquement avec des fixtures.

## Références inspectées

- README.md, omr.py : passerelle Python, configuration et reçus existants.
- ROADMAP.md : surveillance externe des modèles et routage dynamique prévus, non supposés livrés par l'app.
- Documentation officielle Tauri : tray et binaires auxiliaires. Leur existence ne qualifie pas le packaging OMR ni les trois systèmes cibles.
- OpenRouter Auto Router, documentation officielle consultée pendant le cadrage : https://openrouter.ai/docs/guides/routing/routers/auto-router ; annonce officielle : https://openrouter.ai/blog/announcements/introducing-the-new-auto-router/ . Ces sources décrivent classification, classement par dépenses agrégées, bandes de coût et préférence de maintien par session. Elles ne précisent pas la fenêtre interne de messages/tokens lue par le classifieur et ne documentent pas de réglage dédié de cette fenêtre. Ne pas assimiler le tableau `messages` reçu par la passerelle au contexte effectivement analysé par le classifieur.
