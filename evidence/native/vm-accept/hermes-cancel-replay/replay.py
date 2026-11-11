import json, os, pathlib, signal, socket, subprocess, sys, time, uuid
import psutil
b=pathlib.Path(__file__).parent; root=b.parent/'snapshot'; os.chdir(root)
conf=json.loads((b.parent/'config-template.json').read_text()); conf['receipts']=str(b/'receipts.jsonl'); (b/'config.json').write_text(json.dumps(conf,indent=2))
with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
env={k:v for k,v in os.environ.items() if not (k.startswith(('HERMES_','_HERMES','ANTHROPIC_','OPENAI_','CLAUDE_')))}
env.update(HOME=str(b/'home'),HERMES_HOME=str(b/'home/.hermes'),TMPDIR=str(b/'tmp'),NO_PROXY='*',no_proxy='*')
session=str(uuid.uuid4()); (b/'launcher-session.txt').write_text(session+'\n')
log=(b/'gateway.log').open('wb'); gateway=subprocess.Popen([sys.executable,'-B',str(b/'observe.py'),'serve','--config',str(b/'config.json'),'--port',str(port)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
def run(name,prompt,resume=None,cancel=False):
    cmd=[sys.executable,'-B','host-adapters/launch.py','hermes','--port',str(port),'--session',session,'--project',str(b/'project'),'--run-timeout','180','--','--ignore-user-config','--reasoning','none','--format','stream-json']+(['--resume',resume] if resume else [])+['-q',prompt]
    with (b/(name+'.jsonl')).open('wb') as out, (b/(name+'.err')).open('wb') as err:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True,env=env)
        if cancel: (b/'armed.pid').write_text(str(p.pid))
        try: code=p.wait(timeout=200)
        except subprocess.TimeoutExpired:
            p.send_signal(signal.SIGTERM); code=p.wait(timeout=10)
        if cancel: (b/'armed.pid').unlink(missing_ok=True)
    rows=[]
    for line in (b/(name+'.jsonl')).read_text(errors='replace').splitlines():
        try: rows.append(json.loads(line))
        except ValueError: pass
    r={'name':name,'cmd':cmd,'exit':code,'session_ids':list(dict.fromkeys(x.get('session_id') for x in rows if x.get('session_id')))}
    (b/(name+'-result.json')).write_text(json.dumps(r,indent=2)); return r
try:
    for _ in range(100):
        if gateway.poll() is not None: raise RuntimeError('gateway exited')
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2): break
        except OSError: time.sleep(.1)
    else: raise RuntimeError('gateway not ready')
    first=run('initial','Remember this exact synthetic code: blue-otter-73. Reply with the code.')
    if first['exit'] or not first['session_ids']: raise RuntimeError('initial session failed: '+repr(first))
    sid=first['session_ids'][-1]; (b/'native-session.txt').write_text(sid+'\n')
    cancel=run('cancel','Write a numbered list of 400 simple everyday objects, one per line. Start immediately with item 1.',sid,True)
    time.sleep(1)
    marker=json.loads((b/'marker.json').read_text()) if (b/'marker.json').exists() else {}
    after=[dict(local=list(c.laddr),remote=list(c.raddr),status=c.status) for c in psutil.Process(gateway.pid).net_connections(kind='tcp') if c.raddr and c.raddr.ip=='10.77.0.11' and c.status=='ESTABLISHED']
    live=[]
    for proc in psutil.process_iter(['pid','status']):
        try:
            if os.getpgid(proc.pid) in marker.get('child_groups',[]) and proc.info['status'] != psutil.STATUS_ZOMBIE: live.append(proc.pid)
        except (ProcessLookupError,PermissionError): pass
    resumed=run('resume','What exact synthetic code did I ask you to remember? Reply only with the code.',sid)
    receipts=[json.loads(x) for x in (b/'receipts.jsonl').read_text().splitlines()]
    response=(b/'resume.jsonl').read_text(errors='replace')
    checks={'marker':marker,'cancel_exit':cancel['exit'],'upstream_after':after,'live_child_groups':live,'cancel_receipts':receipts[1:-1],'resume_exit':resumed['exit'],'resume_session_ids':resumed['session_ids'],'resume_contains_code':'blue-otter-73' in response,'same_native_session':sid in resumed['session_ids']}
    (b/'checks.json').write_text(json.dumps(checks,indent=2)); print(json.dumps(checks,indent=2),flush=True)
finally:
    gateway.terminate()
    try: gateway.wait(timeout=5)
    except subprocess.TimeoutExpired: gateway.kill(); gateway.wait()
    log.close()
