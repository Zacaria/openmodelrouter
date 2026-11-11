# Campagne locale bornée — protocole figé avant exécution

Périmètre : modèle virtuel Open Model Router, génération locale Ollama et décision Jev autorisée sur données synthétiques. Cette campagne ne compare pas les abonnements Claude/ChatGPT et ne prétend pas remplacer leur modèle par défaut : sa référence est la route locale effectivement observée dans l'essai Hermes, `omr-hermes-qwen3-4b:ctx8192`, effort transmis `none`. Cet alias utilise les poids Qwen instruct, avec contexte 8192, sans retrait d'outils.

## Plan fixé

- Jeux dev et validation séparés, issus de `benchmark_runner.py` et de ses oracles figés. Un cas par famille et par jeu, deux répétitions indépendantes par session, trois bras. Les cinq familles sont simple, code avec quatre tests comportementaux, diagnostic avec preuve outil, difficulté changeante et délégation réelle orchestrée par le runner.
- Trois bras : référence locale fixe ; s1d1 vérifié uniquement au premier prompt, seuil expérimental 0,35 ; Jev 1.13 configuré avec les deux descriptions de route du smoke déjà conservé. Ni seuil ni prompt de décision ne seront ajustés à partir de ces résultats.
- Route `direct` : alias Qwen instruct 8192 / effort `none`. Route `reasoning` : `qwen3:4b`, effort non forcé, donc défaut du backend ; aucun niveau d'effort précis n'est revendiqué. Les deux routes sont explicites, sans fallback. Cette politique reste expérimentale, pas une recommandation de qualité.
- Ordre des bras aléatoire reproductible, graine 27 pour dev et 28 pour validation. Nouveau UUID par parcours, UUID enfant distinct en délégation. Cinq appels HTTP maximum partagés parent/enfant, 256 tokens demandés par appel, 30 secondes maximum par parcours. Les échecs de budget, les sorties vides et les erreurs comptent comme tels.
- Aucun réchauffement ou reset forcé des caches ; état initial Ollama conservé séparément. Usage cache mesuré quand fourni, sinon inconnu. Aucun retry. La durée comprend la décision et l'inférence, pas le lancement initial du serveur/classifieur. Les reçus gateway conservent séparément la décision et ses tokens disponibles.

Les dialogues ne partagent pas leur historique, mais les répétitions ne sont pas des échantillons indépendants du cache ou du matériel. Les cas sont petits et issus de gabarits ; aucune généralisation à une population de tâches ne sera faite. La délégation du runner ne démontre pas les sous-agents natifs de chacun des hôtes.

## Mesures et limites

Conserver plans complets, empreintes des scripts/configurations/jeux, ordre, réponses synthétiques, reçus gateway, tests comportementaux réellement exécutés, durées, catégories de tokens disponibles, absences et échecs. Produire moyennes et dispersion. Prix, valeur équivalente, baseline repricée et facture ne sont pas inventés : ils restent non mesurés tant qu'aucun tarif et périmètre applicables n'est établi. Un résultat négatif est acceptable.

L'installation, les conversations, les outils, le streaming, les erreurs et l'annulation des quatre hôtes restent une vérification distincte. Cette campagne ne clôt pas GOAL.md.
