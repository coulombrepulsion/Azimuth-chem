"""Azimuth without its window: a molecule, the settings of a calculation, its input file, the run on this computer, its
state and its result — the same code Sextant and Spectrum use; and the checks of the program (tools/test.py) as jobs.

§1 PURPOSE
    Commands for scripts, for a language model through tools/azimuth_mcp.py, and for series of calculations: nothing
    here imports Qt (tests/core/test_architecture_boundaries.py). A calculation is prepared by modules/sextant/runner
    (the folder of the jobs, the input of modules/sextant/inputs, the environment of the program) and read by
    modules/spectrum/readers/outputs, so it is the calculation Sextant would make and the result Spectrum would show.
§2 RULES
    1. molecule(spec): {'smiles'} (formats.from_smiles), {'xyz'} (the text of an XYZ file), or {'path'} — a structure
       file (XYZ, MOL/SDF — the first record, PDB, MOL2, an ORCA or Gaussian input, an output — its last geometry);
       'title' names it. An input file brings its charge and multiplicity (returned beside the molecule).
    2. calculation(settings): the fields of azimuth.core.Calculation by name; an unknown name or a wrong type is a
       ValueError that names it; Calculation.validate is the check of the program.
    3. Jobs live in the process (Jobs): an id, a kind ('calculation' | 'tests' | 'server'), the folder, the start; the state is
       read when asked (Job.poll). A calculation runs in a session of its own, so it outlives the process; its folder
       stays readable by result(folder).
    4. Only the programs Sextant knows are run (runner.find_program, or the path given); the checks of the program —
       only tools/test.py with a profile of PROFILES and the options of SAFE_OPTIONS (no shell, a list of arguments).
    5. A calculation on a server (Jobs.start_server, resume_server) goes by azimuth/headless_server.py: the login by
       the key only, the cores and the memory within what the server says is free, a journal of what was sent; stop
       is scancel of its own number.
§3 INTERFACE
    programs(configured=None) -> {kind: path | None}; options(kind) -> {tasks, methods, bases, solvents, dispersions};
    molecule(spec) -> (Molecule, charge | None, multiplicity | None); calculation(settings, base=None) -> Calculation;
    preview(kind, spec, settings) -> text; Jobs: start_calculation(kind, spec, settings, root=None, program=None),
    start_tests(profile, area=None, options=()), status(id, lines=40), stop(id), listing(); result(path, kind=None,
    settings=None) -> dict (energy, convergence, frequencies, thermochemistry, problems and the doctor's remedies).
§7 TESTS tests/core/test_headless.py.
"""

from dataclasses import fields
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ('quick', 'affected', 'area', 'full', 'isolated', 'list')
SAFE_OPTIONS = re.compile(r'^(-x|-q|-v|-vv|-ra|-rf|--lf|--ff|--tb=(short|line|no|long)|--maxfail=\d{1,3}|-k|--timeout|'
                          r'\d{1,4}(\.\d+)?|tests/[\w/.\-]+(::[\w\[\]\-.,]+)*|[\w(][\w\s()\-]{0,119})$')
# the last form is a -k expression («crystal and not slow»): it never begins with «-», so no other option of pytest
# (-p, --rootdir, -c …) gets through
SEMIEMPIRICAL = ('xtb', 'crest', 'mopac')
STRUCTURE_SUFFIXES = ('.xyz', '.mol', '.sdf', '.pdb', '.mol2', '.inp', '.gjf', '.com', '.out', '.log')


def programs(configured=None):
    """Where each program of Sextant is (the path chosen in the settings first — configured {kind: path})."""
    from modules.sextant import inputs, runner

    configured = configured or {}
    found = {}
    for kind in inputs.KINDS:
        path = runner.find_program(kind, configured.get(kind))
        found[kind] = str(path) if path else None
    return found


