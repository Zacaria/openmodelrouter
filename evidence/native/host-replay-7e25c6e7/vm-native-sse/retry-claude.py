import json, os, pathlib, signal, socket, subprocess, sys, time, uuid
import psutil
b=pathlib.Path(__file__).resolve().parent; root=pathlib.Path('/home/operator/repos/open-model-router'); os.chdir(root)
config=json.loads(pathlib.Path('/srv/omr-private/workspaces/open-model-router/vm-final-accept/config-template.json').read_text()); config['timeout_seconds']=60; config['receipts']=str(b/'retry-receipts.jsonl')
def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def gateway(name,conf,observed=False):
    p=port(); (b/(name+'-config.json')).write_text(json.dumps(conf,indent=2)); log=(b/(name+'-gateway.log')).open('wb')
    cmd=[sys.executable,'-B',str(b/'observe.py' if observed else root/'omr.py'),'serve','--config',str(b/(name+'-config.json')),'--port',str(p)]
    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(100):
        if proc.poll() is not None: raise RuntimeError('gateway exited')
        try:
            with socket.create_connection(('127.0.0.1',p),timeout=.2): break
        except OSError: time.sleep(.1)
    else: raise RuntimeError('gateway not ready')
    return p,proc,log,cmd
normal,g,gl,gcmd=gateway('retry-normal',config,True)
badconfig=json.loads(json.dumps(config)); badconfig['routes']['local']['url']='http://127.0.0.1:1/v1'; badconfig['receipts']=str(b/'retry-error-receipts.jsonl')
bad,bg,bgl,bgcmd=gateway('retry-error',badconfig)
(b/'retry-gateway-commands.json').write_text(json.dumps([gcmd,bgcmd],indent=2))
def run(host,name,session,args,error=False,cancel=False):
    cmd=[sys.executable,'-B',str(root/'host-adapters/launch.py'),host,'--port',str(bad if error else normal),'--session',session,'--project',str(b/'project'/host),'--run-timeout',str(25 if error else 75),'--']+args
    env={k:v for k,v in os.environ.items() if not k.startswith(('HERMES_','_HERMES','ANTHROPIC_','OPENAI_','CLAUDE_'))}
    home=b/'home'/host; env.update(HOME=str(home),HERMES_HOME=str(home/'.hermes'),TMPDIR=str(b/'tmp'),NO_PROXY='*',no_proxy='*',PIP_NO_INDEX='1',UV_OFFLINE='1')
    with (b/(name+'.jsonl')).open('wb') as out,(b/(name+'.err')).open('wb') as err:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True,env=env)
        if cancel: (b/'armed.json').write_text(json.dumps({'pid':p.pid,'name':name}))
        try: code=p.wait(timeout=85)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM)
            try: code=p.wait(timeout=4)
            except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); code=p.wait()
        if cancel: (b/'armed.json').unlink(missing_ok=True)
    rows=[]
    for line in (b/(name+'.jsonl')).read_text(errors='replace').splitlines():
        try: rows.append(json.loads(line))
        except ValueError: pass
    marker=json.loads((b/(name+'-marker.json')).read_text()) if (b/(name+'-marker.json')).exists() else {}
    time.sleep(.5 if cancel else 0)
    live=[]
    for proc in psutil.process_iter(['pid','status']):
        try:
            if os.getpgid(proc.pid) in marker.get('child_groups',[]) and proc.info['status']!=psutil.STATUS_ZOMBIE: live.append(proc.pid)
        except (ProcessLookupError,PermissionError): pass
    upstream=[dict(local=list(c.laddr),remote=list(c.raddr),status=c.status) for c in psutil.Process(g.pid).net_connections(kind='tcp') if c.raddr and c.raddr.ip=='10.77.0.11' and c.status=='ESTABLISHED'] if cancel else []
    result={'name':name,'cmd':cmd,'exit':code,'launcher_pid':p.pid,'native_session_ids':list(dict.fromkeys(x.get('session_id') for x in rows if x.get('session_id'))),'marker':marker,'live_child_groups':live,'upstream_after':upstream}
    with (b/'commands.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
    print(json.dumps(result),flush=True); return result
try:
    host='claude'; session='597ec366-b09a-4fb0-a970-8da8a551fae4'; sid='6c309ecf-fc6e-4eed-9d14-ac65122ced44'
    def args(prompt): return ['-p','--resume',sid,'--tools','Read','--allowedTools','Read','--output-format','stream-json','--include-partial-messages','--verbose',prompt]
    run(host,'claude-cancel-retry',session,args('Write a numbered list of 400 simple everyday objects, one per line. Start immediately with item 1.'),cancel=True)
    run(host,'claude-recovery-retry',session,args('Without reading the file again, what exact value did the previous tool result give?'))
finally:
    for proc,log in [(g,gl),(bg,bgl)]:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        log.close()
