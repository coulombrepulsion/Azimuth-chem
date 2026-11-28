"""A fake SLURM server on this computer for the tests of ssh.py, cluster.py and remote_job.py.

The programs ssh, scp, sbatch, squeue, scancel, srun, bash (a login shell without the profile of the computer,
2026-11-12; FAKE_TRACE=<file> — ssh, scp, sbatch and squeue write their start and duration there), orca, orca_2mkl and
mopac are small Python scripts in <tmp>/bin. ssh runs the remote command with bash in <tmp>/home (the «home folder of
the server»); scp copies between this computer and that folder; sbatch starts job.sh in the background in its own
session and records it in <tmp>/home/.queue; squeue answers RUNNING while the process lives (PENDING while a file
<id>.pending exists); scancel kills the session. Files in <tmp> switch failures on (FAKE_ORCA_OUTPUT=<file>: ORCA prints
that output): offline (ssh and scp answer «Connection timed out», code 255), password (the password the server wants;
ssh checks what SSH_ASKPASS prints), sbatch_fail, sbatch_dependency_fail, orca_fail, mopac_fail
(FAKE_MOPAC_OUTPUT=<file>: the .out MOPAC writes, its .aux next to it; mopac.log — its first line of keywords and
OMP_NUM_THREADS; xtb — FAKE_XTB_DIR=<a folder of tests/data/xtb>, xtb_fail, xtb.log). Sbatch takes --parsable (prints only the number) and -J <name> (kept in .queue/<id>.name); squeue -n
<name> lists the live jobs of that name; sacct --name <name> lists every job ever given that name (the file no_sacct:
sacct is not configured, exit 1); the file drop_answer: the next command with az-submit runs and its answer is lost
(«Connection timed out», code 255) — the server accepted the job, the client never heard it (T07); drop_answer with the
text «offline»: and the server is out of reach afterwards (the file offline is made). Cut_downloads / short_downloads
with a number N — the next N downloads by scp bring half of each file, and then «Connection reset by peer» (code 255) or
nothing at all (a short copy scp did not notice).
"""

import os
import shlex
import shutil
import sys
from pathlib import Path

from tests.fake_programs import executable

PY = sys.executable

SSH = r'''
import atexit as _atexit, os as _os, sys as _sys, time as _time
if _os.environ.get('FAKE_TRACE'):  # 2026-11-12: a diagnosis of the times of the fake server (tools: FAKE_TRACE=<file>)
    _t0 = _time.time()
    _atexit.register(lambda: open(_os.environ['FAKE_TRACE'], 'a').write(
        f"{_t0:.3f} {_time.time() - _t0:6.3f} {_os.path.basename(_sys.argv[0])} {' '.join(_sys.argv[1:])[-160:]}\n"))
import os, subprocess, sys
root = os.environ['FAKE_ROOT']
args = sys.argv[1:]
with open(os.path.join(root, 'ssh.log'), 'a') as log:
    log.write(' '.join(args) + '\n')
if os.path.exists(os.path.join(root, 'offline')):
    sys.stderr.write('ssh: connect to host 192.0.2.103 port 22: Connection timed out\n'); sys.exit(255)
want = os.path.join(root, 'password')
key = args[args.index('-i') + 1] if '-i' in args else None  # 0.89.17: a key in authorized_keys of the fake home
authorized = os.path.join(root, 'home', '.ssh', 'authorized_keys')
by_key = key is not None and os.path.exists(key + '.pub') and os.path.exists(authorized) and \
    open(key + '.pub').read().strip() in open(authorized).read().splitlines()
if os.path.exists(want) and not by_key:
    asked = os.environ.get('SSH_ASKPASS')
    given = subprocess.run([asked], capture_output=True, text=True).stdout.strip() if asked else ''
    if given != open(want).read().strip():
        sys.stderr.write('user@192.0.2.103: Permission denied (publickey,password).\n'); sys.exit(255)
i, target = 0, None
while i < len(args):
    a = args[i]
    if a in ('-p', '-o', '-J', '-O', '-l', '-i', '-F'):
        if a == '-O':
            sys.exit(0)
        i += 2; continue
    if a.startswith('-'):
        i += 1; continue
    target = a; i += 1; break
command = ' '.join(args[i:])
home = os.path.join(root, 'home')
env = dict(os.environ, HOME=home)
drop = os.path.join(root, 'drop_answer')
if 'az-submit' in command and os.path.exists(drop):
    gone = open(drop).read().strip() == 'offline'  # 0.107.5: and the server is out of reach afterwards
    os.remove(drop)
    subprocess.run(['bash', '-c', command], cwd=home, env=env, capture_output=True)
    if gone:
        open(os.path.join(root, 'offline'), 'w').close()
    sys.stderr.write('ssh: connect to host 192.0.2.103 port 22: Connection timed out\n'); sys.exit(255)
# the machine of the «server» is the same everywhere: its processors, memory and load are files of the fake root,
# not those of the computer of the tests (two busy cores of a machine of GitHub left the tests no core to take)
command = command.replace('/proc/loadavg', os.path.join(root, 'proc', 'loadavg'))
command = command.replace('/proc/meminfo', os.path.join(root, 'proc', 'meminfo'))
sys.exit(subprocess.run(['bash', '-c', command], cwd=home, env=env).returncode)
'''

