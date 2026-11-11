# Rapport de pilote — non publié

Provenance : reçus fournis ; configuration et routes à vérifier indépendamment. Aucun résultat simulé ne constitue une mesure réelle.

| Jeu | Famille | Bras | Reçus | Exécutés | Évalués | Réussis | Erreurs | Durée moyenne ± écart-type (ms) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| dev | agents | configurable | 2 | 0 | 0 | 0 | 2 | 1349.8 ± 53.5 |
| dev | agents | default | 2 | 0 | 0 | 0 | 2 | 1410.3 ± 1242.9 |
| dev | agents | s1d1 | 2 | 2 | 2 | 0 | 0 | 2486.2 ± 1242.2 |
| dev | code | configurable | 2 | 2 | 2 | 2 | 0 | 1295.1 ± 71.0 |
| dev | code | default | 2 | 2 | 2 | 2 | 0 | 96.3 ± 1.6 |
| dev | code | s1d1 | 2 | 2 | 2 | 2 | 0 | 112.1 ± 1.6 |
| dev | conversation | configurable | 2 | 2 | 2 | 2 | 0 | 1283.5 ± 17.1 |
| dev | conversation | default | 2 | 2 | 2 | 2 | 0 | 107.9 ± 0.0 |
| dev | conversation | s1d1 | 2 | 2 | 2 | 2 | 0 | 115.9 ± 2.4 |
| dev | diagnostic | configurable | 2 | 2 | 2 | 0 | 0 | 1567.1 ± 18.2 |
| dev | diagnostic | default | 2 | 2 | 2 | 0 | 0 | 416.8 ± 4.6 |
| dev | diagnostic | s1d1 | 2 | 2 | 2 | 0 | 0 | 420.3 ± 7.0 |
| dev | simple | configurable | 2 | 2 | 2 | 2 | 0 | 1317.7 ± 29.1 |
| dev | simple | default | 2 | 2 | 2 | 2 | 0 | 903.0 ± 856.4 |
| dev | simple | s1d1 | 2 | 2 | 2 | 2 | 0 | 94.5 ± 2.7 |

## Mesures par groupe

