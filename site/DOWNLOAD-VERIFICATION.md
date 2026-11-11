# Vérification — raccord de téléchargements OMR

## Frontière du candidat

`t_b05fbd63`, branche `work/desktop-download-preparation-v1`, base publiée/revue `3de54ada4c352f30ab85b60adb8435db2f0c5e02`. Le SHA signé exact et son readback distant sont dans le handoff Kanban. Les modifications portent uniquement sur le raccord de build, le bloc disponibilité existant, ses tests et sa documentation. Couleurs, typographie, logo, autres sections et composants shadcn conservés ; aucune dépendance ajoutée.

Le [contrat release](brand/decisions/DOWNLOAD-HANDOFF.md) distingue source produit, qualification native, confiance, génération réelle et admission explicite. Sans manifeste externe, aucun téléchargement actif ; chaque plateforme sans paquet admis reste indisponible, sans inventer d’indisponibilité lorsque les quatre sont admises. macOS ad-hoc bloqué par Gatekeeper et Windows non qualifié restent sans lien. Les parcours macOS qualifiés utilisent un fournisseur préconfiguré et des réponses synthétiques : l’onboarding GUI complet et la génération réelle ne sont pas vérifiés. Le parcours Intel a été testé sous Rosetta, pas sur Intel physique. Aucun binaire, manifeste privé, source ou archive de preuves dans le payload public.

## Exécution et résultats

- RED comportemental : avec l’admission encore vide, le paquet disponible produit zéro lien au lieu d’un ; le manifeste dangereux n’est pas rejeté ; le bloc par défaut n’annonce pas les architectures. Les erreurs initiales de chargement/JSX ont été corrigées avant de retenir ces échecs comme RED.
- GREEN : `npm run check`, `npm run format:check`, `npm run build`, `npm test`, `npm run test:browser`, `npm run test:staging`, `git diff --check` passent. `npm audit --audit-level=moderate` : zéro vulnérabilité signalée. Node 24.21.0, npm 11.19.0, Python 3.13.5, Brave 153.0.8010.37.
- Sept tests de téléchargements couvrent absence/default, paquet admis et octets/checksum/source exacts, qualification partielle, taille/hash incohérents, mélange disponible/refusé, confiance par OS, génération réellement vérifiée distincte de synthétique, manifeste malformé, chemin/URL/archive interdits, champs privés supplémentaires, doublons et symlinks. Les octets sont synthétiques et non exécutables ; aucune qualification réelle n’en est déduite.
- Le staging exécute le vrai build dans une copie minimale temporaire sans historique, jamais dans le `dist/` publiable. Deux formats Linux synthétiques sont admis ; Mac ad-hoc et Windows non qualifié restent refusés. Les six checks HTML/Python et html-validate passent sur ce build actif. Les clics téléchargent les octets exacts et ouvrent les checksums ; les deux checksums sont accessibles par Entrée/Tab. Un second build sans manifeste retire tous les anciens fichiers et liens. La copie temporaire est supprimée en `finally` ; le HTML du `dist/` habituel reste identique.
- Suites canoniques `.github/workflows/tests.yml` exécutées localement : 64 racine, 16 pilot, 6 loop, 5 comparator, 9 integrated, 6 demo, 9 host-adapters, plus 6 landing ; 121 tests découverts, un skip explicite d’inférence locale sans modèle configuré, aucun échec final. Les échecs synthétiques affichés par les tests de certification sont des sondes attendues de leur détection d’échec, pas des échecs de suite. Aucune exécution GitHub Actions n’est revendiquée ici.

## Navigateur et contenu public

Les deux états passent aux douze largeurs 320, 359, 360, 390, 767, 768, 769, 1024, 1100, 1101, 1440 et 1920 px, JavaScript client désactivé et mouvement réduit. Hashes/source ouverts pendant les sondes de débordement : aucun contenu hors viewport. État par défaut : 16 liens, 21 cibles clavier ; staging synthétique : 20 liens, 25 cibles, deux parcours clavier de checksum. Quatre FAQ et les quatre profils natifs fonctionnent dans les deux états. Zéro erreur console/réseau et zéro requête tierce.

Axe A/AA 2.1/2.2 et bonnes pratiques : zéro violation aux largeurs 390/1440 dans les deux états, détails ouverts. Une vérification de contraste reste incomplète sur les vrais dégradés (`bgGradient`). Le contrôle complémentaire aux enveloppes conservatrices `#304235` / `#b8d956` passe sur les quatre profils sans violation ni résultat incomplet ; ne pas présenter cela comme une certification complète d’accessibilité.

Onze captures par état sont conservées avec le rapport navigateur. Inspection des disponibilités 390/1440 : aucun chevauchement ou texte tronqué ; le rendu conserve le bloc citron et ses arcs. Les libellés finaux nomment l’action « Ouvrir le fichier SHA-256 », identifient le commit Git et affichent la confiance et la limite de génération. La taille des notices/hash a été augmentée après inspection mobile. Les images du staging montrent des fixtures et ne doivent jamais être présentées comme des installateurs livrés.

## Payload, limites et remise

Le build par défaut contient exactement onze fichiers (HTML/CSS, favicon, deux logos, trois polices et trois licences), zéro répertoire `downloads/`. Empreintes observées :

- `index.html` SHA-256 : `5537c5199e51a2f65d56fef2fcd75bd8eaabf358be65ed4a98ebfa1897f82d6f`.
- `styles.css` SHA-256 : `bca2753cb5cf3cd84bab73bc5e95f4d430be645a2f2ce35ee1ef06f0a7e92acc`.

Le raccord remplace l’ancienne liste OS seule et son style ; aucun fichier de données ni source existant supprimé. Les paquets temporaires périmés sont retirés uniquement dans les builds de test. Dépendances/build/captures/logs restent ignorés.

Restent hors de cette carte : revue indépendante, publication Vercel, accès public anonyme, véritables installateurs/signatures/notarisation, génération fournisseur réelle, installations natives, Firefox/WebKit et appareils physiques. Aucun déploiement, téléchargement public activé, secret lu/copié ou achat effectué. Après PASS de la revue exacte, `t_29098b54` consomme cette source et les métadonnées réelles pour sa publication autorisée ; la présente préparation ne retire pas le parent release existant.
