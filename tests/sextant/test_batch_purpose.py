"""The purpose of a queue decides whether its results are conformers (PROJECT_RUNTIME_GUIDE.md §2, T22:
«Одинаковые формулы у разных веществ — пакет не превращается автоматически в ансамбль конформеров»).

Oracle: ethanol and dimethyl ether — one formula C2H6O, two substances; only a queue made from the page «Конформеры»
(purpose 'conformers') is ranked as conformers.
"""

import pytest

from azimuth.core import Calculation, read_xyz
from modules.sextant import batch

ETHANOL = read_xyz('3\nethanol (heavy atoms)\nC 0 0 0\nC 1.52 0 0\nO 2.0 1.35 0')
ETHER = read_xyz('3\ndimethyl ether (heavy atoms)\nC 0 0 0\nO 1.41 0 0\nC 1.9 1.33 0')


def queue(purpose, tmp_path, project=False):
    items = [batch.BatchItem(name, m) for name, m in (('ethanol', ETHANOL), ('ether', ETHER))]
    extra = {'project': {'manifest': '../project.qcc', 'ids': ['a', 'b']}} if project else {}
    return batch.Batch('orca', Calculation(), items, tmp_path, purpose=purpose, extra=extra)


def test_one_formula_is_not_enough(tmp_path):
    pytest.importorskip('PySide6')
    from modules.sextant.batch_actions import BatchTool

    assert ETHANOL.formula == ETHER.formula
    assert not BatchTool.queue_of_conformers(queue('structures', tmp_path, project=True))
    assert not BatchTool.queue_of_conformers(queue('structures', tmp_path))
    assert BatchTool.queue_of_conformers(queue('conformers', tmp_path))
    for purpose in ('binding', 'fukui', 'cda'):
        assert not BatchTool.queue_of_conformers(queue(purpose, tmp_path))
    # a batch.json saved has no purpose: the queues of the drawer were not bound to a project
    assert BatchTool.queue_of_conformers(queue('', tmp_path))
    assert not BatchTool.queue_of_conformers(queue('', tmp_path, project=True))


def test_the_purpose_is_kept_in_batch_json(tmp_path):
    made = queue('structures', tmp_path)
    made.save()
    assert batch.Batch.load(tmp_path).purpose == 'structures'