def options(kind):
    """What a program can be asked: its tasks, methods and basis sets as Sextant lists them."""
    from azimuth import core
    from modules.sextant import inputs

    if kind not in inputs.KINDS:
        raise ValueError(f'unknown program {kind!r}; known: {", ".join(inputs.KINDS)}')
    methods = core.methods_for(kind) if hasattr(core, 'methods_for') else ()
    if kind in inputs.SOLVENT_COLUMN:  # only the solvents the program has a name for
        solvents = [k for k, row in core.SOLVENTS.items() if not k or row[inputs.SOLVENT_COLUMN[kind]]]
    elif kind == 'mopac':  # COSMO by the dielectric constant
        solvents = [''] + list(inputs.MOPAC_EPS)
    else:
        solvents = list(core.SOLVENTS)
    bases = core.bases_for(kind) if hasattr(core, 'bases_for') else core.BASES  # GAMESS and NWChem — their own tables
    found = {'tasks': list(inputs.tasks_for(kind)), 'methods': list(methods), 'bases': list(bases),
             'solvents': solvents, 'dispersions': [d for d in core.DISPERSIONS
                                                    if not (d == 'D4' and kind in ('gaussian', 'psi4'))]}  # no D4 there
    found['checked'] = kind not in inputs.UNVERIFIED  # outside the beta: inputs never run by the real program
    if kind in SEMIEMPIRICAL:  # no basis set; the dispersion is a part of the method (D4 of GFN2, PM6-D3H4)
        found.update(bases=[], dispersions=[])
    if kind in ('xtb', 'crest'):
        found['methods'] = ['GFN2-xTB']
        found['note'] = 'GFN2-xTB is the only method; settings "method" and "basis" are ignored.'
    if kind == 'crest':  # it always searches the conformers (iMTD-GC); Sextant does not read a task for it
        found['tasks'] = []
        found['note'] = ('CREST always runs its conformer search (iMTD-GC, GFN2-xTB); "task", "method" and "basis" '
                         'are ignored — charge, multiplicity, cores and solvent are used.')
    return found


def molecule(spec):
    """(Molecule, charge or None, multiplicity or None) of {'smiles' | 'xyz' | 'path', 'title'}."""
    from dataclasses import replace

    from azimuth.core import read_xyz
    from modules.compass.chemistry import formats

    if not isinstance(spec, dict) or not any(spec.get(k) for k in ('smiles', 'xyz', 'path')):
        raise ValueError('a molecule is {"smiles": …}, {"xyz": …} or {"path": …}')
    charge = multiplicity = None
    if spec.get('smiles'):
        made = formats.from_smiles(str(spec['smiles']))
    elif spec.get('xyz'):
        made = read_xyz(str(spec['xyz']))
    else:
        path = Path(str(spec['path'])).expanduser()
        if not path.is_file():
            raise ValueError(f'no file {path}')
        suffix = path.suffix.lower()
        if suffix not in STRUCTURE_SUFFIXES:
            raise ValueError(f'not a structure file: {path.name} (known: {", ".join(STRUCTURE_SUFFIXES)})')
        text = formats.read_text(path)
        if suffix == '.xyz':
            made = read_xyz(text)
        elif suffix in ('.mol', '.sdf'):
            records = formats.read_sdf_records(text) if suffix == '.sdf' else [formats.read_mol(text)]
            if not records:
                raise ValueError(f'no structure in {path.name}')
            made = records[0]
        elif suffix == '.pdb':
            made = formats.read_pdb(text)
        elif suffix == '.mol2':
            made = formats.read_mol2(text)
        elif suffix == '.inp':
            made, charge, multiplicity = formats.read_orca_input(text)
        elif suffix in ('.gjf', '.com'):
            made, charge, multiplicity = formats.read_gaussian_input(text)
        else:
            from modules.spectrum.readers.outputs import read_any

            output = read_any(text, path)
            if output.geometry is None:
                raise ValueError(f'no geometry in {path.name}')
            made = output.geometry
    if isinstance(made, tuple):  # some readers return (molecule, …)
        made = made[0]
    if spec.get('title'):
        made = replace(made, title=str(spec['title']))
    return made, charge, multiplicity


def calculation(settings, base=None):
    """A Calculation of base (or the defaults) with the fields of settings; ValueError names a wrong one."""
    from dataclasses import replace

    from azimuth.core import Calculation

    calc = base or Calculation()
    known = {f.name: f for f in fields(Calculation)}
    changes = {}
    for name, value in (settings or {}).items():
        if name not in known:
            raise ValueError(f'unknown setting {name!r}; known: {", ".join(sorted(known))}')
        current = getattr(calc, name)
        try:
            if isinstance(current, bool):
                value = value if isinstance(value, bool) else str(value).lower() in ('1', 'true', 'yes', 'да')
            elif isinstance(current, int):
                value = int(value)
            elif isinstance(current, float):
                value = float(value)
            elif isinstance(current, str):
                value = str(value)
        except (TypeError, ValueError):
            raise ValueError(f'{name}: {value!r} is not a {type(current).__name__}') from None
        changes[name] = value
    made = replace(calc, **changes)
    if base is None and 'dispersion' not in (settings or {}):
        # the default of a new window of Sextant (core.DEFAULT_DISPERSION): without it a calculation sent from here was
        # B3LYP without D3(BJ) — the same molecule gave other numbers than in the window (the matrix of 2026-11-23)
        from azimuth.core import default_dispersion

        made = replace(made, dispersion=default_dispersion(made.method))
    return made


