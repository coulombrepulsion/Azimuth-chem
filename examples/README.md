# Примеры «Азимута»

Файлы, на которых можно сразу попробовать возможности программы. Открывать их удобнее всего через
**«Файл → Открыть пример…»** (диалог открывается в этой папке): результаты расчётов попадают в Спектр,
структуры и CIF — в Компас, файл фрагментов — в «Мои фрагменты». Можно и обычным «Файл → Открыть…».

Почти все результаты расчётов — настоящие выводы программ из тестовых данных cclib (лицензия BSD-3-Clause,
текст — в `LICENSE-cclib.txt`, источники — внизу). Многие из них — **выдержки**: нужные блоки сохранены без
изменений, пропуски помечены строкой `...  [lines omitted from the excerpt]`. Молекула в большинстве файлов —
дивинилбензол (C₁₀H₁₀), в части — вода. Структуры в папках 0 и 8–11 подготовлены для «Азимута».

| Папка | Файлы | Что сделать | Что увидите |
|---|---|---|---|
| `0-molecules` | `water.xyz`, `methane.xyz`, `ammonia.xyz`, `benzene.xyz` | открыть (или перетащить в окно); подпись под моделью — кнопка точечной группы | простые молекулы для первого знакомства: вращение, приближение, измерения, правка; точечные группы C₂v (вода), T_d (метан), C₃v (аммиак), D₆h (бензол) |
| `1-properties` | `water_mp2_orca5.out`, `divinylbenzene_cation_orca6.out`, `divinylbenzene_cation_gaussian16.log` | открыть; в Компасе — кнопка «±» над моделью | заряды Малликена, Лёвдина, Хиршфельда, спиновая заселённость катиона, порядки связей Майера, дипольный момент — прямо на модели |
| `2-optimization` | `divinylbenzene_opt_gaussian16.log`, `divinylbenzene_opt_psi4.out`, папка `xtb_divinylbenzene_opt` (открывать `dvb_opt.out`) | открыть; панель шагов ☰ слева от модели | шаги оптимизации, график энергии, проигрывание, сравнение с начальной структурой, GIF шагов |
| `3-scans` | `dihedral_scan_relaxed_orca6.out`, `dihedral_scan_relaxed_gaussian16.log`, `zmatrix_scan_rigid_orca5.out` | открыть; панель шагов ☰ | точки скана ППЭ: значение двугранного угла или параметра, ΔE от нижней точки |
| `4-vibrations` | `divinylbenzene_freq_gaussian16.log`, `divinylbenzene_freq_psi4.out`, папка `xtb_divinylbenzene_freq` (`dvb_ir.out`) | Спектр → «Колебания и ИК» | частоты и ИК-спектр, анимация, стрелки (в обе стороны), «GIF…», «Кадры XYZ…», «Сместить +/−» |
| `5-uv-vis-nmr` | `divinylbenzene_tddft_orca6.out`, `divinylbenzene_tddft_gaussian16.log`, `divinylbenzene_nmr_orca6.out`, `divinylbenzene_nmr_gaussian16.log` | Спектр → вкладки «UV-Vis» и «ЯМР» | спектр поглощения с огибающей и таблицей переходов; экранирования и химические сдвиги, эквивалентные атомы |
| `6-orbitals` | `water_mp2_gaussian16.fchk`, `water_gamess.molden`, `divinylbenzene_orbitals_orca6.out`, `MoOCl4_ecp_gaussian16.fchk` | открыть; окно «Орбитали» (для вывода ORCA — кнопка «Орбитали…») | диаграмма уровней, ВЗМО/НСМО, изоповерхность выбранной орбитали и плотности без файлов CUBE |
| `7-programs` | `water_ccsdt_gaussian16.log`, `water_ccsdt_psi4.out`, папка `xtb_divinylbenzene_sp` (`dvb_sp.out`) | открыть по очереди | один и тот же расчёт воды в Gaussian и Psi4 (итоговая энергия CCSD(T)); заряды xtb и порядки связей Виберга |
| `8-compare` | `ethanol.xyz` и `ethanol_other_order.xyz`; `butane_anti.xyz` и `butane_gauche.xyz` | открыть первый файл, затем кнопка «Сравнить» → «Наложить структуру из файла…» → второй | наложение при другом порядке атомов (RMSD ≈ 0, «нумерация другая»), «Перенумеровать модель как в файле»; отличие двух конформеров бутана |
| `9-torsion` | `butane.xyz`, `ethanol.xyz` | правый щелчок по средней связи C–C (или по C–O) → «Вращать вокруг этой связи…» | точный двугранный угол, поворот мышью, ближайший контакт, перебор конформеров в панель шагов или XYZ |
| `10-crystals` | `NaCl_rock_salt.cif`, `CsCl.cif`, `graphite_P1.cif`, `Si_diamond.cif`, `benzoic_acid.cif` | открыть → окно «Кристалл» → «Построить» | ячейка (у NaCl — 14 Na и 13 Cl с атомами на гранях), блок ячеек, рёбра a, b, c; у графита — пример файла без операций симметрии (P1); кремний — алмазная решётка Fd-3m, задача на vc-relax в примитивной и в обычной ячейке (a ≈ 5,47 Å); бензойная кислота — молекулярный кристалл: «Контакты» — водородные связи O–H···O и димер R²₂(8), эллипсоиды смещений, расчёт димера |
| `11-fragments` | `example_fragments.json` | «Файл → Открыть пример…» с этим файлом (или «Фрагмент» → «Импорт фрагментов…») | три фрагмента в «Моих фрагментах»: —CF₃, трет-бутил, ацетил; их можно ставить на атомы и вместо водородов |

