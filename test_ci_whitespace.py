"""Exercise the CI whitespace step against disposable local Git histories."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


WORKFLOW = Path(__file__).parent / '.github/workflows/tests.yml'


def whitespace_command():
    text = WORKFLOW.read_text()
    match = re.search(r'^      - name: Check whitespace\n        run: (?:\|\n((?:          .*\n)+)|([^\n]+))', text, re.MULTILINE)
    if not match:
        raise AssertionError('Could not find the CI whitespace command')
    return '\n'.join(line[10:] for line in match.group(1).splitlines()) if match.group(1) else match.group(2)


class WhitespaceCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')
        self.git('init', '-q')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env,
                              text=True, capture_output=True, check=True)

    def commit(self, content):
        (self.repo / 'sample.txt').write_text(content)
        self.git('add', 'sample.txt')
        self.git('commit', '-qm', 'fixture')

    def check_step(self):
        return subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', whitespace_command()],
                              cwd=self.repo, env=self.env, text=True, capture_output=True)

    def test_clean_root(self):
        self.commit('clean\n')
        result = self.check_step()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clean_successor(self):
        self.commit('clean\n')
        self.commit('clean\nnext\n')
        result = self.check_step()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_whitespace_in_root_is_rejected(self):
        self.commit('bad  \n')
        result = self.check_step()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('trailing whitespace', result.stdout)

    def test_whitespace_in_successor_is_rejected(self):
        self.commit('clean\n')
        self.commit('clean\nbad  \n')
        result = self.check_step()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('trailing whitespace', result.stdout)

    def test_whitespace_in_successor_worktree_is_rejected(self):
        self.commit('clean\n')
        self.commit('clean\nnext\n')
        (self.repo / 'sample.txt').write_text('clean\nnext\nbad  \n')
        result = self.check_step()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('trailing whitespace', result.stdout)


if __name__ == '__main__':
    unittest.main()
