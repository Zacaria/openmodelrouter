"""Read the GitHub immutable-release setting; never change it."""
import argparse
import json
import re
import subprocess


def check_setting(repo):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', repo):
        raise ValueError('invalid repository')
    try:
        response = subprocess.run(
            ['gh', 'api', f'repos/{repo}/immutable-releases'],
            check=True, capture_output=True, text=True, timeout=15,
        )
        state = json.loads(response.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise ValueError('cannot read immutable-release setting') from error
    if not isinstance(state, dict) or state.get('enabled') is not True:
        raise ValueError('immutable releases are not confirmed enabled')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', help='GitHub OWNER/REPO')
    args = parser.parse_args()
    try:
        check_setting(args.repo)
    except ValueError as error:
        parser.exit(1, f'preflight refused: {error}\n')
    print('Immutable releases enabled; drafts, arbitrary tags and notes are not protected by this check.')


if __name__ == '__main__':
    main()
