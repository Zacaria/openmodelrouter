import http.client, http.server, importlib.util, threading, unittest, uuid
spec = importlib.util.spec_from_file_location('launch', __file__.replace('test_launch.py','launch.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Upstream(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        self.server.auth = (self.headers.get('Authorization'), self.headers.get('X-Api-Key'))
        self.server.observed = (self.path, self.headers.get('X-OMR-Session'), self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers(); self.wfile.write(b'data: test\n\ndata: [DONE]\n\n')

class Test(unittest.TestCase):
    def test_error_visibility_over_sockets(self):
        import contextlib, io, socket
        class Failure(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.send_response(503); self.send_header('X-Secret', 'header-secret'); self.end_headers(); self.wfile.write(b'body-secret')
        upstream = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Failure)
        proxy = m.Server(('127.0.0.1', 0), m.Proxy); proxy.session = str(uuid.uuid4()); proxy.upstream = upstream.server_port
        for server in (upstream, proxy): threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                for expected in (503, 502):
                    if expected == 502:
                        upstream.shutdown(); upstream.server_close()
                    c = http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=3)
                    c.request('POST', '/url-secret', b'{}', {'Authorization': 'Bearer token-secret'})
                    r = c.getresponse(); self.assertEqual(r.status, expected); r.read(); c.close()
            self.assertEqual(stderr.getvalue().splitlines(), ['OMR: upstream HTTP error 503', 'OMR: upstream HTTP error 502'])
        finally:
            proxy.shutdown(); proxy.server_close(); upstream.server_close()

    def test_upstream_connection_closed_on_failure(self):
        from unittest.mock import patch
        closed = threading.Event()
        class Broken:
            def __init__(self, *args, **kwargs): pass
            def request(self, *args): raise OSError('synthetic failure')
            def close(self): closed.set()
        proxy = m.Server(('127.0.0.1',0), m.Proxy); proxy.upstream = 1; proxy.session = str(uuid.uuid4())
        threading.Thread(target=proxy.serve_forever,daemon=True).start()
        try:
            import socket
            with patch.object(m.http.client, 'HTTPConnection', Broken):
                with socket.create_connection(('127.0.0.1', proxy.server_port)) as client:
                    client.sendall(b'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{}')
                    self.assertIn(b'502', client.recv(4096))
                self.assertTrue(closed.wait(2), 'upstream connection not closed after failure')
        finally: proxy.shutdown(); proxy.server_close()

    def test_session_and_stream(self):
        upstream = http.server.ThreadingHTTPServer(('127.0.0.1',0), Upstream)
        proxy = m.Server(('127.0.0.1',0), m.Proxy); proxy.upstream = upstream.server_port; proxy.session = str(uuid.uuid4())
        for s in (upstream,proxy): threading.Thread(target=s.serve_forever,daemon=True).start()
        try:
            c = http.client.HTTPConnection('127.0.0.1',proxy.server_port,timeout=3)
            c.request('POST','/v1/chat/completions',b'{}',{'X-OMR-Session':'spoofed'})
            r = c.getresponse(); self.assertEqual(r.status,200); self.assertEqual(r.read(),b'data: test\n\ndata: [DONE]\n\n')
            self.assertEqual(upstream.observed,('/v1/chat/completions',proxy.session,b'{}'))
            c.close()
        finally:
            for s in (proxy,upstream): s.shutdown(); s.server_close()
class ReplayTests(unittest.TestCase):
    def test_stable_port_and_override(self):
        import subprocess, sys, os, tempfile
        session = str(uuid.uuid4())
        env = os.environ.copy()
        with tempfile.TemporaryDirectory() as d:
            f = __import__('pathlib').Path(d, 'hermes')
            f.write_text('#!/bin/sh\nprintf "%s\n" "$*"\n'); f.chmod(0o755)
            env['PATH'] = d + os.pathsep + env['PATH']
            cmd = [sys.executable, '-B', 'host-adapters/launch.py', 'hermes', '--port', '12345', '--session', session, '--project', d]
            a = subprocess.check_output(cmd, env=env); b = subprocess.check_output(cmd, env=env)
            self.assertEqual(a, b)
            self.assertIn(b':45678/v1', subprocess.check_output(cmd + ['--proxy-port','45678'],env=env))

    def test_cancel_before_headers_closes_upstream(self):
        import socket, time
        upstream = socket.socket(); upstream.bind(('127.0.0.1',0)); upstream.listen()
        accepted = threading.Event(); closed = threading.Event()
        def stall():
            conn,_ = upstream.accept(); conn.settimeout(3); conn.recv(65536); accepted.set()
            try:
                while conn.recv(4096): pass
                closed.set()
            except OSError: pass
            conn.close()
        threading.Thread(target=stall, daemon=True).start()
        proxy = m.Server(('127.0.0.1',0),m.Proxy); proxy.upstream = upstream.getsockname()[1]; proxy.session = str(uuid.uuid4())
        threading.Thread(target=proxy.serve_forever,daemon=True).start()
        try:
            client = socket.create_connection(('127.0.0.1',proxy.server_port)); client.sendall(b'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{}')
            self.assertTrue(accepted.wait(2)); client.shutdown(socket.SHUT_RDWR); client.close()
            self.assertTrue(closed.wait(2), 'upstream socket left open after client cancellation')
        finally: proxy.shutdown(); proxy.server_close(); upstream.close()

    def test_collision_fails_and_auth_is_stripped(self):
        import socket, subprocess, sys, tempfile
        upstream = http.server.ThreadingHTTPServer(('127.0.0.1',0), Upstream)
        proxy = m.Server(('127.0.0.1',0),m.Proxy); proxy.upstream=upstream.server_port; proxy.session=str(uuid.uuid4())
        for server in (upstream,proxy): threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as d:
                cmd=[sys.executable,'-B','host-adapters/launch.py','hermes','--port',str(upstream.server_port),'--session',proxy.session,'--project',d,'--proxy-port',str(proxy.server_port)]
                self.assertNotEqual(subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode,0)
            c=http.client.HTTPConnection('127.0.0.1',proxy.server_port); c.request('POST','/',b'{}',{'Authorization':'Bearer real-secret','X-Api-Key':'real-secret'}); c.getresponse().read(); c.close()
            self.assertEqual(upstream.auth, (None,None))
        finally:
            for server in (proxy,upstream): server.shutdown(); server.server_close()

    def test_signal_reaps_process_group(self):
        import os, signal, subprocess, sys, tempfile, time, pathlib
        with tempfile.TemporaryDirectory() as d:
            script=pathlib.Path(d,'hermes'); pidfile=pathlib.Path(d,'pid')
            script.write_text('#!/bin/sh\nsleep 60 &\necho $! > "'+str(pidfile)+'"\nwait\n'); script.chmod(0o755)
            env=os.environ.copy(); env['PATH']=d+os.pathsep+env['PATH']
            p=subprocess.Popen([sys.executable,'-B','host-adapters/launch.py','hermes','--port','12345','--session',str(uuid.uuid4()),'--project',d],env=env)
            try:
                for _ in range(100):
                    if pidfile.exists(): break
                    time.sleep(.05)
                self.assertTrue(pidfile.exists()); pid=int(pidfile.read_text()); p.send_signal(signal.SIGTERM); self.assertEqual(p.wait(timeout=5),143)
                # A reparented zombie is dead, not an executing orphan.
                stat=pathlib.Path('/proc',str(pid),'stat')
                self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')
            finally:
                if p.poll() is None: p.kill(); p.wait()

class BudgetTests(unittest.TestCase):
    def test_timeout_kills_group_and_recovers(self):
        import os, pathlib, subprocess, sys, tempfile, time
        with tempfile.TemporaryDirectory() as d:
            script = pathlib.Path(d, 'hermes'); pidfile = pathlib.Path(d, 'pid')
            script.write_text('#!/bin/sh\ntrap "" TERM\nsleep 60 &\necho $! > "' + str(pidfile) + '"\nwait\n'); script.chmod(0o755)
            env = os.environ.copy(); env['PATH'] = d + os.pathsep + env['PATH']
            cmd = [sys.executable, '-B', 'host-adapters/launch.py', 'hermes', '--port', '12345', '--session', str(uuid.uuid4()), '--project', d, '--run-timeout', '0.3']
            result = subprocess.run(cmd, env=env, capture_output=True, timeout=6)
            self.assertEqual(result.returncode, 124, result.stderr)
            self.assertIn(b'run timeout', result.stderr.lower())
            pid = int(pidfile.read_text()); stat = pathlib.Path('/proc', str(pid), 'stat')
            self.assertTrue(not stat.exists() or stat.read_text().split()[2] == 'Z')
            script.write_text('#!/bin/sh\nexit 0\n')
            self.assertEqual(subprocess.run(cmd, env=env, capture_output=True, timeout=5).returncode, 0)
    def test_omp_limits_and_validation(self):
        import os, pathlib, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            script = pathlib.Path(d, 'omp'); script.write_text('#!/bin/sh\ncat "$PI_CODING_AGENT_DIR/models.yml"\n'); script.chmod(0o755)
            cmd = [sys.executable, '-B', 'host-adapters/launch.py', 'omp', '--port', '1', '--session', str(uuid.uuid4()), '--project', d, '--omp-bin', str(script)]
            r = subprocess.run(cmd, capture_output=True); self.assertIn(b'contextWindow: 8192', r.stdout); self.assertIn(b'maxTokens: 2048', r.stdout)
            r = subprocess.run(cmd + ['--context-window','100','--max-output-tokens','101'], capture_output=True); self.assertNotEqual(r.returncode, 0)
            r = subprocess.run(cmd + ['--run-timeout','0'], capture_output=True); self.assertNotEqual(r.returncode, 0)

if __name__ == '__main__': unittest.main()
