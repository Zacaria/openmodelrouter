# Benchmark synthétique v2 — critères figés avant exécution

« Synthétique » qualifie les tâches et les données, pas nécessairement l'inférence. La campagne réelle locale du 27 octobre 2026 utilise ce jeu inchangé : plan dans `evidence/campaign/STUDY.md`, résultats, reçus et graphiques dans `evidence/campaign/attempt-2/` du dépôt canonique. Elle ne compare pas les abonnements ChatGPT/Claude et ne prouve pas les quatre intégrations.

`benchmark_runner.py` produit 10 cas par famille et par jeu (100 au total), version `synthetic-v2-static-20261027`. Le hash SHA-256 du jeu est enregistré dans chaque reçu. Ne pas modifier validation après consultation des résultats : versionner un nouveau jeu. Les cas sont générés par gabarits : ils ne constituent pas 10 problèmes indépendants par famille et ne satisfont donc pas l'exigence de diversité du protocole complet. Les résultats n'autorisent pas une conclusion générale.

- Simple : réponse numérique exacte.
- Code : interpréteur AST dédié à `transform(x)` : une fonction, un return, expressions `x`, entiers (valeur absolue ≤ 1000), `+`, `-`, `*` et signes unaires, profondeur ≤ 32 ; aucun appel, attribut, import, récursion ou exposant. Les réponses brutes ou un unique bloc fenced Python sont acceptés. Pour x = -3, 0, 1, 9, les valeurs sont comparées à la référence et les tests effectivement effectués figurent dans `code_test_results`. C'est un oracle borné, pas une sandbox de code général ni une preuve d'équivalence pour toute entrée.
- Diagnostic : premier tour JSON avec deux hypothèses et test prévu, puis appel effectif de la fixture lookup et JSON cause/preuve exact. L'outil renvoie un résultat synthétique figé.
- Conversation : les deux réponses numériques et la contrainte initiale sont vérifiées ; le second tour demande une somme composée.
- Sous-agent : outil delegate exécutant une génération enfant HTTP sur la même gateway, UUID de session différent, contexte enfant limité à sa tâche, réponse enfant et synthèse exactes. Cela prouve une délégation orchestrée par le runner, pas la capacité native d'un hôte à déléguer.

Chaque parcours a un budget partagé de cinq appels HTTP parent/enfant, un plafond demandé de 256 tokens par appel et une échéance partagée ; aucun retry. Le plafond de tokens dépend du respect de `max_tokens` par la gateway/fournisseur et n'est pas un plafond financier. L'opérateur doit vérifier ses quotas et limites financières avant de lancer. Chaque appel enregistre modèle déclaré, route, effort, latence décision et usage si transmis, temps, session et type. Cache/raisonnement peuvent être des sous-ensembles des tokens globaux : ne pas additionner. Les données absentes restent null. Les sorties synthétiques sont sauvegardées en fichiers privés après expurgation indicative de motifs de secrets ; cette expurgation n'est pas une garantie générale, contrôler avant partage. Ne jamais utiliser des données privées.

## Exécution après intégration et autorisation

```sh
python3 benchmark_runner.py run --default http://127.0.0.1:8101 --s1d1 http://127.0.0.1:8102 --configurable http://127.0.0.1:8103 --split dev --repetitions 5 --output dev.jsonl --authorized
python3 benchmark_runner.py report --input dev.jsonl --output dev.md --svg dev.svg
python3 -m unittest test_benchmark_runner test_benchmark_complete -v
```

Première campagne bornée : ajouter `--cases-per-family 1 --repetitions 2` pour 5 familles × 1 cas × 2 répétitions × 3 bras = 30 parcours par jeu (60 pour dev et validation). L'option accepte 1 à 10 et vaut 10 par défaut ; elle sélectionne les premiers cas par famille dans l'ordre figé. Avant tout appel, un fichier `<output>.plan.json` privé et exclusif contient le hash SHA-256 du sous-ensemble, le nombre total prévu et l'ordre global complet des parcours ; chaque reçu porte aussi ces métadonnées. Les erreurs restent des reçus ; après interruption, comparer les ordres aux entrées du plan pour identifier les manquants. Ne pas lancer la génération tant que le parent utilise les workers GPU.

Validation : changer `--split` et utiliser de nouveaux noms de fichiers après gel. L'exécution complète est de 750 parcours par jeu, mais ne prouve pas les capacités ni les configurations des bras, la qualité générale, les dépenses ou les économies. Les bras doivent être vérifiés séparément. Ce protocole a été rédigé avant les appels réels ; la campagne bornée est conservée dans les preuves référencées en tête, sans changement de ses critères. Les anciens fichiers `BENCHMARK-PILOT.md` et `integrated-t_dab1958b/fixtures.py` décrivent le pilote historique, pas ce jeu v2.
