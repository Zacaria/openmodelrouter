# Décideur natif Ollama/SystemOne — contrat D3

## Besoin constaté

Le propriétaire a demandé de tester un décideur servi par Ollama, puis d’automatiser ces parcours localement et dans Actions. L’Ollama DEV 0.40.9 est installé ; une interruption DEV est acceptable. Aucun contrôleur de production, nouvelle sauvegarde ou pipeline de bascule n’est nécessaire.

Les trois appels réels `d3:4b` via `/v1/systemone` ont produit les choix 1, 2, 3 sur GPU. Le parseur `decode_imajev` est correctement strict pour Imajev, mais incorrectement réutilisé comme contrat D3. Sur la base revue `1f48a34685fd63f9690635d134771623f44d45c1`, le coordinateur a rejoué les trois captures : trois `invalid_decision` reproduits.

## Entrée réelle, pas réponse reconstituée

Pièce 522 de `t_254a2310` : `/home/operator/.hermes/kanban/boards/open-model-router/attachments/t_254a2310/d3-observed.ndjson`, SHA256 `37cfe753c8352cee734f6fe4a39f6ed215e052289b5d988beadfe9865a927b2d`. Pièce 523 : script `d3_probe.py`. Les requêtes sont synthétiques ; le fichier contient les réponses réellement observées.

Chaque réponse D3 fournit `model`, `answers.quality` avec `type=choice`, `choice`, `probabilities` et `confidence`, puis un usage réellement déclaré. Elle ne fournit ni `abstained` ni `unknown_probability`. Leur absence n’équivaut pas à false ou zéro. Le digest du modèle observé est `2c571f91caf64c47b6ca6bd3adc1daa07dbb84ead8e9489758498cc7e11e533d`.

## Plus petit correctif utile

Tracer les définitions et tous les appelants : construction SystemOne, décodeur, sélection de protocole/configuration et choix dans l’interface Desktop. Introduire une sélection explicite du contrat natif Ollama/SystemOne compatible D3, sans deviner le fournisseur à partir du nom du modèle ni réutiliser le format chat JSON.

Réemployer le payload et les validations communes avant d’ajouter un module ou une abstraction. Garder la validation stricte d’identité, question, type, probabilité finie/bornée, normalisation, choix maximal et confiance. Ne pas supposer que confiance égale probabilité maximale : les captures montrent deux valeurs distinctes. Ne pas fabriquer de champs d’inconnue/abstention ou tokens. Les champs autoritatifs d’abstention éventuellement présents ne doivent pas être ignorés pour obtenir une route.

Imajev conserve exactement ses exigences d’abstention/inconnue ; lui transmettre la réponse D3 doit toujours échouer. Le nouveau contrat accepte la réponse D3 telle quelle. Les réponses malformées, erreurs et refus restent fail-closed, sans générateur appelé, retry ou fallback caché. Ne pas changer les critères ni la calibration d’Imajev : t_3f4a6103 porte ce diagnostic séparément.

Le froid D3 observé vaut 30,743 secondes, puis 0,045/0,050 à chaud. Tenir compte de cette observation dans le budget du nouveau protocole, sans enlever échéance globale ou annulation ni masquer le problème par préchauffage implicite. Mettre à jour tous les appelants si une fonction partagée est renommée ; pas d’alias de compatibilité spéculatif.

## Vérification et remise

Docs d’abord, RED sur les captures et le protocole, plus petite implémentation, tests comportementaux des erreurs/annulation et non-régression Imajev. Préserver les réponses originales dans les fixtures avec provenance. Vérifier le typecheck et les contrôles pertinents de l’interface si sa sélection change.

Coordonner uniquement les essais GPU avec t_3f4a6103 ; les travaux CPU restent indépendants. Qualifier le vrai routage D3 vers le générateur Ollama autorisé, avec données synthétiques et instance isolée. Réemployer le probe OMP existant ; t_818420c6 a déjà prouvé sur CPU qu’un UUID `X-OMR-Session` éphémère et stable est nécessaire au cycle outil dans la configuration native OMP 18.16.0. Ne pas inventer ce header dans le moteur ni supprimer `continuity_route_unavailable` ; déclarer la configuration réellement testée.

Conserver commande, version, reçu, modèle choisi et limites : replay de capture, HTTP contrôlé, inférence native, moteur source, OMP réel et app active sont des preuves distinctes. Pas de remplacement de l’app personnelle, nouveau tunnel, frais ou extraction de secrets. Fournir un candidat signé/poussé puis demander revue native au profil reviewer sur cette même carte. Clôture sur PASS exact seulement. Transmettre à t_818420c6 le commit et les fixtures pour intégrer le correctif revu à la suite locale/CI ; ne pas modifier le worktree de ce writer.
