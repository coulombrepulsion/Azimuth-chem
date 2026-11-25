# Эталоны MOPAC (0.91)

Входы — в `inputs/`; выводы посчитаны MOPAC 23.2.5 (conda-forge, macOS arm64) на компьютере пользователя 2026-11-01:

```
.venv/bin/python -m modules.sextant.install_tools mopac    # MOPAC в .tools/calc
.venv/bin/python tools/run_references.py mopac
```

Рядом с каждым выводом `.out` лежат `.aux` (ключевое слово `AUX`, его читает Спектр) и `.arc`.

| Вход | Что проверяется |
|---|---|
| `h2o_pm7_opt`, `ch2o_pm7_opt`, `c2h4_pm7_opt`, `c6h6_pm7_opt` | оптимизация PM7: ΔHf, шаги, заряды, диполь |
| `ch3_pm7_uhf_doublet_opt` | радикал: UHF, дублет |
| `nh4_pm7_cation_opt` | катион: `CHARGE=1`, сумма зарядов +1 |
| `h2o_pm7_cosmo_opt` | растворитель COSMO (`EPS=78.4`) |
| `h2o_pm6_1scf`, `ch2o_am1_1scf` | одиночные точки PM6 и AM1 |
| `h2o_pm7_force_thermo`, `ch2o_pm7_force`, `c2h4_pm7_force`, `ch3_pm7_uhf_doublet_force`, `c6h6_pm7_force_thermo` | частоты (`FORCE`) и термохимия (`THERMO`) на геометриях оптимизаций выше (второй проход: MOPAC не оптимизирует перед `FORCE`) |
| `h2o_pm7_force_unoptimized` | `FORCE` на неоптимизированной геометрии: MOPAC 23.2.5 не останавливается, «нулевые» моды до 130 см⁻¹ — эталон предупреждения |
| `h2o_pm7_opt_then_force_oldgeo`, `…_blank` | два задания в одном файле (0.91.5): оптимизация, затем `FORCE THERMO OLDGEO` — частоты на её геометрии; с пустой строкой после заголовков второго задания и без — MOPAC 23.2.5 принимает оба; частоты те же, что у двух отдельных запусков |
| `h2s_pm7_opt`, `so2_pm7_opt`, `ticl4_pm7_opt` | d-функции (0.91.6, посчитаны 2026-11-02): знаки и нормировка d в орбиталях `.aux` — сверка с OVERLAP_MATRIX и ATOM_CHARGES (`tests/spectrum/test_mopac_orbitals.py`); у TiCl₄ напечатаны орбитали 7…26 — первые шесть восстанавливаются из матрицы плотности |

Орбитали всех `.aux` выше (0.91.6): перекрывания слэтеровских функций, записанных шестью гауссовыми, совпадают с OVERLAP_MATRIX MOPAC до 1,7·10⁻⁴ (бензол), заряды Коулсона — с ATOM_CHARGES до 10⁻³.

`h2o_atoms_too_close.out` (0.222.14, посчитан 2026-11-22, MOPAC 23.2.5, вход Секстанта, PM7 1SCF): вода, у которой два H в 0,15 Å друг от друга — «GEOMETRY IN ERROR. TO CONTINUE CALCULATION SPECIFY 'GEO-OK'», ничего не посчитано, но в конце «JOB ENDED NORMALLY» и код 0 (`tests/sextant/test_runner.py`, `tests/spectrum/test_mopac.py`).

`h2o_force_gradient_too_large.out`, `.mop` (0.222.26, посчитан 2026-11-23, MOPAC 23.2.5, вход Секстанта «Частоты и термохимия», PM7 FORCE THERMO): вода из SMILES без оптимизации — норма градиента 16 больше предела MOPAC 10, частоты не посчитаны («GRADIENT IS TOO LARGE TO ALLOW THE FORCE MATRIX…»), в конце всё равно «JOB ENDED NORMALLY». Файл не изменён.
