# Воспроизводимость «Азимута»

verified 2026-10-20: Python 3.13.3, macOS arm64; версии runtime и SHA256
зафиксированы в requirements-lock-macos-arm64.txt. Windows x64 Python 3.13:
полный комплект колёс разрешён pip и скачан, хэши — requirements-lock-win-amd64.txt.
Linux x86_64 Python 3.13 (0.194.0): хэши колёс manylinux тех же версий по PyPI — requirements-lock-linux-x86_64.txt.
Это воспроизводимость входных артефактов, а не побитовое совпадение картинки.

## Четыре варианта

1. Обычная установка: `bash setup.sh`; Windows: windows_first_run.bat.
2. Только зависимости: `python -m pip install --require-hashes -r requirements-lock-macos-arm64.txt`
   (на Windows использовать requirements-lock-win-amd64.txt, на Linux — requirements-lock-linux-x86_64.txt).
3. Без интернета: сначала `bash setup.sh --offline-bundle /path/to/wheels`,
   затем на подходящей платформе `bash setup.sh --no-download --offline-bundle /path/to/wheels`.
   PowerShell: `-OfflineBundle DIRECTORY`, затем дополнительно `-NoDownload`.
4. Полный перенос: сохранить каталог исходников без .venv и кэшей вместе с
   каталогом колёс своей платформы, Python-установщиком, документами и лицензиями.
   Скрипт создаёт каталог колёс, не ZIP. На новой машине выполнить вариант 3.

Не смешивайте колёса двух платформ. Сохраните requirements-frozen.txt,
assets-manifest.json, оба lock и результаты verify_install.py. При исчезновении
PyPI локальные колёса позволяют восстановить зависимости; заранее сохраните
также установщик Python. Модели не скачиваются: учебные примеры входят в проект.
Conda-файл создаёт только интерпретатор; затем используйте setup --skip-venv.
Conda-вариант не протестирован и не является полным lock.

Через несколько лет вероятные препятствия — поддержка старой версии Python
новой ОС и изменения графических драйверов. При обновлении зависимостей создайте
новые lock, заново выполните тесты и проверку настоящего окна CUBE. Не заменяйте
хэши только ради успешной установки.

ASSUMPTION: Windows GUI/PowerShell 5.1 и macOS Intel требуют отдельных запусков;
для macOS Intel lock не предоставляется. Проверенная macOS-цель требует 14+
по тегам колёс Qt и NumPy; это не результат испытаний на каждой версии macOS.
