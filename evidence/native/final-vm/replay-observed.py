import json, os, pathlib, signal, socket, subprocess, sys, time, uuid, psutil
root=pathlib.Path('/srv/omr-private/workspaces/open-model-router/host-adapters'); os.chdir(root)
out=root/'evidence/native/final-vm/observed'; out.mkdir(exist_ok=True); core=pathlib.Path('/srv/omr-private/workspaces/open-model-router/router-gateway/omr.py')
project=root/'evidence/native/project'
with socket.socket() as s:
 s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
config=json.loads((root/'evidence/native/replay/gateway-config.json').read_text()); config['receipts']=str(out/'receipts.jsonl'); (out/'config.json').write_text(json.dumps(config,indent=2))
log=(out/'gateway.log').open('wb'); gateway=subprocess.Popen([sys.executable,'-B',str(core),'serve','--config',str(out/'config.json'),'--port',str(port)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
def run(host, name, session, args, bad=False, cancel=False):
 cmd=[sys.executable,'-B','host-adapters/launch.py',host,'--port',str(1 if bad else port),'--session',session,'--project',str(project),'--run-timeout',str(30 if bad else 180),'--']+args
 stdout=(out/(name+'.jsonl')).open('wb'); stderr=(out/(name+'.err')).open('wb'); p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr, start_new_session=True)
 seen=False; group=None; upstream_before=[]
 if cancel:
  until=time.monotonic()+160
  while p.poll() is None and time.monotonic()<until:
   text=(out/(name+'.jsonl')).read_text(errors='replace')
   for line in text.splitlines():
    try: obj=json.loads(line)
    except ValueError: continue
    if (host=='hermes' and obj.get('type')=='text' and obj.get('text')) or (host=='claude' and obj.get('event',{}).get('delta',{}).get('type')=='text_delta' and obj['event']['delta'].get('text')):
     seen=True; break
   if seen:
    children=psutil.Process(p.pid).children(); group=os.getpgid(children[0].pid) if children else None
    upstream_before=[{'fd':c.fd,'local':list(c.laddr),'remote':list(c.raddr),'status':c.status} for c in psutil.Process(gateway.pid).net_connections(kind='tcp') if c.raddr and c.raddr.ip=='10.77.0.11']
    p.send_signal(signal.SIGINT); break
   time.sleep(.03)
 try: code=p.wait(timeout=190)
 except subprocess.TimeoutExpired:
  p.send_signal(signal.SIGTERM); code=p.wait(timeout=6)
 stdout.close(); stderr.close()
 # The child is in its own group. Record any surviving launcher descendants/group from proc snapshots captured while running separately in logs.
 time.sleep(.5 if cancel else 0)
 upstream_after=[{'fd':c.fd,'local':list(c.laddr),'remote':list(c.raddr),'status':c.status} for c in psutil.Process(gateway.pid).net_connections(kind='tcp') if c.raddr and c.raddr.ip=='10.77.0.11'] if cancel else []
 group_live=[]
 if group is not None:
  for proc in psutil.process_iter(['pid','status']):
   try:
    if os.getpgid(proc.pid)==group and proc.info['status'] != psutil.STATUS_ZOMBIE: group_live.append(proc.pid)
   except (ProcessLookupError,PermissionError): pass
 result={'name':name,'cmd':cmd,'exit':code,'native_text_before_sigint':seen,'child_group':group,'live_group_after':group_live,'gateway_upstream_before':upstream_before,'gateway_upstream_after':upstream_after}
 with (out/'commands.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
 print(json.dumps(result),flush=True)
 return [json.loads(x) for x in (out/(name+'.jsonl')).read_text(errors='replace').splitlines() if x.startswith('{')]
try:
 for _ in range(100):
  if gateway.poll() is not None: raise RuntimeError('gateway exited')
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2): break
  except OSError: time.sleep(.1)
 else: raise RuntimeError('gateway not ready')
 for host in ['hermes','claude']:
  session=str(uuid.uuid4()); (out/(host+'-uuid.txt')).write_text(session+'\n')
  def args(prompt, resume=None):
   if host=='hermes': return ['--ignore-user-config','--reasoning','none','--format','stream-json']+(['--resume',resume] if resume else [])+['-q',prompt]
   return ['-p']+(['--resume',resume] if resume else [])+['--tools','Read','--allowedTools','Read','--output-format','stream-json','--include-partial-messages','--verbose',prompt]
  rows=run(host,host+'-turn1',session,args('Read fixture.txt using your read tool, then report its exact contents.'))
  ids=[x.get('session_id') for x in rows if x.get('session_id')]
  if not ids: print(host+' missing session; skipping',flush=True); continue
  sid=ids[-1]; (out/(host+'-session.txt')).write_text(sid+'\n')
  recall='Without reading the file again, what exact value did the previous tool result give?'
  run(host,host+'-turn2',session,args(recall,sid))
  run(host,host+'-error',session,args(recall,sid),bad=True)
  run(host,host+'-after-error',session,args(recall,sid))
  run(host,host+'-cancel',session,args('Count from 1 to 10000, writing every number in order. Do not stop early.',sid),cancel=True)
  run(host,host+'-after-cancel',session,args(recall,sid))
finally:
 gateway.terminate()
 try: gateway.wait(timeout=5)
 except subprocess.TimeoutExpired: gateway.kill(); gateway.wait()
 log.close()
