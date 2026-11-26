"""The menus of each section of the hub: Compass, Compass · Crystal, Sextant, Spectrum. Each function is the branch
of HubMenus._section_menus for its section and gets the helpers made there (menu, own, help_menu…).

Split off hub/menus.py (0.222.30).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QApplication
from azimuth.i18n import to_source, tr


def _held():
    """True while a job of the window is running (azimuth.tasks.held): a new tab waits for it."""
    from azimuth.tasks import held

    return held()


def compass_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window):
    """The menus of compass (self is the hub window). grouped in submenus; the menus of Chemcraft (Файл, Правка, Вид,"""
    # Отображение, Инструменты, Расчёт) — everything Compass can do, also what was only a button
    acts, more = studio.chem_actions, studio.chem_menus

    files = menu(
        'Файл',
        'Новая молекула',
        'Новый проект с расчётами…',
        'Создать проект из расчётов…',  # of outputs of ORCA or Gaussian (project_import.py)
        'Открыть проект…',
        'Молекулы и расчёты проекта…',
        own('Новая вкладка', lambda: _held() or studio.new_document()),
        'Открыть…',
        studio.recent_menu,
        'Перечитать файл',
        'Открыть пример…',
        None,
        'Молекула по SMILES…',
        'Молекула по названию…',  # PubChem
        'Вставить структуру из буфера',  # XYZ, molfile or SMILES
        self._studio_menu('Примеры молекул'),
        None,
        'Сохранить',  # Ctrl+S into the project of the tab, «Сохранить как…» — Ctrl+Shift+S
        'Сохранить как…',
        'Восстановить аварийные копии…',
        menu('Экспорт координат', 'Сохранить XYZ (Å)…', 'Сохранить координаты в выбранном формате…'),
        studio.batch_menu,
        picture_menu(),
        own('Модель для 3D-печати…', lambda: print3d_window().show(studio)),  # STL, VRML
        None,
        'Показать файл в папке',
        'Закрыть вкладку',
        'Закрыть остальные вкладки',
        'Очистить',  # Clear of Chemcraft
        None,
        'Настройки…',  # the preferences of the whole program
        'Отчёт об ошибке…',
        quit_,
    )
    edit = menu(
        'Правка',
        'Отменить',
        'Повторить',
        None,
        'Обзор / выделение',
        menu('Выделение', studio.select_all_action, studio.select_none_action, studio.invert_action,
             studio.element_select_menu, None, acts['expand'], acts['whole'],
             acts['select_numbers'], acts['select_box']),
        menu(
            'Атомы, фрагменты и молекулы',
            'Добавить атом…',
            'Добавить фрагмент',
            'Добавить молекулу',
            'Сохранить выделенное как фрагмент…',
            'Сохранить молекулу в «Мои молекулы»…',
            None,
            acts['set_element'],
            acts['dummy'],
            studio.hydrogens_action,
            studio.hydrogens_live_action,
            None,
            acts['overlap'],
            'Удалить выбранные атомы (Delete)',
        ),
        menu('Связи', 'Создать связь', 'Разорвать связь', None, acts['rebond'], acts['unbond_selected'],
             acts['unbond_all']),
        menu(
            'Геометрия',
            studio.cleanup_action,
            studio.uff_action,
            studio.make_3d_action,
            studio.peptide_action,
            studio.coordination_action,
            studio.tidy_live_action,
            studio.tidy_uff_action,
            'Вращать вокруг связи…',
            'Редактор Z-матрицы…',
            acts['transform'],
            studio.mirror_menu,  # reflects the atoms in place: an edit of the geometry, not a copy
            acts['planes'],
            # «Симметризовать» and the standard orientation are in «Инструменты», next to the point group
        ),
        more['coordinates'],
        more['order'],  # «Порядок атомов»
        more['guides'],  # «Векторы и плоскости»
        menu('Копирование', studio.copy_action, acts['copy_smiles'], studio.paste_action),
    )
    view = menu(
        'Вид',
        acts['isometry'],  # with «Перспектива», one of the two checked
        acts['perspective'],
        acts['center'],
        acts['best'],
        acts['pivot'],
        studio.standard_view_menu,
        menu('Камера', acts['camera_set'], acts['camera_copy'], acts['camera_paste']),
        None,
        acts['axes'],
        more['axes'],  # «Где оси»
        more['labels'],
        None,
        menu('Измерения на модели', studio.lengths_action, acts['all_distances'], acts['all_angles'], None,
             acts['clear_pins'], None, acts['measure_style']),
        studio.hbonds_action,
        acts['vdw'],
        studio.ribbon_action,
        None,
        menu('Скрыть атомы', acts['hide_selected'], acts['hide_dummies'], None, acts['show_all']),
        None,
        acts['copy_image'],
    )
    view.aboutToShow.connect(lambda: (acts['perspective' if studio.viewer.perspective else 'isometry'].setChecked(True),
                                      acts['axes'].setChecked(bool(studio.viewer.show_axes)),
                                      acts['vdw'].setChecked(bool(studio.viewer.show_vdw)),
                                      acts['hide_dummies'].setChecked(bool(studio.viewer.hide_dummies))))
    display = menu(
        'Отображение',
        menu('Модель', *studio.display_actions.values()),
        self._studio_menu('Отображение связей'),
        acts['hide_h'],
        None,
        studio.scheme_menu,
        studio.scheme_editor_action,  # the user's own look instead of more ready ones
        studio.engine_action,  # also in «Компас · Молекула»
    )
    tools = menu(
        'Инструменты',
        # the point group and the symmetrisation are here too
        own('Определить точечную группу', lambda: studio.symmetry_tool.determine_symmetry(apply=False)),
        studio.symmetrize_action,
        studio.standard_action,
        None,
        acts['inertia'],
        acts['statistics'],
        acts['masses'],
        more['fragments'],
        acts['internal'],
        acts['size'],
        None,
        acts['check_structure'],  # before a calculation
        acts['solvate'],
        acts['unsolvate'],
        more['protons'],
        acts['isotopes'],
        None,
        compare_menu(),  # the structure from a file, its settings and «Сравнить с вкладкой» in one
    )
    tools_of_calc, menus_of_calc = studio.calc_tool_actions, studio.calc_tool_menus
    calc = menu(
        'Расчёт',
        own('К параметрам расчёта', lambda: studio.navigate(1)),
        tools_of_calc['charge'],
        menus_of_calc['quick_xtb'],  # Computation of Chemcraft: xtb from the model
        studio.lock_action,
        None,
        'Путь между структурами…',
        'Поиск конформеров…',
        None,
        # «Открыть шаги расчёта…» and what is done with the steps — one submenu
        menu('Шаги расчёта', own('Открыть шаги расчёта…', studio.trajectory_tool.open_trajectory), None,
             *menus_of_calc['steps_data'].actions()),  # Job tools of Chemcraft
        tools_of_calc['modes_of_atoms'],
        'Учебная оптимизация ORCA',
        studio.properties_menu,
        studio.surface_menu,
    )
    project = self._project_menu(menu, own)
    helps = help_menu()
    return [(m.title(), m) for m in (files, edit, view, display, tools, calc, project, helps)]


def crystal_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window):
    """The menus of crystal (self is the hub window). «Компас · Кристалл» — what a crystal needs"""
    def crystal_results_panel():  # the runs of the crystal and what they gave, beside the model
        from modules.compass.actions import crystal_results_panel as module

        return module

    def quick_crystal_menu():
        from modules.compass.actions import crystal_quick

        box = menu('Быстрый расчёт xtb')
        for task, title, tip in crystal_quick.TASKS:
            item = own(title, lambda t=task: crystal_quick.run(studio, t))
            item.setToolTip(tr(tip))
            box.addAction(item)
        return box

    def cod_window():  # the window of COD, imported when asked
        from modules.compass.actions import cod_window as module

        return module

    files = menu(
        'Файл',
        # projects open from the crystal page too
        'Новый проект с расчётами…',
        'Открыть проект…',
        own('Открыть CIF…', studio.crystal_tool.open_cif),
        own('Найти кристалл в COD…', lambda: cod_window().show(studio)),  # the open database
        # reopens the CIF window to rebuild the crystal: the block of cells, the surface (hkl), the view
        'Перестроить кристалл (ячейки, поверхность)…',
        studio.recent_menu,
        'Перечитать файл',  # as in «Компас · Молекула»
        'Открыть пример…',
        own('Новая вкладка', lambda: _held() or studio.new_document()),
        None,
        'Сохранить кристалл в CIF…',
        # the crystal to other programs and its picture (crystal_export; the snapshots of Compass)
        menu('Экспорт кристалла',
             own('POSCAR (VASP)…', lambda: studio.crystal_tool.export_crystal('poscar')),
             own('Расширенный XYZ (ASE, OVITO)…', lambda: studio.crystal_tool.export_crystal('extxyz')),
             own('Блок ячеек в CIF (P 1)…', lambda: studio.crystal_tool.export_crystal('block'))),
        menu('Экспорт координат', 'Сохранить XYZ (Å)…', 'Сохранить координаты в выбранном формате…'),
        picture_menu('GIF: вращение кристалла'),
        own('Модель для 3D-печати…', lambda: print3d_window().show(studio)),  # as Mercury «Print 3D»
        None,
        'Показать файл в папке',  # as in «Компас · Молекула»
        'Восстановить аварийные копии…',
        'Закрыть вкладку',
        'Закрыть остальные вкладки',
        None,
        'Настройки…',  # the preferences of the whole program
        'Отчёт об ошибке…',
        quit_,
    )
    acts, more = studio.chem_actions, studio.chem_menus
    # the selection, the view and the display of «Компас · Молекула» that
    # a crystal needs too — a whole molecule selected before it goes to a tab, the projection, the camera, the
    # labels, the measurements, the hidden atoms; «Отображение» as in a molecule
    edit = menu(
        'Правка',
        'Отменить',
        'Повторить',
        None,
        own('Выделенные молекулы — в новую вкладку молекулы', studio.crystal_tool.selection_to_molecule),
        None,
        menu('Выделение', studio.select_all_action, studio.select_none_action, studio.invert_action,
             studio.element_select_menu, None, acts['expand'], acts['whole'], acts['select_numbers']),
        'Удалить выбранные атомы (Delete)',
    )
    view = menu(
        'Вид',
        acts['isometry'],
        acts['perspective'],
        acts['center'],
        acts['best'],
        acts['pivot'],
        studio.standard_view_menu,
        menu('Камера', acts['camera_set'], acts['camera_copy'], acts['camera_paste']),
        None,
        studio.cell_action,
        acts['axes'],
        more['labels'],
        None,
        menu('Измерения на модели', studio.lengths_action, acts['all_distances'], acts['all_angles'], None,
             acts['clear_pins'], None, acts['measure_style']),
        studio.hbonds_action,
        acts['vdw'],
        None,
        menu('Скрыть атомы', acts['hide_selected'], None, acts['show_all']),
        None,
        acts['copy_image'],
    )
    view.aboutToShow.connect(lambda: (acts['perspective' if studio.viewer.perspective else 'isometry'].setChecked(True),
                                      acts['axes'].setChecked(bool(studio.viewer.show_axes)),
                                      acts['vdw'].setChecked(bool(studio.viewer.show_vdw))))
    display = menu(
        'Отображение',
        menu('Модель', *studio.display_actions.values()),
        self._studio_menu('Отображение связей'),
        acts['hide_h'],
        None,
        studio.scheme_menu,
        studio.scheme_editor_action,
        studio.engine_action,
    )
    # «Кристалл»: everything the panel buttons do; «Расчёт»: the calculation and its results
    # (icons: azimuth/button_icons.TEXT_ICONS)
    tool = studio.crystal_tool

    def shown():
        crystal = getattr(studio, 'crystal', None)
        return crystal if crystal else None

    def block(n):
        crystal = shown()
        if crystal is None:
            studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
            return None
        return tool.build_crystal(crystal[0], n, True, bool(crystal[3]) if len(crystal) > 3 else False)

    looks = menu('Вид кристалла')

    def fill_looks():
        looks.clear()
        for item in tool.view_menu().actions():
            looks.addAction(item)

    looks.aboutToShow.connect(fill_looks)
    blocks = menu('Блок ячеек',
                  own('Одна ячейка', lambda: block((1, 1, 1))),
                  own('Блок 2 × 2 × 2', lambda: block((2, 2, 2))),
                  own('Блок 3 × 3 × 3', lambda: block((3, 3, 3))))
    from modules.compass.actions import (brillouin_window, crystal_code_window, crystal_dynamics, crystal_structure,
                                        morphology_window,
                                        packing_window,
                                        hirshfeld_window, pairs_window, planes_window, setting_window,
                                        shell_window, voids_window)

    def analysis(tab):
        return lambda: crystal_structure.show(studio, tab)

    def label(key):
        return lambda: studio.property_tool.show_crystal_charges(key)

    ionic = {'oxidation': own('Степени окисления на модели', label('oxidation')),
             'bvs': own('Суммы валентностей связей на модели', label('bvs')),
             'madelung': own('Энергия Маделунга…', analysis('madelung')),
             'valence': own('Валентности связей (BVS)…', analysis('valence')),
             'radii': own('Ионные радиусы и правила Полинга…', analysis('radii'))}
    labels = menu('Подписи на модели',  # crystal_energetics.model_labels
                  ionic['oxidation'],
                  ionic['bvs'],
                  own('Дробные координаты на модели', label('fractional')),
                  own('Позиции: метка, кратность, симметрия на модели', label('site')),
                  None,
                  own('Убрать подписи', label(None)))

    def grey_ionic():
        # items that need the ionic model are disabled for molecular crystals; the tooltip says why
        # (crystal_energetics.ionic_problem)
        from modules.compass.chemistry import crystal_energetics

        crystal = shown()
        try:
            problem = crystal_energetics.ionic_problem(crystal[0]) if crystal else None
        except (ValueError, TypeError, IndexError):
            problem = None
        for key, item in ionic.items():
            if key == 'madelung' and problem and properties_run_has_charges():
                problem_here = None  # the charges of a CP2K run still give the energy of Madelung
            else:
                problem_here = problem
            item.setEnabled(not problem_here)
            item.setToolTip(problem_here or '')

    def properties_run_has_charges():
        from modules.compass.chemistry import crystal_results

        run = studio.property_tool.crystal_run()
        try:
            return run is not None and crystal_results.read_charges(run.folder) is not None
        except OSError:
            return False

    # grouped by topic: the model, intermolecular interactions, structure and packing, cell and lattice;
    # the diffraction pattern on its own
    interactions = menu('Межмолекулярные взаимодействия',
                        own('Контакты и водородные связи…', tool.show_contacts),
                        own('Поверхность Хиршфельда…', lambda: hirshfeld_window.show(studio)),
                        own('Энергии пар и каркас (xtb)…', lambda: pairs_window.show(studio)),
                        own('Молекулярная оболочка…', lambda: shell_window.show(studio)))  # Mercury
    structure = menu('Структура и упаковка',  # crystal_energetics: the ionic picture of the crystal first
                     ionic['madelung'], ionic['valence'], ionic['radii'],
                     own('Плотность и упаковка…', analysis('packing')),
                     own('Расчёт и эксперимент…', analysis('compare')),
                     None,
                     own('Пустоты…', lambda: voids_window.show(studio)),  # «Display Voids» of Mercury
                     own('Форма кристалла (BFDH)…', lambda: morphology_window.show(studio)),  # «BFDH Morphology»
                     own('Сравнить упаковку…', lambda: packing_window.show(studio)))  # Crystal Packing Similarity
    lattice = menu('Ячейка и решётка',
                   own('Установка ячейки…', lambda: setting_window.show(studio)),  # Mercury's cell transformation
                   own('Плоскости (hkl) в ячейке…', lambda: planes_window.show(studio)),  # Mercury's hkl planes
                   own('Зона Бриллюэна…', lambda: brillouin_window.show(studio)),
                   None,
                   studio.chem_actions['planes'],  # the planes of groups of atoms, vectors and planes on the model
                   studio.chem_menus['guides'])
    for box in (structure, labels):
        box.setToolTipsVisible(True)
        box.aboutToShow.connect(grey_ionic)
    # outside the beta (AGENTS.md §0): shown, marked — a line that cannot be chosen, on top
    unverified = QAction(tr('Не проверено: анализ кристаллов ещё не сверен с другими программами'), self)
    unverified.setEnabled(False)
    crystal_menu = menu(
        'Кристалл',
        unverified,
        None,
        # the CIF window is opened from «Файл → Перестроить кристалл…» only
        blocks,
        looks,
        labels,
        None,
        interactions,
        structure,
        lattice,
        None,
        own('Порошковая дифрактограмма…', tool.show_powder),
        # «Выделенные молекулы — в новую вкладку…» is in «Правка», «Сохранить кристалл в CIF…» in «Файл»
    )
    properties = studio.property_tool

    def project_steps():
        path = studio.research_path() if hasattr(studio, 'research_path') else None
        if not path or not studio.show_project_crystal_steps(path):
            studio.notify(tr('У этого кристалла нет оптимизации с шагами — посчитайте её в Секстанте.'), 7000)

    def open_pdos():
        # the DOS and PDOS of the last run (crystal_pdos) in Spectrum; the projections of the CP2K Molden
        # file are computed on first use
        studio.navigate(2)
        view = getattr(studio, 'crystal_results', None)
        if view is None or view.run is None or not view.tabs.isTabVisible(view.dos_tab):
            studio.notify(tr('Нет расчёта с плотностью состояний: CP2K (любой расчёт) или Quantum ESPRESSO '
                             '(задача «Плотность состояний»).'), 7000)
            return None
        view.tabs.setCurrentIndex(view.dos_tab)
        if view.pdos_found is None and view.pdos_button.isVisible():
            view.compute_pdos()
        return view

    results = {
        'steps': own('Шаги последней оптимизации', project_steps),
        'charges': own('Заряды атомов в Multiwfn…', properties.compute_crystal_charges),
        'cm5': own('Заряды CM5 на модели', lambda: properties.show_crystal_charges('cm5')),
        'hirshfeld': own('Заряды Хиршфельда на модели', lambda: properties.show_crystal_charges('hirshfeld')),
        'table': own('Таблица зарядов…', properties.crystal_charges_table),
        'aim': own('Связи по AIM (Multiwfn)…', lambda: properties.crystal_aim()),
        'points': own('Критические точки на модели', lambda: crystal_dynamics.show_points(studio)),
        'all_points': own('Все критические точки на модели',
                          lambda: crystal_dynamics.show_points(studio, ('bond', 'ring', 'cage'))),
        'clear': own('Убрать критические точки', lambda: studio.surface_tool.clear_aim()),
        'modes': own('Частоты (точка Γ)', lambda: crystal_dynamics.show_modes(studio)),
        'pdos': own('Плотность состояний (PDOS)', open_pdos),
        'density': own('Электронная плотность на модели', lambda: properties.crystal_field('density')),
        'elf': own('ELF на модели', lambda: properties.crystal_field('elf')),
    }
    # the calculation, its direct results (steps, frequencies, DOS, spectrum), then derived analyses by kind
    charges = menu('Заряды атомов', results['charges'], None, results['cm5'], results['hirshfeld'],
                   results['table'])
    bonding = menu('Связи и критические точки (AIM)', results['aim'], None, results['points'],
                   results['all_points'], results['clear'])
    fields = menu('Поля на модели', results['density'], results['elf'])
    calc = menu(
        'Расчёт',
        own('Посчитать кристалл в Секстанте…', tool.to_calculation),
        quick_crystal_menu(),  # a quick xtb run, as for a molecule
        # CRYSTAL inputs, to run on a cluster
        own('Входной файл CRYSTAL…', lambda: crystal_code_window.show(studio)),
        None,
        own('Результаты расчётов…', lambda: crystal_results_panel().show(studio)),  # a panel
        results['steps'], results['modes'], results['pdos'],
        own('Спектр кристалла', lambda: studio.navigate(2)),
        None,
        charges, bonding, fields,
    )

    def grey_results():
        # items that need a run of the project are disabled; the tooltip names the run (crystal_results)
        from modules.compass.chemistry import crystal_results

        project = studio.research_path() if hasattr(studio, 'research_path') else None
        try:
            cp2k = properties.crystal_run()
            kept = crystal_results.read_charges(cp2k.folder) if cp2k is not None else None
            points = crystal_results.read_aim_points(cp2k.folder) if cp2k is not None else None
            modes = crystal_dynamics.modes_run(project)
            anything = crystal_results.runs(project) if project else []
        except (OSError, ValueError, KeyError, TypeError):
            cp2k = kept = points = modes = None
            anything = []
        none = tr('Нет расчёта CP2K этого кристалла — посчитайте его в Секстанте («К расчёту кристалла»).')
        why = {
            'steps': None if anything else tr('У этого кристалла ещё нет расчётов в проекте.'),
            'charges': None if cp2k else none,
            'cm5': None if kept else (none if cp2k is None else tr('Сначала «Заряды атомов в Multiwfn…».')),
            'hirshfeld': None if kept else (none if cp2k is None else tr('Сначала «Заряды атомов в Multiwfn…».')),
            'table': None if kept else (none if cp2k is None else tr('Сначала «Заряды атомов в Multiwfn…».')),
            'aim': None if cp2k else none,
            'points': None if points else (none if cp2k is None else tr('Сначала «Связи по AIM (Multiwfn)…».')),
            'all_points': None if points else (none if cp2k is None else
                                               tr('Сначала «Связи по AIM (Multiwfn)…».')),
            'clear': None if points else tr('Критических точек на модели нет.'),
            'modes': None if modes else tr('Нет расчёта частот — задача «Частоты (точка Γ)» в Секстанте (CP2K '
                                           'или Quantum ESPRESSO).'),
            'pdos': None if anything else tr('Нет расчёта: CP2K (любой) или Quantum ESPRESSO («Плотность '
                                             'состояний»).'),
            'density': None if cp2k else none,
            'elf': None if cp2k else none,
        }
        for key, item in results.items():
            item.setEnabled(why[key] is None)
            item.setToolTip(why[key] or '')

    calc.setToolTipsVisible(True)
    calc.aboutToShow.connect(grey_results)
    for box in (charges, bonding, fields):  # opened from a button of the panel without «Расчёт» too
        box.aboutToShow.connect(grey_results)
    helps = help_menu()
    return [(m.title(), m) for m in (files, edit, view, display, crystal_menu, calc, helps)]


def sextant_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window):
    """The menus of sextant (self is the hub window)."""
    files = menu(
        'Файл', 'Новый проект с расчётами…', 'Создать проект из расчётов…', 'Открыть проект…',
        'Молекулы и расчёты проекта…', 'Сохранить', 'Сохранить как…', 'Восстановить аварийные копии…', None, 'Сохранить входной файл ORCA…', None, 'Настройки…',
        'Отчёт об ошибке…', quit_
    )
    after = files.actions()[[to_source(a.text()) for a in files.actions()].index('Сохранить входной файл ORCA…') + 1]
    files.insertAction(  # Gaussian, Psi4, xtb — right under the ORCA one
        after, own('Сохранить входной файл выбранной программы…', studio.input_tool.export_program_input)
    )
    files.insertAction(files.actions()[0], own('Открыть входной файл…', lambda: studio.input_tool.open_input_file()))
    files.insertAction(files.actions()[1], own('Входные файлы для набора структур…',
                                               lambda: studio.input_tool.export_set_inputs()))
    # the input editor (azimuth/text_editor.py): find, replace, lines; ready blocks of the program; the check
    pane = studio.preview_pane

    def keyed(title, callback, keys):
        item = own(title, callback)
        item.setShortcut(QKeySequence(keys))  # shown in the menu; the editor itself takes the keys
        item.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        return item

    blocks = menu('Вставить блок')

    def fill_blocks():
        from modules.sextant import input_blocks

        blocks.clear()
        kind = studio.program_kind()
        listed = input_blocks.BLOCKS.get(kind, ())
        for title, text, keyword in listed:
            item = blocks.addAction(tr(title))
            item.triggered.connect(lambda checked=False, t=title, b=text, k=keyword:
                                   studio.input_tool.insert_block(t, b, k))
        if not listed:
            blocks.addAction(tr('Для этой программы готовых блоков нет')).setEnabled(False)

    blocks.aboutToShow.connect(fill_blocks)
    edit = menu(
        'Правка',
        keyed('Отменить', studio.preview.undo, 'Ctrl+Z'),
        keyed('Повторить', studio.preview.redo, 'Ctrl+Shift+Z'),
        None,
        keyed('Найти…', pane.actions['find'], 'Ctrl+F'),
        keyed('Заменить…', pane.actions['replace'], 'Ctrl+R'),
        keyed('Перейти к строке…', pane.actions['go_to'], 'Ctrl+G'),
        None,
        keyed('Закомментировать / раскомментировать', pane.actions['comment'], 'Ctrl+/'),
        keyed('Дублировать строку', pane.actions['duplicate'], 'Ctrl+D'),
        keyed('Удалить строку', pane.actions['delete_line'], 'Ctrl+Shift+K'),
        None,
        blocks,
        own('Проверить входной файл', lambda: studio.input_tool.check_input_now()),
        own('Собрать файл заново по настройкам', lambda: studio.input_tool.reset_input()),
        None,
        own('Скопировать входной файл', lambda: (QApplication.clipboard().setText(studio.preview.toPlainText()),
                                                 __import__('azimuth.ui', fromlist=['copied']).copied(
                                                     studio, tr('входной файл')))),
        keyed('Горячие клавиши редактора…', pane.actions['keys'], 'F1'),
    )
    # running ORCA or xtb (modules/sextant/runner.py)
    calc = menu('Расчёт')
    run = own('Запустить расчёт', studio.run_tool.run_calculation)
    stop = own('Остановить расчёт', studio.run_tool.stop_calculation)
    for item, keys in ((run, 'Ctrl+Return'), (stop, 'Ctrl+.')):  # shown; the page takes the keys
        item.setShortcut(QKeySequence(keys))
        item.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
    for item in (run, stop):
        calc.addAction(item)
    calc.addAction(own('Окно расчёта', studio.show_job_window))
    # the calculations on the server moved aside for the next one (park_server_job), each its window
    others = menu('Другие расчёты на сервере')

    def list_others():
        others.clear()
        found = studio.parked_server_jobs()
        for place, title, running in found:
            item = others.addAction(('▶ ' if running else '✓ ') + title)
            item.triggered.connect(lambda *_, p=place: studio.show_parked_job(p))
        if not found:
            none = others.addAction(tr('Нет — отдельные расчёты на сервере можно запускать, не дожидаясь'))
            none.setEnabled(False)

    others.aboutToShow.connect(list_others)
    calc.addMenu(others)
    calc.addAction(own('Дополнительные настройки…', studio.show_options))
    # several calculations one after another, each on the geometry of the one before
    from modules.sextant import chain

    chains = menu('Цепочка расчётов')
    chain_items = {}
    for key, (title, _steps) in chain.PRESETS.items():
        chain_items[key] = own(title, lambda k=key: studio.batch_tool.start_chain(k))
        chains.addAction(chain_items[key])

    def grey_chains():
        kind = studio.program_kind()
        for key, item in chain_items.items():
            ok = chain.available(key, kind)
            item.setEnabled(ok)
            item.setToolTip('' if ok else tr('В этой программе нет одного из шагов цепочки.'))

    chains.aboutToShow.connect(grey_chains)
    calc.addMenu(chains)
    calc.addSeparator()
    calc.addAction(own('Указать программу…', studio.run_tool.choose_program))
    calc.addAction(own('Установить программы для расчёта…', lambda: studio.run_tool.install_tools_dialog()))
    calc.addAction(own('Папка расчёта', studio.run_tool.open_job_folder))
    calc.addAction(own('История расчётов…', studio.run_tool.show_history))
    calc.addAction(own('Пакеты расчётов…', lambda: studio.batch_tool.show_saved_batches()))
    calc.addAction(own('QTAIM для очереди…', lambda: studio.batch_tool.batch_qtaim(choose=True)))
    calc.addAction(own('Дескрипторы и logK очереди…', lambda: studio.batch_tool.batch_descriptors(choose=True)))
    calc.aboutToShow.connect(
        lambda: (run.setEnabled(studio.run_button.isEnabled()), stop.setEnabled(studio.run_tool.job_running()))
    )
    view = self._sextant_view_menu(menu, own)
    server = self._server_menu(menu, own)
    helps = help_menu()
    return [(m.title(), m) for m in (files, edit, view, calc, server, helps)]


def spectrum_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window):
    """The menus of spectrum (self is the hub window)."""
    files = menu(
        'Файл',
        'Новый проект с расчётами…', 'Открыть проект…', 'Молекулы и расчёты проекта…',
        'Сохранить', None,
        'Открыть результат расчёта…',
        studio.recent_menu,
        'Перечитать файл',
        'Открыть CUBE (3D)…',
        'Открыть орбитали…',
        own('Диаграмма реакции…', studio.reaction_diagram),
        'Открыть пример…',
        None,
        'Учебный результат ORCA',
        'Учебные колебания ORCA',
        'Учебная орбиталь (3D)',
        None,
        'Настройки…',  # the preferences of the whole program
        'Отчёт об ошибке…',
        quit_,
    )
    edit = menu('Правка')
    adopt = own('Взять геометрию из результата', studio.adopt_geometry)
    edit.addAction(adopt)
    edit.aboutToShow.connect(lambda: adopt.setEnabled(studio.use_geometry.isEnabled()))
    view = menu('Вид')
    tabs = studio.result_tabs
    group = QActionGroup(view)
    group.setExclusive(True)
    for index in range(tabs.count()):
        item = own(to_source(tabs.tabText(index)), lambda checked=False, i=index: tabs.setCurrentIndex(i), True)
        item.setText(tabs.tabText(index))
        group.addAction(item)
        view.addAction(item)
    view.aboutToShow.connect(
        lambda: [a.setChecked(i == tabs.currentIndex()) for i, a in enumerate(group.actions())]
    )
    tools = menu(  # the Chemcraft tools that work on results
        'Инструменты',
        own('Изотопный пик молекулярного иона…', lambda: studio.spectrum_tools.show_isotopes()),
        own('Энергии из нескольких файлов…', lambda: studio.spectrum_tools.energies_of_files()),
        own('Доли по Больцману…', lambda: studio.spectrum_tools.boltzmann_dialog()),
        own('Равновесие двух форм…', lambda: studio.spectrum_tools.equilibrium_dialog()),
        own('Заторможенный ротатор…', lambda: studio.spectrum_tools.hindered_rotor_dialog()),
        None,
        own('Множители частот…', lambda: studio.vibrations.open_factor_table()),
        own('Опытные данные для молекулы…', lambda: self._measured_data()),
        own('Пересчёт единиц…', lambda: self._unit_converter()),
    )
    helps = help_menu()
    return [(m.title(), m) for m in (files, edit, view, tools, helps)]
