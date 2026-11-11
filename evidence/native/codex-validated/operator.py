import os,sys,json,time,uuid,signal,socket,select,subprocess,pathlib,hashlib,secrets,threading
P=pathlib.Path(__file__).resolve().parent
CORE=P/'omr.py'
SHA='ec9c11ac447bf37eb5919d98e535d4c91b82a0b39e36202030d01fd8b8eabb0c'
assert hashlib.sha256(CORE.read_bytes()).hexdigest()==SHA
if len(sys.argv)>1 and sys.argv[1]=='serve':
 import omr
 line=next(i for i,s in enumerate(CORE.read_text().splitlines(),1) if 'event_frame.clear(); event_kind' in s)
 def trace(f,e,a):
  if e=='line' and f.f_code.co_filename==str(CORE) and f.f_code.co_name=='do_POST' and f.f_lineno==line:
   ev=f.f_locals.get('event'); typ=ev.get('type') if isinstance(ev,dict) else None
   if typ in ('response.output_text.delta','response.completed'):
    with open(P/'stream-observation.jsonl','a') as h: h.write(json.dumps({'type':typ,'nonempty':bool(ev.get('delta')) if typ.endswith('.delta') else None,'terminal_seen':bool(f.f_locals.get('terminal_seen')),'time_ns':time.time_ns()})+'\n')
    arm=P/'armed.pid'
    if typ=='response.output_text.delta' and ev.get('delta') and not f.f_locals.get('terminal_seen') and arm.exists():
     pid=int(arm.read_text()); arm.unlink(); os.killpg(pid,signal.SIGINT)
     (P/'interrupt.json').write_text(json.dumps({'signal':'SIGINT','owned_group':pid,'event':'nonempty_forwarded_text_delta_after_flush','terminal_seen':False,'time_ns':time.time_ns()}))
  return trace
 threading.settrace(trace); sys.argv=[str(CORE),'serve','--config',str(P/'gateway.json'),'--port','0']; omr.main(); sys.exit()
os.chdir(P); (P/'project').mkdir(); (P/'project/fixture.txt').write_text('SYNTHETIC_SENTINEL_ORANGE_731\n')
env=os.environ.copy(); env['OMR_TEST_GATEWAY_KEY']=secrets.token_urlsafe(48); env['OMR_TEST_SESSION']=str(uuid.uuid4())
cfg={'routes':{'native':{'url':'https://chatgpt.com/backend-api/codex','protocol':'responses','model':'gpt-6.1-terra','effort':'low','forward_auth':True}},'default_route':'native','decision':{'type':'fixed'},'gateway_key_env':'OMR_TEST_GATEWAY_KEY','receipts':str(P/'receipts.private'),'timeout_seconds':80}
(P/'gateway.json').write_text(json.dumps(cfg)); os.chmod(P/'gateway.json',0o600)
results={'sha256':SHA,'tree':'dbbbc6681fda17d5fc387d27f8b96015c835af02','gateway_session':env['OMR_TEST_SESSION'],'turns':[]}; processes=[]
def stop(p):
 if p is None:return
 try: os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError: pass
 try:p.wait(timeout=3)
 except subprocess.TimeoutExpired:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait(timeout=3)
def gone(p):
 try:os.killpg(p.pid,0);return False
 except ProcessLookupError:return True
