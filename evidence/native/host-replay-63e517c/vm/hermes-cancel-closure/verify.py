import json, pathlib
b = pathlib.Path(__file__).resolve().parent
read = lambda name: json.loads((b / name).read_text())
rows = lambda name: [json.loads(line) for line in (b / name).read_text().splitlines()]
c = read('checks.json'); m = read('cancel-marker.json'); session = (b / 'launcher-session.txt').read_text().strip(); native = (b / 'native-session.txt').read_text().strip()
assert c['marker'] == m and m['event'] == 'first_nonempty_chat_delta_after_flush' and m['signal'] == 'SIGINT' and not m['terminal_seen']
assert m['session'] == session and m['upstream_status'] == 200 and m['upstream_before'] and m['child_groups']
assert all(x['status'] == 'ESTABLISHED' and x['remote'] == ['10.77.0.11', 11434] for x in m['upstream_before'])
assert c['cancel_exit'] == 130 and read('cancel-result.json')['exit'] == 130
assert any(x.get('type') == 'result' and x.get('exit_code') == 130 and x.get('session_id') == native for x in rows('cancel.jsonl'))
assert not c['upstream_after'] and not c['live_child_groups']
r = [x for x in rows('receipts.jsonl') if x['request_id'] == m['request_id']]
assert len(r) == 1 and r == c['cancel_receipts']
assert r[0]['status'] == 'cancelled' and r[0]['upstream_status'] == 200 and r[0]['session'] == session
assert r[0]['route'] == 'local' and r[0]['model_requested'] == r[0]['model_observed'] == 'omr-hermes-qwen3-4b:ctx8192'
assert c['resume_exit'] == 0 and c['same_native_session'] and any(x.get('type') == 'result' and x.get('session_id') == native and x.get('exit_code') == 0 and x.get('text') == 'blue-otter-73' for x in rows('resume.jsonl'))
runtimes = list(b.glob('runtime-*.json')); assert len(runtimes) == 1
assert read(runtimes[0].name)['source_sha256'] == '6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b'
print('PASS: compiled source, correlated flushed stream, SIGINT, native exit, socket/group absence, exact cancelled receipt, same-session recovery:', m['request_id'])
