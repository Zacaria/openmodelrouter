import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_remote_collision.py'


class Handler(BaseHTTPRequestHandler):
    status = 404
    paths = []
    checksum_exists = False

    def do_HEAD(self):
        self.paths.append(self.path)
        status = 200 if getattr(self, 'checksum_exists', False) and self.path.endswith('.sha256') else self.status
        self.send_response(status)
        if status == 302:
            self.send_header('Location', '/redirected')
        self.end_headers()

    def log_message(self, format, *args):
        pass


class RemoteCollisionTest(unittest.TestCase):
    def test_only_exact_r15_source_routes_are_allowed(self):
        spec = importlib.util.spec_from_file_location('remote_collision', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        Handler.status, Handler.paths = 404, []
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            origin = f'http://127.0.0.1:{server.server_port}'
            paths = ['/assets/materials/0.3.2/', '/assets/materials/0.3.2/index.html', '/assets/materials/0.3.2/rebuild.tar']
            module.check_new_paths(origin, paths)
            self.assertEqual(Handler.paths, paths)
            with self.assertRaises(ValueError): module.check_new_paths(origin, ['/assets/materials/0.3.2/other.tar'])
            Handler.status = 200
            with self.assertRaises(ValueError): module.check_new_paths(origin, [paths[0]])
        finally:
            server.shutdown(); server.server_close(); worker.join()

    def test_connection_failure_is_not_treated_as_absent(self):
        spec = importlib.util.spec_from_file_location('remote_collision', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        port = server.server_port
        server.server_close()
        with self.assertRaises(OSError):
            module.check_new_paths(f'http://127.0.0.1:{port}',
                                   ['/downloads/1.2.3/omr-1.2.3-linux-x64.deb'])

    def test_existing_checksum_is_a_collision(self):
        spec = importlib.util.spec_from_file_location('remote_collision', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        Handler.status, Handler.checksum_exists = 404, True
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with self.assertRaises(ValueError):
                module.check_new_paths(f'http://127.0.0.1:{server.server_port}',
                                       ['/downloads/1.2.3/omr-1.2.3-linux-x64.deb'])
        finally:
            Handler.checksum_exists = False
            server.shutdown()
            server.server_close()
            worker.join()

    def test_rejects_existing_and_ambiguous_responses(self):
        self.assertTrue(SCRIPT.is_file(), 'remote collision guard not implemented')
        spec = importlib.util.spec_from_file_location('remote_collision', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for status in (200, 302, 403, 500):
            with self.subTest(status=status):
                Handler.status = status
                server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    with self.assertRaises(ValueError):
                        module.check_new_paths(f'http://127.0.0.1:{server.server_port}',
                                               ['/downloads/1.2.3/omr-1.2.3-linux-x64.deb'])
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join()

    def test_absent_package_and_checksum_are_checked(self):
        self.assertTrue(SCRIPT.is_file(), 'remote collision guard not implemented')
        spec = importlib.util.spec_from_file_location('remote_collision', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        Handler.status, Handler.paths = 404, []
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            module.check_new_paths(f'http://127.0.0.1:{server.server_port}',
                                   ['/downloads/1.2.3/omr-1.2.3-linux-x64.deb'])
            self.assertEqual(Handler.paths, ['/downloads/1.2.3/omr-1.2.3-linux-x64.deb',
                                             '/downloads/1.2.3/omr-1.2.3-linux-x64.deb.sha256'])
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