| Jeu/famille/bras | Mesure | Connus/reçus | Moyenne ± écart-type |
|---|---|---:|---:|
| dev/agents/configurable | input | 2/2 | 266.0 ± 0.0 |
| dev/agents/configurable | output | 2/2 | 29.0 ± 0.0 |
| dev/agents/configurable | cache_read | 2/2 | 179.0 ± 86.0 |
| dev/agents/configurable | cache_write | 0/2 | inconnu |
| dev/agents/configurable | reasoning | 0/2 | inconnu |
| dev/agents/configurable | decision_ms | 2/2 | 1139.5 ± 10.8 |
| dev/agents/configurable | retries | 2/2 | 0.0 ± 0.0 |
| dev/agents/default | input | 2/2 | 266.0 ± 0.0 |
| dev/agents/default | output | 2/2 | 29.0 ± 0.0 |
| dev/agents/default | cache_read | 2/2 | 132.5 ± 132.5 |
| dev/agents/default | cache_write | 0/2 | inconnu |
| dev/agents/default | reasoning | 0/2 | inconnu |
| dev/agents/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| dev/agents/default | retries | 2/2 | 0.0 ± 0.0 |
| dev/agents/s1d1 | input | 2/2 | 230.0 ± 0.0 |
| dev/agents/s1d1 | output | 2/2 | 256.0 ± 0.0 |
| dev/agents/s1d1 | cache_read | 2/2 | 114.5 ± 114.5 |
| dev/agents/s1d1 | cache_write | 0/2 | inconnu |
| dev/agents/s1d1 | reasoning | 0/2 | inconnu |
| dev/agents/s1d1 | decision_ms | 2/2 | 17.7 ± 3.7 |
| dev/agents/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| dev/code/configurable | input | 2/2 | 180.0 ± 0.0 |
| dev/code/configurable | output | 2/2 | 14.0 ± 0.0 |
| dev/code/configurable | cache_read | 2/2 | 159.5 ± 19.5 |
| dev/code/configurable | cache_write | 0/2 | inconnu |
| dev/code/configurable | reasoning | 0/2 | inconnu |
| dev/code/configurable | decision_ms | 2/2 | 1191.4 ± 62.7 |
| dev/code/configurable | retries | 2/2 | 0.0 ± 0.0 |
| dev/code/default | input | 2/2 | 180.0 ± 0.0 |
| dev/code/default | output | 2/2 | 14.0 ± 0.0 |
| dev/code/default | cache_read | 2/2 | 179.0 ± 0.0 |
| dev/code/default | cache_write | 0/2 | inconnu |
| dev/code/default | reasoning | 0/2 | inconnu |
| dev/code/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| dev/code/default | retries | 2/2 | 0.0 ± 0.0 |
| dev/code/s1d1 | input | 2/2 | 180.0 ± 0.0 |
| dev/code/s1d1 | output | 2/2 | 14.0 ± 0.0 |
| dev/code/s1d1 | cache_read | 2/2 | 179.0 ± 0.0 |
| dev/code/s1d1 | cache_write | 0/2 | inconnu |
| dev/code/s1d1 | reasoning | 0/2 | inconnu |
| dev/code/s1d1 | decision_ms | 2/2 | 16.2 ± 2.0 |
| dev/code/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| dev/conversation/configurable | input | 2/2 | 362.0 ± 0.0 |
| dev/conversation/configurable | output | 2/2 | 4.0 ± 0.0 |
| dev/conversation/configurable | cache_read | 2/2 | 318.0 ± 12.0 |
| dev/conversation/configurable | cache_write | 0/2 | inconnu |
| dev/conversation/configurable | reasoning | 0/2 | inconnu |
| dev/conversation/configurable | decision_ms | 2/2 | 1170.2 ± 20.8 |
| dev/conversation/configurable | retries | 2/2 | 0.0 ± 0.0 |
| dev/conversation/default | input | 2/2 | 362.0 ± 0.0 |
| dev/conversation/default | output | 2/2 | 4.0 ± 0.0 |
| dev/conversation/default | cache_read | 2/2 | 330.0 ± 0.0 |
| dev/conversation/default | cache_write | 0/2 | inconnu |
| dev/conversation/default | reasoning | 0/2 | inconnu |
| dev/conversation/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| dev/conversation/default | retries | 2/2 | 0.0 ± 0.0 |
| dev/conversation/s1d1 | input | 2/2 | 362.0 ± 0.0 |
| dev/conversation/s1d1 | output | 2/2 | 4.0 ± 0.0 |
| dev/conversation/s1d1 | cache_read | 2/2 | 330.0 ± 0.0 |
| dev/conversation/s1d1 | cache_write | 0/2 | inconnu |
| dev/conversation/s1d1 | reasoning | 0/2 | inconnu |
| dev/conversation/s1d1 | decision_ms | 2/2 | 11.3 ± 3.7 |
| dev/conversation/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| dev/diagnostic/configurable | input | 2/2 | 712.0 ± 4.0 |
| dev/diagnostic/configurable | output | 2/2 | 59.0 ± 2.0 |
| dev/diagnostic/configurable | cache_read | 2/2 | 663.0 ± 4.0 |
| dev/diagnostic/configurable | cache_write | 0/2 | inconnu |
| dev/diagnostic/configurable | reasoning | 0/2 | inconnu |
| dev/diagnostic/configurable | decision_ms | 2/2 | 1128.4 ± 20.0 |
| dev/diagnostic/configurable | retries | 2/2 | 0.0 ± 0.0 |
| dev/diagnostic/default | input | 2/2 | 716.0 ± 0.0 |
| dev/diagnostic/default | output | 2/2 | 61.0 ± 0.0 |
| dev/diagnostic/default | cache_read | 2/2 | 643.0 ± 24.0 |
| dev/diagnostic/default | cache_write | 0/2 | inconnu |
| dev/diagnostic/default | reasoning | 0/2 | inconnu |
| dev/diagnostic/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| dev/diagnostic/default | retries | 2/2 | 0.0 ± 0.0 |
| dev/diagnostic/s1d1 | input | 2/2 | 712.0 ± 4.0 |
| dev/diagnostic/s1d1 | output | 2/2 | 59.0 ± 2.0 |
| dev/diagnostic/s1d1 | cache_read | 2/2 | 663.0 ± 4.0 |
| dev/diagnostic/s1d1 | cache_write | 0/2 | inconnu |
| dev/diagnostic/s1d1 | reasoning | 0/2 | inconnu |
| dev/diagnostic/s1d1 | decision_ms | 2/2 | 15.8 ± 2.2 |
| dev/diagnostic/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| dev/simple/configurable | input | 2/2 | 163.0 ± 0.0 |
| dev/simple/configurable | output | 2/2 | 2.0 ± 0.0 |
| dev/simple/configurable | cache_read | 2/2 | 162.0 ± 0.0 |
| dev/simple/configurable | cache_write | 0/2 | inconnu |
| dev/simple/configurable | reasoning | 0/2 | inconnu |
| dev/simple/configurable | decision_ms | 2/2 | 1271.1 ± 29.3 |
| dev/simple/configurable | retries | 2/2 | 0.0 ± 0.0 |
| dev/simple/default | input | 2/2 | 163.0 ± 0.0 |
| dev/simple/default | output | 2/2 | 2.0 ± 0.0 |
| dev/simple/default | cache_read | 2/2 | 81.0 ± 81.0 |
| dev/simple/default | cache_write | 0/2 | inconnu |
| dev/simple/default | reasoning | 0/2 | inconnu |
| dev/simple/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| dev/simple/default | retries | 2/2 | 0.0 ± 0.0 |
| dev/simple/s1d1 | input | 2/2 | 163.0 ± 0.0 |
| dev/simple/s1d1 | output | 2/2 | 2.0 ± 0.0 |
| dev/simple/s1d1 | cache_read | 2/2 | 162.0 ± 0.0 |
| dev/simple/s1d1 | cache_write | 0/2 | inconnu |
| dev/simple/s1d1 | reasoning | 0/2 | inconnu |
| dev/simple/s1d1 | decision_ms | 2/2 | 41.6 ± 1.9 |
| dev/simple/s1d1 | retries | 2/2 | 0.0 ± 0.0 |

Comparer les reçus au plan associé pour compter les parcours manquants ; les anciens reçus peuvent ne pas avoir de plan. Les taux parmi reçus omettent les parcours non lancés. Tarifs, facture et valeur équivalente : inconnus. Cache fournisseur : inconnu. Les tokens cache/raisonnement peuvent être inclus dans entrée/sortie. Oracle code actuel : interpréteur AST borné, quatre entrées, pas une sandbox générale ; les anciens reçus peuvent utiliser un oracle différent. Aucune comparaison ni économie validée.
