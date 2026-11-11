# OMR Desktop — décisions du 4 novembre 2026

Source : demande Desktop de Zacaria, session `20261104_023430_d1de52`.
Ce complément prévaut sur les limites historiques incompatibles des cartes ; les protections de GOAL.md restent applicables. Le board `open-model-router` reste le seul suivi d'exécution.

## Résultat demandé

1. Harmoniser les formulaires et contrôles avec l'interface existante, sans boutons ou sélecteurs natifs visuellement étrangers ; conserver clavier, focus et accessibilité. La barre de menus macOS utilise une déclinaison reconnaissable du véritable logo OMR fourni, pas un pictogramme générique.
2. Simplifier l'ajout d'un fournisseur : choix du type, valeurs usuelles, paramètres avancés seulement lorsque nécessaires. Réutiliser les transports et validations existants, notamment pi-ai. Synchroniser réellement l'interface et un fichier de configuration lisible et éditable : sauvegarde depuis l'UI, modification manuelle puis chargement effectif. Afficher le chemin et l'action de rechargement. Ne pas confondre un export avec cette synchronisation ; refuser une configuration invalide sans perdre la dernière valide et détecter les modifications concurrentes. Les secrets restent dans leur stockage natif, jamais dans le fichier partageable ni les journaux.
3. Configurer les accès disponibles Codex, Ollama, LiteLLM et OpenRouter sur le Mac. Zacaria indique que LiteLLM est disponible sur la tour : vérifier depuis le véritable appelant, réutiliser les endpoints et accès autorisés, ne pas redéployer LiteLLM. Une absence, un refus ou un catalogue vide ne bloque que ce fournisseur. Ne pas inventer ses modèles ou une génération réussie ; distinguer configuré, découvert et vérifié. Préserver sessions et réglages existants avec sauvegarde privée et vérification après écriture. Aucun achat ni frais supplémentaires.
4. Exposer ensemble, dans les sélecteurs compatibles, les trois modes Économie, Équilibré et Qualité et tous les modèles directs admissibles des fournisseurs connectés. Ne pas se limiter à l'alias unique `open-model-router`. Réutiliser le catalogue mixte existant, corriger son raccordement et qualifier l'affichage côté client. Une sélection directe ne passe pas par le décideur et ne substitue ni fournisseur, modèle, ni effort. Ne pas inventer une traduction de protocole non supportée.

## Autorité de livraison

Zacaria confirme que les itérations et la signature des DMG sur le Mac n'exigent pas de nouvelle autorisation par tentative ; une itération de développement peut rester non signée. Les corrections, pushs privés ordinaires, reconstructions, signatures et relances techniques nécessaires sont autorisés dans le périmètre existant, sans nouveaux frais ni export de clé. Les anciennes limites « une seule tentative puis redemander » ne sont plus un motif d'attente d'autorisation.

Conserver les contrôles d'identité des candidats, la revue indépendante pertinente, la protection des secrets, les sessions personnelles et les règles de publication applicables. La signature/notarisation ne bloque pas le développement ni les essais indépendants autorisés ; un build ad hoc n'est pas une distribution Apple qualifiée. Les protections d'isolation réelles restent en place : ne pas qualifier le profil personnel par des tests destructifs ou par un simple HOME simulé. Pas de changement TCC ou de capture non autorisée.

## Vérification proportionnée

Docs puis régressions comportementales RED, correction minimale et checks du dépôt. Vérifier le parcours de configuration bidirectionnel et les refus d'entrée invalide/concurrente ; le catalogue réellement exposé et le bypass direct ; les contrôles rendus et le logo de tray ; les connexions depuis le Mac avec prompts synthétiques et sans frais nouveaux. Identifier séparément source, build natif, accès fournisseur, signature et livraison. Un fournisseur indisponible n'empêche pas de livrer les autres. Préserver les preuves et faire avancer la continuation existante plutôt que créer une nouvelle architecture de harnais ou un orchestrateur concurrent.