def run(label,base,prompt,session=None,arm=False):
 opts=['--ignore-user-config','--disable','enable_request_compression','--sandbox','read-only','--skip-git-repo-check','--json','-C',str(P/'project'),'-m','open-model-router','-c','project_doc_max_bytes=0','-c','model_provider="omr"','-c','model_providers.omr.name="OpenAI"','-c',f'model_providers.omr.base_url="{base}"','-c','model_providers.omr.requires_openai_auth=true','-c','model_providers.omr.supports_websockets=false','-c','model_providers.omr.request_max_retries=0','-c','model_providers.omr.stream_max_retries=0','-c','model_providers.omr.env_http_headers={"X-OMR-Gateway-Key"="OMR_TEST_GATEWAY_KEY","X-OMR-Session"="OMR_TEST_SESSION"}','-c','model_reasoning_effort="low"']
 cmd=['/opt/homebrew/bin/codex','exec']+opts+(['resume',session] if session else [])+[prompt]
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True,env=env); processes.append(p)
 if arm:(P/'armed.pid').write_text(str(p.pid))
 try:out,err=p.communicate(timeout=88); reason='exit'
 except subprocess.TimeoutExpired:stop(p);out,err=p.communicate();reason='timeout'
 (P/'armed.pid').unlink(missing_ok=True)
 events=[]; sid=None
 for raw in out.splitlines():
  try:v=json.loads(raw)
  except ValueError:continue
  it=v.get('item') or {}; typ=it.get('type'); row={'type':v.get('type')}
  if v.get('type')=='thread.started':sid=v.get('thread_id');row['thread_id']=sid
  if typ:
   row['item_type']=typ
   if typ=='command_execution':row.update(status=it.get('status'),exit_code=it.get('exit_code'),sentinel_seen='SYNTHETIC_SENTINEL_ORANGE_731' in str(it.get('aggregated_output','')))
   if typ=='agent_message':row['sentinel_seen']='SYNTHETIC_SENTINEL_ORANGE_731' in str(it.get('text',''))
  if v.get('type')=='turn.completed':row['usage']=v.get('usage')
  events.append(row)
 (P/(label+'-events.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in events))
 low=(out+' '+err).lower(); cats=[x for x in ('connection refused','stream disconnected','unexpected status','authentication','rate limit','timed out','failed to parse') if x in low]
 result={'label':label,'returncode':p.returncode,'reason':reason,'thread_id':sid,'events':events,'error_categories':cats,'stderr_bytes':len(err.encode()),'group_absent':gone(p)};results['turns'].append(result);(P/'result.json').write_text(json.dumps(results,indent=2));return result
try:
 gw=subprocess.Popen(['/opt/homebrew/bin/python3.11',str(P/'operator.py'),'serve'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True,env=env); processes.append(gw)
 if not select.select([gw.stdout],[],[],5)[0]:raise RuntimeError('gateway startup timeout')
 port=int(gw.stdout.readline());base=f'http://127.0.0.1:{port}/backend-api/codex'
 first=run('first',base,'Use a shell tool to read fixture.txt, then report its exact synthetic sentinel.')
 sid=first.get('thread_id'); assert first['returncode']==0 and sid and any(x.get('item_type')=='command_execution' and x.get('sentinel_seen') for x in first['events'])
 second=run('resume',base,'Without using a tool, repeat the exact synthetic sentinel from the fixture you read in the previous turn.',sid)
 sock=socket.socket(); sock.bind(('127.0.0.1',0)); bad=f'http://127.0.0.1:{sock.getsockname()[1]}/backend-api/codex'
 run('network-refused',bad,'Reply with one word.',sid); sock.close()
 run('network-recovery',base,'Reply with the word RECOVERED.',sid)
 run('interrupt',base,'Write a detailed numbered explanation of 80 different imaginary mechanical devices, with several sentences per device.',sid,True)
 run('interrupt-recovery',base,'Reply with the word RESUMED.',sid)
except Exception as e:results['operator_error']=type(e).__name__+': '+str(e)
finally:
 for p in reversed(processes):stop(p)
 results['owned_groups_absent']=all(gone(p) for p in processes)
 path=P/'receipts.private'; receipts=[]
 if path.exists():
  for line in path.read_text().splitlines():
   try:
    r=json.loads(line);receipts.append({k:r.get(k) for k in ('model_requested','model_observed','effort_transmitted','status','error','route','usage') if k in r})
   except ValueError:pass
  path.unlink()
 results['receipts']=receipts; (P/'result.json').write_text(json.dumps(results,indent=2)); print(json.dumps(results))
