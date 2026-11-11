import json, os, pathlib, signal, sys, threading, time
import psutil
sys.path.insert(0, '/home/operator/repos/open-model-router')
import omr
base = pathlib.Path(__file__).parent
line = next(i for i, s in enumerate(open(omr.__file__), 1) if 'event_frame.clear(); event_kind' in s)
fired = set()
def trace(frame, event, arg):
    global fired
    if event == 'line' and frame.f_code.co_filename == omr.__file__ and frame.f_code.co_name == 'do_POST' and frame.f_lineno == line:
        val = frame.f_locals.get('event')
        choices = val.get('choices', []) if isinstance(val, dict) else []
        text = any(isinstance(c, dict) and isinstance(c.get('delta'), dict) and bool(c['delta'].get('content')) for c in choices) or (isinstance(val, dict) and val.get('type') == 'content_block_delta' and isinstance(val.get('delta'), dict) and val['delta'].get('type') == 'text_delta' and bool(val['delta'].get('text')))
        if text and (base/'armed.json').exists():
            armed=json.loads((base/'armed.json').read_text()); pid=armed['pid']
            upstream=[dict(local=list(c.laddr),remote=list(c.raddr),status=c.status) for c in psutil.Process().net_connections(kind='tcp') if c.raddr and c.raddr.ip=='10.77.0.11' and c.status=='ESTABLISHED']
            if not upstream or frame.f_locals.get('terminal_seen'): return trace
            if armed['name'] in fired: return trace
            fired.add(armed['name'])
            try: groups=sorted({os.getpgid(c.pid) for c in psutil.Process(pid).children()})
            except (psutil.Error, ProcessLookupError): groups=[]
            stamp=time.time_ns(); os.kill(pid,signal.SIGINT)
            (base/(armed['name']+'-marker.json')).write_text(json.dumps({'event':'first_nonempty_chat_delta_after_flush','signal':'SIGINT','time_ns':stamp,'launcher_pid':pid,'child_groups':groups,'upstream_before':upstream,'terminal_seen':bool(frame.f_locals.get('terminal_seen'))},indent=2))
    return trace
threading.settrace(trace)
omr.main()
