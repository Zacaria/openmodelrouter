# Fermeture bornée — Codex natif

## Verdict : GO technique pour le parent

Le parent est autorisé à intégrer et committer cet arbre, puis à tenter sur Mac un parcours synthétique avec authentification native. Ce GO porte uniquement sur la fermeture des défauts examinés ; il ne certifie ni l'intégration Mac, ni l'utilisation réelle, ni les droits du compte. Aucun commit, ajout à l'index, modification de source ou de référence n'a été effectué par cette revue.

## Vérifications ciblées

- **HTTP et SSE** : les réponses HTTP amont non 2xx sont remplacées par une erreur constante ; les 4xx/5xx gardent leur statut, les redirections deviennent 502 sans `Location`. Les événements SSE d'erreur reconnus sont remplacés avant émission. Les tests injectent des marqueurs synthétiques bearer, compte et clé et vérifient leur absence des réponses, reçus et logs. Cela ne constitue pas une garantie de filtrage de contenus arbitraires d'événements non identifiés comme erreurs.
- **Sessions natives** : POST exige un UUID `session_id` ou `X-OMR-Session`, refuse absence, valeur invalide, conflit et doublons ; la clé de routage est le couple identité bearer/compte et UUID. Le test couvre continuité sur plusieurs tours et isolation de deux comptes partageant l'UUID. Le client Mac devra encore démontrer qu'il fournit un identifiant stable et distinct par session.
- **Connection** : une requête désignant `Authorization` ou `chatgpt-account-id` dans `Connection` est refusée localement avant transport ; les tests couvrent GET et POST pour Authorization, GET pour compte, et l'implémentation applique le même contrôle partagé aux deux méthodes.

## Empreintes et exécution

- Base : `bcae37dc960bc2abaa8647aaa02a0dd0da6d72ad` ; arbre d'index avant et après : `1bbe4f988fa40b39eb298b6ef610b68239862524` ; aucune différence non indexée suivie. SHA-256 du statut porcelain complet avant et après : `fbfa67a0dfc1b60d47e116636a48b42c7ba2ec1ece1a2e9fc75624d3d8f762db`.
- SHA-256 des blobs d'index : `omr.py` `29b89bd3d651273dd23947e2b015da8b4474ba743e3060428f6a9ac680f3b921` ; `test_codex_native.py` `34197d9bb3b420665adf6f9fc5de7c141d9a17c0510c328def5e42a48ce63411` ; `GATEWAY-SPEC.md` `6adc947a855ebe261dbac3886067ed52d20ebeba8719e7b7e41a36095e18bd54` ; `test_transport.py` `dbef5a231dd9e859e895c9c466a508dc9311c2292e5f96a944f4a3187bc4f21d` ; `GOAL.md` `b48a4d1cd41bc479b7c3854e2b2f72f79a49258dcd97b678037a97a6f8c7d83b`. SHA-256 de la revue initiale : `c7fd5c217bdc443a582e72f0e3e554ceab781f10e8fe9edbc1d6e37df743aef1`.
- Blobs exportés hors source ; environnement vidé ; `unshare -Urn` avec loopback seul ; `python3 -m unittest -v test_codex_native test_transport` : **10 tests OK**, 5,613 s. HTTPS substitué par un transport HTTP loopback synthétique : ni TLS réel ni fournisseur, credential réel ou client Mac testé.
