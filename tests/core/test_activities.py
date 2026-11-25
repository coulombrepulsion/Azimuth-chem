"""azimuth/activities.py: the long work behind a window put away — one sign in the left panel."""

from azimuth.activities import Board


def test_an_activity_is_shown_while_it_is_put_away_and_until_its_end_is_seen():
    board, told = Board(), []
    board.listen(lambda b: told.append(len(b.shown())))
    board.start('conformers', 'Поиск конформеров', total=10)
    assert board.shown() == [] and board.running()  # its window is open: nothing in the panel
    board.park('conformers')
    assert [a.key for a in board.shown()] == ['conformers'] and board.get('conformers').fraction() == 0.0
    board.progress('conformers', done=4, note='xtb: конформер 5 из 10')
    assert board.get('conformers').fraction() == 0.4
    board.finish('conformers', 'done', '3 мин')
    item = board.get('conformers')
    assert item.state == 'done' and item.fraction() == 1.0 and board.shown() and not board.running()
    board.seen('conformers')
    assert board.get('conformers') is None and told[-1] == 0


def test_an_end_seen_in_its_own_window_leaves_nothing():
    board = Board()
    board.start('job', 'Расчёт')
    board.finish('job', 'failed')
    assert board.get('job') is None  # it ended in front of the user
    board.start('job', 'Расчёт', parked=True)
    board.finish('job', 'stopped')
    assert board.shown()[0].state == 'stopped'
    board.park('job', False)  # its window opened again: the end is seen there
    assert board.get('job') is None
    board.start('a', 'A', parked=True)
    board.start('a', 'A again')  # started again: put away as it was
    assert board.get('a').parked and board.get('a').fraction() is None