def _prepared(kind, spec, settings):
    made, charge, multiplicity = molecule(spec)
    settings = dict(settings or {})
    if charge is not None:
        settings.setdefault('charge', charge)
    if multiplicity is not None:
        settings.setdefault('multiplicity', multiplicity)
    calc = calculation(settings)
    calc.validate(made)
    return made, calc


def preview(kind, spec, settings=None):
    """The input file Sextant would write (the main one; for xtb — its command and files)."""
    from modules.sextant import inputs

    made, calc = _prepared(kind, spec, settings)
    return inputs.preview(kind, made, calc)


def _brief(output):
    return {k: v for k, v in output.items() if v not in (None, [], {}, '')}


def result(path, kind=None, settings=None, code=None):
    """What a finished (or running) calculation gave: path — its output or its folder; code — the exit code of the
    program when it is known (the doctor reads a killed run by it)."""
    from modules.sextant import doctor, runner
    from modules.spectrum.readers.outputs import program, read_any

    path = Path(str(path)).expanduser()
    if path.is_dir():
        candidates = sorted((p for p in path.iterdir() if p.suffix in ('.out', '.log') and p.is_file()),
                            key=lambda p: p.stat().st_size, reverse=True)
        if not candidates:
            raise ValueError(f'no output (.out, .log) in {path}')
        path = candidates[0]
    text = path.read_text(encoding='utf-8', errors='replace')
    if kind == 'crest' or CREST_MARK.search(text[:4000]):
        return _brief(crest_result(path, text, code))
    output = read_any(text, path)
    found = (program(text) or output.program or '').lower()
    kind = kind or next((k for k in ('orca', 'gaussian', 'psi4', 'xtb', 'crest', 'mopac', 'gamess', 'nwchem')
                         if k in found), 'orca')
    energy = output.final_energy[1] if output.final_energy else (output.energies[-1] if output.energies else None)
    freqs = [m.frequency for m in (output.modes or ()) if abs(m.frequency) > 1e-6]
    summary = {
        'file': str(path), 'program': output.program, 'normal_exit': output.normal_exit,
        'optimization_converged': output.optimization_converged if output.steps else None,
        'scf_failed': output.scf_failed,
        'energy_hartree': energy, 'correlated_energy': output.final_energy, 'heat_of_formation_kcal': output.heat_of_formation,
        'steps': len(output.steps or ()), 'atoms': len(output.geometry.atoms) if output.geometry else None,
        'frequencies_cm1': freqs[:12], 'imaginary_frequencies': sum(1 for f in freqs if f < 0),
        'notes': list(output.notes or ()),
    }
    if output.geometry is not None:
        summary['geometry_xyz'] = output.geometry.xyz() if hasattr(output.geometry, 'xyz') else None
    # the geometry of the frequencies, as the tab «Термохимия» of Spectrum takes it (MOPAC turns the molecule for FORCE)
    vibrated = getattr(output, 'vibration_geometry', None) or output.geometry
    if output.frequencies and vibrated is not None:
        try:  # as the queue of Sextant does it (batch.py): σ of the point group, 298.15 K, 1 atm
            from modules.spectrum.analysis import thermo

            sigma = 1
            try:
                from modules.compass.chemistry.symmetry import analyze

                point = analyze(vibrated)
                sigma = thermo.symmetry_number(point.get('name', '') if 'err' not in point else '')
            except Exception:  # noqa: BLE001 — no point group: σ = 1
                sigma = 1
            # no total energy (MOPAC: a heat of formation) — the corrections only, H and G stay None
            found = thermo.thermochemistry(vibrated, output.frequencies, energy,
                                           multiplicity=thermo.multiplicity(text), sigma=sigma)
            summary['thermochemistry_hartree'] = {
                'temperature_K': found.temperature, 'sigma': found.sigma, 'zpe': found.zpe,
                'enthalpy_correction': found.enthalpy, 'gibbs_correction': found.gibbs, 'entropy': found.entropy,
                'H': found.total(found.enthalpy) if energy is not None else None,
                'G': found.total(found.gibbs) if energy is not None else None}
        except (ValueError, ZeroDivisionError) as exc:
            summary['thermochemistry_hartree'] = {'error': str(exc)}
    if getattr(output, 'shieldings', None):  # NMR: the isotropic shielding of each nucleus, ppm (not a shift)
        summary['nmr_shielding_ppm'] = [{'atom': x.atom, 'element': x.element, 'isotropic': x.isotropic,
                                         'anisotropy': x.anisotropy} for x in output.shieldings]
    if output.absorption:
        summary['excitations'] = [{'state': e.state, 'nm': e.wavelength, 'ev': e.energy_ev, 'f': e.fosc,
                                   'multiplicity': e.multiplicity} for e in list(output.absorption)[:10]]
    if summary['imaginary_frequencies'] and output.normal_exit:  # a saddle where a minimum was wanted (doctor §2.5)
        calc = calculation(settings or {})
        remedy = doctor.imaginary(kind, text, calc, path)
        if remedy is not None:
            moved = doctor.displaced(text, path)
            if moved is not None:  # xtb's modes come from its g98.out: the title of that file is «Gaussian»
                from dataclasses import replace as _replace

                moved = _replace(moved, title=f'{summary.get("program") or kind}: moved along the imaginary mode')
            summary['remedies'] = [{'what': remedy.what, 'why': remedy.why, 'repeat': remedy.label,
                                    'changes': remedy.changes, 'start_xyz': moved.xyz() if moved is not None else None}]
    if not output.normal_exit or output.scf_failed or (output.steps and output.optimization_converged is False):
        calc = calculation(settings) if settings else calculation({})
        summary['problems'] = [{'what': what, 'why': why} for what, why in runner.diagnose(kind, text, code)]
        summary['remedies'] = [{'what': r.what, 'why': r.why, 'repeat': r.label, 'changes': r.changes,
                                'last_geometry': r.last_geometry} for r in doctor.examine(kind, text, code, calc)]
    return _brief(summary)


