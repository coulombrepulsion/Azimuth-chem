"""SLURM servers: cores, memory, the job script, the job number (modules/sextant/cluster.py).

Oracles: what the three laboratory servers printed on 27 October 2026 (serv2, serv3, serv4: lscpu, free, sinfo,
module avail; one node «localhost», partition LocalQ, two threads per core), rewritten in the «@key value» lines
of the probe; lscpu fields as Linux prints them; the rule written in the module header (§2) computed here by
hand for each case; the sbatch reply format «Submitted batch job N» (SLURM documentation of sbatch).
"""

import os
import shutil

import pytest

from modules.sextant import cluster
from azimuth.core import Calculation, orca_input, read_xyz

PROBE_48_THREADS = """
@nproc 96
@lscpu CPU(s):                96
@lscpu Thread(s) per core:    2
@lscpu Core(s) per socket:    24
@lscpu Socket(s):             2
@mem MemTotal:       263840000 kB
@mem MemAvailable:   200000000 kB
@sinfo localhost|96|257000|190000|16/80/0/96|mix
@df /dev/mapper/cs_serv3-root 3905945600 3851413504 54532096 99% /
@has sbatch
@has squeue
@has scancel
@has module
@orca /opt/orca-6.1.1/orca
"""


def test_probe_is_read():
    r = cluster.parse_probe(PROBE_48_THREADS)
    assert (r.logical, r.physical, r.threads) == (96, 48, 2)
    assert r.memory_mb == 263840000 // 1024 and r.disk_free_mb == 54532096 // 1024
    node = r.nodes[0]
    assert (node.name, node.cpus, node.memory_mb, node.free_mb) == ('localhost', 96, 257000, 190000)
    assert (node.alloc, node.idle, node.other, node.total, node.state) == (16, 80, 0, 96, 'mix')
    assert r.slurm and r.orca == '/opt/orca-6.1.1/orca'
    assert cluster.parse_probe('garbage\n@nproc x\n@sinfo bad').nodes == ()


def test_plan_counts_physical_cores_when_slurm_counts_threads():
    p = cluster.plan(cluster.parse_probe(PROBE_48_THREADS))
    # 80 idle SLURM CPUs = 40 free physical cores of 48; MemAvailable 200000000 kB = 195312 MB;
    # 60 % of it over 40 processes = 2929.7 → 2900
    assert (p.processes, p.physical, p.physical_free, p.queued) == (40, 48, 40, False)
    assert p.maxcore == 2900 and p.mem_request == int(40 * 2900 * 1.25)
    asked = cluster.plan(cluster.parse_probe(PROBE_48_THREADS), wanted=48)
    assert asked.processes == 48 and asked.queued  # more than free: it waits in the queue
    assert cluster.plan(cluster.parse_probe(PROBE_48_THREADS), wanted=500).processes == 48  # never above the cores


def test_plan_takes_the_memory_of_the_panel():
    # the processes and the memory per process of the panel of Sextant (no question at the start); --mem from them
    p = cluster.plan(cluster.parse_probe(PROBE_48_THREADS), wanted=8, maxcore=3500)
    assert (p.processes, p.maxcore, p.mem_request) == (8, 3500, int(8 * 3500 * 1.25))
    assert cluster.plan(cluster.parse_probe(PROBE_48_THREADS), maxcore=20).maxcore == 100  # never below 100 MB


def test_plan_without_threads_busy_node_and_memory_unknown_to_slurm():
    text = '@nproc 32\n@lscpu Thread(s) per core: 1\n@lscpu Core(s) per socket: 16\n@lscpu Socket(s): 2\n' \
           '@mem MemTotal: 131072000 kB\n@sinfo localhost|32|1|0|32/0/0/32|alloc\n@has sbatch\n@has squeue\n'
    p = cluster.plan(cluster.parse_probe(text))
    # nothing free: all 32 cores asked, the job waits; SLURM has no memory for the node (RealMemory 1): no --mem;
    # 60 % of 128000 MB over 32 = 2400
    assert (p.processes, p.physical_free, p.queued, p.mem_request, p.maxcore) == (32, 0, True, None, 2400)
    assert '--mem' not in cluster.job_script(p)
    bare = cluster.plan(cluster.parse_probe('@nproc 8'))
    # a machine without SLURM: nothing keeps the jobs apart there, so at most 80 % of its cores are given (6 of 8)
    assert (bare.processes, bare.maxcore, bare.mem_request) == (6, 1000, None)


