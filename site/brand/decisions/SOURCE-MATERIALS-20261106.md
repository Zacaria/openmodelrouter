# Matériaux macOS ARM64 0.3.0 — distribution publique

## État

Le 6 novembre 2026, les quatre fichiers ci-dessous ont été intégralement relus sans cookie, authentification ni redirection. Tailles et SHA-256 correspondent aux entrées préparées. Les trois parties WebKit concaténées correspondent à l’archive originale : 1993631802 octets, SHA-256 `fb9d7b9bede6831ca0e7bad51f1309bcae42f0c2abcb8810688d18fa01135951`.

Entrée publique, instructions de restauration et liens vers les quatre fichiers :
`https://open-model-router-materials-3.vercel.app/`.

| Adresse | Déploiement exact | Branche de routage réservée |
| --- | --- | --- |
| `open-model-router-materials-1.vercel.app` | `dpl_BM8vjPk64mLP76Hgv2ZUe3a1oRP8` | `omr-materials-0.3.0-part-1` |
| `open-model-router-materials-2.vercel.app` | `dpl_X8AQSD8yXp5yuk6vX47m5xbzeajM` | `omr-materials-0.3.0-part-2` |
| `open-model-router-materials-3.vercel.app` | `dpl_GnVsML7aMX9AYhC76pHjXpVAMHEf` | `omr-materials-0.3.0-part-3` |

Ces branches sont des liaisons de domaines Vercel, pas de nouvelles branches Git. Elles séparent les domaines des affectations automatiques de production. Chaque domaine dispose d’une exception publique limitée à cet alias (`alias-protection-override`). La protection SSO du projet est inchangée ; les trois URLs générées de déploiement renvoient toujours anonymement une redirection 302 vers la connexion Vercel. Aucun secret de partage ou contournement d’automatisation n’est publié.

## Empreintes

Les fichiers WebKit sont nommés `webkit-d6375c72affe0f70222cdcb45012b10f0bf3a9d5.tar.gz.part-00N` :

| Fichier | Octets | SHA-256 |
| --- | ---: | --- |
| partie 001, domaine 1 | 900000000 | `cda42e9e9449ea13d0138bc4e6fa13eb7d26156c6f189d03f6451dadefba8caf` |
| partie 002, domaine 2 | 900000000 | `fbf70cabd2d3e6bc892d5fd96e6d39f8552b95fd9a3b14171ad156fde2f83e34` |
| partie 003, domaine 3 | 193631802 | `5f52948eeca3bf318f1010e8e5c7333233f071baff40e0ff68856bf2d7f85d5c` |
| `omr-0.3.0-macos-arm64-materials-base.tar`, domaine 3 | 601804800 | `1540d6207856d38961fa1d2bee892874a7014cf3aad7821d9b69896df9ab7d48` |

Le contrôle a parcouru 2595436602 octets sans conserver de copie supplémentaire. Le reçu est conservé dans `/srv/omr-private/artifacts/open-model-router/chat-400-20261105/material-static-payloads/public-binary-verification-20261106T000943648456Z.json` ; `uploaded.json` et `public-indices.json` gardent séparément les phases d’upload et d’ouverture des adresses.

## Portée

La préparation locale a conservé les 797 fichiers du compagnon d’origine, dont 796 dans l’archive de base et WebKit découpé en trois parties. Notices, sources, recettes et limites de provenance restent inchangées. Leur disponibilité ne démontre pas rétroactivement la provenance historique du Bun distribué.

La landing principale reste liée à `dpl_GJmKLpXA6m5C1n4JejktZWcXPwWn` et ses quatre installateurs 0.1.0 sont inchangés. Cette opération ne publie ni ne remplace le DMG 0.3.0. Le raccordement de celui-ci et du catalogue conservé à la garde de publication reste à terminer avant promotion de la landing.

Ce document est une preuve opérateur privée ; `brand/` n’entre pas dans le payload public.
