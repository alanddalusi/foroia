"""Opt-in Caddy parser/provisioning regression; cached image and network=none."""
import json
import os
import shlex
from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('FOROIA_CADDY_TEST') != '1', reason='Requires isolated Docker and cached Caddy image')


def test_www_http_and_https_redirect_directly_to_canonical_preserving_uri():
    def docker(args, **kwargs):
        machine = os.environ.get('FOROIA_TEST_DOCKER_MACHINE')
        command = [machine, 'ssh', 'default', shlex.join(['docker', *args])] if machine else ['docker', *args]
        return subprocess.run(command, check=True, capture_output=True, timeout=45, **kwargs)
    image = 'caddy:2-alpine'
    # Never pull an image as a side effect of running this test.
    docker(['image', 'inspect', image])
    source = (Path(__file__).resolve().parents[1] / 'deploy/Caddyfile').read_bytes()
    result = docker(['run', '--rm', '-i', '--network', 'none', image,
                     'caddy', 'adapt', '--config', '/dev/stdin', '--adapter', 'caddyfile', '--validate'], input=source)
    servers = json.loads(result.stdout)['apps']['http']['servers'].values()
    matched = set()
    for server in servers:
        for route in server['routes']:
            if not any('www.foroiaaldia.com' in match.get('host', []) for match in route.get('match', [])):
                continue
            handlers = route['handle'][0]['routes'][0]['handle']
            redirect = next(h for h in handlers if h['handler'] == 'static_response')
            assert redirect['status_code'] in [301, 308]
            assert redirect['headers']['Location'] == ['https://foroiaaldia.com{http.request.uri}']
            matched.update(server['listen'])
    assert matched == {':80', ':443'}
