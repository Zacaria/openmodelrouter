import hashlib, json
from pathlib import Path
p=Path(__file__).resolve().parent
r=json.loads((p/'result.json').read_text()); turns={x['label']:x for x in r['turns']}
for line in (p/'remote-hashes-and-cleanup.txt').read_text().splitlines():
    parts=line.split('  ',1)
    if len(parts)==2 and len(parts[0])==64:
        assert hashlib.sha256((p/parts[1]).read_bytes()).hexdigest()==parts[0], parts[1]
assert r['sha256']=='6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b'
assert r['owned_groups_absent'] and all(x['group_absent'] for x in r['turns'])
sid=turns['first']['thread_id']; assert sid and all(x['thread_id']==sid for x in r['turns'])
assert all(turns[k]['returncode']==0 and any(e['type']=='turn.completed' for e in turns[k]['events']) for k in ('first','resume','error-recovery','interrupt-recovery'))
assert any(e.get('item_type')=='command_execution' and e.get('status')=='completed' and e.get('exit_code')==0 and e.get('sentinel_seen') for e in turns['first']['events'])
assert any(e.get('item_type')=='agent_message' and e.get('sentinel_seen') for e in turns['resume']['events'])
assert not any(e.get('item_type')=='command_execution' for e in turns['resume']['events'])
assert turns['invalid-session']['returncode']!=0 and r['invalid_generation_delta']==0
rejects=[json.loads(x) for x in (p/'local-reject.jsonl').read_text().splitlines()]
assert rejects and all(x['status']==400 and x['session_invalid'] and x['peer']=='127.0.0.1' for x in rejects)
interrupt=json.loads((p/'interrupt.json').read_text()); assert interrupt['signal']=='SIGINT' and not interrupt['terminal_seen'] and turns['interrupt']['returncode']!=0
stream=[json.loads(x) for x in (p/'stream-observation.jsonl').read_text().splitlines()]
deltas=sum(x['type']=='response.output_text.delta' and x['nonempty'] for x in stream); terminals=sum(x['type']=='response.completed' for x in stream)
assert deltas and terminals>=4
receipts=r['receipts']; assert any(x.get('status')=='invalid_request' and x.get('upstream_status') is None for x in receipts)
assert any(x.get('model_observed')=='gpt-6.1-terra' and x.get('upstream_status')==200 for x in receipts)
print(json.dumps({'verified':True,'thread':sid,'nonempty_forwarded_deltas':deltas,'forwarded_terminals':terminals,'generation_attempts':len((p/'upstream-count.jsonl').read_text().splitlines()),'receipt_statuses':[x['status'] for x in receipts],'owned_groups_absent':r['owned_groups_absent']}))
