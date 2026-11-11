# Connexions pi-ai

## Raccord retenu

Le candidat part de `d23db79b7d193da17eda961e6936be3a13061c7c` et conserve les stratégies natives Codex/Linux. Les nouvelles connexions peuvent sélectionner le transport `pi-ai` ; une connexion existante sans ce champ conserve le transport HTTP historique. Aucun secret ni configuration utilisateur n'est migré.

Chemin : connexion/modèle OMR → sélection Python existante → processus pi-ai privé sur stdin/stdout → adaptateur fournisseur pi-ai → endpoint configuré. Les formats entrants/sortants Chat Completions, Responses et Messages utilisent les parseurs/encodeurs publiés de pi-ai, pas une copie des adaptateurs. Les outils sont transmis au client : le pont n'en exécute aucun. Le décideur externe existant et les stratégies natives restent distincts.

`@oh-my-pi/pi-ai` est épinglé à **18.14.2**, MIT, paquet inspecté via npm (exports TypeScript ; moteur Bun >=1.4.4). Dépendances directes : omptype, pi-catalog, pi-natives, pi-utils et pi-wire, toutes 18.14.2. Le runtime de construction Bun est épinglé à **1.4.4**. Le fichier de verrouillage fige les dépendances transitives et intégrités. L'exécutable Bun compilé est incorporé au sidecar PyInstaller, qui reste l'unique processus lancé par Tauri. Aucun Node, Bun ou Python à installer chez l'utilisateur.

## Authentification et limites

Réutiliser le coffre OS OMR et transmettre le bearer uniquement en mémoire, par stdin privé, jamais par argument, environnement, fichier ou log. Connexions API key et endpoints locaux sans clé uniquement dans cette tranche. Ne pas lire/importer les stores OAuth de l'utilisateur. Les stratégies Codex natives existantes gardent leur gestion de souscription et leurs permissions. Les connexions OAuth supplémentaires de pi-ai (Anthropic, Codex, Google, Copilot…), Azure/Bedrock/Vertex et fournisseurs multimodaux ne sont **pas qualifiés** ici ; leur présence dans la bibliothèque n'est pas une promesse OMR.

Le pont sépare les octets de réponse et les métadonnées dans un IPC JSONL borné. Les callbacks SSE publiés de pi-ai fournissent les seuls compteurs et identités fournisseur admis dans les reçus ; l'identifiant réémis par l'encodeur et ses compteurs zéro par défaut ne sont pas des preuves. En l'absence de métadonnées fournisseur, modèle confirmé et consommation restent inconnus dans les reçus. Le corps API reste celui de l'encodeur pi-ai (identifiant demandé et usage normalisé, pouvant contenir des zéros par défaut) ; il ne doit pas être utilisé comme preuve de facturation ou d'identité fournisseur.

Le pont refuse avec HTTP 400, avant tout appel fournisseur, les options qu'il ne peut conserver plutôt que les ignorer. Le périmètre entrant est texte et outils fonction uniquement : les discriminateurs et champs imbriqués des messages, blocs, appels/résultats et définitions d'outils sont vérifiés, sans interpréter les données libres des arguments ou schémas comme des options de transport. `allowed_tools`, les contrôles de parallélisme Anthropic et le champ `strict` des outils Chat sont refusés dans cette tranche. Les politiques explicites de cache, y compris les TTL sur système, messages et outils, sont refusées ; `cacheRetention: none` désactive les écritures automatiques du pont. Pour Chat SSE, `stream_options.include_usage: true` demande le bloc usage de l'encodeur ; son absence ou `false` ne le demande pas. Les erreurs fournisseur sont remplacées par une erreur stable sans corps ni identifiants. Pas de retry automatique, de fallback de fournisseur ou de redirection authentifiée. Annulation/délai/arrêt du moteur terminent le processus dédié et son transport. Le pont ne reçoit que la configuration de la connexion sélectionnée et le contexte de la requête.

Le dispatch pi-ai transmet au SDK la base fournisseur validée et le protocole client séparément ; le contrôle du chemin HTTP direct ne s'y applique pas. Le parcours Codex du MVP conserve ainsi sa base fixe `/backend-api/codex` sans la remplacer par `/v1`. Les restrictions d'URL et d'origine restent celles de la configuration validée.

Chat et Responses acceptent uniquement `store: false` : `true` et les valeurs mal formées restent refusés avant réseau. Le callback `onPayload` conserve cette instruction de confidentialité après conversion SDK ; le contrôle réseau refuse l'appel si le corps sortant ne contient plus `store: false`. Les régressions vérifient les octets des endpoints synthétiques et le chemin SDK Codex avec réseau simulé, sans authentification ni inférence fournisseur réelle.