def test_summary_line():
    r = cluster.parse_probe(PROBE_48_THREADS)
    line = cluster.summary(r, cluster.plan(r), 'serv3')
    assert line == 'serv3: свободно 40 из 48 ядер, свободно памяти 191 ГБ, на диске 52 ГБ'


def test_job_script():
    p = cluster.plan(cluster.parse_probe(PROBE_48_THREADS))
    text = cluster.job_script(p, 'module add mpi/openmpi-x86_64 && module add orca-6.1.1', 'az-H₂O; rm -rf ~')
    lines = text.splitlines()
    assert lines[0] == '#!/bin/bash -l'
    assert '#SBATCH -n 40' in lines and '#SBATCH -N 1' in lines and f'#SBATCH --mem={p.mem_request}M' in lines
    assert '#SBATCH -J az-H_O__rm_-rf__' in lines  # nothing of the name reaches the shell
    assert lines.index('module add mpi/openmpi-x86_64') < lines.index('module add orca-6.1.1') < lines.index('cd "$SLURM_SUBMIT_DIR"')
    assert '"$ORCA" input.inp > input.out 2>&1' in lines and any('orca_2mkl' in line for line in lines)
    # the job writes its exit code (remote_job: the end known at once), the mark of an earlier run removed first
    assert lines.index(cluster.END_LINES[0]) < lines.index(cluster.END_LINES[1]) < lines.index('module add mpi/openmpi-x86_64')
    assert all(not line.startswith('#SBATCH') for line in lines[lines.index(cluster.END_LINES[0]):])


def test_the_orca_reported_is_the_one_the_job_runs():
    # serv .103 (Windows check 2026-11-24): orca of a login is /opt/orca5, the job puts the newest folder first
    found = cluster.parse_probe('@orca /opt/orca5/orca\n@prog orca /opt/orca5/orca\n@orcadir /opt/orca5/orca\n'
                                '@orcadir /opt/orca6.1.1/orca\n@mpiprobed\n')
    assert 'export PATH=/opt/orca6.1.1:$PATH' in cluster.suggested_setup(found)
    assert cluster.find_on_server(found, 'orca') == '/opt/orca6.1.1/orca'
    assert cluster.find_on_server(found, 'orca', cluster.setup_for('', found, 'orca')) == '/opt/orca6.1.1/orca'
    assert cluster.find_on_server(found, 'orca', 'export PATH=/opt/orca5:$PATH') == '/opt/orca5/orca'  # the user's lines
    assert cluster.find_on_server(found, 'orca', 'module load myorca') == 'строки окружения профиля'


def test_job_number_and_queue_state():
    assert cluster.submitted('Submitted batch job 4127\n') == '4127'
    assert cluster.submitted('sbatch: error: Batch job submission failed') is None
    assert 'squeue -h -j 4127 -o "%T|%M|%R" 2>/dev/null' in cluster.queue_command(4127)
    assert cluster.queue_state('RUNNING|1:02|localhost\n') == 'RUNNING'
    assert cluster.queue_state('PENDING|0:00|(Resources)') == 'PENDING' and cluster.queue_state('') is None


def test_processes_written_into_the_input():
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    text = orca_input(water, Calculation(cores=4, memory_mb=1000))
    changed = cluster.with_processes(text, 40, 2800)
    assert '%pal nprocs 40 end' in changed and '%maxcore 2800' in changed
    assert '%pal nprocs 4 end' not in changed and changed.count('%pal') == 1 and changed.count('%maxcore') == 1
    bare = cluster.with_processes('! HF def2-SVP\n* xyz 0 1\nHe 0 0 0\n*\n', 8, 1500)
    assert bare.index('%pal nprocs 8 end') < bare.index('%maxcore 1500') < bare.index('* xyz')
    block = cluster.with_processes('! HF\n%pal\n  nprocs 2\nend\n* xyz 0 1\nHe 0 0 0\n*\n', 6, 900)
    assert 'nprocs 6' in block and 'nprocs 2' not in block and block.count('%pal') == 1  # the block keeps its layout


