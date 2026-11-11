# Test de génération Desktop

## Contrat

Le clic consenti `test_generation` utilise une seule requête synthétique via la
vraie gateway authentifiée, sans décideur, retry ni substitution. Responses est
préféré lorsqu'il est déclaré ; sinon Chat Completions. Le modèle amont doit
correspondre exactement à l'identité configurée. L'effort configuré est conservé ;
le test ne désactive pas le raisonnement.

Le plafond de sortie est **1024 tokens**, raisonnement compris selon le fournisseur,
contre 16 auparavant. C'est un budget borné de vérification, pas une garantie que
tout modèle à raisonnement terminera. Délai total : **20 secondes**, réponse limitée
à 1 000 000 octets ; fermeture/annulation continue d'utiliser la gateway existante.
Aucune relance automatique, y compris après épuisement du budget.

Une réussite exige du texte assistant non blanc et un état terminal complet
(`stop` en Chat, `completed` en Responses). Un appel d'outil seul ne répond pas à
ce test sans outils déclarés. Une sortie partielle, un refus explicite, une sortie
vide, un JSON invalide ou une identité non confirmée ne vérifient jamais le modèle.
Un HTTP200 et un reçu de transport `completed` ne prouvent pas cette réussite.
Pour Responses, des détails d'incomplétude non nuls ou un statut d'item explicite
non complet invalident aussi la réponse, même si son statut global est `completed`.

## Diagnostic pour les appelants

L'erreur IPC reste un code sûr. Après succès ou échec, lire `snapshot.model_states`
à l'UUID du modèle : `generation` (`verified`/`failed`), `verified_at` (date du
dernier test, non preuve de succès) et `generation_diagnostic`.

Ce diagnostic contient uniquement `code`, `protocol`, `max_output_tokens`,
`gateway_http_status` (entier ou null), `identity_match` (booléen ou null), les
terminaisons reconnues `finish_reason`/`response_status`/`incomplete_reason` et
les compteurs `input_tokens`, `output_tokens`, `reasoning_tokens` lorsqu'ils sont
entiers bornés. Aucun prompt, clé, texte de réponse, refus, erreur fournisseur
arbitraire ou identité inattendue n'est exporté. Les reçus de transport existants
conservent leur sens et leurs usages, sans double comptage.

Codes : `generation_verified`, `generation_budget_exhausted`,
`generation_incomplete`, `generation_refused`, `generation_empty`,
`generation_identity_mismatch`, `generation_upstream_rejected` (HTTP4xx),
`generation_timeout`, `generation_cancelled`, `generation_unavailable`
(erreur transport/HTTP5xx), `generation_failed` (réponse invalide).
Budget épuisé exige `length` ou `incomplete_details.reason=max_output_tokens` ;
le seul compteur de sortie égal au plafond ne suffit pas. Un refus fournisseur
explicite est distinct du refus HTTP ; aucune cause de facturation n'est inférée.

## Observation Mac du 4 novembre 2026

Métadonnées transmises par la coordination : trois reçus NVIDIA
`nvidia/nemotron-3.5-super-vl:free`, `completed`/HTTP200, identité exacte,
20 tokens entrants et 16 sortants, sur Chat/Responses ; UI `generation_failed`.
Le HTTP402 appartient à `prism-ml/ternary-bonsai-2-9b`, pas à NVIDIA.
Aucun corps amont n'a été conservé. Raisonnement seul/troncature est donc une
hypothèse, pas une cause Mac établie. Les fixtures hors réseau reproduisent
ce mécanisme possible et les faux succès voisins ; elles ne qualifient ni le
fournisseur réel ni le paquet Mac. Aucun appel fournisseur ou coffre personnel
n'est nécessaire à la correction source.

## Vérification du candidat Linux (4 novembre 2026)

Base : `8cf9a7f02a9c8bb77cc7cd6c505ab8f6b7a94795`. Quatre chemins seulement :
ce contrat, `desktop_engine.py`, `test_desktop_generation.py` et une terminaison
`finish_reason=stop` ajoutée à la fixture synthétique de `test_desktop.py`.
Aucun fichier supprimé ; l'ancien validateur permissif est remplacé. Aucun
changement dans `desktop/src`, Rust, la gateway générale ou les reçus de transport.

- RED : budget16 reproduisant une sortie vide via gateway Chat/Responses ;
  échecs de classification des sorties blanches, incomplètes et refusées.
  RED additionnel : corps HTTP progressif dépassant le délai total (0,845s pour
  une borne de test 0,1s), corrigé par conservation du socket avant `getresponse()`.
- GREEN final : 10 tests de régression, dont JSONL du sidecar réel, canaris,
  arrêt/timeout/corps progressif, modèle/effort exacts, aucun retry. Suite canonique
  sous Bubblewrap sans réseau externe : racine 290 cas (3 skips empaquetés),
  suites 16/6/5/9/6 cas (1 skip inférence CPU réelle), puis 9 adaptateurs.
  Total : 341 cas, 337 réussites et 4 skips, aucun échec de suite.
  Les sorties `FAILED` imbriquées proviennent des fixtures du test du lanceur CI,
  qui vérifie intentionnellement les échecs d'autres sous-processus.
- Landing : 8 liens fragment, 6 IDs, disclosures français/prototype vérifiés.
  Runtime pi-ai : installation verrouillée hors réseau, `npm run check` et
  `npm run build` réussis. Ruff 0.17.3 : erreurs fatales/variables non définies
  absentes sur les trois fichiers Python, format des deux fichiers moteur/nouveau
  test et `git diff --check` réussis. Format préexistant de la fixture conservé.
- Pyright 1.1.414 : 16 erreurs **préexistantes**, mêmes règles/messages que la base,
  zéro nouvelle erreur et aucune erreur dans le nouveau test. Pas de gate Python
  type strict existant. Avertissements : lien dur uv remplacé par copie ;
  postinstall bun déjà présent non approuvé par npm (binaire compilateur fonctionne) ;
  doublon ZIP volontaire du test négatif de provenance NumPy.

Aucun fournisseur, coffre personnel, interface Mac ou paquet gelé nouveau testé.
Frontend inchangé : aucun build UI/Rust/DMG effectué ici. La qualification native
et le fournisseur réel appartiennent à la composition `t_0fcc8c66`, après revue
indépendante du candidat exact. Le budget1024 peut encore être insuffisant pour
certains modèles ; le diagnostic le distingue sans prétendre le contraire.
