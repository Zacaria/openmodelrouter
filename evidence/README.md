# Preuves de livraison — état du 27 octobre 2026

Le contrat global reste non atteint. Deux hôtes VM ont des parcours réels documentés ; les intégrations Codex et oh-my-pi sur Mac ne sont pas qualifiées. Aucun gain général de qualité, de durée ou de coût n'est établi.

## Vérifié

- `native/final-vm/REPORT.md` et `observed/` : Hermes et Claude, lecture d'une fixture, rappel dans un nouveau processus, streaming, annulation après texte réel, disparition des sockets amont et des groupes de processus puis reprise réussie. La fermeture de connexion ne mesure pas l'arrêt du calcul GPU. Les budgets d'erreur sortent à 124 ; seul Claude expose explicitement le 502 dans la trace native.
- `native/error-visibility/` : le rejeu Hermes expose désormais le statut 502 par un message constant de l'adaptateur, puis sort à 124 après 30 secondes ; aucun processus du groupe enfant ne reste vivant. Ce n'est pas une erreur API native Hermes. Adaptateur signé et poussé : `2527e02b4a7fbc766edba1f17e18e2e274e6d23b`. La seule modification ultérieure aux preuves de ce rejeu synchronise le test de fermeture ; les octets du lanceur sont inchangés. Provenance : `host-adapter-import.json`.
- `campaign/analysis/REPORT.md` : campagne locale complète de 60 parcours planifiés, trois bras réellement exécutés, cinq familles, jeux dev/validation et deux répétitions. La tentative initiale mal configurée reste séparée. Les données et critères n'ont pas été retouchés après les résultats ; le critère diagnostic présente une ambiguïté documentée. Jev a consommé 8 626 tokens d'entrée et 726 de sortie sur les 22 décisions observées, sans prix ni facture attribués.
- La passerelle du commit signé `bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad` et le benchmark du commit signé `f9d0c529e6d755a15f7e87ffcf674e13e00a17cf` sont revus et poussés sur leurs branches privées ; leurs références distantes ont été relues. Cela ne certifie pas le futur candidat intégré.
- `landing/` : déploiement public vérifié, HTML identique au candidat revu et captures desktop/mobile inspectées. La page présente un prototype. La réserve mobile sur le défilement horizontal à 320 px est conservée dans la revue.

- Premier commit signé `8a02c1e622e878546da0a1126b5ad30bda8e2120`, arbre revu `134cf0df11385856063c90ed5c774abc8bc35707`, poussé sur le dépôt privé `Zacaria/open-model-router` et relu par `git ls-remote`. Préservation historique uniquement : cet arbre ne contenait pas le correctif de provenance de la démonstration, présent ensuite dans la branche passerelle revue. Avis : `initial-review.md`.
- `s1d1-identity.json` lie chaque fichier du modèle à la révision Hugging Face `dac13b5c0356864ea4501fa151d74dcd8b3ea22a` : SHA-256 LFS pour les gros objets, empreinte blob Git pour les autres. Wrapper comparé octet pour octet à la révision amont indiquée dans `s1d1-real-smoke.json`. Deux classifications réelles, aucune génération attribuée à s1d1.
- `ollama-protocols-run2.json` : génération réelle Qwen sur les trois protocoles Chat Completions, Responses et Messages. Chaque parcours obtient un appel structuré `read_fixture`, fournit un résultat synthétique et reçoit exactement `SYNTHETIC-ORCHID` en streaming. L'identité du modèle demeure celle d'Ollama ; ce sont des tests directs du backend, pas des tests des clients ni de la passerelle. Effort `none` transmis et reflété par Responses, mais aucun niveau d'effort n'a été qualifié par mesure comportementale.
- `jev-smoke.json` : appel réel `jev-1.13.0`, premier prompt synthétique uniquement, choix `direct`, usage et temps observés. Identifiants restés dans leur gestion native. Cet essai ne mesure pas la qualité générale du routage ni une économie. Aucun achat ou activation de facturation n'a été effectué ; usage observé distinct de facture inconnue.

## Échecs conservés

Le premier essai backend (`ollama-protocols-run1.json`) a produit deux faux échecs de l'oracle : celui-ci cherchait un mot complet dans une seule trame SSE alors que le texte était découpé. Les réponses originales sont conservées. Le script corrigé assemble les deltas avant comparaison ; le deuxième essai est indépendant et passe sur les trois protocoles. Ce correctif d'oracle ne transforme pas rétrospectivement le journal initial en succès.

## Reproduction

`python3 evidence/probe_protocols.py --base-url http://ADRESSE-OLLAMA:11434 --output /chemin/nouvel-essai.json` exerce uniquement les prompts synthétiques présents dans le fichier, sur l'endpoint local explicitement déclaré. Vérifier disponibilité et charge avant lancement ; le script décharge son modèle à la fin. Il n'exécute pas de code produit par le modèle. Un fichier de sortie existant est refusé. Les paramètres de ligne de commande et ce refus ont été ajoutés après les essais conservés ; l'oracle et les requêtes sont inchangés.

Pour s1d1, utiliser les versions `numpy`, `tokenizers` et `onnxruntime` consignées dans le reçu et vérifier les fichiers contre le manifeste avant chargement. Aucun poids, cache ou environnement Python n'est versionné.

## Non établi

Parcours Codex/oh-my-pi sur Mac, message d'erreur natif Hermes avant épuisement du budget, effort gradué démontré, revue du candidat intégré, release publiée puis réinstallée et rejeu des hôtes sur cette version livrée. Le benchmark local ne mesure ni tarifs équivalents ni facture, et ne compare pas les modèles par défaut des abonnements.

Les essais Mac restent des échecs conservés dans `native/mac/` : la pression mémoire a imposé l'arrêt des générateurs locaux et le petit modèle n'a pas produit l'appel d'outil attendu. Les neuf tests passerelle synthétiques passent sous Python 3.11.12 ; cela ne constitue pas une intégration native. Python 3.9 n'est pas supporté.

## Refaire l'analyse sans fournisseur

Depuis le dépôt récupéré : `python3 tools/analyze_campaign.py --source evidence/campaign --output /chemin/nouveau-rapport`. Le script vérifie les plans et empreintes, refuse `-O`/`-OO` et un dossier de sortie existant. Il ne relance pas les modèles. Les brouillons LinkedIn/X restent non publiés. Le SVG a été rendu localement avec ffmpeg puis inspecté visuellement, sans défaut de lisibilité constaté ; l'accès navigateur loopback avait été refusé et n'a pas été contourné.
