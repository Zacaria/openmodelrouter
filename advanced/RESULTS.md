# Résultats et reproduction

## Résultat livré

Trois adapters natifs exécutés dans `advanced/` : Codex compaction/délégation/changement/interrupt ; OMP compaction/changement via RPC ; Claude Code compaction/délégation via stream-json. Pas de raccord au socle ni activation. Hermes et délégation OMP restent non vérifiés ; voir la matrice pour les limites client par client.

Le dernier replay emploie **de vrais fournisseurs sur les souscriptions natives existantes**, pas un backend de génération factice. Les outils de qualification ne donnent accès qu'au projet synthétique ou à une donnée constante. Les fixtures unitaires sont distinctes : elles valident les contrats, erreurs et corrélations, jamais les modèles.

## Comparaison Codex : dernier replay natif

Source : `codex-native-6/results.json`, `events.jsonl`, `native-contexts.json` et `comparison-native-6.json` dans les preuves attachées. Même seed, outil read_fixture et question finale ; thread frais par bras. Quatre jeux complets conservés (runs 3 à 6), plus les échecs des sondes initiales.

| Bras | Durée des actions, seed inclus | Compteurs observés | Fixture, HEAVY, préfixe RAPPORT: |
|---|---:|---|---|
| Maintien gpt-6-luna | 4,592 s | 19 969 tokens cumulés du thread | PASS |
| Changement vers gpt-6.1-sol | 4,414 s | 20 270 tokens cumulés du thread | PASS |
| Compaction puis changement | 6,288 s | snapshot final 20 171 ; **pas** le coût total | PASS |
| Délégation ciblée | 7,484 s | parent 41 071 + enfant 6 588 = 47 659 observés | PASS |

Aucune conclusion d'économie : l'API de compaction distante ne fournit pas son usage auxiliaire complet. Un compteur d'après-compaction peut décrire le contexte restant, non le travail consommé. Prix et facture ne sont pas déduits des tokens. Les tokens cache/raisonnement sont conservés dans le JSON, sans addition de snapshots. Le temps enfant est inclus dans le tour parent, pas ajouté une seconde fois.

Les modèles sont confirmés par le contexte natif du tour, les permissions restent never/read-only et l'effort low. Le run 6 vérifie l'annulation **via l'adapter actif**, non un contrôle RPC qui le contourne : `turn()` synchrone sur un thread, `cancel()` concurrent sur le même transport, ack reçu et tour terminé en échec explicite `interrupted`, puis modèle inexistant refusé sans fallback et RECOVERY_OK. Les régressions sous-processus couvrent les deux ordres ack/terminal, les réponses hors ordre et EOF pour plusieurs attentes. Cela ne mesure pas l'arrêt du calcul fournisseur.

## OMP et Claude

- **OMP, `omp-native-rpc-6.json` :** seed puis maintien, switch, compaction native et switch retour dans une même session synthétique. Les trois réponses de rappel conservent fixture, HEAVY et RAPPORT:. Les générations ont leurs propres usages natifs ; les statistiques de session repartent après compaction et ne doivent pas servir de facture globale. La compaction ne fournit pas son usage auxiliaire. Aucun gain de taille/coût ni conservation de paires outils OMP n'est revendiqué.
- **Claude, `claude-native-6/results.json` :** frontière manuelle réelle, contexte annoncé 1 486 → 857 tokens, rappel correct ; Agent réel terminé à profondeur 1 avec outil/résultat corrélés. Le préfixe strict n'est toujours pas respecté dans le résultat délégué : **échec sémantique enregistré**, comme au run 5. Le type d'enfant ne valide pas le profil worker demandé ni son modèle. Le run 3 sans sous-agent reste un échec conservé.

### Correction des coûts Claude après revue

`total_cost_usd` et `modelUsage` sont des **snapshots cumulatifs de la session reprise**, pas des coûts indépendants. `usage` décrit le résultat local et peut omettre du travail auxiliaire. Le run 5 est recalculé dans `comparison-revision.json` : seed 0,003768 ; compaction 0,009675 ; rappel 0,002332 ; délégation 0,020426 USD équivalents, soit 0,036201 au total. La compaction consomme ainsi 2 560 tokens entrée et 1 423 sortie observables malgré `usage=0`. Les anciens `comparison.json` et `comparison-final.json` du premier candidat sont **supplantés** pour la comptabilité Claude ; ne pas additionner leurs coûts de cas.

Le nouveau run natif 6, avec l'adapter corrigé, conserve les snapshots et leurs deltas dans `accounting` :

| Action | Entrée hors cache | Sortie (raisonnement inclus) | Équivalent natif incrémental USD |
|---|---:|---:|---:|
| Seed | 448 | 751 | 0,004203 |
| Compaction | 2 647 | 1 663 | 0,010962 |
| Rappel | 1 226 | 197 | 0,002211 |
| Délégation et intégration | 3 979 | 1 134 | 0,0214697 |

La délégation comprend aussi 4 787 tokens lus du cache et 5 671 créés. Le snapshot final est 0,0388457 USD équivalent (`costBasis=list`), égal à la somme des deltas à l'arrondi flottant natif près. Le coût enfant n'est pas ajouté une deuxième fois. La facture réelle de souscription reste inconnue ; aucun montant débité ni économie n'est déduit de ces équivalents. Les coûts auxiliaires Codex/OMP restent inconnus.

