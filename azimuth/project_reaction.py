"""The reaction of a project: its molecules as reactants, transition states and products, and ΔG of the reaction
from their results.

HEADER ΔG of a reaction from the molecules of a project. A molecule of a project gets a role in the reaction (reactant,
    transition state, product) and a coefficient; «ΔG реакции…» fills the window «Диаграмма реакции»
    (modules/spectrum/views/reaction_view.py) with the current results of those molecules — the reactants as the first
    stage, every transition state as a stage of its own, the products as the last — and shows ΔG: the barriers, the
    energy of the reaction, the checks of the diagram (the same method, the atoms of both sides) and its quasi-RRHO and
    standard state. Wilkinson convention, sections 1-8.

§1 THEORY
    ΔG = Σ ν G(products) − Σ ν G(reactants) with G of every species from its own calculation of frequencies
    (modules/spectrum/analysis/reaction.py §1, thermo.py): a coefficient ν is the species taken ν times.
§2 ALGORITHM
    The role is kept in the entry of the molecule: entry['reaction'] = {'role': ROLE, 'coeff': n} (no key — no role).
    stages(project, read) -> (stages, problems): the molecules with a role in the order of the list, grouped — the
    reactants, then every transition state alone, then the products; each one's current result read by read(path,
    label) (reaction.read_species) and put coeff times. A molecule without a result, a result that cannot be read or
    has no frequencies is a problem (said, the rest go on); fewer than a reactant and a product — ValueError.
§4 SPECIFICATION
    ROLES; role_of(entry) -> (role | None, coeff); badge(entry) -> text for the list; set_role(path, ids, role,
    coeff=None) (role None — none); stages(project, read=reaction.read_species) -> (list of reaction.Stage, problems).
§7 TEST CASES tests/projects/test_project_reaction.py.
"""

from azimuth import projects
from azimuth.i18n import tr

ROLES = ('reactant', 'ts', 'product')
NAMES = {'reactant': 'реагент', 'ts': 'переходное состояние', 'product': 'продукт'}
SHORT = {'reactant': 'реагент', 'ts': 'ПС', 'product': 'продукт'}
MAX_COEFF = 20


def role_of(entry):
    found = entry.get('reaction') or {}
    role = found.get('role')
    if role not in ROLES:
        return None, 1
    try:
        coeff = int(found.get('coeff', 1))
    except (TypeError, ValueError):
        coeff = 1
    return role, max(1, min(MAX_COEFF, coeff))


def badge(entry):
    """« · реагент ×2» after the name of the molecule in the list, '' without a role."""
    role, coeff = role_of(entry)
    if role is None:
        return ''
    return ' · ' + tr(SHORT[role]) + (f' ×{coeff}' if coeff > 1 else '')


def set_role(path, ids, role, coeff=None):
    """The role (one of ROLES, or None: none) and the coefficient of the molecules ids of the project at path; the
    coefficient kept when not given. Returns how many molecules were changed."""
    if role is not None and role not in ROLES:
        raise ValueError(f'Unknown role {role!r}')
    changed = 0
    with projects.edit(path) as project:
        for ident in ids:
            entry = project.entry(ident)
            if role is None:
                if entry.pop('reaction', None) is not None:
                    changed += 1
                continue
            old_role, old_coeff = role_of(entry)
            value = {'role': role, 'coeff': max(1, min(MAX_COEFF, int(coeff if coeff is not None else old_coeff)))}
            if entry.get('reaction') != value:
                entry['reaction'] = value
                changed += 1
    return changed


def stages(project, read=None):
    """The stages of the reaction of the project (reaction.Stage) and the problems met (texts)."""
    from modules.spectrum.analysis import reaction

    read = read or reaction.read_species
    groups = {role: [] for role in ROLES}
    problems = []
    for entry in project.molecules:
        role, coeff = role_of(entry)
        if role is None:
            continue
        attempt = project.current(entry)
        output = attempt.get('output') if attempt else ''
        if not output:
            problems.append(tr('«{}» — нет результата расчёта').format(entry['name']))
            continue
        try:
            species = read(str(project.absolute(output)), entry['name'])
        except (OSError, ValueError) as exc:
            problems.append(tr('«{}» — {}').format(entry['name'], exc))
            continue
        if not species.frequencies and species.typed is None:
            problems.append(tr('«{}» — нет частот: для ΔG нужен расчёт частот, без него — только ΔE').format(entry['name']))
        groups[role].append((species, coeff))
    if not groups['reactant'] or not groups['product']:
        raise ValueError(tr('Отметьте в списке проекта хотя бы один реагент и один продукт: правый щелчок по молекуле → '
                            '«Роль в реакции».'))

    def stage(label, members):
        return reaction.Stage(label, tuple(s for s, n in members for _ in range(n)))

    def side(members):
        return ' + '.join((f'{n} ' if n > 1 else '') + s.label for s, n in members)

    found = [stage(side(groups['reactant']), groups['reactant'])]
    found += [stage(s.label + ' ‡', [(s, n)]) for s, n in groups['ts']]
    found.append(stage(side(groups['product']), groups['product']))
    return found, problems
