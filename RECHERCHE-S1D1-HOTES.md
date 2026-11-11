# Décision : première intégration locale du routeur

Recherche documentaire consultée le 26 octobre 2026 (UTC). Périmètre : sources publiques ; aucun appel de modèle, achat, compte ou session privée pendant cette recherche. Les pages non épinglées sont susceptibles de changer. Ce document est une recommandation et non une preuve d'intégration fonctionnelle.

## Recommandation

Choisir **oh-my-pi (OMP) avec un fournisseur OpenAI-compatible local sans clé**, et conserver Hermes comme deuxième cible du même protocole. OMP documente explicitement un fournisseur local `auth: none`, son URL et un modèle sélectionnable `provider/model-id` ; Hermes accepte également les fournisseurs personnalisés.[14][15][23] La plus petite tranche utile est une passerelle liée à `127.0.0.1`, alimentée par s1d1 local et un générateur local déjà disponible, sur données synthétiques. Exposer le choix et le raisonnement de routage, garder la même route par session initialement, et vérifier streaming, outils et erreurs. Il ne suffit pas de créer une URL : le modèle génératif local, les appels d'outils et l'hôte n'ont pas été exercés dans cette recherche. Pas de coût réseau ni de données privées dans cet essai ; le temps et les ressources de calcul locales ne sont pas gratuits au sens physique.

**Alternative immédiate :** un lanceur s1d1 qui choisit modèle et effort une fois avant le lancement de Claude ou Codex, sans intercepter les requêtes. Le tutoriel amont le décrit explicitement comme non testé ; il ne fournit ni réévaluation en cours de conversation ni orchestration de sous-agents.[6][7] Un choix local d'un modèle distant ne garantit pas zéro coût ni absence de transmission : utiliser uniquement un backend génératif local pour la démonstration sans coût et sans données privées.

## Baseline réelle : s1d1

La collection contient 12 variantes, quatre tailles × PyTorch fp16, MLX 8 bits ou ONNX int8 ; licence déclarée Apache-2.0.[1][2] La carte et le code principal sont épinglés à `7fb9a4e3d03e3d942a98648268ff76c6152c18d6`. Le modèle prend **le premier message utilisateur seul** pour cette baseline, sans système ni historique, tronqué à 1 024 tokens ; il ne produit pas une réponse générative et ne sélectionne pas lui-même de modèle.[2][3]

Le tenseur de 21 valeurs est décodé ainsi : `clip(0.5 + 0.25 * premier_logit, 0.01, 1)`, argmax des 19 logits de tâche, puis sigmoïde du dernier logit et seuil 0,5 pour `needs_tools`. Le wrapper renvoie aussi niveau de complexité, probabilité et nombre de tokens ; ne pas appliquer un softmax unique aux 21 sorties.[3] Une politique séparée détermine route et effort à partir de ces signaux ; les seuils et noms de modèles choisis pour le projet sont une politique expérimentale, non un résultat appris du classifieur.[2]

Exécution : Python ≥ 3.10, `numpy`, `tokenizers`, `huggingface_hub` si téléchargement Hub ; `onnxruntime` sur CPU pour ONNX, ou PyTorch et `transformers` pour PyTorch, ou `mlx-embeddings` pour MLX. `variant.json` choisit le backend et `vocab_map.npy` est utilisé quand présent.[3] Les variantes ONNX corrigées du 25 octobre 2026 évitent des scores erronés observés sur certains x86 AVX2 sans VNNI ; ne pas inférer que les métriques historiques ont été recalculées pour les nouveaux poids.[2][5] Jeu d'entraînement non publié ; les métriques publiées mesurent l'accord avec un juge LLM, pas une vérité humaine.[2] Vérifier aussi `NOTICE` pour le modèle de base et ses mentions de licence.[4]

**État de preuve :** cette recherche a lu la collection, les cartes et le code ; elle n'a ni téléchargé ni exécuté les poids. Le board rapporte séparément une inférence réelle ONNX tiny, révision `dac13b5c0356864ea4501fa151d74dcd8b3ea22a`, sur prompt synthétique ; la génération aval était simulée. Ce résultat est un témoignage du run de la carte `t_5228779f`, pas une vérification reproduite ici. Les droits d'accès effectifs des poids n'ont pas été testés ici ; le jeu d'entraînement reste indisponible.