# the processors of the fake server: 8 cores of one socket, one thread each (lscpu of a Linux server); sysctl answers
# nothing, so that the probe never takes the values of a Mac that runs the tests
NPROC = 'print(8)\n'
LSCPU = 'print("CPU(s):              8\\nThread(s) per core:  1\\nCore(s) per socket:  8\\nSocket(s):           1")\n'
SYSCTL = 'import sys\nsys.exit(1)\n'
MEMINFO = 'MemTotal:       32768000 kB\nMemAvailable:   30720000 kB\n'
LOADAVG = '0.00 0.00 0.00 1/100 1000\n'

SCP = r'''
import atexit as _atexit, os as _os, sys as _sys, time as _time
if _os.environ.get('FAKE_TRACE'):  # 2026-11-12: a diagnosis of the times of the fake server (tools: FAKE_TRACE=<file>)
    _t0 = _time.time()
    _atexit.register(lambda: open(_os.environ['FAKE_TRACE'], 'a').write(
        f"{_t0:.3f} {_time.time() - _t0:6.3f} {_os.path.basename(_sys.argv[0])} {' '.join(_sys.argv[1:])[-160:]}\n"))
import os, shutil, sys
root = os.environ['FAKE_ROOT']
if os.path.exists(os.path.join(root, 'offline')):
    sys.stderr.write('ssh: connect to host 192.0.2.103 port 22: Connection timed out\n'); sys.exit(255)
args, files, i = sys.argv[1:], [], 0
while i < len(sys.argv) - 1:
    a = args[i]
    if a in ('-P', '-o', '-J', '-i', '-F'):
        i += 2; continue
    if a.startswith('-'):
        i += 1; continue
    files.append(a); i += 1
home = os.path.join(root, 'home')
def local(p):
    if '@' in p and ':' in p:
        p = p.split(':', 1)[1]
        return p if p.startswith('/') else os.path.join(home, p)
    return p
remote = [('@' in f and ':' in f) for f in files]
*sources, dest = [local(f) for f in files]
def cut(kind):  # 0.108.62 (T16): <root>/<kind> holds how many downloads still go wrong
    path = os.path.join(root, kind)
    if not (os.path.exists(path) and any(remote[:-1])):
        return False
    left = int(open(path).read() or 0)
    if left <= 0:
        return False
    open(path, 'w').write(str(left - 1))
    return True
broken = 'reset' if cut('cut_downloads') else ('short' if cut('short_downloads') else '')
for s in sources:
    if not os.path.exists(s):
        sys.stderr.write(f'scp: {s}: No such file or directory\n'); sys.exit(1)
    if os.path.isdir(s):
        shutil.copytree(s, os.path.join(dest, os.path.basename(s.rstrip('/'))), dirs_exist_ok=True)
    elif broken:  # half of the file arrives: the connection is reset (255), or scp says nothing (a short copy)
        target = os.path.join(dest, os.path.basename(s)) if os.path.isdir(dest) else dest
        data = open(s, 'rb').read()
        open(target, 'wb').write(data[: len(data) // 2])
        if broken == 'reset':
            sys.stderr.write('client_loop: send disconnect: Connection reset by peer\n'); sys.exit(255)
    else:
        shutil.copy2(s, dest if os.path.isdir(dest) else dest)
'''

