"""The history of calculations of Sextant (modules/sextant/history.py), without a window."""

import json

from azimuth.core import Calculation
from modules.sextant import history, runner
from modules.sextant.remote_job import JOB_JSON


class Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


def spec(folder, name='H2O_B3LYP.out'):
    folder.mkdir(parents=True, exist_ok=True)
    return runner.JobSpec('orca', folder, ('orca',), folder / name, {})


def test_records_states_and_the_way_back(tmp_path):
    settings = Settings()
    calc = Calculation(task='Оптимизация', cores=4, memory_mb=2000)
    items = []
    local = spec(tmp_path / 'a')
    items = history.add(items, history.record(local, 'orca', calc, 'H₂O · ORCA'))
    server = spec(tmp_path / 'b')
    items = history.add(items, history.record(server, 'orca', calc, 'H₂O · ORCA', place='serv3'))
    history.save(settings, items)
    items = history.load(settings)
    assert [d['folder'] for d in items] == [str(server.folder), str(local.folder)]
    assert history.state_of(items[1]) == 'running' or history.state_of(items[1]) == 'unknown'
    # closed while running: nothing stored, no end in the output
    items = [dict(d, state='') for d in items]
    assert history.state_of(items[1]) == 'unknown'
    local.output.write_text('...\n****ORCA TERMINATED NORMALLY****\n')
    assert history.state_of(items[1]) == 'finished'
    # on a server: job.json written after sbatch, no end yet — «check»
    (server.folder / JOB_JSON).write_text(json.dumps({'job': '4242', 'folder': '~/azimuth/b'}))
    assert history.state_of(items[0]) == 'server' and history.remote_info(items[0])['job'] == '4242'
    items = history.finish(items, server.folder, 'stopped')
    assert history.state_of(items[0]) == 'stopped'
    assert history.calculation_of(items[0]).task == 'Оптимизация' and history.calculation_of(items[0]).cores == 4
    # one entry per folder, at most LIMIT
    for k in range(history.LIMIT + 5):
        items = history.add(items, history.record(spec(tmp_path / f'c{k}'), 'xtb', calc, 'x'))
    assert len(items) == history.LIMIT
    items = history.add(items, history.record(spec(tmp_path / 'c3'), 'xtb', calc, 'x'))
    assert [d['folder'] for d in items].count(str(tmp_path / 'c3')) == 1
    import shutil
    shutil.rmtree(tmp_path / 'c3')
    assert history.state_of(items[0]) == 'missing'
    assert Settings().get(history.KEY) is None and history.load(Settings({history.KEY: 'not json'})) == []
