# Host adapters

Start a trusted gateway on loopback (e.g. `python3 omr.py serve --config PATH --port PORT`), then launch from an isolated synthetic project. `--session` must be a UUID and must be reused only for the same conversation. Each launcher binds a deterministic loopback proxy port derived from the session UUID; use `--proxy-port PORT` to override it consistently across resumes. A collision fails explicitly without choosing another port; it overwrites `X-OMR-Session`, forwards paths, headers and streaming body without inspecting content, then terminates. No content hash. This is not an authentication boundary: other local processes can contact the proxy port. Authorization and X-API-Key headers are stripped by the local proxy. Claude receives a local placeholder token; Codex is configured without OpenAI authentication. Never point the gateway at an untrusted service or log headers. Confirm actual upstream authorization independently; do not copy tokens. Protect native subscription quotas and stop on billing/quota errors; this launcher does not implement a spending cap.

```sh
python3 host-adapters/launch.py hermes --port 8000 --session UUID --project PROJECT -- --help
python3 host-adapters/launch.py codex --port 8000 --session UUID --project PROJECT -- exec --ignore-user-config --ephemeral --sandbox read-only --skip-git-repo-check 'synthetic prompt'
python3 host-adapters/launch.py omp --port 8000 --session UUID --project PROJECT --omp-bin "$HOME/omr-host-adapters-task/bin/omp" -- --print --no-tools --no-session 'synthetic prompt'
python3 host-adapters/launch.py claude --port 8000 --session UUID --project PROJECT -- -p --tools '' --no-session-persistence 'synthetic prompt'
```

Run the gateway on each host's loopback; do not rely on an SSH tunnel. OMP isolates its provider registry in a temporary `PI_CODING_AGENT_DIR`. Do not use normal projects or enable write tools for synthetic probes. Claude and Codex use local no-credential mode; the model sent is `open-model-router`, not a Claude alias. The proxy currently supports POST with Content-Length only, not GET, chunked request bodies, upgrades or web sockets; upstream connection failure is 502. Test with `python3 host-adapters/test_launch.py`. See `evidence/native/final-vm/REPORT.md` for actual VM outcomes and limitations, and `evidence/native/error-visibility/REPORT.md` for the later adapter-visible error replay. Neither report qualifies the Mac clients.

## Catalogue Desktop (opt-in)

`--desktop` lit le catalogue du moteur Desktop authentifié, au lieu de l’alias historique. Fournir la clé éphémère via `OMR_DESKTOP_KEY` (ou `--key-env NOM`), jamais dans un argument de commande ou un fichier de modèles. Le launcher la retire de l’environnement du client ; seul le proxy la garde en mémoire et injecte le bearer vers le moteur loopback. Chaque lancement génère une **autre clé locale**, transmise au seul client par variable d’environnement et requise aussi bien pour GET que POST. Les configurations natives référencent son nom de variable, pas sa valeur. Les requêtes sans cette clé, à Origin ou Host étranger sont refusées ; les autres autorisations du client ne sont pas transmises. Un processus ayant accès à la mémoire ou à l’environnement du même utilisateur reste hors de cette isolation : le mode historique sans `--desktop` garde sa frontière précédente.

```sh
# Dans un shell privé, définir OMR_DESKTOP_KEY avec la clé affichée par l’app.
# Lister sans lancer de client ni générer :
python3 host-adapters/launch.py omp --desktop --list-models --port PORT --session UUID --project PROJECT
# Le mode par défaut est Équilibré ; une route directe est choisie exactement :
python3 host-adapters/launch.py omp --desktop --model 'direct/CONNECTION_UUID/MODEL_UUID' --port PORT --session UUID --project PROJECT
```

