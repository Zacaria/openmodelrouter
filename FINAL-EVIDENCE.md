# Bilan de livraison — 27 octobre 2026

**Objectif global non atteint.** La préversion privée candidate.3 est publiée et réinstallable. Trois parcours d'hôtes disposent de preuves réelles ; oh-my-pi Mac n'a pas de modèle natif disponible. Ce document est le bilan de cette étape, pas une attestation finale des cinq conditions de `GOAL.md`.

## Livrable identifiable

- Tag signé : `v0.1.0-candidate.3`, commit runtime `63e517c25caa503b02eb38b2be994f8e2c32e142`, arbre `f6d12bc5532ca1a132edcaf009f0cf73c21f750a`.
- Archive SHA-256 : `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`. Publication privée relue, trois assets ; le téléchargement après publication est identique au téléchargement certifié. Candidate.2 reste un brouillon inchangé, échec compris.
- CI runtime `40459266741` réussie. Conservation des preuves et instructions au commit signé `9f02ca00d784e0c5d895beee17e1af86f7c77a65`, CI `40461449790` réussie, sans changement du runtime.
- Installation fraîche depuis les assets GitHub : 115 tests exécutés, 114 réussis, un test d'inférence ignoré ; contrôle landing réussi. Ce sont des tests hors ligne, pas des preuves de fournisseurs réels.

[Installation](INSTALL.md) · [État détaillé](DELIVERY-STATUS.md) · [Publication et installation : preuves](evidence/release/candidate.3/RECONCILIATION.md) · [Revue exacte du runtime](evidence/reviews/deadline/deadline-disconnect-independent-review.md)

## Parcours réels du runtime livré

| Hôte | État et limites |
|---|---|
| Hermes VM | Outil/résultat, reprise dans un autre processus, streaming, alias local observé, erreur contrôlée et interruption/reprise. Un essai ciblé corrèle exactement un delta transmis, une socket amont active et le reçu `cancelled` ; le premier essai inconclusif reste conservé. |
| Claude Code VM | Outil/résultat, reprise, streaming, alias local observé, erreur contrôlée et interruption/reprise. Corrélation des marqueurs par session et ordre sériel, pas par identifiant de requête. |
| Codex Mac | Outil/résultat, reprise de thread, streaming, modèle `gpt-6.1-terra` observé, rejet local 400 sans génération et reprise, SIGINT en flux actif et reprise. Fin native et reçu de transport restent distincts. |
| oh-my-pi Mac | Non qualifié. Préflight du 27 octobre à 06:18 UTC : OMP 18.13.0, zéro modèle disponible, commandes réussies. Cela ne prouve pas l'absence de toute session dans les magasins d'authentification. |

[Manifeste et limites des 93 fichiers](evidence/native/host-replay-63e517c/RECONCILIATION.md) · [Annulation Hermes ciblée](evidence/native/host-replay-63e517c/vm/hermes-cancel-closure/REPORT.md) · [Codex](evidence/native/host-replay-63e517c/mac/REPORT.md) · [Préflight OMP](evidence/native/omp-current-preflight.json)

Les deux hôtes VM ont été éprouvés sur une route locale fixe explicite, pas sur toutes les routes commerciales. La fermeture des sockets ne prouve pas l'arrêt du calcul GPU. L'effort transmis n'est pas une preuve indépendante de son application. Une ambiguïté préexistante de classification des resets amont bruts hors délai demeure connue. Ne pas transformer ces limites en validation globale du routage ou des fournisseurs.

## Benchmark, dossier éditorial et landing

La campagne conservée couvre trois bras, cinq familles, deux jeux séparés et deux répétitions : 60 parcours par tentative. La référence est locale, non le modèle natif par défaut d'un abonnement. Les erreurs et résultats négatifs sont conservés ; l'ambiguïté de l'oracle diagnostic, les catégories de tokens inconnues et les limites de provenance sont expliquées. Aucun gain général, économie de facture ou efficacité native des sous-agents n'est démontré.

[Rapport et limites](evidence/campaign/analysis/REPORT.md) : statistiques, données, graphiques et brouillons accompagnent la campagne ; aucune publication LinkedIn/X n'a été effectuée. Les observations de Jev et s1d1 restent bornées à leur protocole et aux poids documentés, pas une qualification universelle du décideur.

La landing publique sert les octets suivis de `site/index.html` ; les huit liens fragments sont valides, sans destination externe. Le contrôle final réutilise explicitement les preuves desktop/mobile du même digest, sans nouvelle session visuelle. La réserve à 320 px concernant l'indication du défilement horizontal demeure. [Relecture de production](evidence/landing/final-readback.md).

## Blocage et reprise

L'accès natif OMP est le prérequis humain restant pour son parcours : sur le Mac, utiliser le flux natif `~/omr-host-adapters-task/bin/omp login openai-codex`, ou établir explicitement un autre backend autorisé. Ne transmettre aucun secret dans la conversation. Une connexion Codex CLI ne vaut pas connexion OMP.

Après cet accès, reprendre uniquement la qualification OMP et réconcilier les conditions de routage/effort du contrat avant toute acceptation globale. Ne pas répéter les essais locaux qui dépassaient la garde mémoire, ni le tunnel SSH refusé, ni copier les identifiants entre clients. Préserver le runtime signé et les traces existantes ; aucun achat, fallback silencieux ou affaiblissement des garde-fous n'est autorisé.