HARTREE_KCAL = 627.509474  # kcal/mol per hartree (CODATA 2018, as modules/spectrum)
CREST_MARK = re.compile(r'Conformer-Rotamer Ensemble Sampling Tool|C R E S T')


def crest_result(path, text, code=None):
    """CREST is no program of an energy but a search: its log (crest.out) and the conformers it kept
    (crest_conformers.xyz next to it, the energies in hartree on the comment lines) — the conformers, lowest first,
    their energies above the lowest, the geometry of the lowest, and the problems Sextant knows (its energy window of
    0 in CREST 3.0.2 on macOS keeps one conformer, crest-lab/crest#431)."""
    from modules.compass.chemistry import conformers as cf
    from modules.sextant import runner

    version = re.search(r'Version\s+(\d+(?:\.\d+)+)', text)
    summary = {'file': str(path), 'program': 'CREST' + (f' {version.group(1)}' if version else ''),
               'normal_exit': 'CREST terminated normally' in text}
    ensemble = Path(path).parent / 'crest_conformers.xyz'
    if ensemble.is_file():
        found = [(e, m) for m, e in cf.read_ensemble(ensemble.read_text(encoding='utf-8', errors='replace'))
                 if e is not None]
        found.sort(key=lambda pair: pair[0])
        if found:
            lowest = found[0][0]
            summary.update(conformers=len(found), energy_hartree=lowest, atoms=len(found[0][1].atoms),
                           relative_kcal=[round((e - lowest) * HARTREE_KCAL, 3) for e, _ in found[:20]],
                           geometry_xyz=found[0][1].xyz(), ensemble=str(ensemble))
    problems = runner.diagnose('crest', text, code if code is not None else (0 if summary['normal_exit'] else None))
    if problems and (not summary['normal_exit'] or runner.crest_window_broken(text)):
        summary['problems'] = [{'what': what, 'why': why} for what, why in problems]
    return summary


