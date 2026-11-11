# Installer la baseline s1d1

La passerelle seule utilise Python 3.11+ et sa bibliothèque standard. La baseline s1d1 ajoute les trois dépendances déclarées dans `requirements-s1d1.txt`. Installer dans un environnement isolé :

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-s1d1.txt
.venv/bin/python download_s1d1.py --directory ~/.cache/open-model-router/s1d1-dac13b5
```

Le téléchargement est explicite, sans prompt ni identifiant envoyé. Les six fichiers nécessaires sont récupérés sur la révision immuable indiquée dans le script puis contrôlés par SHA-256 avant installation. Un fichier déjà présent et différent provoque un refus, jamais une réparation silencieuse. Le routeur vérifie à nouveau leurs empreintes avant et après chargement. Les poids restent hors de Git.

Déclarer ensuite le chemin dans `decision.weights`, `type: s1d1`, un seuil expérimental explicite et deux noms de routes autorisées `low_route`/`high_route`. La classification utilise seulement le premier message utilisateur ; ce seuil n'est pas un calibrage fourni par l'auteur du modèle. Un UUID de session explicite conserve la route aux tours suivants. Les variantes non reconnues sont refusées, pas présentées comme la baseline vérifiée.
