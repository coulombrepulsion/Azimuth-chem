# Проверка тестов — 2026-10-30

Среда: macOS, Python проекта (.venv), Qt offscreen. Рабочий код и иллюстрации не изменялись.

## Добавлено

`tests/compass/test_geometry_invariants.py`: 16 сценариев для публичной функции measurement.
Независимые эталоны: треугольник 3–4–5, ортогональные оси, знаковый двугранный угол.
Проверены сохранение расстояний и углов при повороте и переносе, сохранение углов при масштабировании, смена знака двугранного угла при зеркальном отражении.

## Результаты

- 239 существующих тестов вычислений и парсеров: успешно.
- 16 новых тестов в окружении проекта: успешно.
- Проверка очереди соединений локального сервера Атласа: успешно при разрешённом localhost. Первоначальный отказ Operation not permitted был ограничением среды запуска.
- Общий прогон не завершён: нативный VTK аварийно завершает процесс в vtk_model.render при проверке available. Воспроизведено при сборе test_vtk_model.py и в фикстуре test_bond_depth.py. Причина требует отдельного исследования; этот результат не доказывает сбой обычного оконного запуска.
- В прерванном расширенном прогоне были также ошибки подготовки и провалы тестов; полный их разбор не выполнен.
- Windows и интерактивный интерфейс в рамках этой проверки не проверены. Прохождение всей тестовой базы не заявляется.

## Воспроизведение вычислительной проверки

```sh
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/core/test_core.py tests/compass/test_builder.py tests/compass/test_formats.py tests/compass/test_geometry_tools.py tests/compass/test_measurement_edit.py tests/compass/test_transforms.py tests/spectrum/test_orca_real.py tests/spectrum/test_outputs.py tests/spectrum/test_gaussian.py tests/spectrum/test_orca_spectra.py tests/spectrum/test_vibration_contract.py tests/compass/test_vibration_frames.py tests/spectrum/test_vibrations.py tests/spectrum/test_trajectory.py tests/sextant/test_inputs.py tests/compass/test_crystal.py tests/spectrum/test_thermo.py tests/compass/test_geometry_invariants.py
```
