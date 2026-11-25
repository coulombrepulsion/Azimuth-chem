# Реестр предположений перед бетой

Все пометки `ASSUMPTION` в коде программы (без тестов), разобранные 2026-11-21. Пометки 0.89–0.91 подробно разобраны
в [BETA_ASSUMPTIONS.md](../archive/plans/BETA_ASSUMPTIONS.md); здесь — то, что осталось открытым, и всё, что добавилось после.
Когда пункт закрыт, отметьте его здесь (чем проверено) и уберите пометку из кода.

Порядок групп — по вреду ошибки: сначала то, что может молча дать неверное число.

## 1. Влияют на числа, которые видит студент

| Где | Предположение | Чем закрыть | Статус |
|---|---|---|---|
| `spectrum/readers/output_orbitals.py` | Порядок сферических функций NWChem и Q-Chem m = −l … +l. Все эталоны были в STO-3G, проверки не было | `tools/run_references.py spherical --programs nwchem,qchem`, тест `test_spherical_order.py` | эталон и тест готовы, нужен запуск NWChem (conda-forge `nwchem`); Q-Chem — если есть |
| `spectrum/readers/xtb.py` | x, y, z диполя xtb в а. е., «tot» в дебаях | вывод xtb для молекулы с диполем | закрыто: `scan2d/h2o2_scan2d_xtb.out`, |x, y, z| = 0,1317 а. е. = 0,335 Д, «tot» 0,334 |
| `spectrum/readers/psi4.py` | Формат TD-DFT Psi4 1.4–1.7 по памяти; старый «Dipole Moment: [D]» | вывод Psi4 TD-DFT | открыто: Psi4 не установлен (conda-forge `psi4`) |
| `spectrum/analysis/convergence.py` | Таблицы сходимости ORCA «Geometry convergence» и Gaussian «Converged?» по памяти; тест на рукописных строках | ORCA — любая оптимизация из `tests/data`; Gaussian — нужен вывод | ORCA — закрыто 0.216.157 (`orca601/h2o_opt.out`; найдена и исправлена ошибка: на графике был декартов градиент); Gaussian — открыто |
| `spectrum/readers/orca_scan.py` | Строки таблицы IRC ORCA; настоящего вывода IRC не было | расчёт IRC в ORCA 6 (вода → не годится; HCN ⇄ HNC) | открыто |
| `spectrum/readers/orca_properties.py` | ORCA 4.x печатает те же блоки | — | принять: поддерживается ORCA ≥ 5 (runner.py) — сказать в руководстве |
| `spectrum/readers/mopac.py` | MOPAC 2016 / 2012 пишут те же ключи .aux | вывод старых версий | принять: проверено на 23.2.5, сказать в руководстве |
| `azimuth/core.py:299`, `:389` | Имена базисов библиотеки ORCA 6 и ECP «def2-ECP» не запускались | короткий расчёт с каждым базисом списка (`tools/check_programs.py`) | открыто: ORCA есть на Mac |
| `azimuth/core.py:160`, `sextant/inputs.py:49`, `sextant/input_check.py:30` | Ключевые слова Gaussian 16, Psi4 1.7, xtb 6 по памяти руководств, без запуска | по входному файлу каждой задачи — запуск (xtb есть; Psi4 ставится; Gaussian — у коллег) | xtb: можно закрыть; Psi4, Gaussian — открыто |
| `sextant/inputs_more.py:28`, `sextant/runner.py:86` | Входы GAMESS и NWChem ни разу не запускались; `rungms JOB VERNO NCPUS` | NWChem — conda-forge; GAMESS — после регистрации | открыто |
| `sextant/inputs.py:442` | Проницаемости MOPAC по памяти (CRC) | сверено в пределах 5 % (BETA_ASSUMPTIONS) | закрыто, пометка снята |
| `sextant/runner.py:611`, `:660`, `:859` | Строки хода, сообщения об ошибках и имя `<input>_MEP_trj.xyz` ORCA 5/6, Gaussian 16, Psi4 1.7 | ORCA, xtb — по эталонам; NEB ORCA — один расчёт | частично |
| `spectrum/analysis/nto.py`, `spectrum/analysis/thermo.py` | Файл .nto — это .gbw; RHF открытой оболочки MOPAC | закрыто запуском `check_programs.py --beta` 2026-11-07 | закрыто, пометки сняты |
| `spectrum/readers/orbital_files.py:52` | Порядок d, f, g ORCA по меткам orca_2mkl | проверка ортонормированности отказывает при неверном порядке | защищено проверкой — оставить как есть |

