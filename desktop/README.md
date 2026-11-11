# OMR Desktop

Tauri v2 + React/shadcn, routeur Python existant embarqué. Aucune dépendance Python côté utilisateur. Lire [CONTRACT.md](CONTRACT.md) pour les frontières de sécurité, politiques et mesures.

L’interface suit la [direction artistique fournie](ART-DIRECTION.md) ; [provenance et génération du logo](design/BRAND.md). Navigation, topologie et activité montrent le catalogue et les reçus locaux, jamais les chiffres de la référence. Le thème suit le système ; Réglages permet un choix clair/sombre pour la session courante. Les décorations de fenêtre restent natives.

Le [mandat de livraison](design/delivery/DESKTOP-DELIVERY.md) et la [distribution mise à jour](design/delivery/DESKTOP-DISTRIBUTION-20261031-public.md) autorisent les installateurs/checksums publics depuis le site existant, sans rendre le dépôt public. Ils remplacent les anciennes attentes d’accord de distribution. La revue UI reste distincte de la composition et de la qualification trois OS.

## Version affichée

Le badge de l’interface utilise la version produit déclarée dans `desktop/package.json`, intégrée à la compilation de l’interface.

## Développer sur cet hôte

Pour le candidat ARM macOS : macOS 14+ est requis par ONNX Runtime 1.31.1. Fournir `OMR_WORKER_WHEELS`, un wheelhouse natif correspondant à `desktop/s1d1-requirements.lock` ; `build_sidecar.py` l'installe hors réseau avec contrôle des empreintes avant PyInstaller. Intel/Rosetta n'est pas qualifié par le build ARM. Voir [le contrat macOS](MACOS-NATIVE-20261102.md).

