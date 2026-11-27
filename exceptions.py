# ============================================================
#   exceptions.py — кастомные исключения приложения
# ============================================================

class ActionError(Exception):
    """
    База для всех ошибок модуля actions.

    Наследники несут контекст (символ, частичный результат и т.п.),
    чтобы UI мог показать осмысленное сообщение. Презентационные
    атрибуты (title, icon) + dialog_spec() позволяют показывать
    ошибку единообразно, не разбирая типы.
    """

    title: str = "Ошибка"
    icon: str = "critical"  # "critical" | "warning" | "info"

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @property
    def message(self) -> str:
        return str(self.args[0]) if self.args else ""

    def dialog_spec(self) -> tuple[str, str, str]:
        """(заголовок, текст, иконка) для показа пользователю."""
        return self.title, self.message, self.icon


class CardCancelled(Exception):
    """Пользователь отменил операцию в диалоге политики."""


class UnknownSymbolError(ActionError):
    """
    Символ отсутствует в выбранном алфавите.

    Атрибуты:
        symbol:      символ (или фрагмент), который не найден;
        alphabet_path: путь к JSON-алфавиту;
        partial_out: уже закодированная часть результата.
    """

    def __init__(
        self, symbol: str, alphabet_path: str, partial_out: str = ""
    ) -> None:
        super().__init__(
            f"Символ {symbol!r} отсутствует в алфавите «{alphabet_path}». "
            f"Политика: до первой ошибки."
        )
        self.symbol = symbol
        self.alphabet_path = alphabet_path
        self.partial_out = partial_out


class InvalidAlphabetError(ActionError):
    """
    JSON-файл алфавита имеет неверную структуру.

    Атрибуты:
        path:    путь к проблемному файлу;
        missing: список отсутствующих/некорректных ключей.
    """

    title = "Ошибка алфавита"

    def __init__(self, path: str, missing: list[str]) -> None:
        super().__init__(
            f"Некорректный алфавит '{path}': "
            f"отсутствуют или пусты поля {missing}"
        )
        self.path = path
        self.missing = missing


class InvalidKeySymbolError(ActionError):
    """
    В ключе шифра Виженёра встретился символ, которого нет в алфавите.

    Атрибуты:
        symbol:        символ ключа, отсутствующий в алфавите;
        position:      позиция этого символа в ключе (0-based);
        key:           ключ целиком (для диагностики);
        alphabet_path: путь к JSON-алфавиту.
    """

    title = "Ошибка ключа"

    def __init__(
        self,
        symbol: str,
        position: int,
        key: str,
        alphabet_path: str,
        message: str = "<-- этого символа ключа нет в выбранном словаре!",
    ) -> None:
        super().__init__(
            f"Ключ {key!r}: символ {symbol!r} на позиции {position} "
            f"{message} (алфавит: '{alphabet_path}')"
        )
        self.symbol = symbol
        self.position = position
        self.key = key
        self.alphabet_path = alphabet_path


class MissingSpacerError(ActionError):
    """
    В алфавите не задан разделитель символов (meta.spacer).

    Атрибуты:
        path: путь к файлу алфавита.
    """

    title = "Ошибка алфавита"

    def __init__(self, path: str) -> None:
        super().__init__(f"В алфавите '{path}' не задан meta.spacer")
        self.path = path


class MissingSpaceSymbolError(ActionError):
    """
    В алфавите нет символа пробела, хотя входной текст его содержит.

    Атрибуты:
        symbol:      сам пробельный символ (обычно ' ');
        partial_out: уже закодированная часть результата.
    """

    def __init__(self, symbol: str, partial_out: str) -> None:
        super().__init__(
            f"Символ пробела '{symbol}' отсутствует в выбранном алфавите "
            f"(добавьте его в letters)"
        )
        self.symbol = symbol
        self.partial_out = partial_out


class UnknownSymbolPolicyError(ActionError):
    """
    Политика «Предупреждение» встретила символ, отсутствующий в алфавите.

    Несёт достаточно контекста, чтобы UI мог:
      - показать partial_out;
      - спросить пользователя о политике;
      - повторить операцию.
    """

    title = "Неизвестный символ"

    def __init__(
        self,
        symbol: str,
        alphabet_path: str | None = None,
        partial_out: str = "",
    ) -> None:
        super().__init__(
            f"Символ {symbol!r} отсутствует в алфавите "
            f"{alphabet_path or '<неизвестно>'}."
        )
        self.symbol = symbol
        self.alphabet_path = alphabet_path
        self.partial_out = partial_out