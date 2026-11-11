import os, subprocess, time, threading, urllib.request, json, signal, re
from pathlib import Path
p=Path.home()/'omr-native-mac-20261027'/'pass3'; os.chdir(p)
env=os.environ.copy(); env.update(OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(p/'models'),OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_KEEP_ALIVE='30s',OLLAMA_CONTEXT_LENGTH='8192', TMPDIR=str(p))
bin=str(Path.home()/'omr-native-mac-20261027/runtime/ollama')
log=open('ollama.log','w'); server=subprocess.Popen([bin,'serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print('owned server',server.pid,flush=True)
stop=threading.Event(); bad=threading.Event()
def monitor():
 baseline=None
 while not stop.is_set():
  a=subprocess.run(['memory_pressure'],capture_output=True,text=True).stdout; b=subprocess.run(['vm_stat'],capture_output=True,text=True).stdout; s=subprocess.run(['sysctl','vm.swapusage'],capture_output=True,text=True).stdout.strip()
  m=re.search(r'free percentage: (\d+)%',a); q=re.search(r'Swapouts:\s*(\d+)',b); free=int(m.group(1)) if m else -1; swap=int(q.group(1)) if q else -1
  if baseline is None: baseline=swap
  print('guard',time.strftime('%FT%T%z'),free,swap,s,flush=True)
  if free<20 or swap<0 or swap-baseline>16384:
   print('GUARD STOP',flush=True); bad.set(); os.killpg(server.pid,signal.SIGTERM); return
  stop.wait(5)
t=threading.Thread(target=monitor,daemon=True); t.start()
try:
 for _ in range(30):
  if bad.is_set(): raise RuntimeError('guard stopped server')
  try: urllib.request.urlopen('http://127.0.0.1:11435/',timeout=1); break
  except Exception: time.sleep(1)
 else: raise RuntimeError('server unavailable')
 with open('pull.log','w') as pl:
  pull=subprocess.Popen([bin,'pull','qwen3:1.7b'],env=env,stdout=pl,stderr=subprocess.STDOUT)
  start=time.time()
  while pull.poll() is None and not bad.is_set() and time.time()-start<1200: time.sleep(2)
  if pull.poll() is None: pull.terminate(); pull.wait(timeout=15)
  print('pull exit',pull.returncode,flush=True)
  if pull.returncode or bad.is_set(): raise RuntimeError('pull did not complete safely')
 print('show',urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11435/api/show',data=json.dumps({'model':'qwen3:1.7b'}).encode(),headers={'Content-Type':'application/json'}),timeout=15).read().decode()[:8000],flush=True)
 payload={'model':'qwen3:1.7b','messages':[{'role':'user','content':'Use the read_fixture tool to read the fixture, then answer using the result. /no_think'}], 'tools':[{'type':'function','function':{'name':'read_fixture','description':'Read the fixture','parameters':{'type':'object','properties':{},'required':[]}}}], 'stream':False,'think':False,'keep_alive':'30s','options':{'num_ctx':8192,'num_predict':128}}
 req=urllib.request.Request('http://127.0.0.1:11435/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=240) as r: print('chat',r.read().decode(),flush=True)
finally:
 stop.set(); t.join(timeout=10)
 if server.poll() is None: os.killpg(server.pid,signal.SIGTERM)
 try: server.wait(timeout=20)
 except subprocess.TimeoutExpired: print('server did not stop',flush=True)
 print('server exit',server.poll(),flush=True); log.close()
