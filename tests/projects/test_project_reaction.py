"""The molecules of a project as reactants, transition states and products with coefficients; «ΔG реакции…»
fills «Диаграмма реакции» from their current results (azimuth/project_reaction.py)."""

import pytest

from azimuth import projects
from azimuth import project_reaction as pr
from azimuth.core import Calculation, read_xyz
from modules.spectrum.analysis import reaction
from tests.projects.test_projects import app, window  # noqa: F401 — shared isolated Qt fixtures
from tests.projects.test_project_navigation import empty, ions

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n')
HARTREE = 627.509474  # kcal/mol (reaction.py)
G = {'A': (-100.0, 0.010), 'B': (-50.0, 0.020), 'T': (-249.95, 0.035), 'C': (-250.02, 0.030)}  # E, G − E (hartree)


def typed(path, label):
    energy, correction = G[label]
    return reaction.typed_species(label, energy, gibbs=correction, ts=label == 'T')


def with_results(project, names, missing=()):
    """Molecules named names, each with a current attempt whose output is a file of the project (read by typed)."""
    ids = {}
    for name in names:
        entry = project.add(WATER, Calculation(), name=name)
        ids[name] = entry['id']
        if name in missing:
            continue
        output = project.root / 'calculations' / f'{name}.out'
        output.write_text('result')
        entry['attempts'].append({'id': f'a-{name}', 'output': project.relative(output), 'state': 'done'})
        entry['current'] = f'a-{name}'
    project.save()
    return ids


def test_the_roles_are_kept_and_shown(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    ids = with_results(project, 'ABC')
    assert pr.set_role(project.path, [ids['A']], 'reactant', 2) == 1
    assert pr.set_role(project.path, [ids['C']], 'product') == 1
    view = projects.Project.load(project.path)
    assert pr.role_of(view.entry(ids['A'])) == ('reactant', 2) and pr.badge(view.entry(ids['A'])) == ' · реагент ×2'
    assert pr.role_of(view.entry(ids['C'])) == ('product', 1) and pr.badge(view.entry(ids['C'])) == ' · продукт'
    assert pr.role_of(view.entry(ids['B'])) == (None, 1) and pr.badge(view.entry(ids['B'])) == ''
    pr.set_role(project.path, [ids['A']], 'ts')  # the coefficient kept
    assert pr.role_of(projects.Project.load(project.path).entry(ids['A'])) == ('ts', 2)
    pr.set_role(project.path, [ids['A']], None)
    assert 'reaction' not in projects.Project.load(project.path).entry(ids['A'])
    with pytest.raises(ValueError):
        pr.set_role(project.path, [ids['A']], 'catalyst')
    assert pr.role_of({'reaction': {'role': 'product', 'coeff': 999}}) == ('product', pr.MAX_COEFF)


def test_the_stages_and_the_gibbs_energy_of_the_reaction(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    ids = with_results(project, 'ABTC')
    pr.set_role(project.path, [ids['A']], 'reactant', 2)
    pr.set_role(project.path, [ids['B']], 'reactant')
    pr.set_role(project.path, [ids['T']], 'ts')
    pr.set_role(project.path, [ids['C']], 'product')
    stages, problems = pr.stages(projects.Project.load(project.path), typed)
    assert problems == []
    assert [s.label for s in stages] == ['2 A + B', 'T ‡', 'C']
    assert [len(s.species) for s in stages] == [3, 1, 1] and stages[1].kind == 'ts'
    found = reaction.profile(stages, quantity='G', unit='kcal')
    gibbs = {k: e + c for k, (e, c) in G.items()}
    expected = (gibbs['C'] - 2 * gibbs['A'] - gibbs['B']) * HARTREE  # ΔG = ΣG(products) − ΣG(reactants)
    assert found.reaction == pytest.approx(expected, abs=1e-6)
    assert found.barriers[0].forward == pytest.approx((gibbs['T'] - 2 * gibbs['A'] - gibbs['B']) * HARTREE, abs=1e-6)


def test_the_problems_are_told_and_a_side_missing_is_an_error(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    ids = with_results(project, 'ABC', missing='B')
    pr.set_role(project.path, [ids['A']], 'reactant')
    with pytest.raises(ValueError, match='продукт'):
        pr.stages(projects.Project.load(project.path), typed)
    pr.set_role(project.path, [ids['B']], 'reactant')  # no result
    pr.set_role(project.path, [ids['C']], 'product')
    stages, problems = pr.stages(projects.Project.load(project.path), typed)
    assert len(problems) == 1 and '«B»' in problems[0] and 'нет результата' in problems[0]
    assert [s.label for s in stages] == ['A', 'C']

    def bare(path, label):  # a result without frequencies: said (only ΔE then)
        return reaction.Species(label=label, energy=G[label][0])

    stages, problems = pr.stages(projects.Project.load(project.path), bare)
    assert sum('нет частот' in p for p in problems) == 2


def test_the_menu_of_the_list_and_the_diagram_from_the_project(window, tmp_path):  # noqa: F811
    from PySide6.QtWidgets import QMenu

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    project = projects.Project.load(path)
    first, second = (e['id'] for e in project.molecules)
    with projects.edit(path) as editing:  # the two ions with results (read by a stand-in below)
        for entry in editing.molecules:
            output = editing.root / 'calculations' / (entry['id'] + '.out')
            output.parent.mkdir(exist_ok=True)
            output.write_text('result')
            entry['attempts'].append({'id': 'a-' + entry['id'], 'output': editing.relative(output), 'state': 'done'})
            entry['current'] = 'a-' + entry['id']
    menu = QMenu()
    roles = window.add_reaction_actions(menu, [first])
    names = [a.text() for a in roles.actions()]
    assert names[:4] == ['Реагент', 'Переходное состояние', 'Продукт', 'Не участвует'] and roles.actions()[3].isChecked()
    assert 'ΔG реакции…' in [a.text() for a in menu.actions()]
    roles.actions()[0].trigger()  # the first ion — a reactant
    window.set_reaction_role([second], 'product')
    window.ask_reaction_coefficient([first], 2)
    texts = [window.project_molecules.item(k, 1).text() for k in range(window.project_molecules.rowCount())]
    assert any(t.endswith(' · реагент ×2') for t in texts) and any(t.endswith(' · продукт') for t in texts)
    energies = {first: (-100.0, 0.01), second: (-201.0, 0.02)}
    names_of = {e['name']: e['id'] for e in projects.Project.load(path).molecules}

    def read(file, label):
        energy, correction = energies[names_of[label]]
        return reaction.typed_species(label, energy, gibbs=correction)

    shown = window.project_reaction(read)
    try:
        assert [len(s.species) for s in shown.stages] == [2, 1]
        assert shown.quantity.currentData() == 'G'
        result = shown.refresh()
        assert result.reaction == pytest.approx(((-201.0 + 0.02) - 2 * (-100.0 + 0.01)) * HARTREE, abs=1e-6)
    finally:
        shown.close()
