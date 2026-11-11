# Stratégies natives — contrat d'intégration

Ce module ne décide pas d'un modèle à la place du moteur et n'exécute jamais les outils d'une conversation HTTP. Le client propriétaire garde son historique, ses instructions, son sandbox, ses permissions et son mécanisme d'annulation. Aucune modification de `omr.py`, `desktop/` ou Hermes core.

## Interface minimale

`CodexStrategies(rpc)` se raccorde à une connexion **déjà qualifiée**, possédée par le client, vers le protocole app-server Codex. Le transport fourni expose `request(method, params)` et `wait(predicate, timeout)`. L'adapter ne lit ni credentials ni sessions sur disque et ne lance pas de processus implicitement.

- `compact(thread_id)` déclenche `thread/compact/start`. L'accusé réception seul n'est pas une réussite : attendre l'item natif `contextCompaction` terminé, puis le tour terminé sans erreur, sur le même thread et le même tour. Pas de résumé généré par le proxy.
- `turn(thread_id, text, model=None)` lance un tour natif, conserve les réglages de permissions/instructions du thread ; ne fournit aucun override de sandbox. Attend son résultat effectif.
- `delegate(thread_id, goal, context, model=None)` demande une délégation explicite et bornée au client, pas une seconde génération indépendante présentée comme sous-agent. Réussite seulement avec le spawn natif et une terminaison native du même enfant : `collabAgentToolCall` spawn/wait, ou les items `subAgentActivity` started/completed de Codex 0.159. Une réponse textuelle « j'ai délégué » ne suffit pas. Les champs goal/context sont des données, jamais une nouvelle politique d'autorisation. Le modèle du tour parent et celui de l'enfant ne sont pas confondus : aucun changement de modèle enfant n'est revendiqué sans observation native.
- `cancel(thread_id, turn_id)` transmet `turn/interrupt`, y compris depuis le thread de contrôle pendant un `turn()` synchrone. `StdioRPC` route chaque réponse vers son identifiant et conserve les notifications pour leur attente propriétaire ; un ack d'interruption ne doit pas consommer la terminaison du tour, ni l'inverse. Le `turn()` actif reçoit la terminaison `interrupted` comme échec explicite. L'accusé n'atteste pas l'arrêt du calcul fournisseur. L'appelant doit attendre la terminaison native et fermer la connexion qu'il possède si son budget expire. Les callbacks du transport s'exécutent sur son unique thread de lecture et ne doivent pas y attendre une réponse RPC.

Un seul tour actif par instance ; l'appelant garantit une connexion exclusive, un thread au repos et aucune paire outil/résultat ou approbation en attente avant l'opération. La réponse vide de compact/start ne porte pas d'identifiant : sa corrélation dépend de ce prérequis, puis du turn/started natif. Les notifications d'autres threads/tours ne valident pas l'opération. Erreur, annulation, absence de preuve ou timeout restent des échecs explicites. Le transport ne doit jamais approuver automatiquement une requête serveur d'outil ou de permission. Les prompts et projets des essais sont synthétiques ; cela ne garantit pas que les réponses natives le soient. Avant toute écriture, la sonde Claude expurge récursivement les adresses de type email de tous les champs persistés (assistant, result, outils, stderr, commandes et validations inclus), puis sérialise le résultat. Les événements d'initialisation restent exclus. Ce filtre ciblé ne garantit ni la détection d'identifiants obfusqués ni l'absence de tout autre renseignement personnel ; les preuves sont contrôlées avant attachement. Les captures historiques sont retraitées hors ligne, avec empreintes avant/après et provenance ; les anciens paquets sont non consommables.

## Adapter OMP RPC

`OMPStrategies(rpc)` utilise le protocole JSONL natif OMP 18.13.0, **pas** JSON-RPC 2.0. Le transport propriétaire expose `request(command, params)` retournant la frame response entière et `wait(predicate, timeout)`. `turn` attend `prompt_result` corrélé, pas seulement l'ack ; `compact` exige un vrai CompactionResult avec résumé et frontière conservée ; `switch` vérifie le modèle retourné ; `cancel` transmet `abort`. Aucun nouveau processus ni credential dans l'adapter. La délégation OMP n'est pas exposée comme supportée tant que les événements natifs du Task tool n'ont pas été exercés. Le script de qualification utilise un projet temporaire, les stores natifs inchangés et désactive règles, contexte, extensions et outils.

## Adapter Claude Code

`ClaudeStrategies(execute, session_id)` reçoit un exécuteur CLI déjà isolé et propriétaire de la session synthétique ; `execute(session_id, prompt)` renvoie les événements stream-json natifs. L'adapter ne fournit **aucun** flag de permissions, tools, agents ou credentials. Compaction : `/compact`, frontière native `compact_boundary` de cette session et résultat local réussi. Délégation : appel Agent natif, résultat d'outil correspondant et statistiques d'un seul enfant terminé sans récursion. L'identité/modèle/permissions de l'enfant restent inconnus si le client ne les expose pas ; ne pas en déduire que le profil personnalisé demandé a été choisi.

## Coûts et preuves

Les données d'usage conservent les compteurs natifs et leur périmètre, y compris cache et raisonnement ; absence = inconnu, jamais zéro. Codex renvoie des snapshots cumulatifs de thread et le dernier appel, pas un total de tour. Après compaction ils peuvent repartir d'un compteur de contexte : `usage_scope` le signale et `auxiliary_usage` reste inconnu.

Claude conserve `native_reported_usage` séparément de `accounting.session_snapshot` (`total_cost_usd`, `modelUsage` cumulatifs). `accounting.action_delta` soustrait le résultat immédiatement précédent de la même session : tokens par modèle et équivalent monétaire natif, compaction et enfants inclus lorsqu'observables. `previous_result` doit être le résultat natif immédiatement antérieur ; `session_start=True` autorise une origine zéro uniquement pour une session synthétique neuve attestée par l'appelant. Sans ce prérequis, après un résultat manquant ou une baisse de compteur, les deltas concernés restent inconnus. `ClaudeStrategies` conserve cette origine entre ses opérations ; l'exécuteur doit lui réserver la session sans opération concurrente ou externe. Le rapport utilise la même comptabilité ; `claude_cases(..., session_start=True)` n'est utilisé que pour les sondes créant leur propre UUID frais. Le zéro de `usage` de `/compact` n'annule pas un delta cumulatif observable. Les snapshots et les deltas ne s'additionnent jamais ensemble ; `thinkingTokens` est une sous-catégorie de sortie, pas un supplément.

Les appels de compaction, enfants, intégration du résultat et reprises font partie du total. L'équivalent natif au tarif annoncé n'est pas la facture de souscription : `actual_billed_usd` et `full_cost_usd` restent inconnus. Aucun gain de coût n'est présumé.

La matrice `COMPATIBILITY.md` distingue interface documentée, contrôle natif sur backend synthétique et génération réelle. Les fixtures ne qualifient ni accès fournisseur ni maintien sémantique. Les comparaisons maintien / changement / compaction puis changement / délégation doivent publier les échecs et valeurs manquantes.

## Vérifier

```sh
python3 -B -m unittest discover -s advanced/tests -v
```

Le raccordement au socle appartient à la continuation d'intégration. Ne pas activer un client ou une session existante non qualifiés pour faire passer un test.
