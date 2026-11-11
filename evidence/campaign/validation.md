# Rapport de pilote — non publié

Provenance : reçus fournis ; configuration et routes à vérifier indépendamment. Aucun résultat simulé ne constitue une mesure réelle.

| Jeu | Famille | Bras | Reçus | Exécutés | Évalués | Réussis | Erreurs | Durée moyenne ± écart-type (ms) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| validation | agents | configurable | 2 | 0 | 0 | 0 | 2 | 14.1 ± 1.4 |
| validation | agents | default | 2 | 2 | 2 | 2 | 0 | 1639.6 ± 1248.9 |
| validation | agents | s1d1 | 2 | 2 | 2 | 0 | 0 | 3741.0 ± 5.9 |
| validation | code | configurable | 2 | 0 | 0 | 0 | 2 | 12.9 ± 0.0 |
| validation | code | default | 2 | 2 | 2 | 2 | 0 | 98.9 ± 0.1 |
| validation | code | s1d1 | 2 | 2 | 2 | 2 | 0 | 135.1 ± 19.0 |
| validation | conversation | configurable | 2 | 0 | 0 | 0 | 2 | 17.0 ± 4.7 |
| validation | conversation | default | 2 | 2 | 2 | 2 | 0 | 118.9 ± 4.8 |
| validation | conversation | s1d1 | 2 | 2 | 2 | 2 | 0 | 138.5 ± 2.8 |
| validation | diagnostic | configurable | 2 | 0 | 0 | 0 | 2 | 12.7 ± 0.4 |
| validation | diagnostic | default | 2 | 2 | 2 | 0 | 0 | 445.9 ± 15.4 |
| validation | diagnostic | s1d1 | 2 | 2 | 2 | 0 | 0 | 424.2 ± 5.9 |
| validation | simple | configurable | 2 | 0 | 0 | 0 | 2 | 28.4 ± 3.8 |
| validation | simple | default | 2 | 2 | 2 | 2 | 0 | 62.1 ± 2.8 |
| validation | simple | s1d1 | 2 | 2 | 2 | 2 | 0 | 82.6 ± 0.2 |

## Mesures par groupe