Ещё в корне папки — три учебных файла, которые открываются из меню: `teaching-demo.out` («Учебный результат
ORCA»), `optimization-demo.out` («Учебная оптимизация ORCA»), `vibrations-demo.out` («Учебные колебания ORCA»).

Схемы отображения («Вид → Схема отображения») пробуются на любом из этих файлов.

## Источники

Тестовые данные cclib, https://github.com/cclib/cclib, коммит `76df867532961117427cb3e0877913db3233f83f`
(2026-10-07), загружены 2026-10-23; подробности о выдержках — в `tests/data/*/README.md` программы.

| Файл здесь | Оригинал в cclib |
|---|---|
| `1-properties/water_mp2_orca5.out` | `data/ORCA/basicORCA5.0/water_mp2.out` (весь файл) |
| `1-properties/divinylbenzene_cation_orca6.out` | `data/ORCA/basicORCA6.0/dvb_sp_un_dft.out` (выдержка) |
| `1-properties/divinylbenzene_cation_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_un_sp` (.out или .log) (выдержка) |
| `2-optimization/divinylbenzene_opt_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_gopt` (.out или .log) (выдержка) |
| `2-optimization/divinylbenzene_opt_psi4.out` | `data/Psi4/basicPsi4-1.7/dvb_gopt_rhf.out` (выдержка) |
| `2-optimization/xtb_divinylbenzene_opt/` | `data/XTB/basicXTB6.6.1/dvb_opt/` (файлы целиком) |
| `3-scans/dihedral_scan_relaxed_orca6.out` | `data/ORCA/basicORCA6.0/dvb_scan_relaxed.out` (выдержка) |
| `3-scans/zmatrix_scan_rigid_orca5.out` | `data/ORCA/basicORCA5.0/dvb_scan_unrelaxed.out` (выдержка) |
| `3-scans/dihedral_scan_relaxed_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_scan_relaxed` (.out или .log) (выдержка) |
| `4-vibrations/divinylbenzene_freq_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_ir` (.out или .log) (выдержка) |
| `4-vibrations/divinylbenzene_freq_psi4.out` | `data/Psi4/basicPsi4-1.7/dvb_ir_rhf.out` (выдержка) |
| `4-vibrations/xtb_divinylbenzene_freq/` | `data/XTB/basicXTB6.6.1/dvb_ir/` (файлы целиком) |
| `5-uv-vis-nmr/divinylbenzene_tddft_orca6.out` | `data/ORCA/basicORCA6.0/dvb_td.out` (выдержка) |
| `5-uv-vis-nmr/divinylbenzene_tddft_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_td` (.out или .log) (выдержка) |
| `5-uv-vis-nmr/divinylbenzene_nmr_orca6.out` | `data/ORCA/basicORCA6.0/dvb_nmr.out` (выдержка) |
| `5-uv-vis-nmr/divinylbenzene_nmr_gaussian16.log` | `data/Gaussian/basicGaussian16/dvb_nmr` (.out или .log) (выдержка) |
| `6-orbitals/water_mp2_gaussian16.fchk` | `data/FChk/basicGaussian16/water_mp2.fchk` (весь файл) |
| `6-orbitals/MoOCl4_ecp_gaussian16.fchk` | `data/FChk/basicGaussian16/Mo4OCl4-sp.fchk` (весь файл) |
| `6-orbitals/water_gamess.molden` | `test/io/data/molden5.7_water_mp2.molden` (весь файл) |
| `6-orbitals/divinylbenzene_orbitals_orca6.out` | `data/ORCA/basicORCA6.0/dvb_sp_dft.out` (выдержка) |
| `7-programs/water_ccsdt_gaussian16.log` | `data/Gaussian/basicGaussian16/water_ccsdt` (.out или .log) (выдержка) |
| `7-programs/water_ccsdt_psi4.out` | `data/Psi4/basicPsi4-1.7/water_ccsd(t).out` (выдержка) |
| `7-programs/xtb_divinylbenzene_sp/` | `data/XTB/basicXTB6.6.1/dvb_sp/` (файлы целиком) |

Файлы в папках 8–11 подготовлены «Азимутом» 2026-10-24: структуры — из библиотеки молекул Компаса
(этанол, бутан, тетрафторметан, изобутан, ацетальдегид; повороты, перенумерация и двугранные углы — функциями
программы); параметры ячеек NaCl, CsCl и графита — округлённые учебные значения, не измерение.

`0-molecules` (2026-11-14, по первому отчёту тестировщика): геометрии собраны программой по опытным длинам связей и углам (CRC Handbook, газовая фаза): вода r(OH) 0,9572 Å, ∠HOH 104,52°; метан r(CH) 1,087 Å, тетраэдр; аммиак r(NH) 1,012 Å, ∠HNH 106,7°; бензол r(CC) 1,397 Å, r(CH) 1,084 Å — симметрия точная.

`10-crystals/benzoic_acid.cif` — запись COD 7133168 (Crystallography Open Database, общественное достояние):
бензойная кислота, P2₁/n, 296 К; Sun, Li, Chen и др., Chem. Commun. 60 (2024) 7224, doi:10.1039/d4cc01751j.
Из файла убраны только встроенные блоки `_shelx_res_file` и `_shelx_hkl_file` (входной файл SHELXL и отражения).

`10-crystals/Si_diamond.cif` — запись COD 9008565 (из American Mineralogist Crystal Structure Database): кремний, Fd-3m, a = 5,4307 Å, 300 К; Wyckoff R. W. G., Crystal Structures 1 (1963) 7–83. Файл без изменений (2026-11-21, по первому отчёту тестировщика).
