import json, os, pathlib, signal, sys, threading, time
import psutil
sys.path.insert(0, '/home/operator/repos/open-model-router')
import hashlib, types
source=pathlib.Path('/home/operator/repos/open-model-router/omr.py').read_bytes()
digest=hashlib.sha256(source).hexdigest()
assert digest == '6670df32c589ea6a3324eeff79dd10e45c9eaddb5d62f8526c7bf3e5e0b33a3b'
omr=types.ModuleType('omr'); omr.__file__='/home/operator/repos/open-model-router/omr.py'; sys.modules['omr']=omr
exec(compile(source,omr.__file__,'exec'),omr.__dict__)
pathlib.Path(__file__).with_name('runtime-'+str(os.getpid())+'.json').write_text(json.dumps({'pid':os.getpid(),'source_sha256':digest,'source_file':omr.__file__,'execution':'same verified bytes compiled and executed in this process'}))
base = pathlib.Path(__file__).parent
line = next(i for i, s in enumerate(open(omr.__file__), 1) if 'event_frame.clear(); event_kind' in s)
fired = set()
def trace(frame, event, arg):
    global fired
    if event == 'line' and frame.f_code.co_filename == omr.__file__ and frame.f_code.co_name == 'do_POST' and frame.f_lineno == line:
        
        try: val = json.loads(frame.f_locals.get('event_data', b''))
        except (ValueError, TypeError): return trace
        choices = val.get('choices', []) if isinstance(val, dict) else []
        text = any(isinstance(c, dict) and isinstance(c.get('delta'), dict) and bool(c['delta'].get('content')) for c in choices) or (isinstance(val, dict) and val.get('type') == 'content_block_delta' and isinstance(val.get('delta'), dict) and val['delta'].get('type') == 'text_delta' and bool(val['delta'].get('text')))
        if text and (base/'armed.json').exists():
            armed=json.loads((base/'armed.json').read_text()); pid=armed['pid']
            sock=frame.f_locals.get('upstream_socket', [])
            upstream=[dict(local=list(c.laddr),remote=list(c.raddr),status=c.status,fd=c.fd) for c in psutil.Process().net_connections(kind='tcp') if sock and c.fd==sock[0].fileno() and c.raddr and c.raddr.ip=='10.77.0.11' and c.status=='ESTABLISHED']
            if not upstream or frame.f_locals.get('terminal_seen'): return trace
            if armed['name'] in fired: return trace
            fired.add(armed['name'])
            try: groups=sorted({os.getpgid(c.pid) for c in psutil.Process(pid).children()})
            except (psutil.Error, ProcessLookupError): groups=[]
            stamp=time.time_ns(); os.kill(pid,signal.SIGINT)
            (base/(armed['name']+'-marker.json')).write_text(json.dumps({'request_id':frame.f_locals['row']['request_id'],'session':frame.f_locals['row']['session'],'upstream_status':frame.f_locals['row']['upstream_status'],'event':'first_nonempty_chat_delta_after_flush','signal':'SIGINT','time_ns':stamp,'launcher_pid':pid,'child_groups':groups,'upstream_before':upstream,'terminal_seen':bool(frame.f_locals.get('terminal_seen'))},indent=2))
    return trace
threading.settrace(trace)
omr.main()
