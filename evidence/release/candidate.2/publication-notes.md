# Open Model Router 0.1.0-candidate.2

Préversion de test, pas une validation des quatre intégrations. Le dépôt et ses assets restent privés.

Cette version ajoute la validation incrémentale des flux SSE sans Content-Type sur la route Codex native prévue à cet effet. Les types MIME explicitement incorrects, les trames malformées et les fins de flux tronquées restent contrôlés. Aucun fallback silencieux n'est ajouté.

## Source et vérification

- Commit signé : `7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b`.
- Arbre revu : `dfd45901284f6948d7d86d23b5a38fbb9773afb1`.
- Archive SHA-256 : `3a8ffe5f2557903cd3132f938c0df8a9a118772aa339b6f8ea17ad3637f8c02c`.
- Deux constructions identiques ; 351 fichiers comparés aux blobs Git, permissions comprises.
- Extraction et certification hors ligne : 62 tests racine, 9 tests synthétiques d'adaptateurs et contrôles de la landing réussis. Ces tests ne qualifient pas les hôtes réels.

## Télécharger et vérifier

Depuis un dépôt de confiance contenant le commit ci-dessus, avec Python 3.11+, Git et une connexion GitHub native autorisée :

```sh
gh release download v0.1.0-candidate.2 --repo Zacaria/open-model-router --dir "$HOME/omr-candidate.2-bundle"
python3 build_release.py certify --repo . --revision 7e25c6e7e6547fb9d3bf1f2f1d71602dd3950f3b --bundle "$HOME/omr-candidate.2-bundle" --scratch "$HOME/omr-candidate.2-install"
```

Choisir des répertoires nouveaux, hors du dépôt. Le sous-répertoire `source` produit par la certification contient le cœur utilisable. Suivre `GATEWAY-SPEC.md` pour une configuration locale explicite, sans copier les identifiants des clients. Ne pas employer Python `-O`, `-OO` ou `PYTHONOPTIMIZE` pour certifier.

## Limites connues

Les preuves historiques incluses dans l'archive gardent leur version d'origine. Les nouveaux parcours Codex sont conservés séparément dans le dépôt ; leur réussite native ne signifie pas que le gateway a vérifié la fin complète du transport. Un reçu `cancelled` ne suffit pas à conclure à une annulation par l'utilisateur.

oh-my-pi Mac n'est pas qualifié. La validation cumulée des quatre hôtes et la release finale restent ouvertes. Aucun gain général de performance ou d'économie n'est établi. L'archive ne fournit ni poids de modèle, ni dépendances optionnelles, ni service installé automatiquement.
