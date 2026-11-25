# Сторонние компоненты

Прямые зависимости приложения: PySide6-Essentials 6.12.0 и соответствующий shiboken6 6.12.0. Они устанавливаются через pip в отдельное окружение, исходный архив приложения не содержит Qt и Python.

Qt for Python предоставляется по открытым LGPLv3/GPLv3 и коммерческим условиям, в зависимости от используемых компонентов и варианта поставки. См. официальные сведения:
https://doc.qt.io/qtforpython-6/
https://doc.qt.io/qt-6/licensing.html

Этот прототип использует QtCore, QtGui и QtWidgets. При упаковке самостоятельного приложения необходимо проверить лицензии фактически включённых библиотек, сохранить необходимые уведомления и выполнить условия выбранных лицензий. Эта запись не заменяет полный набор уведомлений будущего бинарного дистрибутива.

pytest используется только для разработки и тестов (MIT); в приложение не импортируется.

ORCA и Multiwfn не включены в дистрибутив и не устанавливаются. Их названия обозначают совместимость/планируемую интеграцию и не означают связь с разработчиками или их одобрение.

3D-просмотр CUBE использует VTK 9.5.2 (BSD-3-Clause, https://vtk.org/about/) и NumPy (BSD-3-Clause, https://numpy.org/doc/stable/license.html). Зависимости устанавливаются отдельно через requirements.txt; исходные лицензии и уведомления находятся в пакетах окружения. VTK подключается через штатный Qt-адаптер; Chemcraft и его код/ресурсы не используются.

Атлас v2 (`modules/atlas/atlas_v2`) содержит шрифты Golos Text, PT Serif и JetBrains Mono
(@fontsource 5.3.0, SIL Open Font License 1.1) — страницы работают без загрузки шрифтов из сети.
Его Python-ядро использует только стандартную библиотеку; numpy (уже в зависимостях «Азимута») ускоряет расчёты.

Боковая панель использует Golos Text Medium (`assets/fonts`, SIL Open Font License 1.1, текст лицензии рядом) — тот же шрифт, что в Атласе; файлы собраны из WOFF2 Атласа без изменения начертаний.

Шрифт окон программы — Inter 4.0 (https://github.com/rsms/inter, © The Inter Project Authors, SIL Open Font License 1.1; `assets/fonts/Inter-*.otf`, текст лицензии — `assets/fonts/LICENSE-inter.txt`): начертания Regular, Italic, Medium, SemiBold и Bold, урезанные fontTools до латиницы, греческого, кириллицы, знаков препинания, стрелок и математических знаков (2026-11-25). Шрифт лежит в папке программы и ниоткуда не загружается; меню и моноширинный текст остаются в шрифтах системы.

Тесты свойств из вывода ORCA (`tests/data/orca_cclib`) используют настоящие выводы ORCA 5.0 и 6.0 из тестовых данных cclib (https://github.com/cclib/cclib, BSD-3-Clause; весь файл или выдержки, источник, коммит и текст лицензии — в `tests/data/orca_cclib/README.md`). В программу они не входят; код cclib не используется. Тесты орбиталей (`tests/data/orbitals`) используют оттуда же выводы ORCA 6.0 (выдержки), файлы .fchk Gaussian 16 и файлы Molden, записанные программой Molden 5.7; сведения и лицензия — в `tests/data/orbitals/README.md`. Соглашения о нормировке файлов Molden разных программ описаны по документации IOData (https://github.com/theochem/iodata, GPL-3.0); код и файлы IOData в «Азимут» не входят. Тесты выводов Gaussian, xtb и Psi4 (`tests/data/gaussian`, `tests/data/xtb`, `tests/data/psi4`) используют выводы Gaussian 16, xtb 6.6.1 и Psi4 1.7 из тестовых данных cclib (выдержки или файлы целиком; сведения и лицензия — в README.md этих папок).

Примеры (`examples/`, 2026-10-24) включают выводы ORCA, Gaussian, xtb и Psi4, файлы .fchk и Molden из тестовых данных cclib (https://github.com/cclib/cclib, BSD-3-Clause) — те же файлы и выдержки, что в `tests/data`; они входят в программу, текст лицензии — в `examples/LICENSE-cclib.txt`, источник каждого файла — в `examples/README.md`.

Силовое поле UFF Компаса (`modules/compass/chemistry/uff.py`, 0.106.0) — своя реализация по статье Rappé и др. (JACS 114, 10024, 1992) и по коду RDKit (https://github.com/rdkit/rdkit, BSD-3-Clause, © Greg Landrum и Rational Discovery LLC): таблица параметров перенесена из `Code/ForceField/UFF/Params.cpp` (выпуск 2024.09.6) в `uff_params.py`, правила типов атомов и слагаемых повторяют `AtomTyper.cpp`, `Builder.cpp` и `ConjugHybrid.cpp`. Код RDKit в программу не входит; RDKit не нужен для работы UFF.

Quantum ESPRESSO (https://www.quantum-espresso.org, GPL-2.0-only; пакет `qe` conda-forge) в дистрибутив не входит: «Установить программы для расчёта» ставит его по выбору пользователя в отдельную папку `.tools/qe` (0.128.0), как xtb, CREST и MOPAC в `.tools/calc`; программа запускает его отдельным процессом. Вместе с ним (0.129.0) скачивается библиотека псевдопотенциалов SSSP 1.3.0 PBE efficiency (Prandini и др., npj Comput. Mater. 4, 72, 2018; Materials Cloud Archive, DOI 10.24435/materialscloud:f3-ym, запись — CC BY 4.0, у каждого файла лицензия его библиотеки — LICENSE.txt записи кладётся рядом) в `.tools/qe/pseudo`; в дистрибутив файлы не входят.

Таблицы кристаллов Компаса (`modules/compass/chemistry/data`, 0.118.0) созданы программой `tools/make_crystal_tables.py` из пакетов, которые программе не нужны: `space_groups.json` — 530 установок 230 пространственных групп из spglib 2.7.0 (https://github.com/spglib/spglib, BSD-3-Clause, © Spglib team; текст лицензии — `data/LICENSE-spglib.txt`); `xray_f0.json` — коэффициенты атомных факторов рассеяния рентгеновских лучей Waasmaier & Kirfel (Acta Cryst. A51, 416, 1995) в виде таблицы xraydb 4.5.8 (https://github.com/xraypy/XrayDB, MIT, © Matthew Newville; текст — `data/LICENSE-xraydb.txt`). Код spglib и xraydb в программу не входит. `xray_anomalous.json` (0.179.0) — поправки f′ и f″ к атомным факторам рассеяния на линиях Kα₁ рентгеновских трубок из таблиц Henke, Gullikson & Davis (At. Data Nucl. Data Tables 54, 181, 1993; CXRO, https://henke.lbl.gov/optical_constants/sf/), опубликованных для свободного использования; источник и способ получения — `data/LICENSE-henke.txt`.

Таблицы ионной модели кристалла (`modules/compass/chemistry/data`, 0.149.0; `crystal_energetics.py`): `bond_valence.json` — параметры валентности связей R₀, b таблицы IUCr bvparm2020 (I. D. Brown, https://www.iucr.org/resources/data/datasets/bond-valence-parameters) в виде файла пакета ions 0.5.1 (https://github.com/dembart/ions, MIT, © Artem Dembitskiy; текст — `data/LICENSE-ions.txt`); `shannon_radii.json` (эффективные ионные радиусы, R. D. Shannon, Acta Cryst. A32, 751, 1976) и `oxidation_states.json` — из pymatgen-core 2026.10.31 (https://github.com/materialsproject/pymatgen, MIT, © MIT и The Regents of the University of California; текст — `data/LICENSE-pymatgen.txt`). Код ions и pymatgen в программу не входит.

Тесты белков (`tests/data/protein`, 0.106.3) используют файлы 1CRN и 1UBQ из Protein Data Bank (https://www.rcsb.org, CC0 1.0); в программу они не входят.
