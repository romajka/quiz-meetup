# Quiz Meetup

Локальное desktop-приложение для проведения квизов на `Python + PySide6 + SQLite`.

Готового `exe` в проекте сейчас нет. Текущая версия запускается через `Python`, а сборка в `exe` подготовлена как следующий этап.

## Как быстро протестировать сейчас

### Linux

Если виртуальное окружение уже создано:

```bash
cd /home/ramin/quiz-meetup
bash start_linux.sh
```

Если зависимостей ещё нет:

```bash
cd /home/ramin/quiz-meetup
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash start_linux.sh
```

### Windows

Если виртуальное окружение уже есть, можно запускать:

- двойным кликом по [start_windows.bat](/home/ramin/quiz-meetup/start_windows.bat)
- или через PowerShell: [start_windows.ps1](/home/ramin/quiz-meetup/start_windows.ps1)

Если зависимостей ещё нет:

```powershell
cd C:\path\to\quiz-meetup
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

После этого:

- двойной клик по `start_windows.bat`
- или команда `python run.py`

## Кроссплатформенность

Сейчас проект уже ориентирован на Linux и Windows:

- локальные пути к данным выбираются по ОС в [paths.py](/home/ramin/quiz-meetup/src/quiz_meetup/paths.py)
- ресурсы интерфейса и схемы БД грузятся безопасно через пакетные ресурсы
- добавлены launcher-скрипты для Linux и Windows
- шрифт приложения теперь выбирается с учётом платформы в [styles.py](/home/ramin/quiz-meetup/src/quiz_meetup/ui/styles.py)

### Где хранятся данные

На Windows:

```text
%LOCALAPPDATA%\Quiz Meetup\
```

На Linux:

```text
~/.local/share/Quiz Meetup/
```

Внутри:

- `quiz_meetup.db` — база данных
- `media/game_<id>/...` — локально скопированные медиафайлы

Если системная папка недоступна, используется резервная папка проекта:

```text
.quiz_meetup_data/
```

## Запуск из VS Code на Windows

1. Открой папку проекта `quiz-meetup`.
2. Установи расширение `Python` от Microsoft.
3. Создай `.venv`.
4. Установи зависимости из `requirements.txt`.
5. Выбери интерпретатор `.venv\Scripts\python.exe`.
6. Нажми `F5` и выбери конфигурацию `Quiz Meetup (run.py)` из [.vscode/launch.json](/home/ramin/quiz-meetup/.vscode/launch.json).

## Будущая сборка в exe через PyInstaller

Когда понадобится Windows-сборка:

```powershell
pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name QuizMeetup ^
  --paths src ^
  --collect-data quiz_meetup ^
  run.py
```

Результат:

```text
dist\QuizMeetup\QuizMeetup.exe
```

## Главные файлы запуска

- [run.py](/home/ramin/quiz-meetup/run.py) — основной локальный запуск
- [start_linux.sh](/home/ramin/quiz-meetup/start_linux.sh) — быстрый запуск на Linux
- [start_windows.bat](/home/ramin/quiz-meetup/start_windows.bat) — запуск двойным кликом на Windows
- [start_windows.ps1](/home/ramin/quiz-meetup/start_windows.ps1) — запуск через PowerShell
- [src/quiz_meetup/__main__.py](/home/ramin/quiz-meetup/src/quiz_meetup/__main__.py) — запуск через `python -m quiz_meetup`
