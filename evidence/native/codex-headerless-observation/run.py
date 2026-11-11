import hashlib, json, os, pathlib, secrets, signal, subprocess, time, uuid, select
root=pathlib.Path.home()/'omr-host-adapters-task/codex-native-20e7e00c-run1'
p=root/'full-stream-proof-1'; assert p.is_dir() and not (p/'result.json').exists(); os.chdir(p)
core=root/'attempt-accept/accept-omr.py'; digest=hashlib.sha256(core.read_bytes()).hexdigest(); assert digest=='ea79ee14a0f3085a479042eb0f5b7ab1848726104428c2ee3e24cff6065b15a4'
(p/'omr.py').symlink_to(core); (p/'project').mkdir(); (p/'project/fixture.txt').write_text('SYNTHETIC_SENTINEL_ORANGE_731\n')
cfg={'routes':{'native':{'url':'https://chatgpt.com/backend-api/codex','protocol':'responses','model':'gpt-6.1-terra','effort':'low','forward_auth':True}},'default_route':'native','decision':{'type':'fixed'},'gateway_key_env':'OMR_TEST_GATEWAY_KEY','receipts':str(p/'receipts.jsonl'),'timeout_seconds':88}
(p/'gateway.json').write_text(json.dumps(cfg)); os.chmod(p/'gateway.json',0o600)
env=os.environ.copy(); env['OMR_TEST_GATEWAY_KEY']=secrets.token_urlsafe(48); env['OMR_TEST_SESSION']=str(uuid.uuid4())
gw=proc=None

def stop(proc):
 if proc is None or proc.poll() is not None: return
 os.killpg(proc.pid,signal.SIGTERM)
 try: proc.wait(timeout=3)
 except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()

try:
 gw=subprocess.Popen(['/opt/homebrew/bin/python3.11',str(p/'observe.py'),'serve','--config',str(p/'gateway.json'),'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True,env=env)
 if not select.select([gw.stdout], [], [], 4)[0]: raise RuntimeError('gateway_start_timeout')
 port=int(gw.stdout.readline()); base=f'http://127.0.0.1:{port}/backend-api/codex'
 opts=['--ignore-user-config','--disable','enable_request_compression','--sandbox','read-only','--skip-git-repo-check','--json','-C',str(p/'project'),'-m','open-model-router','-c','project_doc_max_bytes=0','-c','model_provider="omr"','-c','model_providers.omr.name="OpenAI"','-c',f'model_providers.omr.base_url="{base}"','-c','model_providers.omr.requires_openai_auth=true','-c','model_providers.omr.supports_websockets=false','-c','model_providers.omr.request_max_retries=0','-c','model_providers.omr.stream_max_retries=0','-c','model_providers.omr.env_http_headers={"X-OMR-Gateway-Key"="OMR_TEST_GATEWAY_KEY","X-OMR-Session"="OMR_TEST_SESSION"}','-c','model_reasoning_effort="low"']
 with open(p/'stdout.private','w') as out, open(p/'stderr.private','w') as err:
  os.chmod(p/'stdout.private',0o600); os.chmod(p/'stderr.private',0o600)
  proc=subprocess.Popen(['/opt/homebrew/bin/codex','exec']+opts+['Read fixture.txt using a shell tool and report the synthetic sentinel.'],stdout=out,stderr=err,env=env,start_new_session=True)
  start=time.monotonic(); reason='exit'
  while proc.poll() is None:
   if time.monotonic()-start > 88: reason='timeout'; stop(proc); break
   ep=p/'proof.json'
   if ep.exists() and ep.stat().st_size:
    time.sleep(1); reason='capture_finished'; stop(proc); break
   time.sleep(.05)
  result={'reason':reason,'returncode':proc.returncode,'elapsed_seconds':round(time.monotonic()-start,2),'source_sha256':digest}
  (p/'result.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))
finally:
 stop(proc); stop(gw)
 print(json.dumps({'codex_reaped':proc is None or proc.poll() is not None,'gateway_reaped':gw is None or gw.poll() is not None}))
