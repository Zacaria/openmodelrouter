"""Synthetic gateway benchmark; model outputs are retained after limited redaction."""
import argparse
import hashlib
import json
import os
import random
import statistics
import time
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path

import ast
import math
import re

VERSION = 'synthetic-v2-static-20261027'
MAX_CALLS = 5
MAX_TOKENS = 256


def cases():
    rows = []
    for split, offset in (('dev', 0), ('validation', 20)):
        for i in range(10):
            n = offset + i + 2
            def add(family, prompts, expected, **extra):
                rows.append(dict(id=f'{family}-{split}-{i+1:02}', family=family, split=split, prompts=prompts, expected=expected, **extra))
            add('simple', [f'Calcule {n} × 3. Réponds uniquement par un entier.'], [str(n*3)])
            ref = f'def transform(x):\n    return x * {n} + 1\n'
            add('code', [f'Écris uniquement une fonction Python transform(x) retournant x multiplié par {n}, puis augmenté de 1, avec une seule instruction return.'], None, reference=ref)
            key = f'fixture-{split}-{i+1:02}'; cause = 'dns' if i % 2 == 0 else 'service'
            add('diagnostic', [f'Une connexion échoue. Causes possibles : dns ou service. Réponds seulement en JSON avec hypotheses=["dns","service"] et test="lookup:{key}"; ne conclus pas encore.', f'Appelle lookup avec key="{key}" puis réponds seulement en JSON avec cause et evidence.'], [json.dumps({'hypotheses':['dns','service'],'test':'lookup:'+key}), json.dumps({'cause':cause,'evidence':key})], fixture_key=key, fixture_value=cause)
            add('conversation', [f'Pour toute cette conversation réponds uniquement en chiffres. Combien font {n}+1 ?', f'Calcule la somme des entiers de 1 à {n}, puis ajoute {n+1}.'], [str(n+1), str(n*(n+1)//2+n+1)])
            task = f'Calcule {n} multiplié par 7. Réponds uniquement par un entier.'
            add('agents', [f'Utilise obligatoirement delegate pour la tâche exacte {json.dumps(task, ensure_ascii=False)}. Ensuite réponds uniquement sous la forme enfant=<résultat>;parent=<résultat>, où parent vaut {n}+2.'], [f'enfant={n*7};parent={n+2}'], child_task=task, child_answer=str(n*7))
    return rows


def code_expression(source):
    if not isinstance(source, str) or len(source) > 4096: raise ValueError('invalid source')
    source = source.strip()
    if source.startswith('```'):
        match = re.fullmatch(r'```(?:python)?[ \t]*\n(.*?)\n```', source, re.DOTALL | re.IGNORECASE)
        if not match: raise ValueError('invalid fence')
        source = match.group(1)
    module = ast.parse(source)
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef): raise ValueError('invalid function')
    fn = module.body[0]; args = fn.args
    if (fn.name != 'transform' or fn.decorator_list or fn.returns or fn.type_comment or
        getattr(fn, 'type_params', []) or args.posonlyargs or len(args.args) != 1 or
        args.args[0].arg != 'x' or args.args[0].annotation or args.vararg or args.kwarg or
        args.kwonlyargs or args.defaults or args.kw_defaults or len(fn.body) != 1 or
        not isinstance(fn.body[0], ast.Return) or fn.body[0].value is None):
        raise ValueError('invalid signature or body')
    def validate(node, depth):
        if depth > 32: raise ValueError('expression too deep')
        if isinstance(node, ast.Name) and node.id == 'x': return
        if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 1000: return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            validate(node.operand, depth + 1); return
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            validate(node.left, depth + 1); validate(node.right, depth + 1); return
        raise ValueError('unsupported expression')
    expression = fn.body[0].value
    validate(expression, 1)
    return expression


def code_value(node, x):
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name): return x
    if isinstance(node, ast.UnaryOp):
        value = code_value(node.operand, x)
        return -value if isinstance(node.op, ast.USub) else value
    left, right = code_value(node.left, x), code_value(node.right, x)
    if isinstance(node.op, ast.Add): return left + right
    if isinstance(node.op, ast.Sub): return left - right
    return left * right


def evaluate(case, answers, events, code_test_results=None):
    if case['family'] == 'code':
        try:
            if len(answers) != 1: return False
            candidate = code_expression(answers[0]); reference = code_expression(case['reference'])
            results = []
            for x in (-3, 0, 1, 9):
                actual, expected = code_value(candidate, x), code_value(reference, x)
                results.append({'x': x, 'actual': actual, 'expected': expected, 'pass': actual == expected})
            if code_test_results is not None: code_test_results.extend(results)
            return all(result['pass'] for result in results)
        except (SyntaxError, ValueError, RecursionError, MemoryError, TypeError, KeyError): return False
    if case['family'] == 'diagnostic':
        try:
            return len(answers) == 2 and [json.loads(x) for x in answers] == [json.loads(x) for x in case['expected']] and any(e.get('name') == 'lookup' and e.get('key') == case['fixture_key'] and e.get('turn') == 1 for e in events)
        except (ValueError, TypeError): return False
    if case['family'] == 'agents':
        return answers == case['expected'] and any(e.get('name') == 'delegate' and e.get('child_answer') == case['child_answer'] for e in events)
    return answers == case['expected']


def redact(value):
    value = re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|token|password)\s*[:=]\s*)[^\s,;"}]+', r'\1[REDACTED]', value)
    return re.sub(r'\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{8,}\b', '[REDACTED]', value)


def tool(name):
    field = 'task' if name == 'delegate' else 'key'
    return {'type':'function', 'function':{'name':name, 'description':'Synthetic fixture or child generation', 'parameters':{'type':'object','properties':{field:{'type':'string'}},'required':[field],'additionalProperties':False}}}

ARMS = ('default', 's1d1', 'configurable')
TOOLS = [{'type': 'function', 'function': {'name': 'lookup', 'description': 'Read a synthetic constant', 'parameters': {'type': 'object', 'properties': {'key': {'type': 'string', 'enum': ['alpha', 'beta']}}, 'required': ['key'], 'additionalProperties': False}}}]


def tool_result(name, arguments):
    args = json.loads(arguments)
    if name != 'lookup' or not isinstance(args, dict) or set(args) != {'key'} or args['key'] not in ('alpha', 'beta'):
        raise ValueError('prohibited tool call')
    return {'alpha': '7', 'beta': '11'}[args['key']]


def execute(case, arm, base, timeout):
    session = str(uuid.uuid4()); start = time.monotonic(); deadline = start + timeout
    row = dict(case=case['id'], family=case['family'], split=case['split'], arm=arm, session=session,
        state='error', evaluation=None, reason=None, provenance='gateway-response', route=None, effort=None,
        cache='unknown', decision_ms=None, retry_ms=0, retries=0,
        usage={k:None for k in ('input','output','cache_read','cache_write','reasoning','decision','tools','retry')},
        rates=None, equivalent_value=None, observed_models=[], calls=0, call_records=[], raw_outputs=[], events=[], code_test_results=[] if case['family'] == 'code' else None)
    messages = []; answers = []; events = []
    def request(msgs, sid, tools=None, kind='parent'):
        if row['calls'] >= MAX_CALLS: raise ValueError('shared call budget exceeded')
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise TimeoutError('shared deadline exceeded')
        payload = {'model':'open-model-router','messages':msgs,'stream':False,'max_tokens':MAX_TOKENS}
        if tools: payload['tools'] = tools
        req = urllib.request.Request(base.rstrip('/')+'/v1/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','X-OMR-Session':sid}, method='POST')
        row['calls'] += 1
        # Never allow a loopback gateway to redirect benchmark payloads elsewhere.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        call_start = time.monotonic()
        with urllib.request.build_opener(NoRedirect).open(req, timeout=remaining) as response:
            body = json.load(response)
            headers = {k:response.headers.get(k) for k in ('X-OMR-Route','X-OMR-Effort','X-OMR-Decision-Ms')}
        call_ms = (time.monotonic() - call_start) * 1000
        model = body.get('model')
        if isinstance(model,str) and model not in row['observed_models']: row['observed_models'].append(model)
        row['call_records'].append({'kind':kind,'session':sid,'model':model,'headers':headers,'usage':body.get('usage'),'elapsed_ms':call_ms})
        message = body['choices'][0]['message']; content = message.get('content')
        if isinstance(content,str): row['raw_outputs'].append({'kind':kind,'content':redact(content)})
        return message
    try:
        for turn, prompt in enumerate(case['prompts']):
            messages.append({'role':'user','content':prompt})
            for _ in range(MAX_CALLS):
                offered = [tool('lookup')]
                if case['family'] == 'agents': offered.append(tool('delegate'))
                message = request(messages, session, offered); calls = message.get('tool_calls') or []
                if not calls:
                    answer = message.get('content')
                    if not isinstance(answer,str): raise ValueError('invalid response')
                    answers.append(answer.strip()); messages.append({'role':'assistant','content':answer}); break
                messages.append(message)
                for call in calls:
                    function = call['function']; name = function['name']; args = json.loads(function['arguments'])
                    if not isinstance(args,dict): raise ValueError('invalid tool arguments')
                    if name == 'lookup' and set(args) == {'key'}:
                        key = args['key']
                        if case['family'] == 'diagnostic' and turn == 1 and key == case['fixture_key']: result = case['fixture_value']
                        else: result = tool_result(name, function['arguments'])
                        events.append({'name':name,'key':key,'turn':turn,'result':result})
                    elif name == 'delegate' and case['family'] == 'agents' and args == {'task':case['child_task']} and not any(e['name']=='delegate' for e in events):
                        child_session = str(uuid.uuid4())
                        child = request([{'role':'user','content':case['child_task']}], child_session, kind='child')
                        result = child.get('content')
                        if not isinstance(result,str) or child.get('tool_calls'): raise ValueError('invalid child response')
                        result = result.strip(); events.append({'name':name,'child_session':child_session,'child_answer':redact(result),'turn':turn})
                    else: raise ValueError('prohibited tool call')
                    messages.append({'role':'tool','tool_call_id':call['id'],'content':result})
            else: raise ValueError('tool limit exceeded')
        row['state'] = 'executed'; row['code_test_results'] = [] if case['family'] == 'code' else None
        row['evaluation'] = 'pass' if evaluate(case, answers, events, row['code_test_results']) else 'fail'
    except Exception as exc:
        row['reason'] = type(exc).__name__
    finally:
        row['events'] = events; records = row['call_records']
        def total(path):
            vals = []
            for rec in records:
                val = rec['usage']
                for part in path: val = val.get(part) if isinstance(val,dict) else None
                vals.append(val)
            return sum(vals) if len(records)==row['calls'] and vals and all(type(v) is int and v>=0 for v in vals) else None
        for key,path in {'input':('prompt_tokens',),'output':('completion_tokens',),'cache_read':('prompt_tokens_details','cached_tokens'),'cache_write':('prompt_tokens_details','cache_write_tokens'),'reasoning':('completion_tokens_details','reasoning_tokens')}.items(): row['usage'][key] = total(path)
        times = []
        for rec in records:
            try:
                val = float(rec['headers']['X-OMR-Decision-Ms'])
                if not math.isfinite(val) or val < 0: raise ValueError()
                times.append(val)
            except (TypeError, ValueError): pass
        if len(times) == row['calls'] and times: row['decision_ms'] = sum(times)
        if records: row['route'] = records[-1]['headers']['X-OMR-Route']; row['effort'] = records[-1]['headers']['X-OMR-Effort']
        row['elapsed_ms'] = (time.monotonic()-start)*1000
    return row


