# Réparation du blocage de revue SSE native

Statut : candidat figé pour clôture indépendante bornée ; aucun GO revendiqué. Revue antérieure conservée : `native-sse-independent-review.md`, SHA-256 `a882424b3b118ca8f89256360f924b34b4446830f244a661cc3f3039d83ef849`.

## Identité et périmètre

- Worktree exclusif : `/srv/omr-private/workspaces/open-model-router/router-gateway`.
- HEAD inchangé : `fbf7dc4b9cb2f8d27226ea6e9bb32d56ae31a1c1`.
- Arbre index prédécesseur : `1c459e2d302ccf929cea084e75992e951a7cb923` ; nouvel arbre index : `dbbbc6681fda17d5fc387d27f8b96015c835af02`.
- Delta exact entre ces arbres : `M GATEWAY-SPEC.md`, `M omr.py`, `M test_headerless_native.py`. Ces trois chemins seuls sont indexés ; aucun changement de source canonique, commit ou push.
- SHA-256 des fichiers du candidat :
  - `GATEWAY-SPEC.md` : `2c447eacb0ddbb1991090eb2426d910cbe6215799c5ee56bd1eacdd389c16b03`
  - `omr.py` : `ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c`
  - `test_headerless_native.py` : `51333c7e86fee59ce12d2bc4f1b156a98f10167a4a7292f47a9e2060722b845b`
- Blobs Git correspondants : respectivement `eac82db1506abefaae85d64cffd1002f2e5835a7`, `bb8e0ed9e5eb0b90aed90c8b4ae5caa4f57c8a6f`, `0171d98f6502a0d7be58fff1b5cb144f89252626`.

## Cause et correction

La validation partagée `validate_native_event`, appelée avant transmission de chaque trame native sans Content-Type, ne vérifiait pas les champs optionnels consommés de `ResponseItem` et laissait passer `item.error` non nul. Elle contrôle désormais, pour les quatre variantes déjà prises en charge, `id`, les métadonnées consommées (`turn_id`, `create_time`, `content_item_kinds`), ainsi que `phase`, `encrypted_content`, `namespace`, `encrypted_function_args` et `status` selon la variante. `content` du raisonnement était déjà contrôlé. Les définitions proviennent de `models.rs` épinglé (SHA-256 `58fb6f17b3698efc3ce117f3aed1986b6c5dbfcb1c95de92d99675932224fba3`) ; `ContentItemKind` est une chaîne transparente dans `models/item_metadata.rs` à la même révision SDK `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. Les champs de métadonnées marqués `skip_deserializing` ne sont pas consommés par le SDK et restent des extensions. L'erreur non nulle est rejetée à la frontière directe de l'item, pas par recherche récursive ; `error=null`, les arguments et les extensions sans rapport restent permis. La phrase de spécification distingue ce périmètre headerless.

## Preuves d'exécution locales

- RED avant correction : `PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_headerless_native.HeaderlessNativeTests.test_item_boundary_rejections_on_route test_headerless_native.HeaderlessNativeTests.test_sdk_item_optional_fields` : échec attendu ; les deux sous-cas de route indépendants ont effectivement retransmis `namespace: 42` et `item.error` non nul, et les tests de champs optionnels ont échoué. Journal `native-sse-repair-red.log`, SHA-256 `c70f19a02656212a16516d41482fa833b0ad84c18fbafac54dcbbff2f1eea442`.
- GREEN même commande après réparation : 2 tests réussis, y compris les deux cas route ; journal `native-sse-repair-green.log`, SHA-256 `edd5eca16f2b5dc98c0d1d0c92d52f34099333b9f78e784a76d8c1d1a765ec48`.
- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -v` : 35 tests réussis en 12,909 s, soit les 33 tests existants et 2 ajouts. Journal `native-sse-repair-suite.log`, SHA-256 `d8d782fa69f65e71b2b9b892e22e79f1634156d599cec7e72260b9bc7236fb71`.
- `git diff --cached --check` réussi ; aucune différence non indexée sur les chemins suivis. Des répertoires `__pycache__` non suivis existent dans le worktree et ne sont pas inclus dans l'arbre.

Les essais utilisent des fournisseurs synthétiques locaux ; aucun appel authentifié ni appel de modèle. Les résultats ne remplacent pas la clôture indépendante ni une validation d'intégration Mac réelle.
