# Revue finale bornée — host adapters

**Verdict : NO GO pour le commit de l’arbre exact `fc6f579e1fad31de9e17d8f6aab1d33fd64edfa7` en l’état : une exécution fraîche des 9 tests a échoué, puis une autre a réussi.** La visibilité des erreurs examinée ne montre pas de fuite ; le blocage est la fiabilité du contrôle de fermeture, pas une fuite démontrée ni une demande de qualification macOS.

## Blocage observé

`host-adapters/test_launch.py:50` — `test_upstream_connection_closed_on_failure` a échoué (`Broken.instance.closed` vaut `False`) sur la première exécution complète, puis a réussi sur la seconde. Le client reçoit la réponse 502 avant que le thread serveur n’atteigne nécessairement `finally: c.close()` : le test vérifie immédiatement sans synchronisation. Le test et la fermeture dans `finally` existent déjà dans la baseline GO ; le delta peut modifier l’ordonnancement, mais cette observation ne démontre pas une fuite durable de socket. Stabiliser le test en attendant explicitement la fermeture, puis réexécuter les 9 tests avant GO. Ne pas masquer l’échec par le seul passage suivant.

## Identité et delta

- Comparaison sans écriture Git de chaque entrée mode/blob de l’index : correspondance exacte aux 60 entrées de l’arbre demandé ; six fichiers ajoutés par rapport à HEAD. `git diff --cached --check` propre ; aucun écart suivi index/worktree. SHA-256 de l’index avant et après : `4c5d622ab8f3174cf38c4731f4d037622fe10e49aaae32f37e7060014020e953`.
- Les trois blobs Jev sont exactement ceux du GO de `benchmark-review.md` : `jev_decider.py` `fc0d946c19b9dc6ddcca7bb92f0f3843ad5ca4b7`, `test_jev_decider.py` `c30692b2831ebb386f632b57bf5e7197b2407742`, `JEV.md` `af5346e2cdf67acb6ef7d1c0c0743e680eb3daf4`.
- Baselines host reconstituées **en mémoire seulement** en retirant les deux impressions, le nouveau test socket et le paragraphe documentaire ; les SHA-256 obtenus correspondent exactement aux trois valeurs du GO `host-adapter-review.md`. Ceci établit que le delta est limité à ces ajouts. Les trois SHA-256 actuels concordent avec `evidence/native/error-visibility/source.sha256` : launch `a4ef8463a484a4a5342707ea842da258535257975eb0e7c628c8e13de4175565`, test `49445266f5f8ad2462009733afccbc8870931ce5a61c514fa27692790da0b953`, README `2affd962439cffdf1ea84b14cfaf0e155a633b602b942bd54f648490b0c7f7dd`.

## Vérifications

- Le nouveau stderr imprime uniquement un texte constant et le statut HTTP numérique pour réponse >= 400, ou le texte constant 502 avant en-têtes. Aucun corps, URL, en-tête, clé ou texte d’exception n’est interpolé dans ces nouvelles impressions. Le test socket exige les lignes exactes pour 503 et refus 502 avec secrets synthétiques dans corps, en-tête, URL et authorization. La sortie est celle de l’adaptateur, pas une APIError native.
- Tests frais Linux, environnement réduit et bytecode désactivé : host **8/9 puis 9/9**, Jev **6/6**. Les tests utilisent et nettoient leurs propres répertoires temporaires ; aucun nettoyage manuel, génération de modèle, appel fournisseur, écriture source ou mutation d’index n’a été effectué.
- `error-visibility/REPORT.md` rapporte aussi une invocation Hermes antérieure sur port loopback indisponible : messages 502, timeout 124 et absence de membres vivants du groupe après sortie. Preuve rapportée, non rejouée ; elle ne démontre pas une APIError native ni ne qualifie macOS.

Périmètre limité au delta demandé et aux GO antérieurs ; pas d’audit général ni de qualification fournisseur ou Mac.