SBATCH = r'''
import atexit as _atexit, os as _os, sys as _sys, time as _time
if _os.environ.get('FAKE_TRACE'):  # 2026-11-12: a diagnosis of the times of the fake server (tools: FAKE_TRACE=<file>)
    _t0 = _time.time()
    _atexit.register(lambda: open(_os.environ['FAKE_TRACE'], 'a').write(
        f"{_t0:.3f} {_time.time() - _t0:6.3f} {_os.path.basename(_sys.argv[0])} {' '.join(_sys.argv[1:])[-160:]}\n"))
import os, subprocess, sys
root = os.environ['FAKE_ROOT']
if os.path.exists(os.path.join(root, 'sbatch_fail')):
    print('sbatch: error: Batch job submission failed: Requested node configuration is not available'); sys.exit(1)
if os.path.exists(os.path.join(root, 'sbatch_dependency_fail')) and any(a.startswith('--dependency') for a in sys.argv[1:]):
    print('sbatch: error: Batch job submission failed: Job dependency problem'); sys.exit(1)  # 0.96.0: a job SLURM forgot
queue = os.path.join(root, 'home', '.queue'); os.makedirs(queue, exist_ok=True)
counter = os.path.join(queue, 'next')
n = int(open(counter).read()) if os.path.exists(counter) else 101
open(counter, 'w').write(str(n + 1))
open(os.path.join(queue, 'args'), 'a').write(' '.join(sys.argv[1:]) + '\n')
script = sys.argv[-1]
args = sys.argv[1:]
if '-J' in args:
    open(os.path.join(queue, f'{n}.name'), 'w').write(args[args.index('-J') + 1])
env = dict(os.environ, SLURM_SUBMIT_DIR=os.getcwd(), SLURM_JOB_ID=str(n))
out = open(f'slurm-{n}.out', 'w')
p = subprocess.Popen(['bash', script], cwd=os.getcwd(), env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
open(os.path.join(queue, f'{n}.pid'), 'w').write(str(p.pid))
print(str(n) if '--parsable' in args else f'Submitted batch job {n}')
'''

SQUEUE = r'''
import atexit as _atexit, os as _os, sys as _sys, time as _time
if _os.environ.get('FAKE_TRACE'):  # 2026-11-12: a diagnosis of the times of the fake server (tools: FAKE_TRACE=<file>)
    _t0 = _time.time()
    _atexit.register(lambda: open(_os.environ['FAKE_TRACE'], 'a').write(
        f"{_t0:.3f} {_time.time() - _t0:6.3f} {_os.path.basename(_sys.argv[0])} {' '.join(_sys.argv[1:])[-160:]}\n"))
import os, sys
root = os.environ['FAKE_ROOT']
queue = os.path.join(root, 'home', '.queue')
def alive_pid(job):
    pidfile = os.path.join(queue, f'{job}.pid')
    if not os.path.exists(pidfile):
        return False
    pid = int(open(pidfile).read())
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
        return not os.path.exists(f'/proc/{pid}/stat') or open(f'/proc/{pid}/stat').read().split()[2] != 'Z'
    except OSError:
        return False
if '-n' in sys.argv:  # 0.107.4: the jobs of a name
    name = sys.argv[sys.argv.index('-n') + 1]
    for f in sorted(os.listdir(queue)) if os.path.isdir(queue) else []:
        if f.endswith('.name') and open(os.path.join(queue, f)).read() == name:
            job = f[:-5]
            if os.path.exists(os.path.join(queue, f'{job}.pending')) or alive_pid(job):
                print(job)
    sys.exit(0)
job = sys.argv[sys.argv.index('-j') + 1]
if os.path.exists(os.path.join(queue, f'{job}.pending')):
    print('PENDING|0:00|(Resources)'); sys.exit(0)
pidfile = os.path.join(queue, f'{job}.pid')
if not os.path.exists(pidfile):
    sys.exit(0)
pid = int(open(pidfile).read())
try:
    waited = os.waitpid(pid, os.WNOHANG)
except ChildProcessError:
    waited = None
try:
    os.kill(pid, 0)
    alive = not os.path.exists(f'/proc/{pid}/stat') or open(f'/proc/{pid}/stat').read().split()[2] != 'Z'
except OSError:
    alive = False
if alive:
    print('RUNNING|0:07|serv3')
'''

