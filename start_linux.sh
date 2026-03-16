#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python не найден. Установите Python 3.11+ или создайте .venv."
  exit 1
fi

has_gui_session() {
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]
}

has_xcb_cursor() {
  find /usr/lib /lib -path '*/libxcb-cursor.so.0*' -print -quit 2>/dev/null | grep -q .
}

if ! has_gui_session; then
  echo "Графическая сессия не найдена."
  echo
  echo "Запускайте приложение из обычного рабочего стола Linux,"
  echo "а не из headless-сессии или чистого SSH-терминала."
  exit 1
fi

if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
  if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    export QT_QPA_PLATFORM="wayland;xcb"
  elif [[ -n "${DISPLAY:-}" ]]; then
    export QT_QPA_PLATFORM="xcb"
  fi
fi

if [[ "${QT_QPA_PLATFORM:-}" == *"xcb"* ]] && ! has_xcb_cursor; then
  echo "Qt не нашёл системную библиотеку libxcb-cursor.so.0"
  echo
  echo "Для Ubuntu/Debian установите:"
  echo "  sudo apt update"
  echo "  sudo apt install libxcb-cursor0"
  echo
  echo "После этого снова запустите:"
  echo "  bash start_linux.sh"
  exit 1
fi

set +e
"$PYTHON_BIN" "$SCRIPT_DIR/run.py"
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo
  echo "Приложение не запустилось."
  if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    echo "Попробуйте запуск под Wayland:"
    echo "  QT_QPA_PLATFORM=wayland bash start_linux.sh"
  fi
  if [[ -n "${DISPLAY:-}" ]]; then
    echo "Попробуйте запуск под X11:"
    echo "  QT_QPA_PLATFORM=xcb bash start_linux.sh"
  fi
  echo "Если ошибка повторится, пришлите весь текст из терминала."
fi

exit "$STATUS"
