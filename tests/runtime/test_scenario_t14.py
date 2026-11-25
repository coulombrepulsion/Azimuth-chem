"""T14 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13: repeating five failed rows of 44 gives new attempts to the
same five molecules; the history before is kept.

A queue of 44 molecules of a project (MOPAC, the real output tests/data/mopac/h2o_pm7_opt.out for the 39 done, a cut
output for the 5 failed), imported into a project; a retry of the five prepared (batch_retry.prepare) and run (the same
real output put into its folders). No Qt. Oracles: the records of the project before and after, read back; the bytes of
batch.json of the first queue.
"""

import copy
import shutil
from pathlib import Path

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from modules.sextant import batch, batch_retry

DATA = Path(__file__).parents[1] / 'data'
OUTPUT = DATA / 'mopac' / 'h2o_pm7_opt.out'
WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
CALC = Calculation(method='PM7', task='Оптимизация')
COUNT = 44
FAILED = (3, 10, 17, 30, 41)


def queue_of_44(root):
    root.mkdir(parents=True)
    items = []
    for k in range(COUNT):
        folder = root / f'{k:02d}'
        folder.mkdir()
        result = folder / 'water.out'
        if k in FAILED:
            result.write_text(' MOPAC started\n *** cut ***\n', encoding='utf-8')
            items.append(batch.BatchItem(f'water {k:02d}', WATER, state='failed', folder=str(folder),
                                         output=str(result), note='MOPAC завершилась с ошибкой'))
        else:
            shutil.copy2(OUTPUT, result)
            items.append(batch.BatchItem(f'water {k:02d}', WATER, state='done', folder=str(folder), output=str(result)))
    queue = batch.Batch('mopac', CALC, items, root)
    queue.save()
    return queue


def test_t14_five_failed_of_44_repeated_get_new_attempts_and_the_history_stays(tmp_path):
    source = queue_of_44(tmp_path / 'source')
    project = projects.Project.create(tmp_path / 'project')
    parent = batch.Batch.load(project.import_batch(source.folder))
    before = projects.Project.load(project.path)
    ids = [e['id'] for e in before.molecules]
    history = {e['id']: copy.deepcopy(e['attempts']) for e in before.molecules}
    current = {e['id']: e['current'] for e in before.molecules}
    assert len(ids) == COUNT and all(current[ids[k]] is None for k in FAILED)
    first_queue = (parent.folder / 'batch.json').read_bytes()
    # Act: the five failed rows repeated (their structures as they were), then run
    requests = [(k, WATER, 0, 1, 'input') for k in FAILED]
    retry = batch_retry.prepare(parent, requests, CALC, 'mopac', 'local', project.root)
    assert retry.extra['project']['ids'] == [ids[k] for k in FAILED]
    for item in retry.items:
        folder = retry.folder / item.name.replace(' ', '_')
        folder.mkdir()
        shutil.copy2(OUTPUT, folder / 'water.out')
        item.folder, item.output = str(folder), str(folder / 'water.out')
        retry.finished(item, 'done')
    # Assert: the same 44 molecules in the same order
    after = projects.Project.load(project.path)
    assert [e['id'] for e in after.molecules] == ids
    for k, ident in enumerate(ids):
        entry = after.entry(ident)
        if k in FAILED:
            # the old attempts unchanged, one new attempt, which is the result now
            assert entry['attempts'][:len(history[ident])] == history[ident], k
            assert len(entry['attempts']) == len(history[ident]) + 1, k
            assert entry['current'] == entry['attempts'][-1]['id'] and entry['attempts'][-1].get('usable'), k
        else:  # the other 39 untouched
            assert entry['attempts'] == history[ident] and entry['current'] == current[ident], k
    assert (parent.folder / 'batch.json').read_bytes() == first_queue  # the first queue as it was
    assert batch.Batch.load(parent.folder).items[FAILED[0]].state == 'failed'
