#!/usr/bin/env python3
"""Analyse locale des reçus figés ; aucune exécution du benchmark ni réseau."""
import argparse, collections, hashlib, json, os, statistics, sys
from pathlib import Path
from xml.sax.saxutils import escape

if sys.flags.optimize:
    raise SystemExit('Verification requires assertions; do not use Python -O or -OO.')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='new output directory; never overwrite a report')
args = parser.parse_args()
SRC = args.source.resolve(strict=True)
OUT = args.output.resolve()
if OUT.exists():
    raise SystemExit('Output directory already exists; choose a new directory.')
ARMS = ('default', 's1d1', 'configurable')
FAMILIES = ('simple', 'code', 'diagnostic', 'conversation', 'agents')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def lines(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def stats(xs):
    if not xs: return 'inconnu (0)'
    return f'{sum(xs):.1f} / {statistics.mean(xs):.1f} / {statistics.pstdev(xs):.1f} / {min(xs):.1f}–{max(xs):.1f} (n={len(xs)})'
def mark(r): return r['evaluation'] or ('erreur:' + str(r['reason']))

# Vérification stricte de la grille et des champs d'ordre, pour les deux tentatives.
allrows = {}
for attempt, root in [('1', SRC), ('2', SRC/'attempt-2')]:
    for split, seed in [('dev', 27), ('validation', 28)]:
        p = load(root / f'{split}.jsonl.plan.json'); rows = lines(root / f'{split}.jsonl')
        assert p['split'] == split and p['seed'] == seed and p['planned_total'] == len(p['runs']) == len(rows) == 30
        assert p['cases_per_family'] == 1 and p['repetitions_planned'] == 2
        expected = {(f'{f}-{split}-01', f, a, r) for f in FAMILIES for a in ARMS for r in range(2)}
        key = lambda x: (x['case'], x['family'], x['arm'], x['repetition'])
        assert {key(x) for x in p['runs']} == expected and len({key(x) for x in rows}) == 30
        assert [tuple(x[k] for k in ('case','family','arm','repetition','order','global_order')) for x in p['runs']] == [tuple(x[k] for k in ('case','family','arm','repetition','order','global_order')) for x in rows]
        assert all(x['fixture_sha256'] == p['fixture_sha256'] and x['seed'] == seed for x in rows)
        allrows[attempt, split] = rows
for split in ('dev','validation'):
    assert sha(SRC/f'{split}.jsonl.plan.json') == sha(SRC/'attempt-2'/f'{split}.jsonl.plan.json')
m1, m2 = load(SRC/'frozen-manifest.json'), load(SRC/'attempt-2/frozen-manifest.json')
common = set(m1['files']) & set(m2['files'])
assert len(common) == 3 and all(m1['files'][x] == m2['files'][x] for x in common)
study_keys = [key for key in m1['files'] if Path(key).name == 'STUDY.md']
assert len(study_keys) == 1 and sha(SRC/'STUDY.md') == m1['files'][study_keys[0]]
c1=load(SRC/'configurable-config.json'); c2=load(SRC/'attempt-2/configurable-config.json')
assert '****' in c1['decision']['command'][0] and '****' not in c2['decision']['command'][0]
for arm in ARMS:
    x=load(SRC/f'{arm}-config.json'); y=load(SRC/'attempt-2'/f'{arm}-config.json')
    x.pop('receipts'); y.pop('receipts')
    if arm == 'configurable': x['decision']['command'][0]=y['decision']['command'][0]
    assert x == y
rows = allrows['2','dev'] + allrows['2','validation']
gate = {a: lines(SRC/'attempt-2'/f'{a}-gateway.jsonl') for a in ARMS}
assert all(len({r['session'] for r in rows if r['arm']==a}) == 20 for a in ARMS)
assert all(len(gate[a]) == sum(r['calls'] for r in rows if r['arm']==a) for a in ARMS)
assert all(x['status']=='completed' for v in gate.values() for x in v)
first = allrows['1','dev'] + allrows['1','validation']
assert sum(r['arm']=='configurable' and r['reason']=='HTTPError' for r in first)==20
assert collections.Counter(x['status'] for x in lines(SRC/'configurable-gateway.jsonl')) == {'invalid_request':20}
dec=[x['decision_usage'] for x in gate['configurable'] if x.get('decision_usage') is not None]
assert len(dec)==22 and sum(x['input_tokens'] for x in dec)==8626 and sum(x['output_tokens'] for x in dec)==726
assert all(len(r['code_test_results'])==4 and all(x['pass'] for x in r['code_test_results']) for r in rows if r['family']=='code')

report=['# Open Model Router — analyse de la campagne figée', '', 'Analyse hors Git, sans appel fournisseur ni réexécution du benchmark. Sources locales : `evidence/campaign/STUDY.md`, plans, JSONL, reçus gateway et manifestes ; chemins complets et SHA-256 dans `MANIFEST.sha256`. Données synthétiques uniquement.', '', '## Périmètre et intégrité', '', '- Deux jeux × cinq familles × deux répétitions × trois bras = 60 parcours prévus et 60 reçus pour chaque tentative. Plans comparés ligne par ligne aux résultats (identité, ordre local et global), sans manque ni doublon ; graines dev 27, validation 28. Plans byte-identiques entre tentatives.', '- Les manifestes déclarent les mêmes SHA-256 pour les trois fichiers communs gateway, benchmark et adaptateur Jev ; le hash de STUDY correspond au premier manifeste. Ceci vérifie la concordance des déclarations, pas les octets des scripts externes, hors périmètre de lecture. Plans et empreintes fixture identiques ; les fixtures elles-mêmes ne sont pas incluses ici. Les configurations comparées diffèrent uniquement par le chemin de reçus et, pour configurable, le chemin interpréteur. Cela ne prouve pas indépendamment le contenu des scripts externes ou l’ensemble des prompts.', '- Tentative 1 : 20 erreurs HTTPError côté runner pour configurable et 20 reçus gateway invalid_request. Le chemin interpréteur du fichier de configuration contient littéralement quatre astérisques ; le second n’en contient pas. Le contexte de campagne attribue l’échec à FileNotFound et une résolution native dans le même processus à la correction ; les reçus publics ici ne contiennent ni traceback FileNotFound ni preuve autonome du mécanisme. Les sorties de l’outil peuvent masquer le chemin même lorsqu’il est correct. Aucun secret affiché.', '- Référence : alias local Hermes `omr-hermes-qwen3-4b:ctx8192`, effort transmis `none`, pas le modèle natif par défaut de ChatGPT. Route alternative `qwen3:4b`, effort backend non forcé. s1d1 est expérimental, seuil 0,35 ; configurable utilise Jev. Pas de comparaison avec un abonnement commercial.', '', '## Résultats de la tentative 2', '', '| Jeu | Famille | Bras | Pass | Fail | Erreur (raison) | Durée ms : somme / moyenne / écart-type population / min–max |', '|---|---|---|---:|---:|---|---|']
for split in ('dev','validation'):
 for fam in FAMILIES:
  for arm in ARMS:
   rr=[r for r in allrows['2',split] if r['family']==fam and r['arm']==arm]
   er=collections.Counter(r['reason'] for r in rr if r['state']=='error')
   report.append(f"| {split} | {fam} | {arm} | {sum(r['evaluation']=='pass' for r in rr)} | {sum(r['evaluation']=='fail' for r in rr)} | {dict(er)} | {stats([r['elapsed_ms'] for r in rr])} |")
report += ['', 'Fail signifie évaluation négative ; erreur signifie parcours non évalué, pas un fail converti. Les 12 diagnostics sont `fail` : la sortie brute contient une première hypothèse JSON, le résultat outil `dns`, puis une sortie intermédiaire vide et une réponse finale JSON `{"cause": "dns", "evidence": "dns"}`. Les reçus ne donnent pas de motif de parse précis (`reason` est null) : ne pas prétendre identifier le parseur fautif depuis ces seules preuves. En agents dev, default et configurable ont chacun deux `ValueError` avec sortie parent vide ; s1d1 a deux fail avec sortie vide. En validation, default et configurable réussissent les deux délégations ; s1d1 échoue deux fois.', '', 'Code : les 12 reçus exécutés rapportent chacun quatre tests AST comportementaux effectivement évalués, tous réussis (48 résultats). Ils ne constituent pas une sandbox générale. La délégation est orchestrée par le runner, pas une validation des sous-agents natifs des hôtes.', '', '## Usage observé par bras', '', 'Somme / moyenne / écart-type population / min–max ; `n` compte les valeurs connues sur 20 parcours. Les tokens cache peuvent être inclus dans input ; reasoning peut être inclus dans output. Ne pas additionner ces catégories comme des totaux indépendants.', '', '| Bras | Mesure | Statistiques |', '|---|---|---|']
for arm in ARMS:
 rr=[r for r in rows if r['arm']==arm]
 for field in ('input','output','cache_read','cache_write','reasoning','decision','tools','retry'):
  vals=[r['usage'][field] for r in rr if r['usage'].get(field) is not None]
  report.append(f'| {arm} | {field} | {stats(vals)} |')
 for field in ('elapsed_ms','decision_ms','retries'):
  report.append(f"| {arm} | {field} | {stats([r[field] for r in rr if r.get(field) is not None])} |")
report += ['', f"Reçus gateway : default {len(gate['default'])}, s1d1 {len(gate['s1d1'])}, configurable {len(gate['configurable'])} ; ces nombres sont des appels, pas des parcours. Les 22 reçus configurable avec `decision_usage` totalisent **8 626 input / 726 output** Jev. {len(gate['configurable'])-len(dec)} reçus n’ont pas de decision_usage : absence ne signifie pas zéro décision facturable. Ces tokens sont séparés de l’usage modèle local ci-dessus.", '', 'Tarifs locaux, énergie et facture Jev inconnus ; valeur équivalente et repricing non mesurés, et non nuls. Aucun gain économique revendiqué. Pas de réchauffement/reset forcé ; le cache et le matériel sont partagés et les répétitions ne sont pas indépendantes.', '', '## Paires par cas et répétition', '', 'Différence de durée = bras − référence en ms ; les trois résultats et les usages permettent de constater les désaccords, pas de conclure à un gain. Pour chaque paire, les valeurs de durée et tokens portent sur le parcours complet.', '', '| Cas | Rép. | Résultat default / s1d1 / configurable | Durée ms default / s1d1 / configurable | Δ s1d1 / configurable (ms) | Input default / s1d1 / configurable | Output default / s1d1 / configurable |', '|---|---:|---|---|---|---|---|']
for split in ('dev','validation'):
 for fam in FAMILIES:
  for rep in range(2):
   rr=[next(r for r in allrows['2',split] if r['family']==fam and r['repetition']==rep and r['arm']==a) for a in ARMS]
   durations = ' / '.join(format(r['elapsed_ms'], '.1f') for r in rr)
   report.append(f"| {rr[0]['case']} | {rep} | {' / '.join(mark(r) for r in rr)} | {durations} | {rr[1]['elapsed_ms']-rr[0]['elapsed_ms']:+.1f} / {rr[2]['elapsed_ms']-rr[0]['elapsed_ms']:+.1f} | {' / '.join(str(r['usage']['input']) for r in rr)} | {' / '.join(str(r['usage']['output']) for r in rr)} |")
report += ['', '## Dispersion des différences appariées', '', 'Chaque delta correspond à un même jeu, cas et répétition ; somme / moyenne / écart-type population / min–max. Une différence de tokens ou de temps ne mesure pas une économie financière.', '', '| Comparaison | Mesure (bras − default) | Statistiques |', '|---|---|---|']
for arm in ('s1d1','configurable'):
 for field in ('elapsed_ms','decision_ms','input','output','cache_read'):
  deltas=[]
  for split in ('dev','validation'):
   for fam in FAMILIES:
    for rep in range(2):
     a=next(r for r in allrows['2',split] if r['family']==fam and r['repetition']==rep and r['arm']==arm)
     b=next(r for r in allrows['2',split] if r['family']==fam and r['repetition']==rep and r['arm']=='default')
     x,y=(a['usage'].get(field),b['usage'].get(field)) if field in ('input','output','cache_read') else (a.get(field),b.get(field))
     if x is not None and y is not None: deltas.append(x-y)
  report.append(f'| {arm} − default | {field} | {stats(deltas)} |')
report += ['', 'Usage des 22 décisions Jev connues (par reçu, pas par parcours) : input : '+stats([d['input_tokens'] for d in dec])+' ; output : '+stats([d['output_tokens'] for d in dec])+'.', '', '## Limites de lecture', '', 'Micro-jeux synthétiques, deux répétitions par cas, pas d’inférence générale ni garantie de qualité. Le prototype ne démontre ni installation ni streaming, annulation, erreurs ou intégration validée dans quatre hôtes. Voir `STUDY.md` pour les budgets et le protocole ; les reçus JSONL conservent les réponses et événements.']
report += ['', '## Lecture du critère diagnostic', '', 'Le critère figé du runner v2 exige la clé de fixture dans le champ evidence. Les réponses observées y placent la valeur dns. La consigne demande cause et evidence sans préciser ce choix : cette ambiguïté limite la portée de ces échecs et ne démontre pas un diagnostic erroné. Les scores enregistrés ne sont pas corrigés après consultation de validation ; une consigne différente exigerait une nouvelle version du jeu.']
OUT.mkdir(parents=True, exist_ok=False)
(OUT/'REPORT.md').write_text('\n'.join(report)+'\n')
# Diagramme des résultats bruts, pas un pourcentage.
colors={'pass':'#2a9d8f','fail':'#e9a03b','error':'#d95757'}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="390" viewBox="0 0 900 390" role="img" aria-labelledby="title desc">','<title id="title">Résultats observés par bras</title><desc id="desc">Sur 20 parcours par bras, succès, évaluations négatives et erreurs distincts. Tentative 2 uniquement.</desc>','<rect width="900" height="390" fill="#101827"/><g font-family="sans-serif" fill="#f0f4fa"><text x="35" y="43" font-size="22">Campagne figée — résultats par bras</text><text x="35" y="69" font-size="14">20 parcours par bras · dev + validation · aucun taux généralisable</text>']
for i,a in enumerate(ARMS):
 rr=[r for r in rows if r['arm']==a]; counts=[sum(r['evaluation']=='pass' for r in rr),sum(r['evaluation']=='fail' for r in rr),sum(r['state']=='error' for r in rr)]; assert sum(counts)==20
 y=105+i*68; svg.append(f'<text x="35" y="{y+25}" font-size="17">{escape(a)}</text>'); pos=180
 for label,n in zip(('pass','fail','error'),counts):
  if n:
   svg.append(f'<rect x="{pos}" y="{y}" width="{n*27}" height="37" fill="{colors[label]}"/><text x="{pos+n*13.5}" y="{y+25}" text-anchor="middle" font-size="15" fill="#101827">{n}</text>');pos+=n*27
svg+=['<text x="35" y="335" font-size="15">Vert : pass     Orange : fail évalué     Rouge : erreur non évaluée</text><text x="35" y="360" font-size="13">Oracle borné ; données synthétiques ; aucune économie mesurée.</text></g></svg>']
(OUT/'resultats.svg').write_text('\n'.join(svg)+'\n')
(OUT/'DRAFT-LINKEDIN.md').write_text('''# Brouillon LinkedIn — non publié

J’ai testé un prototype de routage de modèles sur une petite campagne locale : 60 parcours synthétiques, trois approches, cinq familles de tâches, deux répétitions et deux jeux séparés.

La référence était un modèle Qwen local observé dans Hermes, pas le modèle par défaut de ChatGPT. J’ai comparé cette route fixe à s1d1 et à un décideur Jev. Sur ces tâches, le routage n’a pas démontré de gain de réussite.

Le test a aussi révélé une ambiguïté du protocole : le champ « evidence » devait contenir une clé de fixture, mais les modèles y ont mis la cause trouvée. Les diagnostics restent notés en échec selon le critère fixé avant les essais ; ce score ne suffit pas à dire que leurs diagnostics étaient faux. Certains parcours de délégation ont également échoué.

Le plus utile ici n’est pas de promettre une économie : je ne connais ni le coût complet de l’exécution locale ni la facture Jev. Les chiffres ne permettent pas de l’établir. Le code a été testé avec quatre entrées comportementales par parcours ; la délégation était orchestrée par le runner.

C’est un prototype et un résultat borné, pas quatre intégrations hôtes validées ni une conclusion générale. Les plans, reçus et limites accompagnent l’analyse.
''')
(OUT/'DRAFT-X.md').write_text('''# Brouillon X — non publié

Open Model Router : premier test réel sur 60 parcours synthétiques. Route fixe Qwen locale, s1d1 et Jev. Aucun gain de réussite démontré ; un critère diagnostic s'est révélé ambigu. Rapports et erreurs conservés. Les quatre intégrations restent à valider.
''')
# Scelle l'ensemble des sources et livrables sauf le manifeste lui-même.
files=sorted(set([SRC/'STUDY.md', Path(__file__).resolve()]+[p for root in (SRC, SRC/'attempt-2') for p in root.iterdir() if p.is_file() and p.suffix in ('.json','.jsonl')]+[p for p in OUT.iterdir() if p.is_file() and p.name!='MANIFEST.sha256']))
(OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {os.path.relpath(p, OUT)}\n' for p in files))
print('OK : 120 lignes confrontées aux plans ; 60 parcours tentative 2 ; 22 usages Jev, 8626/726 ; manifest',len(files),'fichiers')
