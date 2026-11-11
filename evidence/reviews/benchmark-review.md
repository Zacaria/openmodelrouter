# Revue indépendante — 27 octobre 2026

## Verdicts séparés

- **Benchmark : NO GO pour commit de l'arbre exact `134739f5141b3559adc722cfd16870fb155f86e1`**, base `8a02c1e622e878546da0a1126b5ad30bda8e2120`. Blocage d'intégrité documentaire ci-dessous, pas une exigence de campagne plus volumineuse.
- **Jev : GO pour les seuls trois blobs identifiés ci-dessous**, comme adaptateur autonome et tests hors ligne, sans certification d'intégration ni de qualité fournisseur. Aucun fichier ou index du worktree host-adapters n'a été modifié.
- Aucun verdict ne certifie la réussite finale de GOAL.md.

## Blocage benchmark

**`EDITORIAL-DRAFT.md:5-11`, `BENCHMARK-PILOT.md:1-9,13-22`, `BENCHMARK-V2.md:1,23` — historique présenté sans qualification temporelle suffisante.** Le brouillon affirme au présent que les tests sont simulés et que les évaluations code, diagnostic et délégation restent à compléter, alors que le code v2 les implémente et qu'une campagne réelle a produit des reçus. Le document pilote, pris seul, décrit au présent un autre runner qui ne conserverait pas les réponses et n'évaluerait pas ces familles, alors que le runner livré conserve des sorties expurgées et les évalue. V2 indique « Aucun appel réel n'a été réalisé ici » sans situer cette affirmation dans le temps. Ces textes peuvent induire en erreur un lecteur du commit : marquer explicitement chaque texte concerné comme état historique pré-campagne, avec renvoi au protocole courant et aux preuves réelles, ou actualiser les formulations. Ne pas présenter ces preuves limitées comme un résultat général ou une baseline d'abonnement.

## Vérifications benchmark

- `git write-tree` avant et après revue : arbre demandé ; `git diff --exit-code` propre ; six fichiers ajoutés seulement, `git diff --cached --check` propre. Les tests exécutés depuis une exportation de cet arbre : **9/9 OK**, transports de test uniquement loopback et connexions socket hors loopback interdites ; aucun fournisseur appelé.
- Oracle code : validation AST limitée aux constantes entières, `x`, signes et opérations `+`, `-`, `*`, interprétation sur quatre entrées, sans `exec` ; résultats enregistrés. Ce n'est pas une sandbox ni une preuve générale d'équivalence. Diagnostic exige lookup au second tour ; sous-agent est une requête réelle via gateway avec UUID distinct ; parent et enfant partagent le compteur de cinq appels et l'échéance. Les tests vérifient la requête enfant et les tokens/latence agrégés.
- Plan exclusif écrit avant les appels, ordre et hash consignés ; erreurs conservées, métriques indisponibles à null ; les manquants doivent être comparés au plan, ils ne sont pas calculés automatiquement par le rapport. Un petit pilote est autorisé ; sa taille et sa diversité limitée ne constituent pas un blocage de ce commit.
- Preuves réelles canoniques consultées en lecture seule : `evidence/campaign/attempt-2` contient 30 parcours par split, 3 bras, 5 familles, 1 cas par famille et split, 2 répétitions ; aucun ordre manquant dans les deux plans. Dev : 18 pass, 8 fail, 4 erreurs ; validation : 22 pass, 8 fail. Le manifeste figé porte le SHA-256 du runner `d9258897b243f75cb3e8efea0ba139367ba71c5458b0d7b28526a0b127975efe`, identique au fichier examiné. Le défaut configuré est local ; ces résultats ne sont ni une baseline d'abonnement ni une preuve de gain général. La configuration effective complète des bras et la provenance indépendante de chaque appel ne sont pas certifiées par cette revue.

## Jev — empreintes des fichiers relus

| Fichier | SHA-256 | Git blob SHA-1 |
|---|---|---|
| `jev_decider.py` | `4d28c95d95c7d2910d983602fb7ecb15992d81c6bc476413ba272ab161f28034` | `fc0d946c19b9dc6ddcca7bb92f0f3843ad5ca4b7` |
| `test_jev_decider.py` | `d8bd7abef23060126f7d8ff9f015254ecfeda4b173db7401ffbae1b938d2ca77` | `c30692b2831ebb386f632b57bf5e7197b2407742` |
| `JEV.md` | `c3fee09fa8f0109d711c5b88516c31d454213d55b84f4aecb6fb1490ea38da93` | `af5346e2cdf67acb6ef7d1c0c0743e680eb3daf4` |

Empreintes inchangées après revue ; **6/6 tests OK** sur copie isolée, transport simulé et sans appel fournisseur. Consentement explicite, validation des réponses, erreurs génériques et absence de retry examinés. L'API réelle, l'application de la route par un hôte, les dépenses et la résistance générale aux injections ne sont pas certifiées.