SACCT = r'''
import os, sys
root = os.environ['FAKE_ROOT']
if os.path.exists(os.path.join(root, 'no_sacct')):
    sys.stderr.write('sacct: error: Slurm accounting storage is disabled\n'); sys.exit(1)
queue = os.path.join(root, 'home', '.queue')
name = sys.argv[sys.argv.index('--name') + 1]
for f in sorted(os.listdir(queue)) if os.path.isdir(queue) else []:
    if f.endswith('.name') and open(os.path.join(queue, f)).read() == name:
        print(f[:-5])
'''

# srun of the server — the program once (one rank), its -n/-c taken off. Without it a job of pw.x took mpirun of
# the computer of the tests (Open MPI of Homebrew, brought by «brew install cp2k»): six fake pw.x, 13 «JOB DONE» not 3
SRUN = r'''
import os, sys
args = sys.argv[1:]
while args and args[0].startswith('-'):
    flag = args.pop(0)
    if flag in ('-n', '-np', '-c', '-N', '--ntasks', '--cpus-per-task') and args:
        args.pop(0)
os.execvp(args[0], args)
'''

SCANCEL = r'''
import os, signal, sys
root = os.environ['FAKE_ROOT']
pidfile = os.path.join(root, 'home', '.queue', f'{sys.argv[1]}.pid')
open(os.path.join(root, 'scancel.log'), 'a').write(sys.argv[1] + '\n')
try:
    os.killpg(int(open(pidfile).read()), signal.SIGTERM)
except (OSError, ValueError):
    pass
'''

ORCA = r'''
import os, sys, time
root = os.environ['FAKE_ROOT']
steps = int(os.environ.get('FAKE_ORCA_STEPS', '4'))
print('                                 * O   R   C   A *', flush=True)
nprocs = [l for l in open(sys.argv[1]) if l.lower().startswith('%pal')]
print('PAL: ' + (nprocs[0].strip() if nprocs else 'none'), flush=True)
for k in range(1, steps + 1):
    time.sleep(float(os.environ.get('FAKE_ORCA_DELAY', '0.15')))
    print(f'GEOMETRY OPTIMIZATION CYCLE {k}', flush=True)
    print(f'FINAL SINGLE POINT ENERGY      -76.0{k}', flush=True)
base = os.path.splitext(os.path.basename(sys.argv[1]))[0]  # ORCA names its files after the input
open(base + '.gbw', 'wb').write(b'GBW')
open(base + '_trj.xyz', 'w').write('3\nstep\nO 0 0 0\nH 0 0 1\nH 0 1 0\n')
open(base + '.tmp.0', 'w').write('scratch')
if os.environ.get('FAKE_ORCA_OUTPUT'):  # a real ORCA output (cclib data) for the window tests
    sys.stdout.write(open(os.environ['FAKE_ORCA_OUTPUT']).read()); sys.stdout.flush(); sys.exit(0)
if os.path.exists(os.path.join(root, 'orca_fail')):
    print('ORCA finished by error termination in SCF', flush=True); sys.exit(1)
print('                             ****ORCA TERMINATED NORMALLY****', flush=True)
'''

MOPAC = r'''
import os, sys
root = os.environ['FAKE_ROOT']
mop = sys.argv[1]
base = os.path.splitext(os.path.basename(mop))[0]  # MOPAC writes <base>.out, .aux, .arc next to the input
first = open(mop).readline().strip()
open(os.path.join(root, 'mopac.log'), 'a').write(first + ' | OMP_NUM_THREADS=' + os.environ.get('OMP_NUM_THREADS', '') + '\n')
recorded = os.environ.get('FAKE_MOPAC_OUTPUT')  # a real MOPAC output (tests/data/mopac)
text = open(recorded).read() if recorded else ' MOPAC fake\n'
if os.path.exists(os.path.join(root, 'mopac_fail')):
    text = text.replace('JOB ENDED NORMALLY', 'ERROR')
open(base + '.out', 'w').write(text)
if recorded and os.path.exists(recorded[:-4] + '.aux'):
    open(base + '.aux', 'w').write(open(recorded[:-4] + '.aux').read())
print('MOPAC done', flush=True)
'''