def save_new(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(text)


def run(args):
    if not args.authorized: raise ValueError('explicit --authorized required')
    if not 1 <= args.repetitions <= 100 or args.timeout <= 0: raise ValueError('invalid limits')
    # Restrict destinations to local gateways; the gateway itself may call providers.
    from urllib.parse import urlsplit
    urls = {arm: getattr(args, arm) for arm in ARMS}
    for url in urls.values():
        parsed = urlsplit(url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('gateway must be a local HTTP origin')
    count = getattr(args, 'cases_per_family', 10)
    if type(count) is not int or not 1 <= count <= 10: raise ValueError('invalid cases per family')
    rng = random.Random(args.seed)
    seen = defaultdict(int); fixtures = []
    for case in cases():
        if case['split'] == args.split and seen[case['family']] < count:
            fixtures.append(case); seen[case['family']] += 1
    fingerprint = hashlib.sha256(json.dumps(fixtures, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    schedule = []
    for case in fixtures:
        for repetition in range(args.repetitions):
            order = list(ARMS); rng.shuffle(order)
            for index, arm in enumerate(order):
                schedule.append(dict(case=case['id'], family=case['family'], arm=arm, repetition=repetition, order=index, global_order=len(schedule)))
    plan = dict(fixture_sha256=fingerprint, fixture_version=VERSION, split=args.split, seed=args.seed,
                cases_per_family=count, repetitions_planned=args.repetitions, planned_total=len(schedule), runs=schedule)
    # Reserve both files and persist the complete schedule before the first call.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', buffering=1) as out:
        save_new(str(args.output) + '.plan.json', json.dumps(plan, ensure_ascii=False))
        by_id = {case['id']: case for case in fixtures}
        for item in schedule:
            row = execute(by_id[item['case']], item['arm'], urls[item['arm']], args.timeout)
            row.update(item, seed=args.seed, fixture_sha256=fingerprint, fixture_version=VERSION,
                       repetitions_planned=args.repetitions, planned_total=len(schedule))
            out.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')


def report(args):
    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    if not rows: raise ValueError('no receipts')
    groups = defaultdict(list)
    for row in rows: groups[(row['split'], row['family'], row['arm'])].append(row)
    text = ['# Rapport de pilote — non publié', '', 'Provenance : reçus fournis ; configuration et routes à vérifier indépendamment. Aucun résultat simulé ne constitue une mesure réelle.', '', '| Jeu | Famille | Bras | Reçus | Exécutés | Évalués | Réussis | Erreurs | Durée moyenne ± écart-type (ms) |', '|---|---|---|---:|---:|---:|---:|---:|---:|']
    bars = []
    for (split, family, arm), group in sorted(groups.items()):
        elapsed = [r['elapsed_ms'] for r in group if r.get('elapsed_ms') is not None]
        evaluated = sum(r.get('evaluation') in ('pass', 'fail') for r in group)
        passed = sum(r.get('evaluation') == 'pass' for r in group)
        times = f'{statistics.fmean(elapsed):.1f} ± {statistics.pstdev(elapsed):.1f}' if elapsed else 'inconnu'
        text.append(f"| {split} | {family} | {arm} | {len(group)} | {sum(r['state']=='executed' for r in group)} | {evaluated} | {passed} | {sum(r['state']=='error' for r in group)} | {times} |")
        bars.append((f'{split} {family} {arm}', passed, len(group)))
    text += ['', '## Mesures par groupe', '', '| Jeu/famille/bras | Mesure | Connus/reçus | Moyenne ± écart-type |', '|---|---|---:|---:|']
    for key, group in sorted(groups.items()):
        for metric in ('input', 'output', 'cache_read', 'cache_write', 'reasoning', 'decision_ms', 'retries'):
            vals = [(r.get('usage', {}).get(metric) if metric in ('input','output','cache_read','cache_write','reasoning') else r.get(metric)) for r in group]
            vals = [v for v in vals if type(v) in (int, float) and math.isfinite(v)]
            summary = f'{statistics.fmean(vals):.1f} ± {statistics.pstdev(vals):.1f}' if vals else 'inconnu'
            text.append(f"| {'/'.join(key)} | {metric} | {len(vals)}/{len(group)} | {summary} |")
    text += ['', 'Comparer les reçus au plan associé pour compter les parcours manquants ; les anciens reçus peuvent ne pas avoir de plan. Les taux parmi reçus omettent les parcours non lancés. Tarifs, facture et valeur équivalente : inconnus. Cache fournisseur : inconnu. Les tokens cache/raisonnement peuvent être inclus dans entrée/sortie. Oracle code actuel : interpréteur AST borné, quatre entrées, pas une sandbox générale ; les anciens reçus peuvent utiliser un oracle différent. Aucune comparaison ni économie validée.', '']
    import html
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="700" height="{40+30*len(bars)}">', '<text x="10" y="20">Réussites / reçus (pas / prévus)</text>']
    for i, (label, passed, total) in enumerate(bars):
        y = 40 + i * 30
        svg.append(f'<text x="10" y="{y+12}">{html.escape(label)}</text><rect x="300" y="{y}" width="{300*passed/total:.1f}" height="16" fill="#246"/><text x="610" y="{y+12}">{passed}/{total}</text>')
    svg.append('</svg>')
    save_new(args.output, '\n'.join(text)); save_new(args.svg, '\n'.join(svg))


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    for arm in ARMS: r.add_argument('--' + arm, required=True)
    r.add_argument('--split', choices=('dev', 'validation'), required=True); r.add_argument('--output', required=True)
    r.add_argument('--seed', type=int, default=0); r.add_argument('--repetitions', type=int, default=5)
    r.add_argument('--cases-per-family', type=int, choices=range(1, 11), default=10)
    r.add_argument('--timeout', type=float, default=60); r.add_argument('--authorized', action='store_true'); r.set_defaults(func=run)
    r = sub.add_parser('report'); r.add_argument('--input', required=True); r.add_argument('--output', required=True); r.add_argument('--svg', required=True); r.set_defaults(func=report)
    args = p.parse_args()
    try: args.func(args)
    except (OSError, ValueError, KeyError, TypeError) as exc: p.exit(1, f'error: {type(exc).__name__}: {exc}\n')

if __name__ == '__main__': main()