Ce sont des essais de qualification d'interface et de petit contexte, pas le benchmark général de GOAL.md. Ordre fixe, caches non neutralisés, comptes/quotas partagés ; les replays Codex/Claude 6 ont tourné en parallèle, OMP reste le replay 6/7 antérieur. Les temps ne prouvent pas la supériorité d'une politique. Une native compaction réussie ne garantit pas une réduction ni un respect parfait des instructions par le modèle.

## Reproduction explicite

Hôtes, binaire et compte natif doivent déjà être qualifiés ; ces commandes ne doivent pas être lancées sur une conversation existante. Aucun API key n'est accepté, aucun login n'est automatisé. Un refus natif d'accès/quotas doit arrêter l'essai, pas activer un autre fournisseur.

```sh
python3 -B -m unittest discover -s advanced/tests -v
uv tool run --from ruff==0.17.3 ruff check advanced
uv tool run --from ruff==0.17.3 ruff format --check advanced

python3 -B -m advanced.probe_codex \
  --output advanced/evidence/codex-native-6 \
  --native-binary /home/operator/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex \
  --run-provider --model gpt-6-luna --switch-model gpt-6.1-sol --controls
python3 -B -m advanced.probe_omp --output advanced/evidence/omp-native-rpc-6.json
python3 -B -m advanced.probe_claude --output advanced/evidence/claude-native-6
python3 -B -m advanced.analyze --claude-session-start \
  --codex-run codex-native-6/results.json --claude-run claude-native-6/results.json \
  --output advanced/evidence/comparison-native-6.json
```

Choisir des noms de sortie frais pour rejouer sans écraser les preuves ; l'analyse accepte `--codex-run`, `--omp-run`, `--claude-run`. Linux exige bubblewrap ; les deux CLI lisent uniquement leur fichier d'auth natif bindé en lecture seule à son chemin habituel dans un HOME synthétique. Aucune copie de token ni export de conversations. Les sources ne démontrent pas une isolation réseau du fournisseur (le réseau natif est requis). Mac utilise SSH déjà autorisé et le store natif d'OMP, avec règles/contexte/extensions/outils désactivés. Une rotation native de credentials n'est pas instrumentée ; aucune absence de mutation du store n'est revendiquée.

`comparison-revision.json` recalcule le run 5 avec les mêmes snapshots natifs sans rappel fournisseur. `--claude-session-start` atteste seulement l'UUID frais créé par la sonde ; l'omettre pour analyser une session reprise sans origine connue. Le candidat initial `7dea71e` reste conservé mais n'a pas reçu de PASS : cette correction le remplace pour intégration. Les empreintes `revision-native-source-before.json` relient les modules/lanceurs corrigés aux replays 6.

## Confidentialité des preuves : correction hors ligne

La revue a trouvé une adresse de compte dans les textes natifs Claude, malgré des prompts synthétiques. Le filtre d'initialisation n'était pas suffisant : `probe_claude` expurge désormais les adresses de type email dans l'ensemble du document **avant sa première écriture**, y compris assistant/result, résultats d'outils, stderr et copies dans les validations. La régression exerce cette frontière avec un processus natif remplacé par des sorties synthétiques, sur réussite et échec ; elle ne constitue pas un nouvel essai fournisseur.

Les captures historiques sont retraitées hors ligne. Les compteurs, événements et corrélations sont conservés ; seules les chaînes détectées changent. Le registre de provenance joint donne les empreintes avant/après et les fichiers modifiés, sans reproduire l'adresse. Les replays natifs restent ceux des candidats antérieurs : le nouveau filtre n'a pas été exercé par un nouvel appel fournisseur. Les preuves expurgées ne transfèrent aucune approbation au nouveau source.

**Non consommables :** anciennes pièces `78`, `87`, `94`, `95`, anciens paquets de preuves et anciens index des candidats `7dea71e` et `9346bf6`. Les archives source historiques restent des sources, pas des preuves acceptées. Les remplacements portent un nouvel index et un nouveau manifeste. Les outils natifs disponibles permettent d'attacher/lister mais pas de retirer une pièce jointe ; aucun effacement des anciennes pièces du board n'est revendiqué. Le nouveau paquet exclut tous ces anciens conteneurs. Voir `EVIDENCE-PRIVACY.md` pour la règle de consommation.

Le filtre vise les adresses usuelles non obfusquées, pas toutes les données personnelles ou secrets ; un contrôle des pièces reste nécessaire. Aucun accès à un historique privé, nouvel appel fournisseur, achat, activation ou release n'est effectué pour cette correction.

## Raccordement et livraison

Le consommateur doit fournir connexion exclusive au repos, permissions, catalogue et preuve d'autorisation du client, plus sa propre annulation/fermeture. Pas de conversion d'une requête HTTP non fiable en commande native. Conserver les erreurs, coûts inconnus et verdicts sémantiques ; ne pas exposer une capacité non vérifiée comme disponible. Le contrat n'inclut pas un client Hermes de façade, ni une délégation OMP hypothétique.

Les preuves natives et traces synthétiques ne sont pas committées ; elles sont attachées séparément, avec empreintes par membre. Le candidat ne modifie aucun fichier préexistant : `omr.py`, `desktop/`, workflows et core restent intacts. Seul le petit helper de première sonde OMP print-only a été retiré du nouveau code après son remplacement par le parcours RPC réel. Aucun fichier utilisateur, base ou historique n'a été supprimé.
