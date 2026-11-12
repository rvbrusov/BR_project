# Aviatest — исходники тестовых методик

Репозиторий содержит историческую версию Python-программы с интерфейсом Tkinter.
Последний исходник приложения в этих ветках — `fixed256_app_2026-04-25_portable_build.py`.
Это не актуальная поставка Aviatest 4.x.

## Запуск

Требуются Python 3.10+ и Windows для основного сценария использования.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python fixed256_app_2026-04-25_portable_build.py
```

Отдельная методика: `tensor_matrix_test_2026_04_23_v14.py`.

## Содержимое

- `assets/` — ресурсы методик.
- `method_*_config.json` и `config_schema_version.txt` — настройки.
- `*.spec` — описания сборки PyInstaller.
- `*.docx` — документация и расчёты методик.
- `.github/workflows/` — проверки исходников и сборка EXE.

Ветки `testABC` и `testD` сохраняют свои варианты исходников и настроек.
Данные участников, прогресс, результаты, резервные копии и готовые сборки
не входят в исходники. Программа создаёт рабочую папку `data/` автоматически.

Прежние версии файлов доступны в истории Git.
