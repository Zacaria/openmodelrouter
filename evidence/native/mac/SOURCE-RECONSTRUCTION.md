# Reconstitution de la source du préflight Mac

Le paquet historique `source.tar.gz` est omis : il contenait seulement `omr.py` et `source-manifest.json`, déjà conservé ici. Son arbre intermédiaire `02aee64cd2fde79a6de705c65a22a6e8cbe944b3` n'est pas la tête d'un commit publié.

La source exacte reste reconstructible depuis le commit signé et poussé `bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad`, avec `preflight-source.patch`. Dans un dossier temporaire externe, extraire `git show bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad:omr.py`, puis appliquer le patch avec `git apply`. Ne jamais appliquer ce retour historique dans le code opérationnel : il réintroduit le défaut SSE corrigé.

Reconstruction réellement exécutée dans un répertoire temporaire indépendant, sans modification du dépôt : `git apply --check`, application, puis SHA-256 égal à `1a5390d59458e571379e45c1dfe3e3927592f6ee58b2357ee20442176fd0948b`, conforme au manifeste et au fichier de l'archive originale. Cela préserve le contenu source ; les en-têtes et octets de l'ancien conteneur gzip ne sont pas reconstruits ni revendiqués.

Le constat précédent « aucun commit correspondant à cet arbre » reste exact. Cette reconstitution apporte une conservation durable des octets utiles sans conserver une deuxième archive source.
