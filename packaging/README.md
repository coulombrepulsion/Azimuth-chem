# Сборка «Азимута» для установки

Готовая программа без Python и без папки с исходниками: образ диска для macOS и установщик для Windows. Обе сборки делает PyInstaller по одному файлу `packaging/azimuth.spec`.

## macOS (Apple silicon) — `Azimuth-<версия>-macOS-arm64.dmg`

На своём Маке, из папки программы:

```
zsh packaging/build_macos.sh
```

Что делает скрипт:

1. Ставит PyInstaller в `.venv`, если его там нет.
2. Собирает `dist/Azimuth.app`.
3. Проверяет запуск: открывает хаб и все разделы, как сборка Windows. Если программа не запустилась, образ не делается.
4. Складывает в `dist/installer/` образ (приложение и ярлык «Программы») и его SHA-256.

Проверка запуска идёт без VTK. Перед тем как отдавать образ, откройте приложение руками и постройте молекулу в Компасе.

Тот же образ можно собрать на GitHub: Actions → «macOS disk image» → Run workflow. Сборка запускается и сама, по метке `v*`.

> 2026-11-24: GitHub Actions закрытого репозитория сейчас без минут (бесплатный запас кончился; минута macOS стоит как десять минут Linux). Пока их нет, образ macOS собирается на Mac — `packaging/build_macos.sh`.

**Без подписи.** На Apple silicon PyInstaller подписывает приложение «ad hoc» — без такой подписи оно не запустится вовсе. При первом запуске скачанного образа macOS предупредит, что разработчика проверить нельзя. Тогда:

1. Перетащите «Азимут» в «Программы» и откройте его.
2. Появится сообщение «не удалось проверить разработчика».
3. Откройте «Системные настройки → Конфиденциальность и безопасность → Всё равно открыть».

Это нужно один раз.

**С подписью**, когда будет учётная запись Apple Developer:

1. Создайте сертификат «Developer ID Application»: Xcode → Settings → Accounts → Manage Certificates.
2. Один раз сохраните пароль для нотаризации. Пароль приложения создаётся на account.apple.com:
   ```
   xcrun notarytool store-credentials azimuth --apple-id <почта> --team-id <TEAMID> --password <пароль приложения>
   ```
3. Соберите:
   ```
   AZIMUTH_CODESIGN_IDENTITY="Developer ID Application: Имя (TEAMID)" AZIMUTH_NOTARY_PROFILE=azimuth zsh packaging/build_macos.sh
   ```
   Скрипт подпишет каждую библиотеку и приложение с hardened runtime (`packaging/entitlements.plist`), подпишет образ, отправит его Apple и прикрепит ответ (staple).

Для GitHub те же данные кладутся в секреты репозитория, их список — в начале `.github/workflows/build-macos.yml`.

## Windows — `Azimuth-Setup-<версия>.exe`

Собирается на GitHub: Actions → «Windows installer» → Run workflow, или по метке `v*` (2026-11-24: минут Actions нет — см. выше; без них нужен компьютер с Windows, PyInstaller и Inno Setup). Внутри: PyInstaller, проверка запуска и Inno Setup (`packaging/azimuth.iss`). Программа ставится без прав администратора в `%LOCALAPPDATA%\Programs\Azimuth`.

**Без подписи** SmartScreen при первом запуске покажет «Windows защитил ваш компьютер». Нажмите «Подробнее → Выполнить в любом случае».

**С подписью**: сертификат подписи кода (.pfx) в base64 кладётся в секрет `WINDOWS_CERT_PFX`, пароль — в `WINDOWS_CERT_PASSWORD`. Тогда подписываются и `Azimuth.exe`, и установщик.

## Где собранная программа хранит своё

Внутрь собранной программы ничего не пишется. Подписанное приложение и Program Files менять нельзя.

| | macOS | Windows |
|---|---|---|
| Программы, поставленные из Секстанта (xtb и др.) | `~/Library/Application Support/Azimuth` | `%LOCALAPPDATA%\Azimuth` |
| Журналы | `~/Library/Logs/Azimuth` | `%LOCALAPPDATA%\Azimuth\Logs` |
