import collections, http.client, json, math, socket, ssl, threading, time
import omr

LIMIT = 16 * 1024 * 1024
KNOWN = {'response.created','response.in_progress','response.completed','response.incomplete','response.failed','response.output_item.added','response.output_item.done','response.content_part.added','response.content_part.done','response.output_text.delta','response.output_text.done','response.function_call_arguments.delta','response.function_call_arguments.done','response.reasoning_summary_part.added','response.reasoning_summary_part.done','response.reasoning_summary_text.delta','response.reasoning_summary_text.done','response.reasoning_text.delta','response.reasoning_text.done','error'}
TERMINAL = {'response.completed','response.incomplete','response.failed','error'}

def parse(data, model):
    out = {'bytes':len(data), 'json_valid':True, 'first_event':'absent', 'terminal':'absent', 'model_equal_config':None, 'tool_calls':0, 'event_counts':{}, 'usage':{}, 'complete_sse':False}
    try:
        text = data.decode('utf-8')
        if text.lstrip().lower().startswith(('<!doctype html','<html','<head','<body')): out['failure']='html'; return out
        text = text.replace('\r\n','\n').replace('\r','\n')
        if not text.endswith('\n\n'): out['failure']='incomplete_frame'; return out
        counts=collections.Counter(); seen_terminal=False; frames=0
        for frame in text.split('\n\n'):
            if not frame: continue
            fields=[]; kind=None
            for line in frame.split('\n'):
                if line.startswith(':'): continue
                field, sep, value = line.partition(':')
                if sep and value.startswith(' '): value=value[1:]
                if field == 'data': fields.append(value)
                elif field == 'event': kind=value
                elif field not in ('id','retry'): raise ValueError('field')
            if not fields: continue
            obj=json.loads('\n'.join(fields), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
            if not isinstance(obj,dict): raise ValueError('object')
            typ=obj.get('type')
            if not isinstance(typ,str) or (kind and kind != typ): raise ValueError('type')
            if seen_terminal: raise ValueError('after_terminal')
            label=typ if typ in KNOWN else 'other'; counts[label]+=1; frames+=1
            if frames == 1: out['first_event']=label
            if typ in TERMINAL: seen_terminal=True; out['terminal']=typ
            resp=obj.get('response')
            if isinstance(resp,dict):
                if 'model' in resp:
                    eq=resp['model']==model
                    out['model_equal_config']=eq if out['model_equal_config'] is None else out['model_equal_config'] and eq
                usage=resp.get('usage')
                if isinstance(usage,dict):
                    for k in ('input_tokens','output_tokens','total_tokens'):
                        v=usage.get(k)
                        if type(v) in (int,float) and math.isfinite(v) and v>=0: out['usage'][k]=v
            item=obj.get('item')
            if typ=='response.output_item.done' and isinstance(item,dict) and item.get('type')=='function_call': out['tool_calls']+=1
        out['event_counts']=dict(sorted(counts.items()))
        out['complete_sse']=frames>0 and seen_terminal
        if not out['complete_sse']: out['failure']='missing_terminal'
        elif out['terminal'] != 'response.completed': out['failure']='native_error_or_incomplete'
    except (ValueError,UnicodeError,TypeError): out['json_valid']=False; out['failure']='invalid_sse_or_json'
    return out

def emit(obj):
    with open('proof.json','w') as f: json.dump(obj,f,sort_keys=True,indent=2)

def trace(frame,event,arg):
    if frame.f_code.co_filename != omr.__file__ or frame.f_code.co_name != 'do_POST': return trace
    if event=='exception' and isinstance(arg[1],ValueError) and str(arg[1])=='expected SSE response':
        r=frame.f_locals.get('response'); c=frame.f_locals.get('connection'); route=frame.f_locals.get('route',{})
        meta={'clientrejected_by_unchanged_guard':True,'status':r.status,'content_type_absent':r.getheader('Content-Type') is None,'content_encoding_absent':r.getheader('Content-Encoding') is None,'endpoint_pinned':route.get('url')=='https://chatgpt.com/backend-api/codex','direct_original_https':type(c) is http.client.HTTPSConnection and c.host=='chatgpt.com' and c.port==443 and isinstance(c.sock,ssl.SSLSocket) and c.sock.context.verify_mode==ssl.CERT_REQUIRED and c.sock.context.check_hostname,'redirect_followed':False,'body_forwarded_to_client':False,'capture':'failed'}
        if not meta['endpoint_pinned'] or not meta['direct_original_https'] or not meta['content_type_absent']:
            meta['failure']='prerequisite'; emit(meta); return trace
        try:
            deadline=time.monotonic()+80; data=bytearray()
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise TimeoutError()
                c.sock.settimeout(remaining)
                chunk=r.read1(min(16384,LIMIT+1-len(data)))
                if not chunk: break
                data.extend(chunk)
                if len(data)>LIMIT: raise OverflowError()
            meta.update(parse(bytes(data),route['model'])); meta['capture']='eof'
        except (TimeoutError,socket.timeout): meta['failure']='deadline'
        except OverflowError: meta['failure']='size_limit'
        except Exception: meta['failure']='read_error'
        emit(meta)
    return trace

if __name__=='__main__':
    threading.settrace(trace)
    original=omr.handler
    def wrapped(config):
        cls=original(config); old=cls.do_POST; reply=cls.reply; lock=threading.Lock(); count=0
        def post(self):
            nonlocal count
            with lock: count+=1; n=count
            if n>1: return reply(self,429,b'{}')
            return old(self)
        cls.do_POST=post
        return cls
    omr.handler=wrapped
    omr.main()
