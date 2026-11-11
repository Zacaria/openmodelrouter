# Rapport de pilote — non publié

Provenance : reçus fournis ; configuration et routes à vérifier indépendamment. Aucun résultat simulé ne constitue une mesure réelle.

| Jeu | Famille | Bras | Reçus | Exécutés | Évalués | Réussis | Erreurs | Durée moyenne ± écart-type (ms) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| validation | agents | configurable | 2 | 2 | 2 | 2 | 0 | 3879.0 ± 1270.3 |
| validation | agents | default | 2 | 2 | 2 | 2 | 0 | 388.6 ± 1.9 |
| validation | agents | s1d1 | 2 | 2 | 2 | 0 | 0 | 3749.3 ± 14.2 |
| validation | code | configurable | 2 | 2 | 2 | 2 | 0 | 1249.7 ± 20.6 |
| validation | code | default | 2 | 2 | 2 | 2 | 0 | 100.0 ± 0.2 |
| validation | code | s1d1 | 2 | 2 | 2 | 2 | 0 | 127.0 ± 5.6 |
| validation | conversation | configurable | 2 | 2 | 2 | 2 | 0 | 1298.4 ± 25.0 |
| validation | conversation | default | 2 | 2 | 2 | 2 | 0 | 130.3 ± 1.5 |
| validation | conversation | s1d1 | 2 | 2 | 2 | 2 | 0 | 124.6 ± 1.5 |
| validation | diagnostic | configurable | 2 | 2 | 2 | 0 | 0 | 1532.1 ± 37.7 |
| validation | diagnostic | default | 2 | 2 | 2 | 0 | 0 | 419.8 ± 22.3 |
| validation | diagnostic | s1d1 | 2 | 2 | 2 | 0 | 0 | 424.4 ± 5.9 |
| validation | simple | configurable | 2 | 2 | 2 | 2 | 0 | 1174.1 ± 0.7 |
| validation | simple | default | 2 | 2 | 2 | 2 | 0 | 43.7 ± 0.1 |
| validation | simple | s1d1 | 2 | 2 | 2 | 2 | 0 | 69.8 ± 14.5 |

## Mesures par groupe

