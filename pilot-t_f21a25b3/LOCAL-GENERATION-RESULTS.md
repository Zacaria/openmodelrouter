# Vérification locale — 26 octobre 2026

La commande `python3 -m unittest -v`, avec `OMR_GENERATOR_PYTHON` pointant vers l'environnement Python isolé et `OMR_GENERATOR_WEIGHTS` vers les poids locaux, a exécuté 16 tests avec succès. Un appel CLI a traversé `safe_router.py`, un décideur de test et `local_generator.py` avec le prompt synthétique « The capital of France is » : route low, modèle tiny-gpt2, effort `unsupported`, 12 tokens d'entrée et 8 de sortie ; réponse « stairs » répétée. Cela démontre une génération CPU réelle mais pas une réponse correcte ou utile. Le décideur était simulé ; cette exécution ne démontre pas le bras s1d1 avec génération réelle.

Le générateur utilise PyTorch 2.14.1+cpu et Transformers 4.57.6 ; poids publics `sshleifer/tiny-gpt2`, révision `5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be`, téléchargés dans le scratch puis chargés avec `local_files_only=True`. Pour reproduire, installer ces versions dans un environnement isolé, télécharger cette révision dans un dossier local, puis exécuter :

```sh
OMR_GENERATOR_PYTHON=/chemin/venv/bin/python OMR_GENERATOR_WEIGHTS=/chemin/poids python3 -m unittest -v
```

Sans ces variables, seul le test d'inférence réelle est ignoré. Les poids et dépendances ne sont pas inclus dans le dépôt. Une commande configurée reste un programme de confiance avec accès au système ; l'environnement vide n'isole pas le réseau ni les fichiers. Ne pas utiliser de données privées.

OMP a été installé dans le scratch et `omp --version` a renvoyé `omp/18.13.0` avec Bun 1.4.4 dans le PATH. Ce n'est pas une intégration : aucun fournisseur virtuel, streaming, outil ou appel OMP au routeur n'a été testé. Les métadonnées d'effort ne sont pas appliquées par le générateur. Les bras du comparateur, les autorisations hôte, le repli génératif et les familles restent à intégrer ; aucun résultat économique ou benchmark de qualité réelle n'est revendiqué. Aucun appel payant, session privée, déploiement ou publication.