# the three servers as they answered on 27 October 2026 (free -g «available» × 1024² kB; sinfo, lscpu, modules).
# ASSUMPTION: the /opt/orca* lines of serv2 were not probed that day — /opt/orca6 is the folder of the laboratory's
# orca.sh, /opt/orca5.0.4 is added here to check that the newest is taken.
SERV4 = """@nproc 128
@lscpu CPU(s): 128
@lscpu Thread(s) per core: 2
@lscpu Core(s) per socket: 32
@lscpu Socket(s): 2
@mem MemTotal: 526385152 kB
@mem MemAvailable: 468713472 kB
@sinfo localhost|128|502000|13338|96/32/0/128|mix
@df /dev/mapper/cs-home 2684354560 2147483648 502267904 81% /home
@has sbatch
@has squeue
@has module
@module prog/orca5
@module prog/orca6.1.1
"""
SERV2 = """@nproc 48
@lscpu CPU(s): 48
@lscpu Thread(s) per core: 2
@lscpu Core(s) per socket: 12
@lscpu Socket(s): 2
@mem MemAvailable: 447741952 kB
@sinfo localhost|48|450000|323455|40/8/0/48|mix
@has sbatch
@has squeue
@orcadir /opt/orca6/orca
@orcadir /opt/orca5.0.4/orca
"""
SERV3 = """@nproc 96
@lscpu CPU(s): 96
@lscpu Thread(s) per core: 2
@lscpu Core(s) per socket: 24
@lscpu Socket(s): 2
@mem MemAvailable: 331350016 kB
@sinfo localhost|96|377000|308509|86/10/0/96|mix
@has sbatch
@has squeue
@has module
@module /etc/modulefiles:
@module orca-6.1.1
"""


def test_three_laboratory_servers():
    four, two, three = (cluster.parse_probe(t) for t in (SERV4, SERV2, SERV3))
    assert (four.physical, two.physical, three.physical) == (64, 24, 48)  # cores, not the threads SLURM counts
    p4, p2, p3 = cluster.plan(four), cluster.plan(two), cluster.plan(three)
    # idle threads / 2: 32 → 16, 8 → 4, 10 → 5 physical cores free now
    assert (p4.processes, p2.processes, p3.processes) == (16, 4, 5)
    # serv4: SLURM says 13338 MB free, MemAvailable 457728 MB: 60 % over 16 = 17164 → the limit 8000, not 500
    assert cluster.free_memory(four) == 468713472 // 1024 and p4.maxcore == 8000
    assert p4.mem_request == 16 * 8000 * 1.25 and four.disk_free_mb == 502267904 // 1024
    # what puts ORCA into PATH differs: an Lmod module on serv4, a folder on serv2, a module on serv3
    assert cluster.suggested_setup(four) == 'module load mpi/openmpi-x86_64\nmodule load prog/orca6.1.1'
    assert cluster.suggested_setup(two) == ('module load mpi/openmpi-x86_64\nexport PATH=/opt/orca6:$PATH\n'
                                            'export LD_LIBRARY_PATH=/opt/orca6:$LD_LIBRARY_PATH')
    assert three.orca_modules == ('orca-6.1.1',)  # the folder line of `module -t avail` is not a module
    assert cluster.suggested_setup(cluster.parse_probe('@nproc 4')) == ''
    script = cluster.job_script(p3, cluster.suggested_setup(three)).splitlines()
    assert 'module load orca-6.1.1' in script and '#SBATCH -n 5' in script


