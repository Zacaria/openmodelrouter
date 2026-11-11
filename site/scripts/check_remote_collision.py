"""Read-only building block for a future release gate; not a publication command."""
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_new_paths(origin, paths):
    if not paths:
        raise ValueError('no new download paths')
    opener = build_opener(NoRedirect)
    for path in paths:
        material = path in {'/assets/materials/0.3.2/', '/assets/materials/0.3.2/index.html', '/assets/materials/0.3.2/rebuild.tar'}
        if (not material and not path.startswith('/downloads/')) or '?' in path or '#' in path or '..' in path:
            raise ValueError('invalid download path')
        for suffix in (('',) if material else ('', '.sha256')):
            try:
                with opener.open(Request(origin + path + suffix, method='HEAD'), timeout=15):
                    raise ValueError('remote destination already exists or is ambiguous')
            except HTTPError as error:
                if error.code != 404:
                    raise ValueError('remote destination already exists or is ambiguous') from error
