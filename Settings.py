# ============================================================
#   settings.py — глобальные настройки + политика неизвестных символов
# ============================================================
#
#   Используется:
#       - ConverterWidgets.py  (загрузка/сохранение/сброс, UI)
#       - Actions.py           (AlphabetAction)
#       - ConverterLogic.py    (execute + диалог)
# ============================================================

from __future__ import annotations

import json
import os

from Paths import data_path


# ------------------------------------------------------------
#   Файл и дефолты
# ------------------------------------------------------------

SETTINGS_FILE: str = data_path("settings.json")

# Используются, если settings.json отсутствует, повреждён
# или в нём нет нужного ключа.
DEFAULT_SETTINGS: dict = {
    # ---------- ПРИЛОЖЕНИЕ ----------
    "theme": "Системная",               # Системная | Светлая | Тёмная
    "version": "beta.0.0",              # НЕИЗМЕНЯЕМО
    # ---------- КОНВЕРТАЦИЯ ----------
    "und_char_pol": "Предупреждение",   # Предупреждение | Игнорировать | Заменить
    "replacement": "?",                 # Символ для замены
    "case_sensitive": False,            # Регистрозависимость
    # --- Морзе → звук ---
    "morse_freq": 800,                  # Частота звука, Гц
    "morse_sample_rate": 44100,         # Частота дискретизации, Гц
    "morse_wpm": 25,                    # Слов в минуту
}

# Глобальный словарь. Заполняется load_settings() при старте.
SETTINGS: dict = dict(DEFAULT_SETTINGS)


# ------------------------------------------------------------
#   Загрузка / сохранение / сброс
# ------------------------------------------------------------

def load_settings() -> dict:
    """Прочитать settings.json (если есть) поверх дефолтов."""
    result = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                result.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    # version — из файла не доверяем, всегда текущая
    result["version"] = DEFAULT_SETTINGS["version"]

    SETTINGS.clear()
    SETTINGS.update(result)
    return SETTINGS


def save_settings(values: dict | None = None) -> None:
    """Сохранить SETTINGS в файл, при необходимости — с обновлением."""
    if values is not None:
        # version — константа, из UI не перезаписывается
        values = {k: v for k, v in values.items() if k != "version"}
        SETTINGS.update(values)
    SETTINGS["version"] = DEFAULT_SETTINGS["version"]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
        json.dump(SETTINGS, fp, indent=4, ensure_ascii=False)


def reset_settings() -> dict:
    """Удалить settings.json и восстановить SETTINGS из DEFAULT_SETTINGS."""
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

POLICY_IGNORE = "Игнорировать"
POLICY_REPLACE = "Заменить"
POLICY_WARN = "Предупреждение"

VALID_POLICIES: tuple[str, ...] = (POLICY_IGNORE, POLICY_REPLACE, POLICY_WARN)


class UnknownPolicy:
    """
    Политика обработки символа, отсутствующего в алфавите.

    mode:
        POLICY_IGNORE  — resolve() -> None (символ выбросить);
        POLICY_REPLACE — resolve() -> replacement (может быть пустым —
                         это осознанная замена на пустоту, не игнор);
        POLICY_WARN    — resolve() бросает UnknownSymbolPolicyError.
    """

    __slots__ = ("mode", "replacement", "case_sensitive")

    def __init__(
        self,
        mode: str | None = None,
        replacement: str | None = None,
        case_sensitive: bool | None = None,
    ) -> None:
        self.mode = (
            mode if mode is not None
            else SETTINGS.get("und_char_pol", POLICY_WARN)
        )
        self.replacement = (
            replacement if replacement is not None
            else SETTINGS.get("replacement", "")
        )
        self.case_sensitive = (
            case_sensitive if case_sensitive is not None
            else bool(SETTINGS.get("case_sensitive", False))
        )
        if self.mode not in VALID_POLICIES:
            self.mode = POLICY_WARN

    @classmethod
    def current(cls) -> "UnknownPolicy":
        """Политика из текущих SETTINGS."""
        return cls()

    def resolve(
        self,
        ch: str,
        alphabet_path: str | None = None,
        partial_out: str = "",
    ) -> str | None:
        """Разрешить неизвестный символ по текущей политике."""
        # Локальный импорт: Settings грузится очень рано, а Exceptions
        # тянет за собой Actions-зависимости — не хотим циклов на старте.
        from Exceptions import UnknownSymbolPolicyError

        if self.mode == POLICY_IGNORE:
            return None
        if self.mode == POLICY_REPLACE:
            return self.replacement
        raise UnknownSymbolPolicyError(ch, alphabet_path, partial_out)