Le processus privé du pont fixe `PI_REQUEST_COMPRESSION=0`. Le SDK pourrait sinon compresser les requêtes longues avant le contrôle réseau, qui exige un corps JSON lisible pour vérifier `store: false`. Les requêtes restent non compressées, y compris au-delà du seuil SDK de 1 Kio ; le contrôle de confidentialité, l’URL autorisée et la limite d’un seul appel réseau restent inchangés. Ce réglage ne provient pas de l’environnement utilisateur.

## OpenRouter : préparation hors réseau

Les connexions `pi-ai` acceptent les bases `/v1` et `/api/v1`, notamment `https://openrouter.ai/api/v1`. Le transport HTTP conserve son contrat `/v1`. Les deux transports acceptent HTTP et HTTPS, y compris pour un serveur sur le réseau local. HTTP ne chiffre ni les requêtes ni les éventuelles clés ; utiliser HTTPS sur les réseaux non fiables. Les URL doivent commencer directement par `http://` ou `https://` et contenir un hôte valide ; espaces, caractères de contrôle, identifiants, query, fragment et port vide ou nul sont refusés avant tout appel. Chat ajoute exactement `/chat/completions` à la base configurée.

Pour Chat uniquement, le pont accepte le contrôle `provider` dans cette forme stricte :

```json
{"only":["cohere"],"allow_fallbacks":false,"max_price":{"prompt":0,"completion":0}}
```

Un seul identifiant fournisseur ASCII non vide est admis (128 caractères maximum, lettres minuscules, chiffres, `.`, `_`, `/`, `-`). Les trois champs sont obligatoires ; tout champ supplémentaire, fournisseur multiple, fallback activé, plafond non numérique ou non nul est refusé HTTP 400 avant réseau. Responses et Messages refusent ce contrôle. Le callback publié `onPayload` ajoute le contrôle validé après le parseur pi-ai : il ne doit pas disparaître pendant la conversion de format. Sans contrôle entrant, aucun contrôle fournisseur n’est injecté.

Cette préparation prouve la conservation des contraintes dans les octets reçus par une fixture loopback, en JSON et SSE, pas une génération OpenRouter réelle. `max_price` nul n’est ni une preuve d’absence de BYOK facturable ni une garantie globale de gratuité. Avant toute inférence réelle : établir l’absence de BYOK facturable applicable ou son exclusion documentée, puis revérifier prix complets et quota sans changer la confidentialité du compte. Les installateurs publics et les replays natifs restent des qualifications distinctes.

Rejeu ciblé après construction du pont : `python3 -B -m unittest test_pi_ai -v`.

## Construction et reproduction

Depuis la racine du dépôt :

```sh
npm ci --prefix desktop
npm ci --prefix desktop/provider-runtime
npm run check --prefix desktop/provider-runtime
npm run build --prefix desktop/provider-runtime
python3 -B -m unittest test_pi_ai -v
# Environnement Python de build créé avec les requirements verrouillés :
.venv/bin/python desktop/scripts/build_sidecar.py
npm run native:build --prefix desktop -- --ci --bundles deb
OMR_TEST_ENGINE=/chemin/absolu/omr-engine .venv/bin/python -B -m unittest test_pi_ai_packaged test_desktop_packaged -v
```

`build_sidecar.py` réinstalle les dépendances verrouillées du pont, compile Bun pour l'hôte et incorpore le binaire **et** l'addon `pi-natives` baseline/default. Ce dernier n'est pas inclus automatiquement par `bun build --compile`. Les licences MIT OhMyPi, les mentions tierces de l'addon et celles de Bun/JavaScriptCore sont incluses dans les ressources Tauri. Les obligations de source/relinking du runtime restent à satisfaire avant une distribution publique ; aucune publication n'est effectuée ici.

## Qualification

| Périmètre | État du candidat |
| --- | --- |
| Responses, Chat Completions, Messages | Adaptateurs réellement exécutés sur serveurs synthétiques : JSON et SSE |
| Modèle, effort, limite de sortie, outils/résultats | Transmission prouvée ; aucun outil exécuté par le pont |
| Erreurs, troncature, redirection, annulation et délai | Refus/arrêt bornés ; un seul appel réseau par requête |
| Authentification | Clé OMR par IPC privé ; sans clé, aucune authentification ambiante. Pi-ai utilise Bearer pour les endpoints Anthropic non officiels ; sa règle `x-api-key` pour l'hôte officiel est inspectée, pas testée en ligne |
| Paquet Linux x86_64 | Sidecar autonome sans runtime sur PATH et replay WebKit natif depuis le DEB extrait |
| macOS, Windows, OAuth supplémentaires, fournisseurs réels | Non qualifiés par ce candidat |

Essais exclusivement synthétiques, endpoints loopback : configuration/modèle, Responses, streaming, aller-retour outils, erreurs avant/après émission, annulation, absence de fuite et exécution du paquet sans PATH de runtimes. Une preuve synthétique qualifie le raccord logiciel, pas l'accès réel à un abonnement ni la qualité d'un modèle. Les replays natifs macOS/Windows et toute activation restent hors de ce candidat.