XTB = r'''
import os, shutil, sys
root = os.environ['FAKE_ROOT']
# xtb.log — its arguments and the OpenMP environment; FAKE_XTB_DIR=<a folder of tests/data/xtb>: its output printed and the
# files xtb writes beside it (xtbopt.xyz, xtbopt.log, g98.out, charges, wbo, vibspectrum) put in the folder of the job
open(os.path.join(root, 'xtb.log'), 'a').write(' '.join(sys.argv[1:]) + ' | OMP_NUM_THREADS=' + os.environ.get(
    'OMP_NUM_THREADS', '') + ' OMP_STACKSIZE=' + os.environ.get('OMP_STACKSIZE', '') + '\n')
recorded = os.environ.get('FAKE_XTB_DIR')
if os.path.exists(os.path.join(root, 'xtb_fail')):
    print('[ERROR] Program stopped due to fatal error', flush=True); sys.exit(1)
if recorded:
    for name in os.listdir(recorded):
        if name.endswith('.out') and not name.startswith('g98'):
            sys.stdout.write(open(os.path.join(recorded, name)).read())
        elif not name.endswith('.xyz') or name == 'xtbopt.xyz':
            shutil.copy(os.path.join(recorded, name), name)
else:
    print('   * finished run on 2026/11/28\n normal termination of xtb', flush=True)
'''

MKL = r'''
import sys
open(sys.argv[1] + '.molden.input', 'w').write('[Molden Format]\n')
'''


FIND = r'''
import os, sys
# the probe looks for the programs in /opt and /usr/local too: here only the «home folder of the server» is the server
os.execv('/usr/bin/find', ['find'] + [a for a in sys.argv[1:] if a not in ('/opt', '/usr/local')])
'''

SLURM = ('sbatch', 'squeue', 'sacct', 'scancel', 'srun')


def make(root, slurm=True):
    root = Path(root)
    bin_dir = root / 'bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    (root / 'home').mkdir(exist_ok=True)
    for name, code in (('ssh', SSH), ('scp', SCP), ('sbatch', SBATCH), ('squeue', SQUEUE), ('sacct', SACCT), ('scancel', SCANCEL), ('srun', SRUN),
                       # mpirun of the «server»: one copy of the program, as srun here (a real mpirun of the computer of the
                       # tests would start N copies of the fake pw.x)
                       ('mpirun', SRUN),
                       ('orca', ORCA), ('orca_2mkl', MKL), ('mopac', MOPAC), ('xtb', XTB)):
        if slurm or name not in SLURM:  # slurm=False — a server without SLURM (serv1): the jobs go by nohup
            executable(bin_dir / name, f'#!{PY}\n' + code)  # one checked copy for all the tests (fake_programs)
    if os.name != 'nt':
        executable(bin_dir / 'find', f'#!{PY}\n' + FIND)
        for name, code in (('nproc', NPROC), ('lscpu', LSCPU), ('sysctl', SYSCTL)):
            executable(bin_dir / name, f'#!{PY}\n' + code)
    (root / 'proc').mkdir(exist_ok=True)
    (root / 'proc' / 'meminfo').write_text(MEMINFO)
    (root / 'proc' / 'loadavg').write_text(LOADAVG)
    # the commands reach the server as «bash -lc …» (a login shell: the modules of a cluster); here the
    # server is the computer of the tests, and a login bash of macOS reads /etc/profile — its path_helper took about a
    # second on every call (a test of 0.1 s on Linux lasted 4–9 s on the Mac). The bash of the fake server is the
    # real one without the profile files of the computer; the commands are not changed.
    real = shutil.which('bash', path=os.pathsep.join(p for p in os.environ.get('PATH', '').split(os.pathsep)
                                                       if Path(p) != bin_dir))
    if real and os.name != 'nt':
        executable(bin_dir / 'bash', f'#!/bin/sh\nexec {shlex.quote(real)} --noprofile "$@"\n')
    return bin_dir


def install(tmp_path, monkeypatch, slurm=True):
    """The fake server in tmp_path; its programs first in PATH (the test's environment only)."""
    bin_dir = make(tmp_path / 'server', slurm)
    monkeypatch.setenv('FAKE_ROOT', str(tmp_path / 'server'))
    monkeypatch.setenv('PATH', f'{bin_dir}{os.pathsep}{os.environ.get("PATH", "")}')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '0.1')
    return tmp_path / 'server'
