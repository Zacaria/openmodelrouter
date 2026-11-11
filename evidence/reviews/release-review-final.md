# Revue finale bornée — deux blocages release

**Verdict : GO pour intégrer et committer les trois blobs corrigés identifiés ci-dessous**, sous réserve que le commit final contienne effectivement ces octets. Ce n'est ni un GO de publication, ni une certification du commit final : celui-ci n'existe pas encore dans cette revue. Aucun commit, écriture source ou index du dépôt canonique, appel fournisseur ou publication n'a été effectué. Aucun nouvel audit de l'analyse ou du reste du code.

Rapport prédécesseur conservé : `release-analysis-review.md`, SHA-256 `fc69e97dd71e1a5ac82b4c92584c3deabd09675c43a3c21f426f09b10e52b6d6`.

## Identité des blobs revus

Source figée `/srv/omr-private/workspaces/open-model-router/release-tools` ; empreintes recalculées conformes au rapport de correctif :

- `build_release.py` : `c06a19f3f5d8bc1a1da47212f9a733bba5db33d38ae2e4662ab9c48142482d28`
- `test_build_release.py` : `80d917bccf5a72bb0d95c93addf68992bc8b645262d8ddbf986526827bb269d7`
- `INSTALL.md` : `d22c9d434e498ad7f3c4cd08637ced16a6f10413a63f2c81f0786d8b6ef33ac7`

## Fermeture des deux blocages

1. **Liaison Git : fermé dans le périmètre.** Le chemin corrigé exige séparément dépôt et révision SHA complète ; il résout commit et tree Git, compare leur identité au manifeste, puis compare l'ensemble des chemins, modes et octets de l'archive aux blobs Git avant création du scratch. Les deux nouveaux tests falsifient respectivement l'identité et simultanément le contenu et les hashes du manifeste et de l'archive ; ils exigent le refus avant extraction. Les empreintes non signées ne sont pas une authentification : dépôt et révision attendus doivent être obtenus par un canal de confiance indépendant.
2. **Landing Python 3.13 : fermé dans le périmètre.** Le script landing est lancé directement ; les autres modules `tests/test*.py` restent soumis à discovery. Exécution indépendante Python 3.13.5 : fixture Git contenant les vrais `tests/test_landing.py` et `site/index.html` du commit `dafe00b78b4da6b8c250d1445b9b91d7c5a6040d`, avec `omr.py` factice. Certification réussie, script réel exécuté directement : 8 liens et 6 IDs. Ce test n'est pas une certification du commit landing lui-même.

## Exécutions fraîches et comparaison

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v test_build_release` depuis la source figée : **10 tests OK**, dont les deux falsifications ; les échecs imprimés par les sous-suites négatives sont attendus. Le rapport antérieur dénombrait 8 tests release : le delta est **+2 tests release**, soit 10 au total, et non +10. Le cas d'échec d'un autre module dans `tests` est aussi ajouté comme sous-test.
- Certification fraîche de `build-reviewed-bcae37d` avec dépôt canonique `/home/operator/repos/open-model-router` et révision attendue explicitement fournie `bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad` : **20 tests réels OK**, comme les 20 rapportés dans `certification-final-bcae37d.log`. Tree résolu `515251105b1650d9e114108748b9ac7fdfdb755e` ; 64 membres au manifeste. Archive SHA-256 `0e0d0b5c83eafa01467dbd000e9c8d04fdba949a8f99ad975fd426497f850cf7` ; manifeste `c70d455f21716dec2e150ccd500381aa98f913a10ed8dcda67de9a11c766e294`. La certification porte sur cette révision existante, pas sur les trois blobs corrigés non encore committés.
- Journaux frais : `/home/operator/.hermes/cache/scratch/release-review.xNs7pW/{tests,cert,landing}.log` (scratch temporaire). `git status --porcelain=v1 -z` du dépôt canonique : SHA-256 `11b45efd377b433d0007e325488dd4c4b05ce50f131a30239993b73506bb7bcb` avant et après fixture landing ; seul le dépôt fixture temporaire a reçu un commit.

Les vérifications de l'analyse et les autres résultats du rapport initial sont hérités, non réexécutés. Pas de validation d'intégration hôte ni de garantie d'absence de secrets. Après intégration, vérifier les blobs du commit final et le certifier séparément avant toute publication.