Les trois profils sont conservés ensemble, plus **toutes les routes directes activées compatibles avec le protocole du client** : Chat pour Hermes/OMP, Responses pour Codex, Messages (`anthropic`) pour Claude. Les routes incompatibles sont exclues, pas traduites. Un profil sans décideur consenti reste affiché mais refuse la génération ; une route sans outils peut être utilisée sans outils mais refuse une requête qui en impose. Une déclaration de protocole n’est pas une vérification fournisseur. Relancer le launcher après un changement de catalogue pour rafraîchir les registres natifs.

- **OMP** : registre privé `models.yml` mult modèles, repris par `/models` et le sélecteur natif. Les fenêtres de contexte/sortie viennent des limites opérateur, pas d’une découverte. Aucun prix ni capacité de raisonnement n’est inventé ; un éventuel coût natif nul par défaut ne prouve pas la gratuité.
- **Codex** : `model_catalog_json` privé passé au démarrage, trois profils et routes Responses dans le catalogue natif. Métadonnées texte seules, sans niveaux d’effort réglables ni capacités web/image inventées ; l’effort fixe d’une route est appliqué par OMR. Ce raccordement exige une version Codex prenant en charge cette option.
- **Hermes** : `/v1/models` disponible via le proxy pour le sélecteur du fournisseur custom ; le client reste démarré avec `--base-url` et `--model`. Le launcher fournit `OPENAI_BASE_URL` égal à cette URL `/v1` et `OPENAI_API_KEY` égal à la clé éphémère du proxy dans le seul environnement enfant : le résolveur associe ainsi la clé au bon loopback au lieu d’utiliser `no-key-required`. `CUSTOM_API_KEY` reste fourni pour les versions qui le lisent, mais ne suffit pas seul. Aucun réglage Hermes persistant n’est modifié. La visibilité réelle doit être qualifiée avec sa version native.
- **Claude Code** : sélection explicite `--model ID` et liste du launcher ; pas d’injection de toutes les routes dans son menu propriétaire. Ne pas annoncer une visibilité native universelle.

`--list-models` prouve uniquement la liste filtrée du launcher. Les tests utilisant un exécutable factice prouvent les arguments et fichiers, jamais l’affichage natif. Les parcours Linux réellement exécutés et les limites Mac sont consignés dans la preuve de la tranche.

## Ollama context for Hermes

The tested Qwen 4B model's 4096-token default cannot fit Hermes' isolated initial prompt and tool schemas (4433 tokens). Configure an Ollama model alias with a larger context rather than removing tools or changing permissions. For example, on a trusted Ollama endpoint with the base model already installed:

```sh
curl -fsS "$OLLAMA_URL/api/create" -H 'Content-Type: application/json' -d '{"model":"omr-hermes-qwen3-4b:ctx8192","from":"qwen3:4b-instruct-2507-q4_K_M","parameters":{"num_ctx":8192},"stream":false}'
```

Set the gateway's local route `model` to `omr-hermes-qwen3-4b:ctx8192` and start or reload the gateway using its supported lifecycle. Confirm `/api/show` reports `num_ctx 8192`, and after a request `/api/ps` reports `context_length 8192`. This consumes additional VRAM and is only a bounded capacity for these probes, not a guarantee for larger conversations; size context for the workload and hardware. The wrapper does not alter tool access. Use the same session UUID and optional proxy port to resume a conversation; the proxy base URL remains stable. See `evidence/native/hermes/diagnostic.md`.

For upstream HTTP status >= 400 or a failure before upstream headers, the adapter prints a constant message and numeric status to stderr (502 for a connection failure). It does not log the response body, headers, URL or token. This is adapter-visible output, not a native Hermes APIError; Hermes may keep retrying until the runtime budget expires.

## Runtime and OMP limits

`--run-timeout SECONDS` sets a positive total command runtime budget; the default is unlimited for interactive use. It is not a per-turn deadline. Expiry sends SIGTERM to the host process group, then SIGKILL after a two-second grace, and exits 124 with a message.

OMP uses operator-specified `--context-window` (default 8192) and `--max-output-tokens` (default 2048, no larger than context). These are configured ceilings, not detected capabilities; they do not change the backend context or output limits.
