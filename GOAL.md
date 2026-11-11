# Open Model Router — contrat de livraison autonome

Décisions acceptées dans la conversation Desktop du 27 octobre 2026, session `20261026_231933_e4f42b`. Ce contrat précise et remplace les restrictions historiques incompatibles du brief et des cartes ; il ne transforme pas leurs anciens résultats en preuves de livraison.

## Résultat attendu

Un routeur local réellement utilisable comme modèle virtuel, à la place d'une sélection fixe telle que `GPT-6.1-terra`, avec choix du modèle et de l'effort lorsque le fournisseur le permet. Cibles obligatoires : Hermes sur la VM, Codex et oh-my-pi sur `mac-worker`, et Claude Code. Ne pas substituer la réussite d'un hôte à celle d'un autre. La cible souhaitée est le 28 octobre 2026 ; ce n'est pas une promesse de délai ni une autorisation de réduire les vérifications.

## Autorité et ressources

- Push sur le dépôt GitHub privé existant `Zacaria/open-model-router`, publication de la landing et releases nécessaires sont autorisés, avec relecture de l'état distant. Conserver la visibilité privée du dépôt sauf instruction contraire. Préparer les articles LinkedIn/X, sans publier sur ces comptes.
- Utiliser les souscriptions existantes, Jev et les modèles déjà hébergés sur la tour si elle est disponible. Ne pas acheter de crédits API, réclamer un budget de 20 € par défaut ni activer une facturation supplémentaire. Respecter les quotas et les modes d'accès supportés ; ne pas copier les secrets ou supposer la portabilité d'un abonnement.
- Essais avec prompts et projets synthétiques ou publics prévus pour publication. Ne pas exporter les conversations privées, données clients ou identifiants. Les identifiants restent dans leur gestion native, jamais dans les logs ou le dépôt.
- Vérifier les services et la charge de la tour avant utilisation ; pas de relance de l'ancien programme Gimli. L'absence de la tour ne bloque pas les autres pistes. Préserver les sessions utilisateur actives ; tester d'abord avec configurations isolées et retour arrière.
- Canonique : `/home/operator/repos/open-model-router`. Nouveaux worktrees liés exclusivement sous `/srv/omr-private/workspaces/open-model-router/`, avec chemin et branche explicites. Aucun clone temporaire sous `/home/operator/repos`. Le canonique n'a pas encore de HEAD : préserver et examiner les fichiers avant le premier commit signé, puis seulement créer les worktrees. Ne pas ajouter caches, poids, dépendances ou secrets à Git.

## Conditions cumulatives de réussite

1. **Quatre intégrations réelles.** Installation documentée et reproduite ; route sélectionnable ; conversation multi-tours ; streaming, appels d'outils et réponses d'outils ; choix réellement transmis au fournisseur ; annulation et erreur contrôlées. Vérifier les capacités de chaque hôte sans falsifier les métadonnées. Conserver commandes, versions, traces expurgées et résultat de chaque parcours. Une route simulée, tiny-gpt2 ou un HTTP 200 ne valide pas une intégration utile.
2. **Routage observable.** Décideur interchangeable, Jev qualifié dans le périmètre autorisé, baseline s1d1 réelle sur le premier prompt avec identité des poids prouvée, effort appliqué ou explicitement non supporté, gestion du contexte et permissions conservées. Pas de bascule silencieuse inter-familles ou vers le local : refus explicite ou mode dégradé préalablement configuré et visible.
3. **Benchmarks reproductibles.** Trois bras réellement exécutés : défaut modèle/effort observé, s1d1 premier prompt, décideur configurable. Couvrir simple, code avec tests, diagnostic ambigu, difficulté changeante et sous-agents. Figer jeux développement/validation et critères avant ajustement, répéter indépendamment les cas, conserver ordre, cache, versions, échecs et données manquantes. Mesurer réussite, durée, tokens par catégorie, surcoût des décisions et reprises, moyennes et dispersion. La valeur équivalente des tokens et une baseline repricée à volume identique sont des estimations distinctes des comparaisons exécutées et de la facture de souscription. Comparer les routes locales lorsqu'elles sont disponibles, sans prétendre qu'elles ont gagné.
4. **Dossier éditorial.** Rapports d'essais, scripts de reproduction, résultats bruts expurgés, tableaux/graphiques et brouillons exploitables pour LinkedIn/X. Distinguer résultat positif, négatif, non mesuré et limite. Ne pas chercher artificiellement un pourcentage d'économie ; un résultat négatif documenté est valable, mais ne valide pas une intégration absente.
5. **Livraison.** Source récupérable sur GitHub avec contrôles pertinents, revue indépendante du candidat exact, release identifiable et réinstallable, landing publique vérifiée sur desktop/mobile, liens fonctionnels et instructions conformes au produit. Refaire les parcours des hôtes sur la version livrée. Une archive locale, un plan ou des cartes terminées ne suffisent pas.

## Boucle et arrêts

Budget accepté : 500 tours de continuation pour le goal. Ce plafond ne désactive ni les permissions, ni les garde-fous, ni l'arrêt demandé par le propriétaire.

À chaque blocage technique : établir la cause, faire une tentative proportionnée ou changer d'approche, puis avancer sur les travaux indépendants. Ne pas répéter une action inchangée, réclamer des accords déjà acquis, interrompre un worker sain ou considérer une remise intermédiaire comme la fin. Les quotas attendus appellent une attente native bornée, pas une boucle d'appels agressive. Une dépendance ne bloque que son consommateur.

Le goal ne peut être déclaré atteint qu'avec les cinq conditions vérifiées. Si toutes les pistes utiles autorisées sont épuisées, si un accès humain est indispensable ou si le plafond est atteint : conserver l'état, fournir le blocage précis et les alternatives essayées, puis suspendre honnêtement ; ne pas supprimer un garde-fou ou fabriquer un succès.

## Reprise opérationnelle

Le board `open-model-router` est le suivi de tâches. Aucun worker n'y était actif lors de cette préparation. Réutiliser la chaîne existante : `t_b039cae4` attend un candidat stable issu de `t_f7609a9d`, puis `t_dab1958b` doit poursuivre l'intégration. La revue d'une tranche synthétique ne doit pas être un préalable artificiel à la préparation indépendante des adaptateurs ou de la landing. La carte `t_5228779f` reste l'acceptation globale, pas un second orchestrateur concurrent.

Candidat corrigé durable : `/home/operator/.hermes/kanban/boards/open-model-router/attachments/t_f7609a9d/candidat-t_f7609a9d.tar.gz`. Landing existante : `/home/operator/.hermes/kanban/boards/open-model-router/attachments/t_a92ab1b1/open-model-router-landing.zip`. Vérifier leurs empreintes et contenus avant intégration. Séparer les writers et la revue ; pas de nouvelle décomposition récursive du même livrable.

La session goal coordonne l'exécution et initie les étapes techniques éligibles ; elle ne doit pas attendre la fermeture de toutes les cartes pour commencer. Au retour de chaque worker, vérifier le résultat et avancer la chaîne sans demander à Zacaria de relayer.
