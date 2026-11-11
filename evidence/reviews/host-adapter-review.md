# Revue indépendante — adaptateurs hôtes

**Verdict : GO code sur les trois fichiers ci-dessous, sans blocker concret identifié.** Ce verdict ne qualifie ni macOS, ni un fournisseur distant, ni l'ensemble du produit.

## Identité et périmètre

Worktree : `/srv/omr-private/workspaces/open-model-router/host-adapters`. Fichiers lus intégralement, empreintes identiques aux valeurs demandées avant et après les tests et en fin de revue :

- `host-adapters/launch.py` : `5a4b26958337bda4465c673f2d93eaa1273dfb76ec3ce246559219223f3ffcd2`
- `host-adapters/test_launch.py` : `59ca81aa3af3c621123906bf65e1b1f60dd418c6142f6d0f87f8c6bc8d4fe251`
- `host-adapters/README.md` : `b8cb88b901d712a11abc371f0c22eea046c999cef0ad23ad519298ac0dbfea85`

Aucune modification source ou Git, aucun appel fournisseur. Le seul fichier produit est ce rapport, hors worktree.

## Vérification

- Exécution fraîche sur Linux : `env -i PATH="$PATH" HOME="$TMPDIR" TMPDIR="$TMPDIR" PYTHONDONTWRITEBYTECODE=1 python3 -B host-adapters/test_launch.py -v` depuis le worktree. **8 tests réussis en 8,381 s**, exit 0 ; processus et sockets loopback réels, hôtes simulés. Ce n'est pas une qualification native macOS.
- UUID normalisé, port déterministe, override stable ; collision au bind échoue sans réaffectation silencieuse. Le proxy remplace `X-OMR-Session` et supprime `Authorization` et `X-Api-Key`. Loopback n'est pas une frontière d'authentification ; autres en-têtes transmis comme documenté.
- Fermeture amont vérifiée avant réception des en-têtes lors de la déconnexion ; deadline amont de 120 s avant en-têtes. SIGTERM et timeout testés sur groupe de processus, y compris enfant ignorant TERM, escalade et reprise ; SIGINT et sortie 130 observés dans la preuve VM. Le budget est global, optionnel, et retourne 124 ; pas de plafond de dépense.
- Registre OMP temporaire isolé avec nettoyage ; limites de contexte et sortie validées, configurées par opérateur, non détectées et ne modifiant pas les capacités du backend. Les répertoires temporaires ne constituent pas une isolation générale des configurations de tous les hôtes.

## Preuve VM existante et limites

`evidence/native/final-vm/REPORT.md`, `source.sha256` et `observed/receipts.jsonl` concordent avec les empreintes et décrivent les traces Hermes/Claude multi-tours, outils, streaming, annulation de connexion et reprise. Les reçus montrent deux annulations amont 200 suivies de requêtes complétées. Le rapport documente aussi les snapshots de sockets et groupes de processus ; aucune inférence d'arrêt effectif du calcul GPU. Il s'agit de preuves rapportées antérieures, non d'un nouveau replay fournisseur.

Sur panne amont Hermes, la preuve rapporte expiration du budget et code 124, **sans APIError ni 502 natif visible** ; le 502 du proxy est couvert séparément par test synthétique. Claude a montré un retry 502. Aucune qualification Mac n'est réclamée pour ce GO code.
