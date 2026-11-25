"""«Сервер → Очередь кластера…» (modules/sextant/cluster_queue.py) — squeue read, scancel of the numbers only,
the window over a connection that answers as SLURM."""

import pytest

from modules.sextant import cluster_queue as cq

LISTING = """1201|azimuth_h2o|user|RUNNING|12:03|2-00:00:00|1|8|node03
1202|azimuth_dvb|user|PENDING|0:00|2-00:00:00|1|16|(Resources)
1203_4|gaussian_job|user|PENDING|0:00|1-00:00:00|1|4|(Priority)
squeue: error: something not a row
"""


def test_the_queue_is_read_and_cancelled_by_numbers_only():
    rows = cq.parse(LISTING)
    assert [r.id for r in rows] == ['1201', '1202', '1203_4'] and rows[1].reason == '(Resources)'
    assert cq.counts(rows) == (1, 2) and cq.ours(rows[0]) and not cq.ours(rows[2])
    assert '-u "$USER"' in cq.list_command() and '-u' not in cq.list_command(everyone=True)
    assert cq.cancel_command(['1201', '1203_4']) == 'scancel 1201 1203_4'
    for bad in ([], ['1201; rm -rf ~'], ['abc']):
        with pytest.raises(ValueError):
            cq.cancel_command(bad)


def test_the_window_shows_the_jobs_and_cancels_the_chosen(tmp_path):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication, QWidget

    from modules.sextant.remote import ServerProfile

    app = QApplication.instance() or QApplication([])
    sent = []

    class Connection:
        def text(self, command, timeout=None):
            sent.append(command)
            return '' if command.startswith('scancel') else LISTING

    owner = QWidget()
    window = cq.QueueWindow(owner, ServerProfile('serv3', 'serv3.lab', 22, 'user', '~/azimuth'), Connection())
    try:
        assert window.table.topLevelItemCount() == 3 and 'идут 1, ждут 2' in window.status.text()
        assert window.table.topLevelItem(0).text(3) == 'идёт' and not window.cancel_button.isEnabled()
        window.table.topLevelItem(1).setSelected(True)
        assert window.cancel_button.isEnabled()
        assert window.cancel(confirm=False) == 0 and not any(c.startswith('scancel') for c in sent)
        assert window.cancel(confirm=True) == 1 and 'scancel 1202' in sent
        window.everyone.setChecked(True)
        assert '-u' not in sent[-1]
    finally:
        window.close()
        owner.deleteLater()
        assert app is not None
