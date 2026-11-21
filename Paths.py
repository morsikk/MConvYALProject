import sys, os


def base_dir() -> str:
    """
    Папка, относительно которой лежат ВНЕШНИЕ (изменяемые) файлы:
    settings.json, temp_morse.wav и т.п.

    В обычном запуске .py — папка скрипта.
    В exe (frozen) — папка, где лежит сам exe (sys.executable).
    Это гарантирует, что пользователь видит и может редактировать файлы
    рядом с программой, и они не теряются при пересоздании _MEIPASS.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative: str) -> str:
    """
    Абсолютный путь к РЕСУРСУ, упакованному внутрь exe (read-only).

    В обычном запуске .py — путь относительно папки скрипта.
    В exe PyInstaller (в т.ч. --onefile) — относительно sys._MEIPASS.

    Аргумент relative может содержать подпапки через '/' (например
    'alphabets/alphabets.json'). Возвращается абсолютный путь.
    """
    if hasattr(sys, "_MEIPASS"):
        root = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        root = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root, *relative.split("/"))


def data_path(relative: str) -> str:
    """
    Абсолютный путь к ИЗМЕНЯЕМОМУ файлу рядом с exe (или скриптом).

    settings.json, temp_morse.wav и подобные пишутся в base_dir().
    """
    return os.path.join(base_dir(), *relative.split("/"))