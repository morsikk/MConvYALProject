# ============================================================
#   settings.py
# ============================================================
#
#   Глобальные настройки приложения + политика обработки
#   символов, отсутствующих в алфавите.
#
#   Используется:
#       - ConverterWidgets.py  (загрузка/сохранение/сброс, UI)
#       - unknown_policy       -> теперь часть этого модуля
#       - actions.py           (AlphabetAction)
#       - ConverterLogic.py    (execute + диалог)
# ============================================================

from __future__ import annotations

import json
import os

from Paths import data_path


# ------------------------------------------------------------
#   Файл и дефолты
# ------------------------------------------------------------

SETTINGS_FILE = data_path("settings.json")

# Дефолтные настройки. Используются, если settings.json отсутствует,
# повреждён или в нём нет нужного ключа.
DEFAULT_SETTINGS: dict = {
    "und_char_pol": "Предупреждение",  # Предупреждение | Игнорировать | Заменить
    "replacement": "?",                # Символ для замены
    "theme": "Системная",              # Системная | Светлая | Тёмная
    "version": "valpha.0.4",             # НЕИЗМЕНЯЕМО
}

# Глобальный словарь настроек. Заполняется load_settings() при старте.
SETTINGS: dict = dict(DEFAULT_SETTINGS)


# ------------------------------------------------------------
#   Загрузка / сохранение / сброс
# ------------------------------------------------------------

def load_settings() -> dict:
    result = dict(DEFAULT_SETTINGS)
    path = SETTINGS_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                result.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    # version не доверяем файлу — всегда текущая версия приложения
    result["version"] = DEFAULT_SETTINGS["version"]

    SETTINGS.clear()
    SETTINGS.update(result)
    return SETTINGS


def save_settings(values: dict | None = None) -> None:
    if values is not None:
        # version — константа, из UI не перезаписывается
        values = {k: v for k, v in values.items() if k != "version"}
        SETTINGS.update(values)
    # version всегда актуален в SETTINGS (из DEFAULT_SETTINGS при load/reset)
    SETTINGS["version"] = DEFAULT_SETTINGS["version"]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
        json.dump(SETTINGS, fp, indent=4, ensure_ascii=False)


def reset_settings() -> dict:
    """
    Сбрасывает настройки до дефолтных: удаляет settings.json
    и восстанавливает глобальный SETTINGS из DEFAULT_SETTINGS.
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
    except OSError:
        pass

    SETTINGS.clear()
    SETTINGS.update(DEFAULT_SETTINGS)
    return SETTINGS


# ============================================================
#   Политика обработки неизвестных символов
# ============================================================

# ============================================================
#   Политика обработки неизвестных символов
# ============================================================

POLICY_IGNORE = "Игнорировать"
POLICY_REPLACE = "Заменить"
POLICY_WARN = "Предупреждение"

VALID_POLICIES = (POLICY_IGNORE, POLICY_REPLACE, POLICY_WARN)


class UnknownPolicy:
    __slots__ = ("mode", "replacement")

    def __init__(self, mode: str | None = None, replacement: str | None = None) -> None:
        self.mode = mode if mode is not None else SETTINGS.get("und_char_pol", POLICY_WARN)
        self.replacement = (
            replacement if replacement is not None
            else SETTINGS.get("replacement", "")
        )
        if self.mode not in VALID_POLICIES:
            self.mode = POLICY_WARN

    @classmethod
    def current(cls) -> "UnknownPolicy":
        return cls()

    def resolve(self, ch: str, alphabet_path: str | None = None, partial_out: str = "") -> str | None:
        """
        Возвращает:
            - None  -> «игнорировать» (символ выбросить);
            - str   -> строка-замена (может быть пустой — это
                       осознанная замена на пустоту, но НЕ игнор).
        """
        # импорт здесь, чтобы не тянуть Exceptions на уровне модуля
        # (Settings импортируется очень рано, из ConverterWidgets)
        from Exceptions import UnknownSymbolPolicyError

        if self.mode == POLICY_IGNORE:
            return None
        if self.mode == POLICY_REPLACE:
            return self.replacement
        raise UnknownSymbolPolicyError(ch, alphabet_path, partial_out)