| Jeu/famille/bras | Mesure | Connus/reçus | Moyenne ± écart-type |
|---|---|---:|---:|
| validation/agents/configurable | input | 0/2 | inconnu |
| validation/agents/configurable | output | 0/2 | inconnu |
| validation/agents/configurable | cache_read | 0/2 | inconnu |
| validation/agents/configurable | cache_write | 0/2 | inconnu |
| validation/agents/configurable | reasoning | 0/2 | inconnu |
| validation/agents/configurable | decision_ms | 0/2 | inconnu |
| validation/agents/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/agents/default | input | 2/2 | 622.0 ± 0.0 |
| validation/agents/default | output | 2/2 | 56.0 ± 0.0 |
| validation/agents/default | cache_read | 2/2 | 455.5 ± 147.5 |
| validation/agents/default | cache_write | 0/2 | inconnu |
| validation/agents/default | reasoning | 0/2 | inconnu |
| validation/agents/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/agents/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/agents/s1d1 | input | 2/2 | 232.0 ± 0.0 |
| validation/agents/s1d1 | output | 2/2 | 256.0 ± 0.0 |
| validation/agents/s1d1 | cache_read | 2/2 | 0.0 ± 0.0 |
| validation/agents/s1d1 | cache_write | 0/2 | inconnu |
| validation/agents/s1d1 | reasoning | 0/2 | inconnu |
| validation/agents/s1d1 | decision_ms | 2/2 | 18.7 ± 6.3 |
| validation/agents/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/code/configurable | input | 0/2 | inconnu |
| validation/code/configurable | output | 0/2 | inconnu |
| validation/code/configurable | cache_read | 0/2 | inconnu |
| validation/code/configurable | cache_write | 0/2 | inconnu |
| validation/code/configurable | reasoning | 0/2 | inconnu |
| validation/code/configurable | decision_ms | 0/2 | inconnu |
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
| validation/code/s1d1 | decision_ms | 2/2 | 18.0 ± 7.4 |
| validation/code/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/configurable | input | 0/2 | inconnu |
| validation/conversation/configurable | output | 0/2 | inconnu |
| validation/conversation/configurable | cache_read | 0/2 | inconnu |
| validation/conversation/configurable | cache_write | 0/2 | inconnu |
| validation/conversation/configurable | reasoning | 0/2 | inconnu |
| validation/conversation/configurable | decision_ms | 0/2 | inconnu |
| validation/conversation/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/default | input | 2/2 | 367.0 ± 0.0 |
| validation/conversation/default | output | 2/2 | 7.0 ± 0.0 |
| validation/conversation/default | cache_read | 2/2 | 320.5 ± 12.5 |
| validation/conversation/default | cache_write | 0/2 | inconnu |
| validation/conversation/default | reasoning | 0/2 | inconnu |
| validation/conversation/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/conversation/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/conversation/s1d1 | input | 2/2 | 367.0 ± 0.0 |
| validation/conversation/s1d1 | output | 2/2 | 7.0 ± 0.0 |
| validation/conversation/s1d1 | cache_read | 2/2 | 333.0 ± 0.0 |
| validation/conversation/s1d1 | cache_write | 0/2 | inconnu |
| validation/conversation/s1d1 | reasoning | 0/2 | inconnu |
| validation/conversation/s1d1 | decision_ms | 2/2 | 12.7 ± 3.3 |
| validation/conversation/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/configurable | input | 0/2 | inconnu |
| validation/diagnostic/configurable | output | 0/2 | inconnu |
| validation/diagnostic/configurable | cache_read | 0/2 | inconnu |
| validation/diagnostic/configurable | cache_write | 0/2 | inconnu |
| validation/diagnostic/configurable | reasoning | 0/2 | inconnu |
| validation/diagnostic/configurable | decision_ms | 0/2 | inconnu |
| validation/diagnostic/configurable | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/default | input | 2/2 | 716.0 ± 0.0 |
| validation/diagnostic/default | output | 2/2 | 61.0 ± 0.0 |
| validation/diagnostic/default | cache_read | 2/2 | 643.0 ± 24.0 |
| validation/diagnostic/default | cache_write | 0/2 | inconnu |
| validation/diagnostic/default | reasoning | 0/2 | inconnu |
| validation/diagnostic/default | decision_ms | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/default | retries | 2/2 | 0.0 ± 0.0 |
| validation/diagnostic/s1d1 | input | 2/2 | 712.0 ± 4.0 |
| validation/diagnostic/s1d1 | output | 2/2 | 59.0 ± 2.0 |
| validation/diagnostic/s1d1 | cache_read | 2/2 | 663.0 ± 4.0 |
| validation/diagnostic/s1d1 | cache_write | 0/2 | inconnu |
| validation/diagnostic/s1d1 | reasoning | 0/2 | inconnu |
| validation/diagnostic/s1d1 | decision_ms | 2/2 | 11.3 ± 0.6 |
| validation/diagnostic/s1d1 | retries | 2/2 | 0.0 ± 0.0 |
| validation/simple/configurable | input | 0/2 | inconnu |
| validation/simple/configurable | output | 0/2 | inconnu |
| validation/simple/configurable | cache_read | 0/2 | inconnu |
| validation/simple/configurable | cache_write | 0/2 | inconnu |
| validation/simple/configurable | reasoning | 0/2 | inconnu |
| validation/simple/configurable | decision_ms | 0/2 | inconnu |
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
| validation/simple/s1d1 | decision_ms | 2/2 | 9.2 ± 4.3 |
| validation/simple/s1d1 | retries | 2/2 | 0.0 ± 0.0 |

Comparer les reçus au plan associé pour compter les parcours manquants ; les anciens reçus peuvent ne pas avoir de plan. Les taux parmi reçus omettent les parcours non lancés. Tarifs, facture et valeur équivalente : inconnus. Cache fournisseur : inconnu. Les tokens cache/raisonnement peuvent être inclus dans entrée/sortie. Oracle code actuel : interpréteur AST borné, quatre entrées, pas une sandbox générale ; les anciens reçus peuvent utiliser un oracle différent. Aucune comparaison ni économie validée.