## Solutions déjà disponibles

- **s1d1-tantive + LiteLLM Auto Router :** l'auteur rapporte un test local LiteLLM 1.106.4 avec son API hébergée puis tantive 0.8.0 ; l'image 0.8.1 embarque les poids corrigés. La classification de l'intégration documentée porte sur le **dernier** message utilisateur, donc ne constitue pas directement la baseline premier prompt exigée ici. La démo/API hébergée conserve les données pour réentraînement selon le tutoriel : ne pas y envoyer des données privées.[5]
- **Tutoriels amont Claude et Codex :** lanceur à sélection initiale non testé ; passerelle Claude non testée de bout en bout et chemin Responses Codex non écrit dans le hook documenté. Ne pas les présenter comme intégrations validées.[6][7]
- **Hermes OrqueHelx :** routage à la délégation, avec fournisseurs déjà configurés et authentifiés ; solution existante plutôt qu'un modèle universel ou une preuve que les abonnements sont interchangeables.[20]
- **OMP natif :** rôles `default`, `smol`, `slow`, `plan`, `task` et sélection par modèle/fournisseur ; comparer à cette fonctionnalité avant de reconstruire une politique statique.[15]

## Interfaces par hôte

### Claude Code

`--model`, `/model`, configuration ou `ANTHROPIC_MODEL` sélectionnent le modèle ; `--effort`, `/effort` et `CLAUDE_CODE_EFFORT_LEVEL` contrôlent l'effort selon compatibilité du modèle.[9] `ANTHROPIC_BASE_URL` redirige une passerelle ; son authentification et les facturations dépendent de la configuration, et une clé de passerelle n'est pas automatiquement financée par l'abonnement. Anthropic ne prend pas en charge le routage Claude Code vers des modèles non-Claude par passerelle.[8] Les sous-agents ont un contexte séparé, des choix de modèle/effort et des possibilités de reprise ; exception et sémantique exactes dépendent du mécanisme de fork. `--continue` ou `--resume` reprend une session mais ne prouve pas la continuité après changement de fournisseur.[10][25] Le tutoriel amont cite des en-têtes d'identité de session/prompt/classes dès Claude Code v2.1.273 si activés ; ils peuvent aider une passerelle mais leur présence reste à vérifier sur la version réellement installée.[6]

### Codex

`--model`, `model_provider`, `[model_providers.<id>]` et `model_reasoning_effort` sont documentés ; une passerelle compatible Responses est nécessaire pour le chemin concerné, et un endpoint Chat Completions seul ne prouve pas la compatibilité.[11][21] ChatGPT/Codex par abonnement et clé API sont des modes distincts ; un fournisseur tiers n'est pas automatiquement inclus dans l'abonnement.[12] Les sous-agents héritent par défaut modèle et effort, peuvent être configurés autrement, mais héritent du fournisseur et des permissions : router différents backends dans une session exige donc une passerelle compatible ou une autre intégration hôte.[13] Le contexte initial varie selon version et surface multi-agent : le code V2 expose `fork_turns` avec `all` par défaut et `none` pour un contexte neuf ; ne pas attribuer ce comportement indistinctement à toutes les versions.[24] `codex resume` reprend une session, pas une garantie de migration inter-fournisseurs.[26]

### oh-my-pi

L'hôte expose `provider/model-id`, les rôles et `~/.omp/agent/models.yml` ; l'exemple documenté `auth: none` permet de sélectionner un endpoint local sans clé.[14][15] La configuration peut définir l'effort et les contraintes par modèle ; le comportement de propagation a évolué, notamment dans v18.5.0 : tester la version installée.[15][22] Les agents démarrent sans historique parent implicite ; transmettre explicitement contexte et contraintes. Le hook hôte `before_subagent_spawn` peut agir sur le routage avant création ; l'effort par sous-agent est optionnel et son exposition est désactivée par défaut (`task.enableEffort=false`).[16] Le mécanisme de suivi/réactivation des agents conservés n'équivaut pas à une garantie de continuité universelle entre fournisseurs.[16] Compaction et handoff suivent les règles de l'hôte.[27] OMP documente aussi différents mécanismes OAuth/abonnement par fournisseur ; leur existence ne confère aucun droit de réutilisation via notre propre proxy.[14]

