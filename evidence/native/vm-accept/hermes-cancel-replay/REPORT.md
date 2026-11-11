# Preuve d'annulation Hermes — 27 octobre 2026

**Résultat : positif pour ce parcours local, un seul essai.** L'ancienne preuve est inchangée. Elle montrait `completed` et ne démontrait pas un bug. Aucun rejeu Claude ni route payante.

## Identité et préflight

- Core snapshot et blob `97d2b77d:omr.py` : SHA-256 `ea79ee14a0f3085a479042eb0f5b7ab1848726104428c2ee3e24cff6065b15a4`. Lanceur : `a4ef8463a484a4a5342707ea842da258535257975eb0e7c628c8e13de4175565`. Les cinq fichiers du manifeste `source.sha256` vérifiés avant et après (`preflight.txt`, `after.txt`). Aucun edit ni commit de source.
- Contrairement à l'hypothèse initiale, `/api/ps` était vide au préflight ; GPU 227/16303 MiB, 0 %. L'alias existant `omr-hermes-qwen3-4b:ctx8192` a été chargé automatiquement par le premier tour synthétique. Après : modèle présent, GPU 4164/16303 MiB, 0 % ; il n'a pas été déchargé. Processus GPU préexistants conservés ; aucun arrêt d'un service ou processus utilisateur.
- Projet, home, TMP et configuration séparés ici. L'alias existant est le seul modèle configuré ; pas d'identifiants relayés, données privées ni API payante.

## Exécution et vérifications

Depuis `/srv/omr-private/workspaces/open-model-router/vm-final-accept` :

```sh
curl -sS --max-time 5 http://10.77.0.11:11434/api/ps
ssh -o BatchMode=yes -o ConnectTimeout=5 windows-ops 'nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits && nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader'
sha256sum snapshot/omr.py snapshot/host-adapters/launch.py
(cd snapshot && sha256sum -c ../source.sha256)
git -C /home/operator/repos/open-model-router show 97d2b77d:omr.py | sha256sum
python -B hermes-cancel-replay/replay.py > hermes-cancel-replay/replay.log 2>&1
python -B hermes-cancel-replay/verify.py
```

`replay.py` enregistre les commandes exactes du lanceur dans `initial-result.json`, `cancel-result.json` et `resume-result.json`. Il lance le core intact via `observe.py` : trace bornée sur `do_POST`, après retour de `wfile.write` et `flush`, au premier événement SSE chat contenant un delta texte non vide ; il observe uniquement des métadonnées, puis envoie SIGINT au lanceur. Il n'attend pas le JSONL final du client et ne bloque ni ne ralentit artificiellement le transport. Le prompt demande une liste normale de 400 objets simples.

- `marker.json` : delta texte transmis, terminal non encore vu, socket TCP gateway→Ollama `ESTABLISHED`, groupe enfant `3358403`, SIGINT au lanceur `3358399`. Le marqueur n'enregistre pas l'ID de requête ; le rapprochement au reçu s'appuie sur l'unique reçu `cancelled` dans la séquence de ce rejeu et sur l'UUID de session du lanceur, non sur un ID inscrit dans le marqueur.
- Reçu `e5306cd4-3480-47e5-99e3-523550271682` : `cancelled`, amont HTTP 200, session `864bb3bb-55f8-4636-8ddd-9cf04c3f1962`. `checks.json` inclut aussi d'autres reçus initial/reprise : ne pas les attribuer à l'annulation.
- Exit 130 ; après attente bornée, socket amont absente et aucun processus non-zombie dans le groupe enfant observé. La fermeture de socket ne prouve pas l'arrêt du calcul GPU.
- Reprise effective avec le même ID natif `local-84837aaeb4b38688678aa4d036182343d6d0218d310a020e67b98cfa76354c77`, exit 0 et rappel correct du code synthétique `blue-otter-73`.
- `python -B hermes-cancel-replay/verify.py` : PASS. Un seul essai d'annulation ; pas de seconde tentative nécessaire. Résultat limité à Hermes, à ce candidat et à cette route ; pas une acceptation globale.

Les traces et métadonnées sont dans ce dossier. `preflight.txt` et `after.txt` contiennent les commandes/mesures effectives. La commande de statut Git lancée depuis le dossier de preuve non Git a échoué sans rien modifier ; le statut ultérieur avec `git -C /home/operator/repos/open-model-router status --short` a fonctionné et montre des éléments non suivis préexistants/concurrents, non inclus dans cette preuve.
