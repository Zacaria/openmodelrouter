import json, pathlib
b=pathlib.Path(__file__).parent
rows=[json.loads(s) for s in (b/'commands.jsonl').read_text().splitlines()]
def entry(name): return next(x for x in rows if x['name']==name)
def events(name): return [json.loads(x) for x in (b/(name+'.jsonl')).read_text().splitlines() if x.startswith('{')]
def final(name):
    return next((x.get('text',x.get('result','')) for x in reversed(events(name)) if x.get('type')=='result'), '')
def receipt(path,session,status):
    return [x['request_id'] for x in map(json.loads,(b/path).read_text().splitlines()) if x.get('session')==session and x.get('status')==status]
checks={}
for host in ('hermes','claude'):
    turn=entry(host+'-turn1'); session=turn['cmd'][turn['cmd'].index('--session')+1]; sid=turn['native_session_ids'][-1]
    cancel=entry('hermes-cancel' if host=='hermes' else 'claude-cancel-retry'); recovery='hermes-recovery-specific' if host=='hermes' else 'claude-recovery-retry'
    e=events(host+'-turn1'); text=(b/(host+'-turn1.jsonl')).read_text()
    checks[host]={'tool_call_and_result': ('read_file' in text and 'tool_result' in text) if host=='hermes' else ('"type":"tool_use"' in text and '"type":"tool_result"' in text), 'first_final_fixture':'blue-otter-73' in final(host+'-turn1'), 'resumed_final_fixture':'blue-otter-73' in final(host+'-turn2'), 'resumed_same_session':sid in entry(host+'-turn2')['native_session_ids'], 'no_tool_on_resume':not any(x.get('type')=='tool_use' for x in events(host+'-turn2')) if host=='hermes' else '"type":"tool_use"' not in (b/(host+'-turn2.jsonl')).read_text(), 'native_streaming':any(x.get('type')==('text' if host=='hermes' else 'stream_event') for x in e), 'upstream_error_receipts':receipt('error-receipts.jsonl',session,'upstream_error'),'error_timeout':entry(host+'-error')['exit']==124,'cancel_exit_130':cancel['exit']==130,'terminal_not_seen':cancel['marker'].get('terminal_seen') is False,'upstream_established_before':bool(cancel['marker'].get('upstream_before')),'child_group_observed':bool(cancel['marker'].get('child_groups')),'no_group_survivors':cancel['live_child_groups']==[],'no_upstream_socket_after':cancel['upstream_after']==[],'cancelled_receipts':receipt('receipts.jsonl' if host=='hermes' else 'retry-receipts.jsonl',session,'cancelled'),'recovered_same_session':sid in entry(recovery)['native_session_ids'], 'recovered_fixture':'blue-otter-73' in final(recovery)}
(b/'checks.json').write_text(json.dumps(checks,indent=2)+'\n'); print(json.dumps(checks,indent=2))
assert all(all(bool(v) for v in x.values()) for x in checks.values())
