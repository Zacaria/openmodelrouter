# Revue bornée — corrections gateway

**Verdict : NO GO code / commit** pour le tree indexé `02aee64cd2fde79a6de705c65a22a6e8cbe944b3`, base `8a02c1e622e878546da0a1126b5ad30bda8e2120`. Ce verdict ne porte pas sur l'atteinte finale de `GOAL.md`.

## Blocker concret : fin SSE non cadrée acceptée

`omr.py:405-420,425-427` interprète chaque ligne `data:` indépendamment du cadrage SSE : une ligne terminale est acceptée sans la ligne vide qui doit terminer et distribuer l'événement. Reproduction TCP loopback : réponse chat `Content-Type: text/event-stream`, `Content-Length: 13`, corps exact `b'data: [DONE]\n'`, puis fermeture. Le client reçoit HTTP 200 et ce corps sans événement SSE complet ; le reçu indique pourtant `status: completed`, sans erreur. Un consommateur SSE conforme ne reçoit pas le terminal. Exiger un événement complet et correctement délimité avant de marquer la fin, tout en conservant la vérification du cadrage HTTP. Cela reste dans le deuxième blocker de la revue précédente.

## Vérifications ciblées

- Les reçus filtrent les champs numériques connus, sous-champs inclus ; le modèle observé doit correspondre au modèle configuré et l'effort est énuméré. Le test de régression avec marqueurs privés passe. L'EOF avec `Content-Length` tronqué et sans terminal produit `upstream_error` et un événement erreur dans le cas testé.
- Deadline absolue : le test d'ingestion du corps au compte-gouttes et celui des headers amont passent. Probe distinct sur headers entrants au compte-gouttes : connexion fermée en 0,241 s pour une limite de 0,2 s. Les limites de scheduling restent celles de l'environnement local.
- Installateur : révision et six empreintes fixées, contrôle SHA-256 avant lien atomique sans remplacement, refus des fichiers existants différents et des symlinks finaux ; nettoyage du téléchargement temporaire en cas d'échec. Deux tests synthétiques passent. Pas de téléchargement réel ni d'installation de dépendances pendant cette revue. Le chargement réel préalable de poids s1d1 est une information transmise, non reproduite ici ; aucune inférence GPU ni fournisseur réel n'a été exercé.
- `GOAL.md` et `gateway-review.md` lus. La revue est limitée aux blockers nommés et au nouveau périmètre installateur ; elle ne certifie ni intégrations hôtes ni produit final.

## Commandes et preuve

Export isolé du tree indexé et exécution hors ligne, avec environnement minimal, uniquement des fournisseurs TCP synthétiques loopback et des téléchargements mockés :

```sh
D=$(mktemp -d "$TMPDIR/omr-review-XXXXXX")
git archive 02aee64cd2fde79a6de705c65a22a6e8cbe944b3 | tar -x -C "$D"
cd "$D"
env -i HOME="$D" TMPDIR="$D" PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest -v test_review_regressions test_deadlines test_transport test_omr test_download
```

Résultat frais : **10 tests OK**, dont 2 regressions et 8 autres. Le RED avant correctif est rapporté par le demandeur mais son journal n'a pas été vérifié dans cette revue ; seul le GREEN est observé ici. Pas d'isolation réseau au niveau du noyau revendiquée.

Reproduction du blocker dans le même export :

```sh
env -i HOME="$PWD" TMPDIR="$PWD" PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -c 'import http.client,json,tempfile,time; from pathlib import Path; from http.server import BaseHTTPRequestHandler; from test_transport import serve; import omr
class B(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_POST(self):
  self.rfile.read(int(self.headers["Content-Length"])); p=b"data: [DONE]\n"; self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.send_header("Content-Length",str(len(p))); self.end_headers(); self.wfile.write(p)
with tempfile.TemporaryDirectory() as d, serve(B) as up:
 p=Path(d,"r"); cfg={"routes":{"x":{"url":f"http://127.0.0.1:{up}/v1","model":"m","protocol":"chat"}},"default_route":"x","receipts":str(p)}
 with serve(omr.handler(cfg)) as port:
  c=http.client.HTTPConnection("127.0.0.1",port,timeout=2); c.request("POST","/v1/chat/completions",json.dumps({"model":"open-model-router","stream":True}),{"Content-Type":"application/json"}); r=c.getresponse(); body=r.read(); c.close()
  for _ in range(100):
   if p.exists() and p.stat().st_size: break
   time.sleep(.01)
  print("http",r.status,"body",repr(body),"receipt_status",json.loads(p.read_text())["status"])'
```

Sortie : `http 200 body b'data: [DONE]\n' receipt_status completed`.

Contrôle final : `git ls-files --stage` comparé à `git ls-tree -r` du tree ci-dessus : identiques ; `git diff --quiet` : fichiers suivis du worktree identiques à l'index. `HEAD` demeure `8a02c1e622e878546da0a1126b5ad30bda8e2120`. Les répertoires `__pycache__` non suivis existaient au départ et n'ont pas été modifiés intentionnellement. Aucun fichier source modifié ni commit créé. Note de procédure : `git write-tree` a été exécuté au début pour identifier l'index ; il peut matérialiser des objets Git, bien qu'il ne change ni source ni index.