1. Installer Node 24, Rust 1.91+, uv et les [prérequis système Tauri v2](https://v2.tauri.app/start/prerequisites/).
2. Depuis la racine : `uv venv --python 3.13.5 desktop/.sidecar-build/venv`, puis `uv pip sync --python desktop/.sidecar-build/venv/bin/python --require-hashes desktop/sidecar-requirements.txt` et `desktop/.sidecar-build/venv/bin/python desktop/scripts/build_sidecar.py`. Sous Windows, employer `desktop/.sidecar-build/venv/Scripts/python.exe` à la place du chemin `bin/python`.
3. Dans `desktop/` : `npm ci`, puis `npm run native:dev`.
4. Construire le paquet natif : `npm run native:build`. Les artefacts sont sous `src-tauri/target/release/bundle/`.

Faire la même préparation et compilation sur chaque OS cible. La release signe/notarise avec les accès existants ; aucun workflow de publication automatique n'est installé.

Les paquets embarquent les autorités publiques certifi 2026.10.23 pour vérifier HTTPS sans dépendre d'un Python installé. Les autorités privées et proxies TLS d'entreprise ne sont pas configurables dans cette version ; une validation TLS refusée reste une erreur, sans repli non vérifié.

## Premier démarrage

1. Depuis un état vide, l’assistant propose de connecter un répondant Responses, choisir un décideur facultatif, régler le routage et lancer un test explicite. « Reprendre la configuration » le rouvre ; une configuration existante utilisable n’est pas forcée à le suivre. Les souscriptions natives Codex/Claude/Hermes/OMP ne sont pas importées.
Le choix du type de fournisseur propose les valeurs usuelles Ollama, LiteLLM et OpenRouter ; Codex conserve son parcours natif sans import de token. Le chemin du fichier éditable et « Charger le fichier » sont dans Fournisseurs : voir [PROVIDERS-FILE.md](PROVIDERS-FILE.md) pour modifier les réglages hors UI, les refus et les consentements.

2. Ajouter la clé via « Enregistrer dans le coffre OS » si l'API l'exige. Sur Linux, un service Secret Service déverrouillé est nécessaire. En cas d'erreur, aucun repli non chiffré n'est utilisé.
3. Découvrir le catalogue (sans génération), ou tester un modèle après confirmation du coût possible. L'absence de `/v1/models` n'empêche pas la déclaration manuelle.
4. Brancher un client API via l'URL et la clé éphémère affichées dans État. Un redémarrage change le port et la clé. Les IDs `direct/…` ne passent jamais par le décideur. Ajouter `X-OMR-Session: <UUID>` pour la continuité par session.
   Une continuation d’outils ou une session sans réévaluation reste liée à sa route exacte ; si elle est désactivée, modifiée ou devenue incompatible, la requête est refusée avec `continuity_route_unavailable`, sans bascule silencieuse. Rétablir la route exacte ou démarrer une nouvelle session pour une nouvelle tâche ; ne pas rejouer un résultat d’outil sur une autre route.
5. Pour les profils automatiques, choisir BYOK, serveur existant par URL (dont Ollama), ou s1d1 téléchargé/géré explicitement. Le protocole Jev utilise SystemOne et son vrai décodeur. Lire [ONBOARDING.md](ONBOARDING.md) pour les limites et états. Changer la destination exacte ou restaurer une révision exige un nouvel accord. Les profils restent bloqués sans décideur consenti ; les routes directes restent disponibles.

La fermeture minimise la fenêtre sous Linux pour qu'elle reste accessible sans tray ; sur macOS/Windows elle la masque quand le tray est disponible, sinon demande confirmation d'arrêt. « Quitter » est explicite et refuse d'interrompre des requêtes actives sans confirmation. Les réglages sont appliqués aux prochaines requêtes sans redémarrage. Autostart se règle dans Réglages. Les reçus et leur export sont sans transcript ; rétention 30 jours et 10 000 reçus maximum. Les exports sont des copies manuelles à supprimer après usage, sans rétention automatique.

## Rejouer la configuration et un grand catalogue

Depuis la racine, installer les notices verrouillées avec `npm ci --prefix desktop/provider-runtime --ignore-scripts`. Puis, dans `desktop/`, exécuter `npm ci`, `npm test`, `npm run check`, `npm run build`, puis :

```sh
uv run --python 3.13.5 --with playwright==1.58.0 python scripts/test_provider_ux.py --evidence test-results/provider-ux
```

Ce replay ouvre le vrai frontend compilé dans Brave, avec un `Runtime` Python isolé pour les enregistrements, rechargements et refus CAS réels. Les 604 identifiants de découverte, le coffre et la génération sont des fixtures explicites : aucun fournisseur ni coffre OS n’est appelé. Il vérifie la coalescence pendant une écriture, le vidage avant clé/découverte/test, la sélection filtrée au clavier, les actions groupées, les captures clair/sombre à 800 et 1180 px, et la reprise après conflit de révision/fichier. Ce replay Linux ne qualifie pas le DMG ni le profil Mac.

## Rejouer les parcours natifs Linux

`scripts/native_replay.py` utilise Selenium 4.38.0, tauri-driver 2.1.0 et WebKitWebDriver de la même version que WebKitGTK. Le harnais Linux utilise xfwm4 et wmctrl dans le serveur Xvfb isolé pour exercer une vraie fermeture OS/minimisation, sans confondre celle-ci avec la fin de session WebDriver. `scripts/run_native_replay.sh` crée un HOME/XDG isolé et un runtime court sous TMPDIR pour respecter la limite des sockets Unix de Secret Service. Il pilote l'application Tauri réelle, son IPC et son sidecar gelé avec une API synthétique locale. Fournir `OMR_TEST_APP` (binaire exact), `OMR_EVIDENCE` et des dossiers HOME/XDG isolés ; démarrer tauri-driver sur 127.0.0.1:4444 sous dbus/Xvfb, puis `npm run test:native`. Ne jamais pointer ce replay vers une session ou un profil personnel. Le test de coffre utilise uniquement une clé factice et documente l'absence éventuelle d'un coffre déverrouillé.

Ajouter `OMR_TEST_ART_DIRECTION=1` pour parcourir les six écrans, les deux thèmes et les fenêtres 1180 × 820 / 800 × 640, capturer leurs parties hautes/basses, vérifier le focus modal/clavier, le logo chargé et une vraie erreur de découverte HTTP 503. `OMR_TEST_DARK=1` exerce aussi le thème système sombre au lancement. Les captures WebDriver sont celles du webview : sous cet hôte, 1180 × 795 / 800 × 615, sans fabriquer de chrome OS. Pour éviter une collision avec un autre replay, régler deux ports libres distincts via `OMR_TEST_DRIVER_PORT` et `OMR_TEST_WEBKIT_PORT` (défauts 4444/4445).

Vérifications visuelles hors runtime : `uv run --python 3.13.5 --with pillow==12.0.0 python scripts/test_brand.py` contrôle provenance, formats et régénération ; `npm test` contrôle aussi les composants réels rendus et les contrastes de tokens. Le chargement initial est couvert par rendu du vrai composant ; sa brièveté n’est pas une preuve de capture native. Aucun aperçu Linux ne qualifie un menu/Dock macOS ou une taskbar Windows.

## Rejouer le premier démarrage

`scripts/run_onboarding_replay.sh` crée une session HOME/XDG/D-Bus/Secret Service jetable et lance `scripts/onboarding_replay.py` contre le vrai binaire Tauri. Renseigner les chemins absolus `OMR_TEST_APP`, `OMR_TAURI_DRIVER` (2.1.0), `OMR_WEBKIT_DRIVER` (version système identique) et `OMR_TEST_PYTHON` (Selenium 4.38.0), puis `sh desktop/scripts/run_onboarding_replay.sh` depuis la racine. Les deux ports peuvent être isolés par `OMR_TEST_DRIVER_PORT`/`OMR_TEST_WEBKIT_PORT` ; les preuves vont dans `OMR_EVIDENCE`.

Le replay utilise uniquement une clé factice dans un coffre jetable, des serveurs API synthétiques et le vrai téléchargement public s1d1 explicitement déclenché. Il vérifie reprise après interruption, trois modes, refus/reprise API, vrais protocoles SystemOne, annulation atomique, décision ONNX non constante, arrêt du groupe gelé et relance sans auto-démarrage. Aucun fournisseur payant ni checkpoint Imajev n’est qualifié par ces fixtures.

## Mesures

Niveaux qualité, prix par million de tokens en USD et sortie attendue sont déclarés par l'utilisateur. Aucun gain de qualité ou d'économie n'est garanti. Le repricing d'une référence utilise le même volume observé, sans facture de souscription, réduction cache ou économie de tokens inventée. Le surcoût du décideur est séparé. Sans référence ni prix, la comparaison est non mesurée. Sans historique direct local, le classement personnel est vide.

Les [stratégies natives](NATIVE-STRATEGIES.md) ajoutent des commandes explicites dans une **nouvelle session Codex isolée**, sur Linux x86_64 avec Codex 0.159.0 et Bubblewrap installés. Aucun import de session ni changement du routage HTTP. Claude, OMP, Hermes et les autres OS restent non disponibles pour ces commandes dans Desktop ; leurs qualifications partielles ne sont pas une activation. Les liens de conversations restent indisponibles. Le gateway conserve les trois contrats clients ; pi-ai adapte les nouvelles connexions fournisseurs. Le test de génération API intégré utilise Responses quand le répondant le déclare, sinon Chat Completions. Pour Messages, exercer le client API correspondant. Le modèle géré nécessite numpy, tokenizers et onnxruntime dans le sidecar : les versions de référence figurent dans `../requirements-s1d1.txt`. L’ajout de ces dépendances au lock et aux notices de distribution est suivi séparément ; ne pas qualifier un paquet qui les omet.
