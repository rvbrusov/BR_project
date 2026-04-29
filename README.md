# BR_project

Локальный Python-проект с графическим интерфейсом (Tkinter) для проведения и фиксации результатов тестовых методик.

## Требования

- Python 3.10+
- `pip`
- Windows (основной сценарий использования)

## Установка

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Запуск

Основной рабочий скрипт:

```powershell
python fixed252_app_2026-04-25_portable_build.py
```

Дополнительные тестовые/экспериментальные сценарии:

```powershell
python tensor_matrix_test_2026_04_23_v14.py
```

## Структура

- `assets/` - изображения и графические ресурсы
- `data/` - данные участников и результаты
- `fixed*_app_*.py` - версии основного приложения
- `tensor_matrix_test_*.py` - отдельные тестовые сценарии

## Работа с GitHub

После изменений:

```powershell
git status
git add .
git commit -m "Описание изменений"
git push
```

## Публикация EXE через GitHub Releases

В репозитории настроен workflow `.github/workflows/release-exe.yml`.

Как выпустить новую сборку:

```powershell
git tag v254
git push origin v254
```

После пуша тега GitHub Actions:
- соберет последний `fixed*_portable_upx_onefile.spec` на `windows-latest`;
- создаст/обновит релиз для тега;
- прикрепит `.exe` к релизу.

Постоянная страница загрузок:
- `https://github.com/rvbrusov/BR_project/releases`
