"""
Менеджер фонового демона SLUGA (OS Process Daemon Manager).
Обеспечивает автономную работу агента 24/7 в фоновом режиме операционной системы
без необходимости держать открытым терминал или SSH-сессию (по аналогии с Hermes / PM2 / Systemd).
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PID_FILE = DATA_DIR / "sluga.pid"
LOG_FILE = DATA_DIR / "sluga.log"

def is_pid_running(pid: int) -> bool:
    """Проверяет, жив ли процесс с указанным PID."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

def get_running_pid() -> int | None:
    """Возвращает PID запущенного демона или None, если он не запущен."""
    if not PID_FILE.exists():
        return None
    try:
        content = PID_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return None
        pid = int(content)
        if is_pid_running(pid):
            return pid
        else:
            # Процесс умер, чистим мусорный PID
            PID_FILE.unlink(missing_ok=True)
            return None
    except Exception:
        return None

def start_daemon():
    """Запускает агента SLUGA в полностью изолированном фоновом процессе (24/7 без терминала)."""
    pid = get_running_pid()
    if pid:
        print(f"⚠️ SLUGA уже запущен в фоновом режиме! PID: {pid}")
        print(f"📊 Проверить статус: python main.py status")
        print(f"⏹️ Остановить:       python main.py stop")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Автоопределение виртуального окружения .venv
    python_bin = sys.executable
    venv_linux = BASE_DIR / ".venv" / "bin" / "python"
    venv_win = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_linux.exists():
        python_bin = str(venv_linux)
    elif venv_win.exists():
        python_bin = str(venv_win)

    main_script = str(BASE_DIR / "main.py")
    cmd = [python_bin, main_script, "bot"]

    log_f = open(LOG_FILE, "a", encoding="utf-8")

    # Изоляция от терминала (setsid / new process group)
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            creationflags=flags
        )
    else:
        # На Linux start_new_session=True вызывает setsid(), полностью отвязывая процесс от TTY
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            start_new_session=True,
            close_fds=True
        )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    time.sleep(1)

    if is_pid_running(proc.pid):
        print("=" * 60)
        print(f"🚀 SLUGA УСПЕШНО ЗАПУЩЕН В АВТОНОМНОМ РЕЖИМЕ 24/7!")
        print("=" * 60)
        print(f"🆔 PID процесса:   {proc.pid}")
        print(f"📝 Файл логов:     {LOG_FILE}")
        print(f"💡 Теперь можно закрывать терминал или отключать SSH.")
        print(f"   Бот продолжит работать независимо на сервере.")
        print("-" * 60)
        print(f"Управление демоном:")
        print(f"   python main.py status   — статус и последние логи")
        print(f"   python main.py logs     — просмотр свежих логов")
        print(f"   python main.py restart  — перезапуск бота")
        print(f"   python main.py stop     — остановка демона")
        print("=" * 60)
    else:
        print("❌ Не удалось запустить фоновый процесс. Проверьте sluga.log:")
        show_logs(20)

def stop_daemon():
    """Останавливает фонового демона SLUGA."""
    pid = get_running_pid()
    if not pid:
        print("ℹ️ Фоновый демон SLUGA не запущен.")
        return

    print(f"🛑 Остановка демона SLUGA (PID: {pid})...")
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(10):
                time.sleep(0.5)
                if not is_pid_running(pid):
                    break
            if is_pid_running(pid):
                os.kill(pid, signal.SIGKILL)
    except Exception as e:
        print(f"⚠️ Ошибка при остановке: {e}")

    PID_FILE.unlink(missing_ok=True)
    print("✅ SLUGA успешно остановлен.")

def status_daemon():
    """Выводит подробный статус фонового демона."""
    pid = get_running_pid()
    print("=" * 60)
    print("📊 СТАТУС АВТОНОМНОГО ДЕМОНА SLUGA:")
    print("=" * 60)
    if pid:
        print(f"🟢 Статус:          АКТИВЕН (Работает 24/7)")
        print(f"🆔 PID:             {pid}")
        print(f"📝 Логи:            {LOG_FILE}")
        print("-" * 60)
        print("📜 Последние события из лога:")
        show_logs(10)
    else:
        print(f"🔴 Статус:          ОСТАНОВЛЕН")
        print(f"💡 Для запуска в фоне выполните: python main.py start")
    print("=" * 60)

def restart_daemon():
    """Перезапускает фонового демона."""
    print("🔄 Перезапуск агента SLUGA...")
    stop_daemon()
    time.sleep(1)
    start_daemon()

def show_logs(lines: int = 40):
    """Выводит последние строки из файла логов."""
    if not LOG_FILE.exists():
        print("📝 Файл логов пока пуст.")
        return
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line.rstrip())
    except Exception as e:
        print(f"Не удалось прочесть логи: {e}")
