# Démonstration locale intégrée

Le comparateur crée une Session indépendante par cas et bras et conserve son historique entre les tours. Les commandes de génération sont fiables mais non isolées : données synthétiques uniquement. Les permissions outils et sous-agents ne sont pas accordées ; code et délégation restent indisponibles. Le bras s1d1 n'est disponible qu'avec classifieur et politique de correspondance réellement fournis ; aucune politique de sélection n'est inventée. Le défaut fourni ici est simulé, pas une observation OMP.

Le classifieur local peut être activé avec `--weights`, `--threshold`, `--low-route`, `--high-route`. L'identité de fichiers arbitraires n'est pas établie : leur classification est étiquetée `real-local-identity-unknown`, jamais s1d1 vérifié. Les reçus enregistrent les empreintes des fichiers chargés et la politique expérimentale (seuil, routes et modèles/efforts demandés), non calibrée. Si les poids ou le runtime manquent, le bras est indisponible. Une panne de classification ne déclenche pas de repli pour ce bras.

## Reproduction synthétique

Depuis ce dossier :

```sh
python3 example_config.py > /chemin/config.json
python3 demo.py --config /chemin/config.json --output /chemin/resultats.jsonl --seed 0
python3 -m unittest -v
```

Le fichier de sortie doit être nouveau. Pour la classification réelle, lancer avec un Python disposant de numpy, tokenizers et onnxruntime, et ajouter `--weights /chemin/snapshot-local --threshold 0.5 --low-route low --high-route high`. Le seuil 0,5 n'est pas calibré ; dans la configuration exemple les deux routes visent le même modèle simulé. La configuration exemple et son décideur ne représentent pas le défaut observé de l'hôte. Les temps incluent l'appel local au générateur mais excluent le chargement initial du classifieur. Les réponses ne sont pas conservées ; le diagnostic nécessite une évaluation aveugle séparée. Les compteurs vides signifient usage inconnu, pas zéro. Pour un générateur réel de confiance, remplacer explicitement les commandes et métadonnées de route ; ne jamais injecter de données privées.

## Résultats observés le 26 octobre 2026

Résultats historiques de la version précédente : 30 lignes, 18 parcours exécutés, 12 indisponibles, 12 échecs d'oracle exact et 18 non évalués. Six classifications locales et toutes les générations simulées ; l'identité du modèle n'était pas vérifiée dans ces reçus et leur étiquette `real-local-s1d1` ne constitue pas une preuve. Les erreurs exactes ne mesurent pas la qualité d'un modèle ; les temps ne sont pas reproductibles bit à bit.

Une autre exécution historique a relié un classifieur ONNX d'identité non vérifiée, Session et tiny-gpt2 CPU local réel : score 0,184, route `low`, 14 tokens d'entrée et 8 de sortie, 5371 ms côté générateur ; modèle demandé `sshleifer/tiny-gpt2`, effort demandé `unsupported`, modèle et effort appliqués inconnus. Elle n'a pas été évaluée pour la qualité. Les deux routes pointaient sur le même modèle local ; le seuil 0,5 n'établit pas une bonne politique de routage. Les poids et environnements locaux sont éphémères et non inclus.

Tests frais : 4 tests de démonstration, 6 de boucle, 5 de comparateur, 9 de passerelle/fixtures, 9 à la racine et 15 du pilote réussis ; un test pilote d'inférence réelle ignoré sans variables. L'essai réel ci-dessus est distinct. Aucun lint, typage, format ou build canonique n'a été identifié. Les diagnostics de l'éditeur sur les imports dynamiques et attributs de fonction ne constituent pas un contrôle de typage réussi.

## Limites et suite

La passerelle OMP existante n'utilise pas Session : son identité multi-tours, son modèle/effort par défaut et ses permissions effectives ne sont pas établis par cette démonstration. Il faut un adaptateur OMP qui transmette une identité de session fiable et vérifie les capacités, puis une configuration de défaut réellement observée. Les commandes locales ne sont pas sandboxées ; les refus d'outils dans l'enveloppe ne sont pas une preuve d'isolation des processus. Pas de coût, économie, qualité réelle, prise en charge d'outils ou benchmark payant revendiqué. Aucune dépense, publication ni transmission de session privée.