class Jobs:
    """The jobs started by this process: calculations of this computer and runs of tools/test.py."""

    def __init__(self, python=None):
        self.jobs = {}
        self.python = python or sys.executable
        self.counter = 0

    def _id(self, kind):
        self.counter += 1
        return f'{kind[0]}{self.counter}-{time.strftime("%H%M%S")}'

    def start_calculation(self, kind, spec, settings=None, root=None, program=None, configured=None):
        from modules.sextant import runner

        made, calc = _prepared(kind, spec, settings)
        found = Path(program) if program else runner.find_program(kind, (configured or {}).get(kind))
        if found is None:
            raise ValueError(f'{kind} is not found on this computer (programs() lists what is)')
        mpirun = runner.find_mpirun(found) if kind == 'orca' and calc.cores > 1 else None
        spec_ = runner.prepare(kind, found, made, calc, (), Path(root) if root else runner.default_jobs_root(),
                               mpirun=mpirun)
        job = runner.Job(spec_)
        job.start()
        ident = self._id('calculation')
        self.jobs[ident] = {'kind': 'calculation', 'program': kind, 'job': job, 'spec': spec_, 'settings': settings,
                            'started': time.time()}
        return {'job': ident, 'folder': str(spec_.folder), 'output': str(spec_.output)}

    # -- a server (azimuth/headless_server.py: the key only, the limits, the journal) ----------------------------------
    def start_server(self, kind, spec, settings=None, store=None, server=None, cores=None, memory_mb=None, hours=None,
                     root=None, opener=None, interval=10.0):
        """One calculation of ORCA or MOPAC sent to the server of a profile of Sextant; the cores and the memory are
        those of the call (within what is free there), not those of settings."""
        from azimuth import headless_server

        made, calc = _prepared(kind, spec, settings)
        job, plan, profile = headless_server.send(kind, made, calc, store, server, cores, memory_mb, hours, root, opener,
                                                  interval)
        return self._watch_server(job, kind, settings, root, profile.title(), plan)

    def resume_server(self, folder, store=None, root=None, opener=None, interval=10.0):
        """A calculation sent from here before this process was restarted, watched again (nothing is sent again)."""
        from azimuth import headless_server

        folder = str(Path(str(folder)).expanduser())
        known = next((k for k, v in self.jobs.items() if v['kind'] == 'server' and str(v['spec'].folder) == folder), None)
        if known is not None:
            return {'job': known, 'folder': folder, 'watched': 'already'}
        job = headless_server.resume(folder, store, root, opener, interval)
        return self._watch_server(job, job.spec.kind, None, root, job.profile.title(), None)

    def _watch_server(self, job, kind, settings, root, title, plan):
        ident = self._id('server')
        self.jobs[ident] = {'kind': 'server', 'program': kind, 'job': job, 'spec': job.spec, 'settings': settings,
                            'started': time.time(), 'root': root, 'server': title}
        # the end goes into the journal when the watcher ends, asked or not (the status asked only then wrote it, and a
        # calculation nobody asked about stayed «open»)
        from azimuth import headless_server

        def note_end():
            job.join()
            code = job.poll()
            if code is None:
                return  # not watched (no thread): nothing is known of its end
            try:
                headless_server.ended(root, job.spec.folder, job.state, code)
            except OSError:
                pass

        import threading

        threading.Thread(target=note_end, name='azimuth-server-end', daemon=True).start()
        out = {'job': ident, 'server': title, 'folder': str(job.spec.folder), 'output': str(job.spec.output)}
        if plan is not None:
            out.update(cores=plan.processes, memory_mb_per_process=plan.maxcore)
        return out

    def _server_status(self, ident, entry, lines):
        from azimuth import headless_server
        from modules.sextant import runner

        job = entry['job']
        code = job.poll()
        text = job.text(limit=4_000_000) or ''
        cycles, energy = runner.progress(entry['program'], text, entry['spec'].folder)
        out = {'job': ident, 'where': entry['server'], 'state': job.state, 'message': job.message, 'slurm_job': job.job_id,
               'exit_code': code, 'seconds': round(time.time() - entry['started']), 'cycles': cycles,
               'last_energy_hartree': energy, 'folder': str(entry['spec'].folder), 'tail': runner.tail(text, min(lines, 60))}
        if code is not None:
            headless_server.ended(entry['root'], entry['spec'].folder, job.state, code)
            try:
                out['result'] = result(entry['spec'].output, entry['program'], entry['settings'], code)
            except (OSError, ValueError) as exc:
                if code == 0:  # a failed run: its message says why; «no recognisable sections» only confused it
                    out['result'] = {'error': str(exc)}
        return out

    def tests_command(self, profile, area=None, options=()):
        """The arguments of tools/test.py for a profile; ValueError for anything not allowed."""
        if profile not in PROFILES:
            raise ValueError(f'profile is one of {", ".join(PROFILES)}')
        if profile == 'area' and not (area and re.fullmatch(r'[\w\-]+', area)):
            raise ValueError('area: the name of an area of tools/test.py list')
        options = [str(o) for o in options or ()]
        bad = [o for o in options if not SAFE_OPTIONS.match(o)]
        if bad:
            raise ValueError(f'not allowed: {bad}')
        args = [self.python, str(ROOT / 'tools' / 'test.py'), profile] + ([area] if profile == 'area' else [])
        return args + ((['--'] + options) if options else [])

    def start_tests(self, profile, area=None, options=()):
        args = self.tests_command(profile, area, options)
        folder = ROOT / 'artifacts' / 'mcp'
        folder.mkdir(parents=True, exist_ok=True)
        ident = self._id('tests')
        log = folder / f'{ident}.log'
        handle = open(log, 'w', encoding='utf-8')
        # a session of its own: a stop ends tools/test.py and the pytest it started together
        group = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen(args, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}, **group)
        self.jobs[ident] = {'kind': 'tests', 'process': process, 'log': log, 'handle': handle, 'args': args[1:],
                            'started': time.time()}
        return {'job': ident, 'log': str(log), 'command': ' '.join(args[1:])}

    def status(self, ident, lines=40):
        entry = self.jobs.get(ident)
        if entry is None:
            raise ValueError(f'no job {ident!r}; jobs: {", ".join(self.jobs) or "none"}')
        elapsed = round(time.time() - entry['started'])
        if entry['kind'] == 'tests':
            code = entry['process'].poll()
            text = entry['log'].read_text(encoding='utf-8', errors='replace')
            state = 'running' if code is None else 'passed' if code == 0 else 'stopped' if entry.get('stopped') else 'failed'
            out = {'job': ident, 'state': state,
                   'exit_code': code, 'seconds': elapsed, 'tail': '\n'.join(text.splitlines()[-lines:])}
            summary = re.findall(r'artifacts/tests/[^\s]+', text)
            if code is not None and summary:
                out['artifacts'] = summary[-1]
            return out
        if entry['kind'] == 'server':
            return self._server_status(ident, entry, lines)
        from modules.sextant import runner

        job = entry['job']
        code = job.poll()
        text = job.text(limit=4_000_000) or ''
        cycles, energy = runner.progress(entry['program'], text, entry['spec'].folder)
        state = 'running' if code is None else ('done' if runner.finished_normally(entry['program'], text, code)
                                                else 'stopped' if job.stopped else 'failed')
        out = {'job': ident, 'state': state, 'exit_code': code, 'seconds': elapsed, 'cycles': cycles,
               'last_energy_hartree': energy, 'folder': str(entry['spec'].folder),
               'tail': runner.tail(text, min(lines, 60))}
        if code is not None:
            try:
                out['result'] = result(entry['spec'].output, entry['program'], entry['settings'], code)
            except (OSError, ValueError) as exc:
                if code == 0:  # a failed run: its message says why; «no recognisable sections» only confused it
                    out['result'] = {'error': str(exc)}
        return out

    def stop(self, ident):
        entry = self.jobs.get(ident)
        if entry is None:
            raise ValueError(f'no job {ident!r}')
        if entry['kind'] == 'tests':
            process = entry['process']
            entry['stopped'] = True
            if process.poll() is None:
                if os.name == 'nt':
                    from modules.sextant import runner

                    runner.kill_tree(process.pid) or process.terminate()
                else:
                    import signal

                    try:
                        os.killpg(process.pid, signal.SIGTERM)  # tools/test.py and its pytest
                    except OSError:
                        process.terminate()
        else:
            entry['job'].stop()
        return {'job': ident, 'stopping': True}

    def listing(self):
        return [{'job': k, 'kind': v['kind'], 'seconds': round(time.time() - v['started']),
                 **({'server': v['server'], 'folder': str(v['spec'].folder)} if v['kind'] == 'server' else {})}
                for k, v in self.jobs.items()]


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)