@pytest.mark.skipif(os.name == 'nt' or shutil.which('bash') is None, reason='the probe is a bash script of the server')
def test_the_probe_runs_and_succeeds_on_a_machine_without_slurm_or_modules():
    import subprocess

    done = subprocess.run(['bash', '-c', cluster.probe_command('/tmp')], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0  # a missing sinfo or module must not make the probe fail (serv2 has no ORCA module)
    r = cluster.parse_probe(done.stdout)
    assert r.logical and r.logical >= 1 and r.disk_free_mb is not None


def test_probe_of_a_mac():
    # no nproc, lscpu and /proc/meminfo (macOS, where the fake server of the tests runs the probe): getconf and
    # sysctl — 10 logical, 8 physical, 16 GiB
    r = cluster.parse_probe('@nproc 10\n@physical 8\n@memsize 17179869184\n')
    assert (r.logical, r.physical, r.threads, r.memory_mb) == (10, 8, 1, 16384)
    linux = cluster.parse_probe(SERV3 + '@physical 2\n')  # lscpu wins where it answered
    assert linux.physical == cluster.parse_probe(SERV3).physical



def test_programs_found_on_the_server():
    # the programs of Sextant on the server — in PATH (command -v) or as environment modules; ORCA also by
    # the old lines of the probe (@orca, @orcadir, @module); the setup lines of the profile count as «it is there»
    probe = SERV3 + '@prog xtb /home/user/miniconda3/bin/xtb\n@progmodule prog/psi4-1.9\n@progmodule /etc/modulefiles:\n'
    r = cluster.parse_probe(probe)
    assert r.programs == (('xtb', '/home/user/miniconda3/bin/xtb'),) and r.program_modules == ('prog/psi4-1.9',)
    assert cluster.find_on_server(r, 'xtb') == '/home/user/miniconda3/bin/xtb'
    assert cluster.find_on_server(r, 'psi4') == 'модуль prog/psi4-1.9'
    assert cluster.find_on_server(r, 'orca') == 'модуль orca-6.1.1'  # SERV3: the module of `module -t avail`
    assert cluster.find_on_server(r, 'gaussian') is None
    assert cluster.find_on_server(r, 'gaussian', 'module load g16') == 'строки окружения профиля'
    assert cluster.find_on_server(cluster.parse_probe(SERV2), 'orca') == '/opt/orca6/orca'
    assert cluster.find_on_server(cluster.parse_probe('@prog g16 /opt/g16/g16'), 'gaussian') == '/opt/g16/g16'


def test_mopac_on_the_server():
    """MOPAC found by the probe (in PATH or as a module) and its lines of job.sh."""
    found = cluster.parse_probe('@prog mopac /opt/mopac/bin/mopac\n@progmodule chem/mopac-23.1\n@progmodule chem/mopac-22.0')
    assert cluster.find_on_server(found, 'mopac') == '/opt/mopac/bin/mopac'
    assert cluster.suggested_setup(found, 'mopac') == 'module load chem/mopac-23.1'
    modules_only = cluster.parse_probe('@progmodule chem/mopac-23.1')
    assert cluster.find_on_server(modules_only, 'mopac').endswith('chem/mopac-23.1')
    assert cluster.suggested_setup(cluster.parse_probe(''), 'mopac') == ''
    plan = cluster.Plan(processes=8, maxcore=1000, mem_request=10000, physical=16, physical_free=16, queued=False)
    script = cluster.job_script(plan, 'module load chem/mopac-23.1', 'az-H2O', 'H2O_PM7', 'mopac')
    assert '#SBATCH -c 8' in script and '#SBATCH -n 1' in script and '#SBATCH -n 8' not in script
    assert 'module load chem/mopac-23.1' in script and '"$MOPAC" H2O_PM7.mop > H2O_PM7.stdout 2>&1' in script
    assert 'mopac' in cluster.probe_command('~/calc')


def test_lines_of_the_profile_and_those_found_for_the_program():
    # the lines of the profile written for MOPAC no longer take the place of the lines found for ORCA
    two = cluster.parse_probe(SERV2)  # ORCA in /opt/orca6
    mopac_line = 'export PATH=/opt/anaconda3/envs/mopac/bin:$PATH'
    found = cluster.suggested_setup(two)
    assert cluster.setup_for(mopac_line, two, 'orca') == mopac_line + '\n' + found
    assert cluster.setup_for(mopac_line, two, 'mopac') == mopac_line  # it names MOPAC: the user's choice for it
    assert cluster.setup_for('', two, 'orca') == found
    assert cluster.setup_for('module load prog/orca-5.0.4', two, 'orca') == 'module load prog/orca-5.0.4'
    assert cluster.setup_for('source ~/.env', cluster.parse_probe('@nproc 4'), 'orca') == 'source ~/.env'


def test_the_partition_and_the_time_limit_of_the_profile_go_into_the_head_of_the_job():
    # -p, -t, -A, --qos of the
    # profile, and #SBATCH lines written among the setup lines, stand before the first command (sbatch reads no
    # further); a partition that has the name of a program is not taken for that program
    from modules.sextant import remote

    profile = remote.ServerProfile('hpc', 'hpc.univ', 22, 'u', partition='long', time_limit='2-00:00:00',
                                   account='chem-lab', qos='normal')
    assert profile.directives() == ['#SBATCH -p long', '#SBATCH -t 2-00:00:00', '#SBATCH -A chem-lab',
                                    '#SBATCH --qos=normal']
    plan = cluster.Plan(processes=8, maxcore=1000, mem_request=None, physical=16, physical_free=16, queued=False)
    nothing = cluster.parse_probe('')
    setup = cluster.setup_for('module load orca/6.1\n#SBATCH --gres=gpu:0', nothing, 'orca',
                              profile.directives())
    for script in (cluster.job_script(plan, setup, 'az-H2O', 'h2o'), cluster.batch_script(plan, setup, 'q', [('a', 'a', '1')])):
        lines = script.splitlines()
        first_command = next(i for i, line in enumerate(lines) if line.strip() and not line.startswith('#'))
        for wanted in profile.directives() + ['#SBATCH --gres=gpu:0']:
            assert wanted in lines and lines.index(wanted) < first_command, (wanted, script)
        assert 'module load orca/6.1' in lines
    assert cluster.commands(setup) == 'module load orca/6.1'
    assert cluster.find_on_server(nothing, 'orca', '#SBATCH -p orca') is None
    assert 'sinfo -h -N -p long -o' in cluster.probe_command('~/calc', 'long')
    assert 'sinfo -h -N -o' in cluster.probe_command('~/calc')
    assert remote.ServerProfile('a', 'h', 22, 'u').directives() == []
    bad = remote.ServerProfile('a', 'h', 22, 'u', partition='long; rm', time_limit='two days')
    problems = ' '.join(bad.validate())
    assert 'partition' in problems and 'Предел времени' in problems
    for good in ('90', '12:00:00', '2-00', '2-12:30', '7-00:00:00', '30:00'):
        assert not remote.ServerProfile('a', 'h', 22, 'u', time_limit=good).validate(), good
    kept = remote.ServerProfile.from_dict(profile.to_dict())
    assert kept.directives() == profile.directives()


def test_the_lines_of_one_program_reach_only_its_jobs():
    # serv3 as it answered on 2026-11-22: the modules cp2k and orca-6.1.1; CP2K there needs «module load cp2k» and
    # «source /opt/cp2k/tools/toolchain/install/setup» (the colleague who built it). Written as lines of every job, the
    # second one reached the jobs of ORCA too, and alone it took the place of «module load cp2k». As the lines of CP2K
    # they go into its jobs as they are — after the common ones — and nowhere else
    serv3 = cluster.parse_probe('@nproc 48\n@has sbatch\n@has squeue\n@has module\n@orcadir /opt/orca6.1.1/orca\n'
                                '@module orca-6.1.1\n@progmodule cp2k\n@progmodule orca-6.1.1\n')
    common = 'export PATH=/opt/anaconda3/envs/mopac/bin:$PATH'
    cp2k = 'module load cp2k\nsource /opt/cp2k/tools/toolchain/install/setup'
    assert cluster.setup_for(common, serv3, 'cp2k', program=cp2k) == common + '\n' + cp2k
    orca = cluster.setup_for(common, serv3, 'orca')  # no lines of ORCA: it is found on the server, as before
    assert 'cp2k' not in orca and orca.endswith('module load mpi/openmpi-x86_64\nmodule load orca-6.1.1')
    assert cluster.setup_for(common, serv3, 'cp2k') == common + '\nmodule load cp2k'  # none of its own: found too
    # the trap the lines of one program remove: the «source» line among the common ones named CP2K, and the module was
    # no longer loaded
    assert 'module load cp2k' not in cluster.setup_for(common + '\n' + cp2k.splitlines()[1], serv3, 'cp2k')
    assert cluster.setup_for('', serv3, 'cp2k', ('#SBATCH -p long',), cp2k) == '#SBATCH -p long\n' + cp2k
    script = cluster.job_script(cluster.plan(serv3, wanted=10), cluster.setup_for(common, serv3, 'cp2k', program=cp2k),
                                program='cp2k')
    lines = script.splitlines()
    assert lines.index('source /opt/cp2k/tools/toolchain/install/setup') == lines.index('module load cp2k') + 1
    assert lines.index('module load cp2k') < next(k for k, line in enumerate(lines) if line.startswith('CP2K='))
    # with lines of its own the program is the user's: not said to be missing on a server where the probe saw none
    bare = cluster.parse_probe('@nproc 4')
    assert cluster.find_on_server(bare, 'mopac') is None
    assert cluster.find_on_server(bare, 'mopac', program='source ~/env.sh') == 'строки окружения профиля'


# serv1 of the laboratory (192.0.2.101, 2026-11-22): 20 cores, no SLURM; xtb and CREST in the home folder, MOPAC in
# an environment of conda — written by hand as the probe prints them
SERV1 = """@nproc 20
@lscpu CPU(s): 20
@lscpu Thread(s) per core: 1
@lscpu Core(s) per socket: 10
@lscpu Socket(s): 2
@mem MemTotal: 131000000 kB
@mem MemAvailable: 117000000 kB
@df /dev/sda1 1000000 400000 600000 40% /home
@orca /opt/orca/orca
@prog orca /opt/orca/orca
@found /home/user/xtb-6.7.1/bin/xtb
@found /home/user/crest/crest
@found /home/user/old/copy/of/crest
@found /opt/anaconda3/envs/mopac/bin/mopac
@load 9.61
"""


def test_a_server_without_slurm_and_the_programs_outside_path():
    res = cluster.parse_probe(SERV1)
    assert not res.slurm and res.load == 9.61 and cluster.busy_cores(res) == 10
    assert ('xtb', '/home/user/xtb-6.7.1/bin/xtb') in res.found
    # the programs outside PATH are found and named with their path (the shortest of several copies)
    assert cluster.find_on_server(res, 'xtb') == '/home/user/xtb-6.7.1/bin/xtb'
    assert cluster.find_on_server(res, 'crest') == '/home/user/crest/crest'
    assert cluster.find_on_server(res, 'psi4') is None
    # the lines of the job put such a program into PATH; ORCA in PATH needs none
    assert cluster.suggested_setup(res, 'mopac') == 'export PATH=/opt/anaconda3/envs/mopac/bin:$PATH'
    assert cluster.suggested_setup(res, 'orca') == ''
    # the cores: 20, of them 10 busy by the load; with a new calculation at most 16 (80 %) may be busy → 6
    chosen = cluster.plan(res)
    assert (chosen.physical, chosen.physical_free, chosen.processes) == (20, 6, 6) and cluster.room(res) == 6
    assert cluster.no_room(res, chosen, 'serv1') == ''
    assert 'свободно сейчас 6 из 20' in cluster.no_room(res, cluster.plan(res, wanted=8), 'serv1')
    busy = cluster.parse_probe(SERV1.replace('@load 9.61', '@load 18.2'))
    assert cluster.plan(busy).physical_free == 0 and 'свободных ядер сейчас нет' in cluster.no_room(busy, cluster.plan(busy, wanted=2), 'serv1')
    # a server with SLURM is not refused here (its queue decides), and its room is 80 % of the node with the busy ones
    slurm = cluster.parse_probe(SERV3)
    assert cluster.no_room(slurm, cluster.plan(slurm, wanted=48), 'serv3') == ''
    free, physical = cluster.plan(slurm).physical_free, cluster.plan(slurm).physical
    assert cluster.room(slurm) == max(0, min(free, int(0.8 * physical) - (physical - free)))


def test_the_state_and_the_stop_of_a_job_without_slurm():
    # with SLURM — squeue and scancel as before; without — the process the helper started (its pid), only while it
    # runs a script, and its session, group and itself are ended
    state, stop = cluster.queue_command(4321), cluster.cancel_command(['4321', '77'])
    assert 'squeue -h -j 4321' in state and 'ps -p 4321 -o args=' in state
    assert 'scancel 4321 77' in stop and 'pkill -TERM -s 77' in stop and 'kill -TERM -- -4321' in stop
    assert cluster.queue_state('RUNNING|1:02|nohup') == 'RUNNING' and cluster.queue_state('') is None
    with pytest.raises(ValueError):
        cluster.cancel_command('1; rm -rf ~')  # only numbers reach the server


def test_the_helper_without_sbatch_reads_the_time_limit(tmp_path):
    if os.name == 'nt' or shutil.which('bash') is None:
        pytest.skip('a POSIX shell is needed')
    import subprocess
    import time

    from azimuth.runtime import runs

    (tmp_path / runs.HELPER).write_text(runs.helper_script(), encoding='ascii')
    (tmp_path / 'job.sh').write_text('#!/bin/bash -l\n#SBATCH -t 00:01:00\ncd "$SLURM_SUBMIT_DIR"\necho "$SLURM_JOB_NAME" > ran.txt\n')
    env = {**os.environ, 'PATH': '/usr/bin:/bin'}  # no sbatch here
    done = subprocess.run(['bash', runs.HELPER, 'tok', 'az-water', 'job.sh'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert done.returncode == 0 and runs.answer_job(done.stdout), done
    end = time.monotonic() + 10
    while time.monotonic() < end and not (tmp_path / 'ran.txt').is_file():
        time.sleep(0.05)
    assert (tmp_path / 'ran.txt').read_text().strip() == 'az-water'  # the script ran in its folder, by itself
    again = subprocess.run(['bash', runs.HELPER, 'tok', 'az-water', 'job.sh'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert runs.answer_job(again.stdout) == runs.answer_job(done.stdout)  # the same token: no second start


def test_the_lines_found_for_orca_fit_the_server():
    # serv1 (2026-11-23): modules prog/orca and prog/orca_4_2_1, no Open MPI module — the job got «module load
    # mpi/openmpi-x86_64» (no such module) and the old 4.2.1 as the «newest», and ORCA was not found
    serv1 = cluster.parse_probe('@nproc 20\n@mpiprobed\n@module prog/orca\n@module prog/orca_4_2_1\n'
                                '@progmodule prog/mopac\n@progmodule prog/mopac_gpu\n')
    assert serv1.mpi_modules == () and cluster.suggested_setup(serv1) == 'module load prog/orca'
    assert cluster.suggested_setup(serv1, 'mopac') == 'module load prog/mopac'
    # serv3: the module of the laboratory is there — as before; another Open MPI module is taken when it is the only one
    serv3 = cluster.parse_probe('@nproc 48\n@mpiprobed\n@mpimodule mpi/openmpi-x86_64\n@module orca-6.1.1\n@module orca-5.0.4\n')
    assert cluster.suggested_setup(serv3) == 'module load mpi/openmpi-x86_64\nmodule load orca-6.1.1'
    other = cluster.parse_probe('@nproc 48\n@mpiprobed\n@mpimodule openmpi/4.1.6\n@orcadir /opt/orca6/orca\n')
    assert cluster.suggested_setup(other).splitlines()[0] == 'module load openmpi/4.1.6'
    # an answer recorded before the probe asked about Open MPI keeps the module of the laboratory
    old = cluster.parse_probe('@nproc 48\n@module orca-6.1.1\n')
    assert old.mpi_modules is None and cluster.suggested_setup(old) == 'module load mpi/openmpi-x86_64\nmodule load orca-6.1.1'
