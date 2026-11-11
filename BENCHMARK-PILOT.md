# Pilote figé v1 — avant toute exécution ou calibration

> Archive pré-campagne : ce texte décrit le pilote v1, pas le runner actuel. Ses limites au présent sont historiques. Le protocole courant est `BENCHMARK-V2.md` ; le plan exécuté et les preuves réelles sont dans `evidence/campaign/STUDY.md` et `evidence/campaign/attempt-2/` du dépôt canonique. Ces preuves comparent des routes locales, pas les modèles par défaut d'abonnements.

Statut : pilote de faisabilité, non validation complète du protocole. Les dix cas versionnés de `integrated-t_dab1958b/fixtures.py` sont séparés dev/validation (un cas par famille et jeu). La validation complète exige 10 cas distincts par famille et jeu et cinq répétitions, soit 750 parcours ; ce pilote ne permet aucune conclusion générale. Ne pas modifier validation ou ses oracles après consultation des résultats : versionner un nouveau paquet.

Les réponses simples et conversationnelles doivent correspondre exactement aux réponses figées, à chaque tour. Code, diagnostic et sous-agents restent non évalués : sans sandbox ou instrument de délégation observable, ils ne sont jamais considérés réussis. Aucun code généré n'est exécuté. Pour les outils synthétiques, seule la fonction `lookup` accepte les clés `alpha` et `beta`, avec réponses constantes respectivement 7 et 11 ; tout autre appel échoue. Elle ne délègue pas à des sous-agents. Cette limite ne prouve pas la délégation ni ses permissions.

Trois serveurs gateway séparés, configurés respectivement défaut sans décideur, s1d1 premier prompt (poids/version/mapping prouvés, route conservée pendant le parcours) et décideur configurable. Les configurations, routes et efforts réellement observés doivent être enregistrés indépendamment ; le nom du bras ou modèle virtuel ne les prouve pas. Une session UUID distincte par parcours, ordre mélangé par bloc avec graine fixe, cinq répétitions indépendantes par défaut. Cache gateway isolé/désactivé à vérifier par opérateur ; cache fournisseur inconnu. Pas de reprises automatiques. Les erreurs et états non évalués sont conservés ; les données manquantes restent null. Ne pas comparer bras si leur configuration ou leurs capacités ne sont pas vérifiées.

Le runner envoie des prompts synthétiques uniquement et ne conserve ni prompts, réponses, arguments ou résultats d'outils dans les reçus. Les durées sont mesurées en monotone de bout en bout ; latence décision, reprises et tokens détaillés restent inconnus sauf métadonnées explicites observables. L'usage agrégé OpenAI ne distingue pas systématiquement cache, raisonnement ou décision : conserver ces catégories à null plutôt que soustraire ou inventer. Aucun tarif n'est supposé. Valeur équivalente, estimation à volume identique et facture sont inconnues sans tarifs et usage suffisants ; aucune économie ne peut être revendiquée.

Objectif fixé avant validation : zéro violation de permission, et réussite globale et par famille du configurable au moins égale au défaut. Ce pilote incomplet ne peut vérifier cet objectif. L'exécution réelle exige autorisation explicite des destinations, quotas, coûts et plafond effectif conformément à GOAL.md ; aucune autorisation fournisseur n'est implicite. Les tests locaux sont des simulations et ne sont pas des résultats de performance.

## Exécution après intégration parent et autorisation

Depuis le checkout qui contient `omr.py`, démarrer trois processus `python3 omr.py serve --config PATH --port PORT` avec configurations séparées et conserver leurs versions, hashes, paramètres, modèles/efforts, fournisseurs, identités des poids s1d1 et cache. Vérifier les routes observées dans la télémétrie gateway ; le runner ne les invente pas. Dans ce worktree, lancer par exemple :

```
python3 benchmark_runner.py run --default http://127.0.0.1:8101 --s1d1 http://127.0.0.1:8102 --configurable http://127.0.0.1:8103 --split dev --output results.jsonl --authorized
python3 benchmark_runner.py report --input results.jsonl --output report.md --svg results.svg
```

Ne pas réutiliser de fichier de sortie. Répéter avec `--split validation` seulement après gel du calibrage et autorisation ; conserver le manifeste d'exécution, les conditions et les reçus. `--authorized` est une affirmation explicite de l'opérateur, pas un contrôle technique du plafond fournisseur. Les sorties sont créées en mode privé. Aucun résultat simulé ou historique ne doit être mélangé aux résultats réels.