### Hermes

Hermes distingue les fournisseurs API et abonnements/OAuth ; les paramètres `delegation.provider`, `delegation.model` et `delegation.base_url` déterminent la cible des enfants, et un contexte doit leur être transmis explicitement.[17][18][23] Le proxy d'abonnement documente les adaptateurs `nous` et `xai` ; il expose l'inférence et ne prouve ni support générique de tous les abonnements ni orchestration d'outils par le proxy.[19] La reprise d'une conversation ou d'un résultat terminé ne signifie pas qu'un sous-agent en cours survit à un redémarrage : son état peut devenir inconnu.[18] L'effort et son champ doivent être traduits au format effectivement accepté par le backend, pas seulement indiqués dans l'interface.[17]

## Frontière d'architecture et critères d'essai

Un modèle virtuel / proxy peut sélectionner une cible, appliquer une politique d'effort acceptée par le backend, préserver une affinité de route et traduire le protocole **dans la mesure où les champs et l'identité de session sont visibles**. Il ne peut pas garantir, à lui seul, que l'hôte créera un sous-agent, transmettra le contexte pertinent, reprendra un processus ou autorisera la délégation : cela exige une interface ou un adaptateur hôte. Le routage caché ne doit pas modifier silencieusement les permissions. Changer de modèle peut invalider des blocs de raisonnement et des caches ; le tutoriel Claude parle de reprise après rejet et d'une politique d'escalade, pas d'une continuité gratuite.[6]

Pour valider la première tranche : 1) sélectionner le modèle virtuel local dans OMP ; 2) traiter un prompt synthétique par s1d1 local et une vraie génération locale ; 3) observer modèle, effort, latence et usage disponible ; 4) vérifier un aller-retour d'outil, streaming, erreurs et deux tours de session ; 5) enregistrer les limites, sans transfert de secrets. Les champs d'effort, d'usage et le protocole de chaque modèle doivent être vérifiés par exécution : aucun résultat de benchmark réel ni d'intégration hôte n'est revendiqué ici.

## Préservation

Dépôt canonique repéré : `/home/operator/repos/open-model-router`, avec des fichiers de travail non suivis. La consigne de coordination limite les écritures de cette recherche à ce fichier distinct dans le scratch partagé ; l'intégration durable au dépôt doit être faite par l'implémenteur/superviseur, sans écraser ces fichiers. Board associé : `open-model-router`, carte `t_df757c6a`.

## Sources

[1] https://huggingface.co/api/collections/scombat/s1d1-router
[2] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/README.md
[3] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/s1d1_router.py
[4] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/NOTICE
[5] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/tutorials/02-litellm.md
[6] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/tutorials/03-claude-code.md
[7] https://huggingface.co/scombat/s1d1-router/resolve/7fb9a4e3d03e3d942a98648268ff76c6152c18d6/tutorials/04-codex.md
[8] https://code.claude.com/docs/en/llm-gateway
[9] https://code.claude.com/docs/en/model-config
[10] https://code.claude.com/docs/en/sub-agents
[11] https://developers.openai.com/codex/config-advanced
[12] https://developers.openai.com/codex/auth
[13] https://developers.openai.com/codex/multi-agent
[14] https://github.com/can1357/oh-my-pi/blob/main/docs/providers.md
[15] https://github.com/can1357/oh-my-pi/blob/main/docs/models.md
[16] https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md
[17] https://hermes-agent.nousresearch.com/docs/user-guide/configuration
[18] https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation
[19] https://hermes-agent.nousresearch.com/docs/user-guide/features/subscription-proxy
[20] https://hermes-agent.nousresearch.com/docs/plugins/orquehelx
[21] https://learn.chatgpt.com/docs/enterprise/gateway-compatibility
[22] https://github.com/can1357/oh-my-pi/releases/tag/v18.5.0
[23] https://hermes-agent.nousresearch.com/docs/integrations/providers
[24] https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/handlers/multi_agents_spec.rs
[25] https://code.claude.com/docs/en/tutorials
[26] https://learn.chatgpt.com/docs/cli/reference
[27] https://github.com/can1357/oh-my-pi/blob/main/docs/compaction.md
