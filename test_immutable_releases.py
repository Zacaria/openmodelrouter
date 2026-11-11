"""Deterministic checks for the immutable-release setting reader."""
import subprocess
import unittest
from unittest.mock import patch

from ci.check_immutable_releases import check_setting


class ImmutableReleaseTests(unittest.TestCase):
    @patch('ci.check_immutable_releases.subprocess.run')
    def test_enabled_only(self, run):
        run.return_value.stdout = '{"enabled":true,"enforced_by_owner":false}'
        check_setting('example/project')
        self.assertEqual(run.call_args.args[0], ['gh', 'api', 'repos/example/project/immutable-releases'])
        for body in ('{"enabled":false}', '{}', '{"enabled":"true"}', 'garbage', '[]'):
            run.return_value.stdout = body
            with self.subTest(body=body), self.assertRaises(ValueError):
                check_setting('example/project')
        for repo in ('', '../project', 'a/b/c', '-x/y', 'a?x/b'):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                check_setting(repo)
        run.side_effect = subprocess.CalledProcessError(1, 'gh')
        with self.assertRaises(ValueError):
            check_setting('example/project')
        run.side_effect = subprocess.TimeoutExpired('gh', 15)
        with self.assertRaises(ValueError):
            check_setting('example/project')


if __name__ == '__main__':
    unittest.main()
