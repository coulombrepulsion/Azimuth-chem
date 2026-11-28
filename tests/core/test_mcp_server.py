"""tools/azimuth_mcp.py — the protocol of MCP over stdio, through a pipe as a client speaks it.

Oracles: JSON-RPC 2.0 (an answer per request with its id, none for a notification, -32601 for an unknown method,
-32700 for a broken line) and the stdio transport of the Model Context Protocol (one JSON message per line;
initialize answers the version of the client, tools/list, tools/call with content and isError).
"""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[2]


def talk(*messages):
    lines = '\n'.join(m if isinstance(m, str) else json.dumps(m) for m in messages) + '\n'
    run = subprocess.run([sys.executable, str(ROOT / 'tools' / 'azimuth_mcp.py')], input=lines, capture_output=True,
                         text=True, encoding='utf-8', timeout=120, cwd=ROOT)
    return [json.loads(line) for line in run.stdout.splitlines()]


def test_the_protocol_through_a_pipe():
    answers = talk(
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                                                                       'clientInfo': {'name': 'test', 'version': '0'}}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
         'params': {'name': 'azimuth_preview_input',
                    'arguments': {'program': 'orca', 'molecule': {'smiles': 'O'}, 'settings': {'task': 'Энергия'}}}},
        {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'azimuth_options',
                                                                       'arguments': {'program': 'nope'}}},
        {'jsonrpc': '2.0', 'id': 5, 'method': 'bogus'},
        'not json',
        {'jsonrpc': '2.0', 'id': 6, 'method': 'ping'},
    )
    by_id = {a['id']: a for a in answers}
    assert [a['id'] for a in answers] == [1, 2, 3, 4, 5, None, 6]  # nothing for the notification
    assert by_id[1]['result']['protocolVersion'] == '2025-06-18' and 'tools' in by_id[1]['result']['capabilities']
    names = {t['name'] for t in by_id[2]['result']['tools']}
    assert {'azimuth_run', 'azimuth_status', 'azimuth_result', 'azimuth_tests', 'azimuth_preview_input'} <= names
    assert all('inputSchema' in t for t in by_id[2]['result']['tools'])
    # the server of SLURM (azimuth/headless_server.py): its three tools, and only ORCA, MOPAC and xtb are offered there
    assert {'azimuth_server', 'azimuth_run_server', 'azimuth_server_resume', 'azimuth_crystal_run_server'} <= names
    # the open window (azimuth/window_control.py): what it can be asked, nothing more
    assert {n for n in names if n.startswith('azimuth_window_')} == {'azimuth_window_state', 'azimuth_window_show',
                                                                    'azimuth_window_select', 'azimuth_window_snapshot'}
    remote = next(t for t in by_id[2]['result']['tools'] if t['name'] == 'azimuth_run_server')
    assert remote['inputSchema']['properties']['program']['enum'] == ['orca', 'mopac', 'xtb']
    assert not any('password' in t['inputSchema'].get('properties', {}) for t in by_id[2]['result']['tools'])  # the key only
    preview = by_id[3]['result']
    assert not preview['isError'] and '! B3LYP D3BJ def2-SVP' in preview['content'][0]['text']  # the D3(BJ) of a new window
    assert by_id[4]['result']['isError'] and 'unknown program' in by_id[4]['result']['content'][0]['text']
    assert by_id[5]['error']['code'] == -32601 and by_id[None]['error']['code'] == -32700
    assert by_id[6]['result'] == {}
