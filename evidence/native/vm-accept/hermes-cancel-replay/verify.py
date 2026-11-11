import json, pathlib
b=pathlib.Path(__file__).parent
c=json.loads((b/'checks.json').read_text()); m=c['marker']
assert m['event']=='first_nonempty_chat_delta_after_flush' and not m['terminal_seen']
assert m['upstream_before'] and m['child_groups'] and c['cancel_exit']==130
assert not c['upstream_after'] and not c['live_child_groups']
rows=[r for r in c['cancel_receipts'] if r['status']=='cancelled' and r['upstream_status']==200]
assert len(rows)==1 and rows[0]['session']==(b/'launcher-session.txt').read_text().strip()
assert c['resume_exit']==0 and c['same_native_session'] and c['resume_contains_code']
print('PASS: marker, socket, exit, child group, cancelled receipt, same-session recall; receipt',rows[0]['request_id'])
