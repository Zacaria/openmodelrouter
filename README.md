# Open Model Router

Ce dépôt est un instantané source dérivé ; sa provenance et les limites des preuves historiques sont décrites dans [PUBLIC-HISTORY.md](PUBLIC-HISTORY.md).

Un point d'entrée local `open-model-router` pour choisir une route de modèle, conserver ce choix pendant une conversation et mesurer ce qui a réellement été exécuté.

**État : prototype en qualification. Le contrat complet de `GOAL.md` n'est pas encore satisfait.** La préversion macOS Apple Silicon 0.3.0 signée et notarisée est disponible sur la landing, avec les quatre installateurs 0.1.0 conservés. Les preuves des quatre clients sur la version livrée restent à compléter ; cette publication n'est pas une promesse de compatibilité universelle.

## Lancer la passerelle

Python 3.11+ suffit pour une route fixe ; aucune bibliothèque tierce n'est nécessaire. Le backend doit déjà fonctionner et accepter le protocole choisi. Le routeur ne transfère pas automatiquement un abonnement d'un client à un autre.

1. Préparer votre backend et sa limite de contexte. L'essai Hermes a nécessité 8192 tokens : un backend limité à 4096 refusait sa requête avec outils. Ne réduisez pas les permissions ou outils pour masquer ce problème.
   Pour un Ollama déjà installé et une machine disposant de mémoire suffisante : `ollama pull qwen3:4b-instruct-2507-q4_K_M`, puis `ollama create omr-hermes-qwen3-4b:ctx8192 -f examples/Modelfile`. Cette opération télécharge les poids publics ; elle n'est pas requise si le backend existant convient.
2. Copier `examples/local.json` vers un fichier local et renseigner l'URL, le modèle réellement disponible et le chemin des reçus. L'exemple vise un alias Ollama explicite du modèle Qwen, sans authentification relayée.
3. Démarrer : `python3 omr.py serve --config /chemin/local.json --port 8765`.
4. Dans le client, choisir le modèle virtuel `open-model-router` et l'endpoint loopback. Pour conserver une route entre tours, transmettre le même UUID dans `X-OMR-Session` ; un nouveau UUID représente une nouvelle conversation. Sans cet identifiant, la requête est stateless.

Les points d'entrée sont `/v1/chat/completions`, `/v1/responses` et `/v1/messages`. Le backend doit implémenter lui-même le protocole demandé : aucune traduction ni fausse identité de modèle. Les appels et résultats d'outils sont transmis au client ; le routeur ne les exécute pas à sa place.

## Décider et observer

- `fixed` conserve la route de référence configurée.
- `s1d1` charge des poids vérifiés contre une révision et des empreintes fixes. Installation : `INSTALL-S1D1.md`. Le seuil et les deux routes sont une politique explicite, pas un réglage calibré par l'auteur du classifieur.
- `command` appelle une commande locale de confiance avec le seul premier prompt utilisateur. L'envoi de prompts publics doit être explicitement autorisé ; une commande n'est pas une sandbox. L'intégration Jev utilise la gestion native du secret ou une variable d'environnement, jamais une clé versionnée.

La route est figée pour la durée de vie de la session dans le serveur. Aucun fallback silencieux, aucun retry automatique. Le redémarrage du serveur perd cette affinité en mémoire ; il faut considérer cette limite avant une reprise de conversation. Les sessions sont bornées ; la saturation est un refus explicite.

Les reçus JSONL ne contiennent pas de messages : route, modèle demandé et observé reconnu, effort transmis ou acquitté, catégories de tokens disponibles, décision, durée, erreur et annulation. Un champ absent reste inconnu. Accepter un paramètre d'effort n'établit pas qu'un fournisseur en applique tous les niveaux. Détails et limites : `GATEWAY-SPEC.md`.

## Preuves et limites actuelles

`evidence/README.md` distingue les tests simulés, les composants réellement exécutés et les intégrations encore ouvertes. `evidence/campaign/STUDY.md` fixe une campagne locale à trois bras, cinq familles et jeux séparés ; les résultats bruts, plans, erreurs et graphiques se trouvent dans `evidence/campaign/attempt-2/`.

Cette campagne compare une référence **locale observée**, s1d1 et Jev, pas les modèles par défaut des abonnements ChatGPT ou Claude. Les tâches sont petites et issues de gabarits. La délégation est orchestrée par le runner, pas prouvée dans chacun des quatre hôtes. Aucun gain général, prix équivalent ou économie de facture n'est établi.

Les modules historiques `router.py`, `compare.py`, `pilot-*`, `loop-*`, `demo-*`, `integrated-*` et `comparator-*` restent des expériences antérieures. `simulated.jsonl` contient des nombres inventés pour tester le calcul ; ce n'est pas un benchmark réel.

## Vérifier hors ligne

Dans un environnement Python 3.13 isolé, préparer les dépendances de test avec `python3 -m pip install --require-hashes --only-binary=:all: -r desktop/sidecar-requirements.txt`. Les tests de distribution utilisent PyInstaller et packaging ; cela n'ajoute pas de dépendance à la passerelle à route fixe.

`python3 -B -m unittest discover -v` exécute ensuite les tests racine, dont les transports TCP synthétiques, les bornes, l'annulation et les régressions de revue. Les tests des dossiers historiques se lancent depuis leur propre dossier. `python3 -B tests/test_landing.py` vérifie les liens et la structure de la landing. Ces contrôles ne remplacent pas les parcours réels des clients.

La passerelle écoute uniquement sur loopback. Ne l'exposez pas comme service public. Les identifiants sont supprimés des requêtes amont par défaut ; leur relais exige une route explicitement autorisée et TLS, hors loopback de test.
