# OMR Desktop — téléchargement public et fonctionnement vérifié

## Mandat du 31 octobre 2026

Zacaria demande : « Orchestre l'implémentation, pousse en prod jusqu'à ce qu'on puisse télécharger depuis le site, les artefacts qui fonctionnent ».

Ce mandat autorise la publication des installateurs OMR et de leurs checksums pour téléchargement anonyme depuis la landing existante. Il complète GOAL.md et remplace l'attente d'un accord supplémentaire de distribution publique dans DESKTOP-DISTRIBUTION.md et la carte t_29098b54. Il ne rend pas le dépôt GitHub public et n'autorise ni publication des archives du dépôt, secrets, données privées, achat ou nouvelle facturation. Le code nécessaire embarqué dans les binaires est distinct d'une publication des sources du dépôt.

## Critère de fin

Depuis `https://open-model-router.vercel.app/`, sans session GitHub/Vercel : choisir son système et architecture, télécharger l'installateur de la version annoncée, vérifier son SHA-256, installer puis démarrer OMR et accomplir un parcours utile. Cette chaîne doit être vérifiée sur macOS, Windows et Linux ; une compilation, un paquet local ou un lien vers une release privée ne clôt pas la mission.

Le parcours utile couvre le moteur embarqué sans installation manuelle de Python, la configuration d'un fournisseur supporté, les profils automatiques et une route directe, une réponse et son usage inspectable, la fermeture/réouverture et l'arrêt explicite. Préserver permissions, consentement externe, annulation et absence de secrets/transcripts. Utiliser les accès existants autorisés et des données synthétiques/publiques. Distinguer tests avec backend synthétique, génération réelle, build et installation native : une fixture ne prouve pas un fournisseur réel. Ne pas imposer les stratégies avancées comme préalable à cette première livraison.

L'identité fournie (landing, interface et logo) reste le contrat visuel. Les disponibilités partielles peuvent être publiées honnêtement, mais ne sont pas une réussite globale tant qu'un OS demandé reste non vérifié. Signatures/notarisation uniquement avec les moyens déjà autorisés ; documenter l'état réel et les éventuelles étapes natives de confiance, sans désactiver les protections de l'OS pour fabriquer un succès.

## Chemin minimal de distribution

Réutiliser le site Vercel existant : installateurs versionnés dans des fichiers statiques et liens natifs, pas de proxy de téléchargement ni backend supplémentaire. Conserver les binaires hors Git ; produire le payload de publication depuis les artefacts revus et un manifeste version/OS/architecture/taille/SHA-256/source exacte. Le dépôt et ses releases de conservation peuvent rester privés.

Préflight observé le 31 octobre : équipe Vercel `team_lpN3ikyEWpXFfrV53eNYNWQd`, slug `zacaria-chtatars-projects`, abonnement Pro actif, relu avec la CLI autorisée ; projet existant `prj_2ZuPDmm7IDcBakYR51rVSqjQ9P0k`, `rootDirectory=site`. La documentation officielle https://vercel.com/docs/limits indique un plafond CLI de 1 GB de fichiers source pour Pro (100 MB pour Hobby). L'AppImage de la base précédente fait 117 508 600 octets ; le canal privé GitHub n'est donc ni nécessaire ni un motif pour demander un autre accord. Vérifier les tailles cumulées finales, quotas existants et limites effectives avant publication, sans augmenter le plan ni activer de surcoût. Ce préflight ne prouve pas encore l'upload du payload final.

Le connecteur hébergé Vercel a refusé la lecture de ce scope ; la CLI Vercel existante y a réussi. Réutiliser ce chemin autorisé plutôt que demander une réauthentification inutile. Ne pas copier ses secrets.

## Chaîne et responsabilité

- `t_ef5e93f2` → `t_5c4e05b7` : landing et publication de la direction fournie.
- `t_01bf8649` + `t_230d11c2` + `t_c230c679` → `t_a3a76415` : socle, UI/logo, CI, composition exacte revue, vrais builds et parcours natifs.
- Landing publiée + `t_a3a76415` → `t_29098b54` : mise à disposition anonyme des binaires, liens de production et vérification finale des octets téléchargés/installés.

Réutiliser ces cartes et leurs cycles de correction/revue ; pas de second orchestrateur ni de réimplémentation parallèle. t_5228779f garde son acceptation historique distincte. Chaque blocage technique appelle diagnostic et correctif borné dans la chaîne, sans arrêt à une remise intermédiaire. Les notifications terminales existantes réveillent le coordinateur du canal projet ; conserver les checkpoints et signaler un accès réellement manquant plutôt que déclarer la mission terminée.

## Preuves finales attendues

Manifeste public et URL de chaque artefact, SHA-256 des fichiers téléchargés anonymement, identité de la source revue, résultats d'installation/lancement par OS et architecture, captures de la landing et de l'app, statut exact de signature/notarisation, parcours de routage réellement exercés et rollback conservé. Vérifier les fichiers obtenus depuis les liens de production, pas seulement leurs équivalents locaux ; ne jamais confondre un HTTP 200 renvoyant une page de connexion avec un installateur.
