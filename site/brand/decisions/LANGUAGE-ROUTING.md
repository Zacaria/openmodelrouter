# Choix de langue — comportement du script

Les pages `/en/` et `/fr/` restent des documents pré-rendus et leurs liens de langue fonctionnent sans JavaScript. À `/`, le script choisit d'abord la préférence manuelle stockée (`omr-language`), puis la première langue EN ou FR dans `navigator.languages`, ou `navigator.language` lorsque la liste est absente ou vide ; le repli est EN. Les variantes régionales et la casse sont acceptées. Une URL explicite ne redirige jamais automatiquement.

Un clic sur un lien de langue `data-language` enregistre la préférence lorsque le stockage est disponible et conserve le fragment courant ; le lien reste navigable si le stockage échoue. À la racine, une redirection garde le fragment et remplace l'entrée d'historique pour éviter une boucle au retour. Ces règles ne remplacent pas le prérendu, la traduction ou la validation navigateur du candidat complet.
