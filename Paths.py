# ============================================================
#   Paths.py — пути к ресурсам/данным и синхронизация alphabets.json
# ============================================================

import json
import os
import sys


# ============================================================
#   Константы по умолчанию
# ============================================================

# Шифры, которые автоматически добавляются в блок "ciphers"
DEFAULT_CIPHERS: dict[str, dict] = {
    "caesar":   {"name": "Шифр Цезаря"},
    "vigenere": {"name": "Шифр Виженёра"},
    "A1Z26":    {"name": "Шифр A1Z26"},
    "atbash":   {"name": "Шифр Атбаш"},
    "playfair": {"name": "Шифр Плейфера"},
    "reverse":  {"name": "Переворот строки"},
    "columnar": {"name": "Транспонирование по столбцам"},
}

# Бинарные кодировки, которые автоматически добавляются в блок "binary"
DEFAULT_BINARY: dict[str, dict] = {
    "utf-8":  {"name": "UTF-8"},
    "utf-16": {"name": "UTF-16"},
}


# ============================================================
#   Базовые пути
# ============================================================

def base_dir() -> str:
    """
    Папка ВНЕШНИХ (изменяемых) файлов: settings.json, temp_morse.wav и т.п.

    .py — папка скрипта; exe (frozen) — папка рядом с sys.executable.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative: str) -> str:
    """
    Абсолютный путь к РЕСУРСУ, упакованному в exe (read-only).

    .py — относительно папки скрипта; exe PyInstaller — sys._MEIPASS.
    `relative` может содержать подпапки через '/'.
    """
    if hasattr(sys, "_MEIPASS"):
        root = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        root = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root, *relative.split("/"))


def data_path(relative: str) -> str:
    """
    Абсолютный путь к ИЗМЕНЯЕМОМУ файлу рядом с exe (или скриптом).
    """
    return os.path.join(base_dir(), *relative.split("/"))


def alphabet_file(subdir: str, filename: str) -> str:
    """
    Путь к файлу алфавита: приоритет data_path (изменяемые),
    затем resource_path (упакованные). Если нет ни там, ни там —
    возвращает resource_path, чтобы ошибка открытия была понятной.
    """
    relative = f"alphabets/{subdir}/{filename}"
    for base in (data_path, resource_path):
        path = base(relative)
        if os.path.exists(path):
            return path
    return resource_path(relative)


# ============================================================
#   Синхронизация alphabets.json
# ============================================================

def update_alphabets(folder_path: str = "alphabets") -> None:
    """
    Синхронизировать alphabets.json с реальными файлами в папке alphabets.

    - для каждой подпапки (morse, braille, binary, number_systems, ciphers)
      блок перезаписывается списком файлов с диска;
    - для 'ciphers' дополнительно гарантируются DEFAULT_CIPHERS;
    - для 'binary' дополнительно гарантируются DEFAULT_BINARY.
    """
    base_path = resource_path(folder_path)
    json_path = data_path(f"{folder_path}/alphabets.json")

    alphabets_data = _load_json(json_path) or {}

    if os.path.isdir(base_path):
        for entry in os.listdir(base_path):
            subfolder = os.path.join(base_path, entry)
            if not os.path.isdir(subfolder):
                continue
            disk_entries = _collect_entries_from_json(subfolder)
            if entry == "ciphers":
                _sync_ciphers(alphabets_data, disk_entries)
            else:
                alphabets_data[entry] = disk_entries

    # Блок binary (utf-8, utf-16) должен быть всегда — даже без папки на диске
    binary_block = alphabets_data.get("binary")
    if not isinstance(binary_block, dict):
        binary_block = {}
    binary_block.update(DEFAULT_BINARY)
    alphabets_data["binary"] = binary_block

    _save_json(json_path, alphabets_data)


def _sync_ciphers(alphabets_data: dict, disk_entries: dict) -> None:
    """
    Обновить блок 'ciphers': alps — с диска, дефолтные шифры — принудительно.
    """
    ciphers_block = alphabets_data.get("ciphers")
    if not isinstance(ciphers_block, dict):
        ciphers_block = {}
    ciphers_block["alps"] = disk_entries
    ciphers_block.update(DEFAULT_CIPHERS)
    alphabets_data["ciphers"] = ciphers_block


def _collect_entries_from_json(folder: str) -> dict[str, dict]:
    """
    { "имя_файла.json": {"name": ...} } для всех .json в папке.

    name берётся из meta.name; если его нет — {"name": None}
    (в будущем сюда же можно добавлять author/description и т.п.).
    """
    result: dict[str, dict] = {}
    for filename in os.listdir(folder):
        if not filename.lower().endswith(".json"):
            continue

        json_file = os.path.join(folder, filename)
        data = _load_json(json_file)
        if data is None:
            continue

        meta = data.get("meta") if isinstance(data, dict) else None
        if isinstance(meta, dict) and "name" in meta:
            result[filename] = {"name": meta["name"]}
        else:
            print(f"⚠ В файле {json_file} нет поля 'meta.name'")
            result[filename] = {"name": None}
    return result


# ============================================================
#   Внутренние хелперы JSON
# ============================================================

def _load_json(path: str) -> dict | None:
    """Прочитать JSON-объект; при ошибке вернуть None и напечатать причину."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"⚠ Ошибка чтения {path}: {e}")
        return None


def _save_json(path: str, data: dict) -> None:
    """Сохранить JSON-объект; создать родительскую папку при необходимости."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)