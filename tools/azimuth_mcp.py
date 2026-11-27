"""Azimuth as an MCP server (stdio): a language model — Claude, or a local one through an MCP client — prepares and runs
calculations, reads their results and runs the checks of the program, by the commands of azimuth/headless.py.

§1 USE
    .venv/bin/python tools/azimuth_mcp.py — speaks JSON-RPC 2.0, one message per line on stdin and stdout (the stdio
    transport of the Model Context Protocol); everything else goes to stderr. Registered in a client as
        {"command": "<program folder>/.venv/bin/python", "args": ["<program folder>/tools/azimuth_mcp.py"]}
    (docs/features/HEADLESS.md). Windows: .venv\\Scripts\\python.exe tools\\azimuth_mcp.py.
§2 RULES
    1. Methods: initialize (the protocol version of the client is answered back), tools/list, tools/call, ping;
       notifications get no answer; an unknown method — error -32601.
    2. A tool answers JSON as text; a ValueError of the command is a tool result with isError (the model reads why),
       any other exception too, with its type — the server goes on.
    3. Only what TOOLS declares can be done: programs of Sextant on this computer, tools/test.py with safe options,
       and — the owner, 2026-11-22 — one calculation of ORCA or MOPAC sent to the SLURM server of a profile of
       Sextant (azimuth/headless_server.py: the login by the key only, never a password; the cores and the memory
       of a queue of SLURM — those asked for, of a server without it — within what is free; a time limit; a journal; stop is
       scancel of its own job). Nothing is deleted, nothing is pushed, no command of the model is run on the server.
    4. The paths of the programs chosen in «Настройки → Программы» are read from the settings of Azimuth when
       PySide6 is there (QtCore only, no window); without it the programs are searched as Sextant searches them.
§7 TESTS tests/core/test_mcp_server.py (the protocol through a pipe, the tools on the test data).
"""

import contextlib
import io
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from azimuth import headless  # noqa: E402

