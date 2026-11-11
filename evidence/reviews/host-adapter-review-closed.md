# Clôture bornée — flake host adapter

**GO — commit signé `2527e02b4a7fbc766edba1f17e18e2e274e6d23b`, arbre `011e2185e22a293130cba489116ed277b558ca8b`.**

Le seul delta par rapport à `fc6f579e1fad31de9e17d8f6aab1d33fd64edfa7` concerne le test de fermeture : événement local signalé par `close()`, attente bornée à deux secondes après la réponse 502. Cela synchronise l’assertion avec le `finally` serveur ; aucune référence à `Broken.instance` ne subsiste dans ce test. Production, README et fichiers Jev inchangés dans ce delta.

- Vérification fraîche : `env -i PATH="$PATH" HOME=/nonexistent PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s host-adapters -p test_launch.py -v` : **9/9**.
- Contrôle négatif exécuté en mémoire : substitution unique de `def close(self): closed.set()` par `def close(self): pass` ; le test ciblé échoue après deux secondes avec `upstream connection not closed after failure`. Aucun masquage observé.
- Avant commit : index identique à l’arbre demandé, six chemins attendus exactement, aucune différence suivie worktree/index, `git diff --cached --check` propre. Après commit : signature vérifiée, arbre et six chemins confirmés.
- Les 6 tests Jev mentionnés par le parent n’ont pas été relancés dans cette clôture. Aucun appel fournisseur ou usage de credentials, aucun push, aucun audit global ni qualification macOS. Les fichiers non suivis préexistants ont été conservés.
