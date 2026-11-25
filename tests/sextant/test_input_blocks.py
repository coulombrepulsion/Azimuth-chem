"""«Правка → Вставить блок» of Sextant (modules/sextant/input_blocks.py) — a block of ORCA before the
coordinates, its keyword after the «!» lines; Link 0 of Gaussian at the top."""

from modules.sextant import input_blocks as ib

ORCA = '! B3LYP def2-SVP Opt\n%maxcore 1000\n\n* xyz 0 1\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n*\n'


def test_a_block_of_orca_goes_before_the_coordinates():
    pal = next(b for b in ib.BLOCKS['orca'] if b[1].startswith('%pal'))
    text = ib.inserted(ORCA, 'orca', pal[1], pal[2])
    assert text.index('%pal') < text.index('* xyz') and text.index('%maxcore') < text.index('%pal')
    assert text.endswith('H -0.24 0.93 0\n*\n')


def test_a_keyword_it_needs_after_the_keywords():
    moinp = next(b for b in ib.BLOCKS['orca'] if b[2] == 'MORead')
    text = ib.inserted(ORCA, 'orca', moinp[1], moinp[2])
    lines = text.split('\n')
    assert lines[0] == '! B3LYP def2-SVP Opt' and lines[1] == '! MORead' and '%moinp' in text
    again = ib.inserted(text, 'orca', moinp[1], moinp[2])
    assert again.count('! MORead') == 1  # not twice


def test_link0_of_gaussian_at_the_top_and_no_coordinates_at_the_end():
    gjf = '#p B3LYP/def2SVP Opt\n\nwater\n\n0 1\nO 0 0 0\n\n'
    assert ib.inserted(gjf, 'gaussian', '%mem=4GB').startswith('%mem=4GB\n#p')
    assert ib.inserted('! HF', 'orca', '%pal\n  nprocs 2\nend') == '! HF\n%pal\n  nprocs 2\nend\n'
