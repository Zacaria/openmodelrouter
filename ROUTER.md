# Tranche locale : exécution avec sélection s1d1

`router.py` accepte un objet JSON sur stdin, une configuration locale et un répertoire de poids s1d1 ONNX. Il choisit une route autorisée selon le premier message puis exécute le programme de cette route, sans shell. Ce programme reçoit la requête JSON entière sur stdin et doit renvoyer un objet JSON avec `answer` et `usage`. La configuration et ces programmes sont du code local explicitement approuvé par l'utilisateur ; leur comportement réseau est sous sa responsabilité. Aucun fournisseur distant n'est intégré ni appelé automatiquement.

Configuration : `{"routes":{"low":["programme", "argument"],"high":["programme", "argument"]},"threshold":0.5,"timeout_seconds":30}`. `messages` contient des objets avec `role` et `content` ; le premier message user seul est soumis au classifieur. La sélection et les données de consommation renvoyées par le programme sont affichées ; celles-ci ne sont pas vérifiées par le routeur. Une défaillance produit une erreur sans relance ni changement de fournisseur. La classification ne transmet rien au réseau si les poids sont locaux. Aucune continuité persistante, politique d'effort, intégration hôte, repli automatique ou estimation de prix n'est revendiquée. Le seuil est expérimental et non calibré, pas une preuve d'économie.

Dépendances à installer séparément : numpy, tokenizers, onnxruntime ; `s1d1_upstream.py` provient du dépôt officiel `scombat/s1d1-router`. Le modèle testé est `scombat/s1d1-router-6src-tiny-onnx-int8`, révision `dac13b5c0356864ea4501fa151d74dcd8b3ea22a`. Aucun téléchargement implicite ni transmission de prompt à Hugging Face : le chemin passé à `--weights` doit exister localement.

Commande : `python router.py --weights /chemin/poids --config /chemin/config.json < request.json`. Les commandes de test simulées ne sont pas des modèles réels ; l'inférence s1d1 locale est réelle mais ne constitue pas un benchmark de qualité.

## Command safety and configurable decision
Child processes receive an empty environment by default, not the parent environment. Configured commands are trusted code, not a sandbox: they retain OS access. A configurable local decision command receives only the first user prompt over stdin, returns {"route":"low"|"high"}, and must be explicitly configured; no remote call is performed by the router. Errors fail closed without retry.