| Jeu/famille/bras | Mesure | Connus/reçus | Moyenne ± écart-type |
|---|---|---:|---:|
| validation/agents/configurable | input | 2/2 | 622.0 ± 0.0 |
| validation/agents/configurable | output | 2/2 | 56.0 ± 0.0 |
| validation/agents/configurable | cache_read | 2/2 | 455.5 ± 147.5 |
| validation/agents/configurable | cache_write | 0/2 | inconnu |
| validation/agents/configurable | reasoning | 0/2 | inconnu |
| validation/agents/configurable | decision_ms | 2/2 | 2228.5 ± 10.2 |
| validation/agents/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/agents/default | input | 2/2 | 622.0 ± 0.0 |
| validation/agents/default | output | 2/2 | 56.0 ± 0.0 |
| validation/agents/default | cache_read | 2/2 | 603.0 ± 0.0 |
| validation/agents/default | cache_write | 0/2 | inconnu |
| validation/agents/default | reasoning | 0/2 | inconnu |
| validation/agents/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/agents/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/agents/s1d1 | input | 2/2 | 232.0 ± 0.0 |
| validation/agents/s1d1 | output | 2/2 | 256.0 ± 0.0 |
| validation/agents/s1d1 | cache_read | 2/2 | 0.0 ± 0.0 |
| validation/agents/s1d1 | cache_write | 0/2 | inconnu |
| validation/agents/s1d1 | reasoning | 0/2 | inconnu |
| validation/agents/s1d1 | decision_ms | 2/2 | 19.9 ± 10.5 |
| validation/agents/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/code/configurable | input | 2/2 | 181.0 ± 0.0 |
| validation/code/configurable | output | 2/2 | 15.0 ± 0.0 |
| validation/code/configurable | cache_read | 2/2 | 180.0 ± 0.0 |
| validation/code/configurable | cache_write | 0/2 | inconnu |
| validation/code/configurable | reasoning | 0/2 | inconnu |
| validation/code/configurable | decision_ms | 2/2 | 1149.2 ± 20.5 |
| validation/code/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/code/default | input | 2/2 | 181.0 ± 0.0 |
| validation/code/default | output | 2/2 | 15.0 ± 0.0 |
| validation/code/default | cache_read | 2/2 | 180.0 ± 0.0 |
| validation/code/default | cache_write | 0/2 | inconnu |
| validation/code/default | reasoning | 0/2 | inconnu |
| validation/code/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/code/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/code/s1d1 | input | 2/2 | 181.0 ± 0.0 |
| validation/code/s1d1 | output | 2/2 | 15.0 ± 0.0 |
| validation/code/s1d1 | cache_read | 2/2 | 160.0 ± 20.0 |
| validation/code/s1d1 | cache_write | 0/2 | inconnu |
| validation/code/s1d1 | reasoning | 0/2 | inconnu |
| validation/code/s1d1 | decision_ms | 2/2 | 18.5 ± 0.0 |
| validation/code/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/configurable | input | 2/2 | 367.0 ± 0.0 |
| validation/conversation/configurable | output | 2/2 | 7.0 ± 0.0 |
| validation/conversation/configurable | cache_read | 2/2 | 320.5 ± 12.5 |
| validation/conversation/configurable | cache_write | 0/2 | inconnu |
| validation/conversation/configurable | reasoning | 0/2 | inconnu |
| validation/conversation/configurable | decision_ms | 2/2 | 1159.0 ± 30.0 |
| validation/conversation/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/default | input | 2/2 | 367.0 ± 0.0 |
| validation/conversation/default | output | 2/2 | 7.0 ± 0.0 |
| validation/conversation/default | cache_read | 2/2 | 333.0 ± 0.0 |
| validation/conversation/default | cache_write | 0/2 | inconnu |
| validation/conversation/default | reasoning | 0/2 | inconnu |
| validation/conversation/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/conversation/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/s1d1 | input | 2/2 | 367.0 ± 0.0 |
| validation/conversation/s1d1 | output | 2/2 | 7.0 ± 0.0 |
| validation/conversation/s1d1 | cache_read | 2/2 | 333.0 ± 0.0 |
| validation/conversation/s1d1 | cache_write | 0/2 | inconnu |
| validation/conversation/s1d1 | reasoning | 0/2 | inconnu |
| validation/conversation/s1d1 | decision_ms | 2/2 | 9.2 ± 1.8 |
| validation/conversation/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/configurable | input | 2/2 | 708.0 ± 0.0 |
| validation/diagnostic/configurable | output | 2/2 | 57.0 ± 0.0 |
| validation/diagnostic/configurable | cache_read | 2/2 | 635.0 ± 24.0 |
| validation/diagnostic/configurable | cache_write | 0/2 | inconnu |
| validation/diagnostic/configurable | reasoning | 0/2 | inconnu |
| validation/diagnostic/configurable | decision_ms | 2/2 | 1098.6 ± 9.4 |
| validation/diagnostic/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/default | input | 2/2 | 712.0 ± 4.0 |
| validation/diagnostic/default | output | 2/2 | 59.0 ± 2.0 |
| validation/diagnostic/default | cache_read | 2/2 | 663.0 ± 4.0 |
| validation/diagnostic/default | cache_write | 0/2 | inconnu |
| validation/diagnostic/default | reasoning | 0/2 | inconnu |
| validation/diagnostic/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/s1d1 | input | 2/2 | 712.0 ± 4.0 |
| validation/diagnostic/s1d1 | output | 2/2 | 59.0 ± 2.0 |
| validation/diagnostic/s1d1 | cache_read | 2/2 | 663.0 ± 4.0 |
| validation/diagnostic/s1d1 | cache_write | 0/2 | inconnu |
| validation/diagnostic/s1d1 | reasoning | 0/2 | inconnu |
| validation/diagnostic/s1d1 | decision_ms | 2/2 | 12.5 ± 0.6 |
| validation/diagnostic/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/simple/configurable | input | 2/2 | 164.0 ± 0.0 |
| validation/simple/configurable | output | 2/2 | 3.0 ± 0.0 |
| validation/simple/configurable | cache_read | 2/2 | 163.0 ± 0.0 |
| validation/simple/configurable | cache_write | 0/2 | inconnu |
| validation/simple/configurable | reasoning | 0/2 | inconnu |
| validation/simple/configurable | decision_ms | 2/2 | 1129.1 ± 0.4 |
| validation/simple/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/simple/default | input | 2/2 | 164.0 ± 0.0 |
| validation/simple/default | output | 2/2 | 3.0 ± 0.0 |
| validation/simple/default | cache_read | 2/2 | 163.0 ± 0.0 |
| validation/simple/default | cache_write | 0/2 | inconnu |
| validation/simple/default | reasoning | 0/2 | inconnu |
| validation/simple/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/simple/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/simple/s1d1 | input | 2/2 | 164.0 ± 0.0 |
| validation/simple/s1d1 | output | 2/2 | 3.0 ± 0.0 |
| validation/simple/s1d1 | cache_read | 2/2 | 128.0 ± 35.0 |
| validation/simple/s1d1 | cache_write | 0/2 | inconnu |
| validation/simple/s1d1 | reasoning | 0/2 | inconnu |
| validation/simple/s1d1 | decision_ms | 2/2 | 10.7 ± 0.5 |
| validation/simple/s1d1 | retries | 2/2 | 0.0 ± 0.0 |

Comparer les reçus au plan associé pour compter les parcours manquants ; les anciens reçus peuvent ne pas avoir de plan. Les taux parmi reçus omettent les parcours non lancés. Tarifs, facture et valeur équivalente : inconnus. Cache fournisseur : inconnu. Les tokens cache/raisonnement peuvent être inclus dans entrée/sortie. Oracle code actuel : interpréteur AST borné, quatre entrées, pas une sandbox générale ; les anciens reçus peuvent utiliser un oracle différent. Aucune comparaison ni économie validée.