NAME, VERSION = 'azimuth', '1'
MOLECULE = {
    'type': 'object',
    'description': 'One of: {"smiles": "CC=O"}, {"xyz": "<text of an XYZ file>"}, {"path": "<structure file>"}; '
                   'optional "title".',
    'properties': {'smiles': {'type': 'string'}, 'xyz': {'type': 'string'}, 'path': {'type': 'string'},
                   'title': {'type': 'string'}},
}
SETTINGS = {
    'type': 'object',
    'description': 'Fields of the calculation of Sextant, e.g. {"method": "B3LYP", "basis": "def2-SVP", "task": '
                   '"Оптимизация + частоты", "charge": 0, "multiplicity": 1, "cores": 4, "memory_mb": 1000, '
                   '"solvent": "water", "dispersion": "D3BJ"}; tasks, methods and bases — azimuth_options.',
}
PROGRAM = {'type': 'string', 'enum': ['orca', 'gaussian', 'psi4', 'xtb', 'crest', 'mopac', 'gamess', 'nwchem']}
TOOLS = [
    {'name': 'azimuth_programs', 'description': 'Which calculation programs are installed on this computer.',
     'inputSchema': {'type': 'object', 'properties': {}}},
    {'name': 'azimuth_options', 'description': 'The tasks, methods, basis sets, solvents and dispersions a program '
                                               'can be asked for in Azimuth.',
     'inputSchema': {'type': 'object', 'properties': {'program': PROGRAM}, 'required': ['program']}},
    {'name': 'azimuth_preview_input', 'description': 'The input file Sextant would write for a molecule and settings '
                                                     '(nothing is run). Use it before azimuth_run.',
     'inputSchema': {'type': 'object', 'properties': {'program': PROGRAM, 'molecule': MOLECULE, 'settings': SETTINGS},
                     'required': ['program', 'molecule']}},
    {'name': 'azimuth_run', 'description': 'Start a calculation on this computer (in the folder of the calculations '
                                           'of Azimuth). Returns a job id; follow it with azimuth_status.',
     'inputSchema': {'type': 'object', 'properties': {'program': PROGRAM, 'molecule': MOLECULE, 'settings': SETTINGS},
                     'required': ['program', 'molecule']}},
    {'name': 'azimuth_status', 'description': 'The state of a job (calculation or tests): running or finished, its '
                                              'progress, the end of its output; for a finished calculation — its result.',
     'inputSchema': {'type': 'object', 'properties': {'job': {'type': 'string'}, 'lines': {'type': 'integer'}},
                     'required': ['job']}},
    {'name': 'azimuth_stop', 'description': 'Stop a job started here.',
     'inputSchema': {'type': 'object', 'properties': {'job': {'type': 'string'}}, 'required': ['job']}},
    {'name': 'azimuth_jobs', 'description': 'The jobs started by this server.',
     'inputSchema': {'type': 'object', 'properties': {}}},
    {'name': 'azimuth_result', 'description': 'Read an output (or the folder of a calculation): energy, convergence, '
                                              'frequencies, thermochemistry, excitations, problems and the remedies '
                                              'of the doctor of Sextant.',
     'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']}},
    {'name': 'azimuth_server', 'description': 'What the SLURM server of a profile of Sextant says now (login by the '
                                              'SSH key only): free cores and memory, the most one calculation may '
                                              'ask (with SLURM a job asking more than is free waits in the queue), '
                                              'ORCA and MOPAC found there, the calculations sent from here and '
                                              'still open. Call it before azimuth_run_server.',
     'inputSchema': {'type': 'object', 'properties': {'server': {'type': 'string', 'description': 'The title of a '
                     'profile; without it — the one chosen in Azimuth.'}}}},
    {'name': 'azimuth_run_server', 'description': 'Send one calculation of ORCA or MOPAC to the server (sbatch; a '
                                                  'server without SLURM — nohup, only on free cores) and watch it: a '
                                                  'job id for azimuth_status and azimuth_stop (the end of this job '
                                                  'alone). With SLURM the job is queued: cores — those asked for '
                                                  '(default 8), at most 80 % of the node for one job; more than are '
                                                  'free — it waits (waits_in_queue). Without SLURM: at most what is '
                                                  'free, no more than 80 % of the node busy, at most 3 calculations '
                                                  'at once. memory_mb per process (default 2000), hours — the time '
                                                  'limit when the profile has none (default 4, at most 24). The cores '
                                                  'and memory of settings are replaced by these.',
     'inputSchema': {'type': 'object', 'properties': {
         'program': {'type': 'string', 'enum': ['orca', 'mopac']}, 'molecule': MOLECULE, 'settings': SETTINGS,
         'server': {'type': 'string'}, 'cores': {'type': 'integer'}, 'memory_mb': {'type': 'integer'},
         'hours': {'type': 'integer'}}, 'required': ['program', 'molecule']}},
    {'name': 'azimuth_server_resume', 'description': 'Watch again a calculation sent to a server from here before this '
                                                     'server process was restarted (its folder is in azimuth_server → '
                                                     'calculations_open): nothing is sent again; returns a job id.',
     'inputSchema': {'type': 'object', 'properties': {'folder': {'type': 'string'}}, 'required': ['folder']}},
    {'name': 'azimuth_tests', 'description': 'Run the checks of the program: tools/test.py affected (the tests of '
                                             'what changed — after a small change) | quick | area <name> | full | '
                                             'isolated | list (full takes about 20 minutes, before a push). Returns a job id; follow '
                                             'it with azimuth_status. options: pytest options after «--», e.g. ["-x", '
                                             '"-k", "crystal"] or a test file under tests/.',
     'inputSchema': {'type': 'object', 'properties': {
         'profile': {'type': 'string', 'enum': list(headless.PROFILES)}, 'area': {'type': 'string'},
         'options': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['profile']}},
]


def configured_programs():
    """{kind: path} chosen in «Настройки → Программы» of Azimuth, when its settings can be read here."""
    try:
        from azimuth.settings import open_settings
    except ImportError:
        return {}
    try:
        settings = open_settings()
        return {k: settings.value(f'programs/{k}', '') or None for k in PROGRAM['enum']}
    except Exception:  # noqa: BLE001 — no Qt, or a broken store: search as Sextant does
        return {}


