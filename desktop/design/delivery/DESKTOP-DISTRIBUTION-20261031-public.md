# OMR Desktop — CI et landing

## Mandat

Dans la session Desktop `20261030_224613_eb22ab`, Zacaria demande en parallèle de l'app une CI inspirée de Float pour produire les livrables macOS, Linux et Windows, ainsi qu'une landing avec shadcn. Les autorisations de GitHub privé et de publication du site déjà accordées par GOAL.md restent applicables. Aucun achat, changement de visibilité du dépôt ou copie de secrets Float n'est autorisé.

## Réutilisation et propriété

- Float canonique, en lecture seule : `/home/operator/repos/float`, révision observée `1d827be7ce76e190f45d3765b1068a874bb5911e`, `.github/workflows/release-bundles.yml`. Reprendre les contrôles pertinents, pas les scripts Swift ni les identités du produit. Float a des jobs macOS et Windows ; Linux est à ajouter pour OMR.
- Le worker CI possède les nouveaux workflows de packaging, scripts propres à la CI et documentation distribution ; il préserve `.github/workflows/tests.yml` et ses garde-fous. L'app et `desktop/scripts/build_sidecar.py` restent au worker app `t_01bf8649` ; communiquer les corrections nécessaires, sans écrire dans son worktree.
- Le worker landing possède `site/`, `tests/test_landing.py`, ses tests frontend et documentation dédiée. Il reprend le site existant, sans nouveau site parallèle ni backend, compte ou analytics non demandés. Il ne modifie pas les workflows de l'autre worker.
- Publication du site après revue indépendante via sa continuation dédiée. Construction/publication des installateurs via la carte de release existante `t_a3a76415`, qui consomme app et CI revues. Mise à jour des téléchargements après ces deux livraisons, sans les bloquer mutuellement.

## CI attendue

GitHub Actions, builds natifs sur macOS, Linux et Windows. Verrouiller les dépendances et actions ; permissions minimales, PR non privilégiées, aucun secret sur code non approuvé. Conserver les tests existants. Compiler frontend, Rust et sidecar Python sur le même OS/architecture, puis tester le sidecar embarqué et le contenu des paquets : aucune dépendance à Python installé chez l'utilisateur.

Le contrat app observé, encore en cours d'implémentation : `desktop/package.json` propose `check`, `test`, `build`, `native:build`; `desktop/scripts/build_sidecar.py` construit PyInstaller pour le triple natif ; Tauri référence `binaries/omr-engine`. Vérifier le contrat réellement livré avant composition. Ne pas copier un checkout vivant comme candidat accepté.

Livrables prévus : DMG macOS, installateur Windows, paquets Linux adaptés à Tauri, noms architecture/version explicites et checksums. Qualifier macOS Apple Silicon et Intel selon les runners réellement disponibles ; ne pas prétendre qu'un sidecar mono-architecture est universel. S'inspirer de Float pour signature/notarisation et vérifications d'installation, en utilisant seulement les accès déjà autorisés pour OMR. Un accès de signature manquant ne bloque pas les builds non signés ni les autres OS ; distinguer clairement build de test, signature, notarisation et exécution native.

La release existante doit composer les candidats exacts, déclencher la CI réelle, télécharger les artefacts et vérifier leur contenu et installation. Un workflow syntaxiquement valide ou une fixture ne vaut pas un build macOS/Windows/Linux réussi. Pas de nouveau pipeline de release parallèle, pas de publication sur simple push de branche ni workflow hérité du starter activé aveuglément. Les quotas gratuits/existants n'autorisent aucun nouveau coût facturé.

## Landing attendue

Source actuelle `site/index.html` ; publication existante `https://open-model-router.vercel.app/`. Réutiliser l'hébergement et le contenu utile, remplacer la présentation par une vraie UI shadcn responsive cohérente avec OMR Desktop. Français par défaut, HTML indexable/prérendu, clavier et mobile ; garder la solution statique minimale, sans imposer Next.js ou un serveur.

Présenter la configuration providers/modèles, les trois profils, l'accès direct, l'inspecteur et les mesures honnêtes. Pas de gains chiffrés inventés, témoignages fictifs ou captures de maquette présentées comme un produit livré. Supprimer le benchmark simulé si sa présence brouille la promesse. Les cibles futures ne deviennent pas des compatibilités acquises.

CTA utilisables vers les seules destinations vérifiées ; avant release, état honnête de disponibilité. Le dépôt reste privé : un lien GitHub privé n'est pas un téléchargement public anonyme. Le 31 octobre 2026, Zacaria a autorisé explicitement la livraison jusqu'aux artefacts fonctionnels téléchargeables depuis le site ; `DESKTOP-DELIVERY.md` fixe ce critère de fin et la distribution publique des installateurs/checksums. Réutiliser l'hébergement existant sans publier les archives du dépôt, ajouter de jeton au navigateur ou créer un proxy. Vérifier anonymement les fichiers servis puis leur installation réelle ; ne plus demander un accord de distribution déjà acquis.

## Vérification et suite

Deux préparations sans parents, revue native sur chacune (builder request_review vers reviewer ; PASS avant complete, sinon request_changes). CI candidate-ready n'est pas livraison : son consommateur vérifie les vrais builds. Site prêt après build, checks de liens/accessibilité, captures desktop/mobile inspectées et source récupérable. Publication depuis le candidat exact revu, vérification de l'alias public et retour arrière disponible. Les liens de téléchargement ne sont activés qu'après lecture des artefacts réellement publiés. Le board `open-model-router`, tenant `omr-desktop-v1`, reste l'unique suivi vivant.
