import sys, os, json

import sys, os, json


# Шифры, которые автоматически добавляются в блок "ciphers"
import sys, os, json

# Шифры, которые автоматически добавляются в блок "ciphers"
DEFAULT_CIPHERS = {
    "caesar":   {"name": "Шифр Цезаря"},
    "vigenere": {"name": "Шифр Виженёра"},
    "A1Z26":    {"name": "Шифр A1Z26"},
    "atbash":   {"name": "Шифр Атбаш"},
    "playfair": {"name": "Шифр Плейфера"},
}

# Бинарные кодировки, которые автоматически добавляются в блок "binary"
DEFAULT_BINARY = {
    "utf-8":  {"name": "UTF-8"},
    "utf-16": {"name": "UTF-16"},
}


def update_alphabets(folder_path: str = "alphabets") -> None:
    """
    Обрабатывает папку alphabets: для каждой подпапки создаёт словарь в alphabets.json.

    Формат записи для каждого файла:
        "имя_файла.json": { "name": "значение поля meta.name из этого файла" }

    Особый случай: папка 'ciphers' — файлы лежат прямо в ней (без вложенных
    подпапок), но в alphabets.json они всё равно записываются в отдельный
    блок "alps":
        "ciphers": { "alps": { "файл.json": {"name": ...}, ... }, ... }

    После обхода:
      * в блок "ciphers" добавляются предустановленные шифры из DEFAULT_CIPHERS;
      * создаётся/обновляется блок "binary" с DEFAULT_BINARY.
    """
    base_path = resource_path(folder_path)
    alphabets_json_path = data_path(f"{folder_path}/alphabets.json")

    # Загружаем существующий alphabets.json или создаём пустой
    if os.path.exists(alphabets_json_path):
        with open(alphabets_json_path, "r", encoding="utf-8") as f:
            alphabets_data = json.load(f)
    else:
        alphabets_data = {}

    # Проходим по всем подпапкам в alphabets/
    for entry in os.listdir(base_path):
        subfolder = os.path.join(base_path, entry)
        if not os.path.isdir(subfolder):
            continue

        if entry == "ciphers":
            # Особый случай: файлы лежат прямо в ciphers/, но пишем в "alps"
            alps_entries = _collect_entries_from_json(subfolder)
            alphabets_data["ciphers"] = {"alps": alps_entries}
            print(f"✓ Обработана папка 'ciphers' -> alps: "
                  f"{len(alps_entries)} файлов")
        else:
            # Обычная папка: { "файл.json": {"name": ...}, ... }
            alphabets_data[entry] = _collect_entries_from_json(subfolder)
            print(f"✓ Обработана папка '{entry}': "
                  f"{len(alphabets_data[entry])} файлов")

    # Автоматически добавляем/перезаписываем предустановленные шифры
    ciphers_block = alphabets_data.get("ciphers", {})
    if not isinstance(ciphers_block, dict):
        ciphers_block = {}
    ciphers_block.update(DEFAULT_CIPHERS)
    alphabets_data["ciphers"] = ciphers_block

    # Автоматически создаём/обновляем блок binary
    binary_block = alphabets_data.get("binary", {})
    if not isinstance(binary_block, dict):
        binary_block = {}
    binary_block.update(DEFAULT_BINARY)
    alphabets_data["binary"] = binary_block

    # Сохраняем результат
    with open(alphabets_json_path, "w", encoding="utf-8") as f:
        json.dump(alphabets_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Результат сохранён в {alphabets_json_path}")


def _collect_entries_from_json(folder: str) -> dict:
    """
    Возвращает словарь { "имя_файла.json": {"name": ...} } для всех
    .json-файлов в указанной папке.

    Значение — словарь с полем "name" (берётся из meta.name файла),
    чтобы в будущем можно было добавлять другие поля (author, description, ...).
    Если поля meta.name нет — кладём {"name": None}.
    """
    result = {}
    for filename in os.listdir(folder):
        if not filename.lower().endswith(".json"):
            continue
        json_file = os.path.join(folder, filename)
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)

            meta = file_data.get("meta") if isinstance(file_data, dict) else None
            if isinstance(meta, dict) and "name" in meta:
                result[filename] = {"name": meta["name"]}
            else:
                print(f"⚠ В файле {json_file} нет поля 'meta.name'")
                result[filename] = {"name": None}
        except json.JSONDecodeError as e:
            print(f"⚠ Ошибка чтения {json_file}: {e}")
        except Exception as e:
            print(f"⚠ Ошибка при обработке {json_file}: {e}")
    return result

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