def settings_store():
    """The settings of Azimuth (the server profiles of Sextant are there); ValueError when they cannot be opened."""
    try:
        from azimuth.settings import open_settings

        return open_settings()
    except Exception as exc:  # noqa: BLE001 — no PySide6 here, or a broken store
        raise ValueError(f'the settings of Azimuth cannot be read here ({type(exc).__name__}: {exc}) — the server '
                         'profiles are kept in them') from None


class Server:
    def __init__(self):
        self.jobs = headless.Jobs()
        self.configured = configured_programs()

    def call(self, name, args):
        if name == 'azimuth_programs':
            return headless.programs(self.configured)
        if name == 'azimuth_options':
            return headless.options(args['program'])
        if name == 'azimuth_preview_input':
            return headless.preview(args['program'], args['molecule'], args.get('settings'))
        if name == 'azimuth_run':
            return self.jobs.start_calculation(args['program'], args['molecule'], args.get('settings'),
                                               configured=self.configured)
        if name == 'azimuth_status':
            return self.jobs.status(args['job'], int(args.get('lines', 40)))
        if name == 'azimuth_stop':
            return self.jobs.stop(args['job'])
        if name == 'azimuth_jobs':
            return self.jobs.listing()
        if name == 'azimuth_result':
            return headless.result(args['path'])
        if name == 'azimuth_server':
            from azimuth import headless_server

            return headless_server.state(settings_store(), args.get('server'))
        if name == 'azimuth_run_server':
            return self.jobs.start_server(args['program'], args['molecule'], args.get('settings'), settings_store(),
                                          args.get('server'), args.get('cores'), args.get('memory_mb'), args.get('hours'))
        if name == 'azimuth_server_resume':
            return self.jobs.resume_server(args['folder'], settings_store())
        if name == 'azimuth_tests':
            return self.jobs.start_tests(args['profile'], args.get('area'), args.get('options') or ())
        raise ValueError(f'unknown tool {name!r}')

    def handle(self, message):
        """The answer to one JSON-RPC message (None for a notification)."""
        ident = message.get('id')
        method = message.get('method', '')
        if ident is None:  # a notification: notifications/initialized, cancelled …
            return None
        if method == 'initialize':
            version = (message.get('params') or {}).get('protocolVersion') or '2025-06-18'
            return self._ok(ident, {'protocolVersion': version, 'capabilities': {'tools': {}},
                                    'serverInfo': {'name': NAME, 'version': VERSION},
                                    'instructions': 'Azimuth (quantum chemistry): preview an input before running it; '
                                                    'calculations and tests are jobs — poll azimuth_status.'})
        if method == 'ping':
            return self._ok(ident, {})
        if method == 'tools/list':
            return self._ok(ident, {'tools': TOOLS})
        if method == 'tools/call':
            params = message.get('params') or {}
            name, args = params.get('name', ''), params.get('arguments') or {}
            try:
                with contextlib.redirect_stdout(io.StringIO()) as said:  # stdout is the channel: prints go aside
                    value = self.call(name, args)
                text = value if isinstance(value, str) else headless.dumps(value)
                if said.getvalue().strip():
                    print(said.getvalue(), file=sys.stderr)
                return self._ok(ident, {'content': [{'type': 'text', 'text': text}], 'isError': False})
            except (ValueError, KeyError, OSError) as exc:
                return self._ok(ident, {'content': [{'type': 'text', 'text': f'{type(exc).__name__}: {exc}'}],
                                        'isError': True})
            except Exception as exc:  # noqa: BLE001 — the server goes on; the model sees what broke
                traceback.print_exc(file=sys.stderr)
                return self._ok(ident, {'content': [{'type': 'text', 'text': f'{type(exc).__name__}: {exc}'}],
                                        'isError': True})
        return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32601, 'message': f'unknown method {method}'}}

    @staticmethod
    def _ok(ident, value):
        return {'jsonrpc': '2.0', 'id': ident, 'result': value}


def main(stdin=None, stdout=None):
    stdin = stdin or io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    stdout = stdout or io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
    server = Server()
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            answer = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': str(exc)}}
        else:
            answer = server.handle(message) if isinstance(message, dict) else None
        if answer is not None:
            stdout.write(json.dumps(answer, ensure_ascii=False) + '\n')
            stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
