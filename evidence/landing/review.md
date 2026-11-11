# Revue indépendante — landing prototype

**Verdict : GO borné pour publier la page prototype actuelle, avec réserve mobile ci-dessous.** Ce verdict concerne uniquement les octets du fichier identifié ci-dessous ; il ne valide ni le produit fini, ni les quatre intégrations, ni une release ou un déploiement. Aucun commit, push ou déploiement effectué.

- Page relue : `/srv/omr-private/workspaces/open-model-router/landing/site/index.html` — SHA-256 `3ab910b3d6ce0e333037976bc4c773f1fde2af0d927c6683cbe4a5d2a440a054` (empreinte demandée confirmée).
- Test relu : `/srv/omr-private/workspaces/open-model-router/landing/tests/test_landing.py` — SHA-256 `d128a50aa4ec568199931971f64692056aa175cb17d02e90e132fc93d6a631d6`.
- Contrat lu : `/srv/omr-private/workspaces/open-model-router/landing/GOAL.md` — SHA-256 `b48a4d1cd41bc479b7c3854e2b2f72f79a49258cd97b678037a97a6f8c7d83b`.

## Constats

- La copie distingue prototype local, dépôt privé, données simulées et intégrations visées mais non validées ; elle ne promet ni économie prouvée, ni compatibilité d’abonnement, et distingue valeur équivalente et facture. Elle signale que les commandes locales sont du code de confiance non isolé. Les reçus locaux `evidence/s1d1-identity.json` et `evidence/s1d1-real-smoke.json` dans `/home/operator/repos/open-model-router/` documentent l'identité et deux classifications ; cette revue ne réexécute pas l'inférence.
- Les huit liens sont des fragments internes vers six identifiants uniques ; aucun lien externe ou ressource externe dans le HTML. Recherche ciblée de chemins locaux et signatures courantes de secrets : aucune correspondance ; ce contrôle ne prouve pas l'absence de tout secret possible.
- Test réellement exécuté depuis `/srv/omr-private/workspaces/open-model-router/landing` : `PYTHONDONTWRITEBYTECODE=1 python3 tests/test_landing.py -v` → code 0, `OK: 8 fragment links, 6 unique IDs, French and prototype disclosures`. Ce test vérifie structure et présence de termes, pas véracité produit ou accessibilité complète.
- Preuves préexistantes : `/home/operator/.hermes/cache/scratch/open-model-router-landing-evidence/results.json` (SHA-256 `9b3d8ac54e34ceeb8d15eb17f80cb0f3309b7fd56186c5cf6da8b7c7801aa3f2`), associé par son contenu au SHA de la page ; 200 et absence de débordement global rapportés à 320, 390, 760, 761 et 1440 px, JavaScript désactivé et mouvement réduit. Son script clique les fragments. Captures examinées : `320x700-full.png` (SHA-256 `ba0506e55400c8bf30ff893ed33d52eec63cd24f15000d51585ce6b2e5c3dbd2`) et `1440x900-full.png` (SHA-256 `bc246edd18f581b2398deb259a89c7d276fd84bfdc99a497432ed35f1985e3b1`) dans ce même répertoire. Ces preuves sont préexistantes, non régénérées dans cette revue ; elles ne prouvent pas tous navigateurs ou conditions d'accessibilité.

## Réserve non bloquante pour cette page prototype

À 320 px, le panneau préformaté des hôtes dépasse sa zone visible : `pre` utilise `overflow-x:auto`, sans indication visible de défilement. Les mêmes noms et la réserve de validation figurent toutefois en entier dans le paragraphe précédent. Amélioration recommandée : retour à la ligne ou indication de défilement, puis nouvelle revue des nouveaux octets. La capture desktop ne montre pas de débordement manifeste. Pas d'audit exhaustif du contraste, du clavier ou de l'accessibilité.