## 2. Окружение: сервер, Windows, сеть

| Где | Предположение | Чем закрыть | Статус |
|---|---|---|---|
| `sextant/cluster.py:59` | SLURM ≥ 20, Linux с lscpu и /proc/meminfo; sinfo сверен с serv3 | вывод lscpu, free, scontrol на трёх серверах; второй кластер | открыто — этап 2, T24 |
| `azimuth/runtime/runs.py:42` | `squeue -n`, `sacct --name` находят задание по имени | настоящий кластер | открыто — этап 2 |
| `sextant/remote_job.py:324` | Один THREADS MOPAC на весь файл | сервер лаборатории | открыто — этап 2 |
| `sextant/remote_job.py:68` | Вывод ORCA — ASCII | ORCA пишет ASCII | закрыто, пометка снята |
| `sextant/ssh.py:47` | OpenSSH ≥ 8.4 (SSH_ASKPASS_REQUIRE) | `ssh -V` на Windows 10/11 | открыто — этап 2 |
| `azimuth/runtime/writer_lock.py:19` | Проект на локальном диске; flock на сетевой папке может не работать | решение проекта: облачные и сетевые папки не поддерживаются — сказать в руководстве | принять |
| `sextant/install_tools.py:36` | Адрес micromamba и пакеты conda-forge без проверки суммы | проверка установщика на чистом компьютере (этап 2) | открыто |
| `compass/chemistry/pubchem.py:12`, `:33` | Коды ответов и лимиты PubChem | один запрос несуществующего имени и плохого SMILES | открыто, быстро |
| `spectrum/readers/nist.py:13` | Формат страниц NIST WebBook | один поиск из программы | открыто, быстро |
| `compass/view/opengl_setup.py:37` | OpenGL на macOS рисует Атлас как раньше | Атлас ушёл на сайт (0.160.0) | устарело, пометка снята |

## 3. Решения проекта и приближения (не непроверенные факты)

Это не ошибки, которые надо найти, а сознательный выбор. Пометку `ASSUMPTION` у них стоит заменить на обычное
объяснение в комментарии, а важное для пользователя — сказать в интерфейсе или руководстве.

| Где | Решение |
|---|---|
| `sextant/advice.py:30` | Подсказки метода по обзорам Bursch et al. 2022 и GMTKN55 в упрощённом виде |
| `sextant/batch_conformers.py:35` | Конформеры очереди ищутся в газовой фазе GFN2-xTB / MMFF |
| `sextant/binding.py:49` | Один ион на комплекс, закрытые оболочки |
| `spectrum/analysis/descriptors.py:37` | Металл комплекса — самый тяжёлый металл |
| `spectrum/analysis/nmr_multiplets.py:14` | Мультиплеты первого порядка (сказано под графиком) |
| `spectrum/analysis/nmr_reference.py:39` | Результат без «Opt» считается на чужой геометрии |
| `spectrum/analysis/reaction.py:59` | В выводах есть эхо входного файла |
| `spectrum/readers/orca_spectra.py:74` | Ширина полосы 0,3 эВ по умолчанию |
| `spectrum/readers/results.py:22` | Предел 256 МБ на вывод |
| `spectrum/wavefunction/batch_qtaim.py:45` | Очередь xtb даёт Molden только по запросу |
| `compass/chemistry/protein.py:19` | Вторичная структура по расстояниям, а не по энергии DSSP |
| `compass/chemistry/uff.py:19`, `:21`, `:248` | Типы атомов UFF и ароматичность проще, чем у RDKit |
| `compass/chemistry/iupac.py:63`, `:1151`, `:1161` | Китайские названия по общепринятому употреблению |
| `compass/view/result_overlay.py:32` | Учебные диапазоны значений |
| `atlas/.../core/h2.py:65` | Сверено с PySCF 2.x и Колосом — Вольневичем; пометка снята |

## Что можно закрыть на Mac владельца за один вечер

1. NWChem через «Установить программы для расчёта» (0.216.158) → `tools/run_references.py spherical --programs nwchem` (порядок сферических функций).
4. Короткие расчёты ORCA со всеми базисами списка и def2-ECP на атоме 5-го периода.
5. Один IRC ORCA (HCN ⇄ HNC) → `orca_scan.py`.
6. По одному запросу PubChem и NIST из программы.

После этого в группе 1 останутся только Psi4, Gaussian и GAMESS — программы, которых на Mac нет.
