# ============================================================
#   actions.py
# ============================================================

import json
from fractions import Fraction

import exceptions as exs

# ============================================================
#   Action — базовый класс
# ============================================================


class Action:
    """
    Базовый класс для операций преобразования текста.

    Отвечает за:
        - загрузку и валидацию алфавита из JSON-файла;
        - хранение входной строки;
        - накопление результата в self.out (список фрагментов).
    """

    REQUIRED_KEYS = ("meta", "letters")

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8") -> None:
        self.alphabet_path = alphabet

        with open(alphabet, encoding=enc) as a:
            self.alphabet = json.load(a)

        self._validate_alphabet()

        self.inp = inp
        self.out: list[str] = []

    def _validate_alphabet(self) -> None:
        missing = [key for key in self.REQUIRED_KEYS if not self.alphabet.get(key)]
        if missing:
            raise exs.InvalidAlphabetError(self.alphabet_path, missing)

    def _reset_output(self) -> None:
        self.out = []


# ============================================================
#   Morse — кодирование/декодирование азбукой Морзе
# ============================================================


class Morse(Action):
    """
    Кодирование и декодирование текста азбукой Морзе.

    JSON-алфавит:
        {
            "meta":    { "spacer": "<разделитель>", ... },
            "letters": { "<символ>": "<код>", ... }
        }

    Кодирование идёт «жадно»: сначала самый длинный чанк.
    Декодирование разбивает вход по spacer (и по пробелам —
    как разделителям слов).

    Для этой операции spacer обязателен.
    """

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8") -> None:
        super().__init__(alphabet, inp, enc)

        # spacer нужен именно для Морзе
        if self.alphabet["meta"].get("spacer") is None:
            raise exs.MissingSpacerError(self.alphabet_path)

        self.inp = self.inp.upper()

        self._has_space_symbol = " " in self.alphabet["letters"]

        # карта «код -> символ» (при дубликатах — первый встреченный)
        self._code_to_char: dict[str, str] = {}
        for ch, code in self.alphabet["letters"].items():
            self._code_to_char.setdefault(code, ch)

        self._max_code_len = max((len(c) for c in self._code_to_char), default=1)

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
        self._reset_output()

        spacer = self.alphabet["meta"]["spacer"]
        letters = self.alphabet["letters"]
        max_len = max((len(k) for k in letters), default=1)
        value_len = max_len
        i = 0

        while i < len(self.inp):
            ch = self.inp[i]

            if ch == " " and not self._has_space_symbol:
                raise exs.MissingSpaceSymbolError(" ", spacer.join(self.out))

            if value_len <= 0:
                raise exs.UnknownSymbolError(
                    symbol=ch,
                    partial_out=spacer.join(self.out),
                )

            chunk = self.inp[i : i + value_len]
            value = letters.get(chunk)
            if value is None:
                value_len -= 1
                continue

            i += len(chunk)
            value_len = max_len
            self.out.append(value)

        return spacer.join(self.out)

    # --------------------------------------------------------
    #   Декодирование
    # --------------------------------------------------------

    def encode(self) -> str:
        self._reset_output()

        if not self.inp.strip():
            return ""

        result_parts: list[str] = []
        spacer = self.alphabet["meta"]["spacer"]

        # Разбиваем по пробелам, сохраняя пустые сегменты
        # (несколько пробелов = разделитель слов)
        segments = self.inp.split(" ")

        for idx, seg in enumerate(segments):
            if seg == "":
                if 0 < idx < len(segments) - 1:
                    if not self._has_space_symbol:
                        raise exs.MissingSpaceSymbolError(" ", "".join(result_parts))
                    result_parts.append(" ")
                continue

            # Если spacer — не пробел, дополнительно разбиваем по нему
            if spacer != " " and spacer in seg:
                codes = seg.split(spacer)
            else:
                codes = [seg]

            for code in codes:
                if code == "":
                    continue
                ch = self._code_to_char.get(code)
                if ch is None:
                    raise exs.UnknownSymbolError(
                        symbol=code,
                        partial_out="".join(result_parts),
                    )
                result_parts.append(ch)

        result = "".join(result_parts)
        self.out = [result]
        return result


# ============================================================
#   NumberSystem — перевод между системами счисления
# ============================================================


class NumberSystem(Action):
    """
    Перевод чисел между системами счисления.

    Поддерживает:
        - целые числа;
        - отрицательные числа (знак '-' перед числом);
        - дробные числа (разделитель '.' — точка).

    JSON-алфавит:
        {
            "meta":    { "spacer": " ", "name": ... },
            "letters": { "<символ>": <вес>, ... }
        }

    Допустимые цифры входной системы — те, у которых 0 <= вес < inpSys.
    Всё, что не является цифрой/знаком/точкой в нужном контексте,
    считается разделителем между числами и сохраняется в выводе.

    Точность перевода дробей ограничена self.max_frac_digits (по
    умолчанию 20 знаков после точки). Округление — усечение.

    ВАЖНО: spacer для этой операции НЕ требуется.
    """

    def __init__(self, alphabet, inpSys, outSys, inp, enc="utf-8") -> None:
        super().__init__(alphabet, inp, enc)

        self.inpSys = int(inpSys)
        self.outSys = int(outSys)

        if self.inpSys < 2 or self.outSys < 2:
            raise exs.ActionError(
                f"Основание системы счисления должно быть >= 2 "
                f"(получено {self.inpSys} -> {self.outSys})"
            )

        # сколько знаков после точки максимум выдавать
        self.max_frac_digits = 20

        # ВАЖНО: сохраняем оригинал, регистр приводим только
        # при сравнении с цифрами (см. _tokenize / _parse_number)
        self.inp = inp
        self._inp_upper = inp.upper()

        # карта символ -> вес и обратная
        self._digit_value: dict[str, int] = {
            sym: int(val) for sym, val in self.alphabet["letters"].items()
        }
        self._value_digit: dict[int, str] = {}
        for sym, val in self._digit_value.items():
            self._value_digit.setdefault(val, sym)

        # допустимые цифры входной системы (строго < inpSys)
        self._allowed = {
            sym for sym, val in self._digit_value.items() if 0 <= val < self.inpSys
        }

    # --------------------------------------------------------
    #   Разбор входа на токены
    # --------------------------------------------------------

    def _tokenize(self) -> list[tuple[str, bool]]:
        """
        Разбивает self.inp на последовательность (фрагмент, is_number).

        Логика:
            - цифра из allowed (без учёта регистра) -> часть числа;
            - '-' -> часть числа ТОЛЬКО если это начало числа
            (предыдущий символ не цифра и следующий — цифра);
            - '.' -> часть числа ТОЛЬКО если уже есть целая часть
            и следующий символ — цифра;
            - всё прочее — разделитель (сохраняется с исходным регистром).
        """
        tokens: list[tuple[str, bool]] = []
        buf: list[str] = []
        buf_is_num: bool | None = None

        def flush():
            nonlocal buf, buf_is_num
            if buf and buf_is_num is not None:
                tokens.append(("".join(buf), buf_is_num))
            buf = []
            buf_is_num = None

        def is_digit(ch: str) -> bool:
            return ch.upper() in self._allowed

        n = len(self.inp)
        i = 0
        while i < n:
            ch = self.inp[i]

            if is_digit(ch):
                if buf_is_num is not True:
                    flush()
                    buf_is_num = True
                buf.append(ch)
                i += 1
                continue

            # Знак минус: часть числа, если это начало числа
            # и следующая цифра допустима
            if ch == "-" and buf_is_num is not True:
                nxt = self.inp[i + 1] if i + 1 < n else ""
                if is_digit(nxt):
                    flush()
                    buf_is_num = True
                    buf.append("-")
                    i += 1
                    continue

            # Точка: часть числа, если уже есть цифры в buf
            # и следующая цифра допустима
            if ch == "." and buf_is_num is True and buf and is_digit(buf[-1]):
                nxt = self.inp[i + 1] if i + 1 < n else ""
                # не допускаем вторую точку
                if "." not in buf and is_digit(nxt):
                    buf.append(".")
                    i += 1
                    continue

            # Всё прочее — разделитель (регистр сохраняется)
            if buf_is_num is not True:
                if buf_is_num is None:
                    buf_is_num = False
                buf.append(ch)
            else:
                flush()
                buf_is_num = False
                buf.append(ch)
            i += 1

        flush()
        return tokens

    # --------------------------------------------------------
    #   Один токен <-> Fraction
    # --------------------------------------------------------

    def _parse_number(self, token: str) -> Fraction:
        """
        Переводит строку-число в inpSys в Fraction.

        Исключения:
            UnknownSymbolError: если встретился недопустимый символ.
        """
        sign = 1
        s = token
        if s.startswith("-"):
            sign = -1
            s = s[1:]

        if "." in s:
            int_part, frac_part = s.split(".", 1)
        else:
            int_part, frac_part = s, ""

        def digits_to_int(part: str) -> int:
            value = 0
            for ch in part:
                v = self._digit_value.get(ch.upper())
                if v is None or v >= self.inpSys:
                    raise exs.UnknownSymbolError(symbol=ch, partial_out="")
                value = value * self.inpSys + v
            return value

        int_val = digits_to_int(int_part) if int_part else 0

        frac_val = Fraction(0, 1)
        if frac_part:
            num = digits_to_int(frac_part)
            den = self.inpSys ** len(frac_part)
            frac_val = Fraction(num, den)

        return sign * (int_val + frac_val)

    def _format_number(self, value: Fraction) -> str:
        """
        Переводит Fraction в строку в outSys.

        Исключения:
            UnknownSymbolError: если для какого-то веса нет символа.
        """
        sign = ""
        if value < 0:
            sign = "-"
            value = -value

        int_part = value.numerator // value.denominator
        frac_part = value - int_part

        # целая часть
        int_digits: list[str] = []
        if int_part == 0:
            sym0 = self._value_digit.get(0)
            if sym0 is None:
                raise exs.UnknownSymbolError(symbol="0", partial_out="")
            int_digits.append(sym0)
        else:
            n = int_part
            while n > 0:
                n, r = divmod(n, self.outSys)
                sym = self._value_digit.get(r)
                if sym is None:
                    raise exs.UnknownSymbolError(
                        symbol=str(r),
                        partial_out="".join(reversed(int_digits)),
                    )
                int_digits.append(sym)
            int_digits.reverse()

        result = sign + "".join(int_digits)

        # дробная часть
        if frac_part > 0:
            frac_digits: list[str] = []
            for _ in range(self.max_frac_digits):
                frac_part *= self.outSys
                d = frac_part.numerator // frac_part.denominator
                frac_part -= d
                sym = self._value_digit.get(d)
                if sym is None:
                    raise exs.UnknownSymbolError(
                        symbol=str(d),
                        partial_out=result + "." + "".join(frac_digits),
                    )
                frac_digits.append(sym)
                if frac_part == 0:
                    break
            result += "." + "".join(frac_digits)

        return result

    # --------------------------------------------------------
    #   Публичные методы
    # --------------------------------------------------------

    def convert(self, n: Fraction) -> str:
        """Переводит одно число (Fraction) в outSys."""
        return self._format_number(n)

    def oper(self) -> str:
        """
        Прогоняет весь входной текст через конвертер.

        Возвращает:
            Строку, где числа переведены в outSys,
            а разделители сохранены как есть.
        """
        self._reset_output()

        parts: list[str] = []
        for fragment, is_num in self._tokenize():
            if is_num:
                parts.append(self.convert(self._parse_number(fragment)))
            else:
                parts.append(fragment)

        result = "".join(parts)
        self.out = [result]
        return result

    # алиасы под execute() в MainWindow
    def code(self) -> str:
        return self.oper()

    def encode(self) -> str:
        return self.oper()


# ============================================================
#   Braille — кодирование/декодирование шрифтом Брайля
# ============================================================


class Braille(Action):
    """
    Кодирование и декодирование текста шрифтом Брайля.

    JSON-алфавит (пример):
        {
            "meta":    { "dots": 6, ... },
            "prefixes": {
                "num_prefix":          { "char": "⠼", ... },
                "capital_prefix":      { "char": "⠘", ... },
                "capital_word_prefix": { "char": "⠘⠘", ... }
            },
            "letters":     { "А": { "char": "⠁", ... }, ... },
            "digits":      { "1": { "char": "⠁", ... }, ... },
            "punctuation": { ".": { "char": "⠲", ... }, ... },
            "math":        { "+": { "char": "⠬", ... }, ... }
        }

    Кодирование идёт «жадно» (самый длинный чанк).
    Заглавные буквы кодируются префиксом capital_prefix.
    Цифры (последовательность цифр) кодируются num_prefix
    + цифры, причём num_prefix ставится ОДИН раз на всё
    число (до разделителя).

    Декодирование:
        - num_prefix действует на всё слово до разделителя
          (пробел, пунктуация, конец строки) — все символы
          слова трактуются как цифры, если это возможно;
        - capital_word_prefix действует на слово целиком;
        - capital_prefix действует на следующую букву;
        - всё остальное — буквы/пунктуация/математика.

    spacer для этой операции НЕ требуется.
    """

    _SYMBOL_SECTIONS = ("letters", "digits", "punctuation", "math")

    # символы, которые считаются разделителями слов
    # (пробел + всё, что в punctuation/math, кроме цифр)
    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8") -> None:
        super().__init__(alphabet, inp, enc)

        # ---- префиксы ----
        prefixes = self.alphabet.get("prefixes") or {}
        self._num_prefix = self._prefix_char(prefixes, "num_prefix")
        self._cap_prefix = self._prefix_char(prefixes, "capital_prefix")
        self._cap_word_prefix = self._prefix_char(prefixes, "capital_word_prefix")

        # ---- отдельные карты: буквы и цифры ----
        # (у них общие коды — ⠁ = А и 1, и т.п.)
        self._letter_to_code: dict[str, str] = {}
        self._digit_to_code: dict[str, str] = {}
        self._code_to_letter: dict[str, str] = {}
        self._code_to_digit: dict[str, str] = {}
        self._other_to_code: dict[str, str] = {}
        self._code_to_other: dict[str, str] = {}

        for sym, info in (self.alphabet.get("letters") or {}).items():
            code = self._code_of(info)
            if code:
                self._letter_to_code.setdefault(sym, code)
                self._code_to_letter.setdefault(code, sym)

        for sym, info in (self.alphabet.get("digits") or {}).items():
            code = self._code_of(info)
            if code:
                self._digit_to_code.setdefault(sym, code)
                self._code_to_digit.setdefault(code, sym)

        for section in ("punctuation", "math"):
            for sym, info in (self.alphabet.get(section) or {}).items():
                code = self._code_of(info)
                if code:
                    self._other_to_code.setdefault(sym, code)
                    self._code_to_other.setdefault(code, sym)

        # общая карта для кодирования (жадный поиск)
        self._char_to_code: dict[str, str] = {}
        for d in (
            self._letter_to_code,
            self._digit_to_code,
            self._other_to_code,
        ):
            for sym, code in d.items():
                self._char_to_code.setdefault(sym, code)

        # разделитель слов
        self._word_sep = self._char_to_code.get(" ", " ")

        # максимальная длина кода для жадного кодирования/декодирования
        self._max_code_len = max((len(c) for c in self._char_to_code), default=1)

        # символы, которые НЕ являются разделителями слов при
        # декодировании (буквы/цифры/прочие символы из алфавита)
        self._word_chars = set(self._char_to_code.keys()) - {" "}

        self._inp_upper = self.inp.upper()

    # --------------------------------------------------------
    #   Вспомогательное
    # --------------------------------------------------------

    @staticmethod
    def _code_of(info) -> str | None:
        if isinstance(info, dict):
            return info.get("char")
        return info

    @staticmethod
    def _prefix_char(prefixes: dict, key: str) -> str | None:
        info = prefixes.get(key)
        if not info:
            return None
        if isinstance(info, dict):
            return info.get("char")
        return info

    def _is_word_char(self, ch: str) -> bool:
        """Символ — часть слова (буква или цифра), а не разделитель."""
        return ch.isalnum()

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
        """
        Кодирует self.inp в строку символов Брайля.

        Правила:
            - пробел -> word_sep;
            - последовательность цифр -> num_prefix + цифры (один раз);
            - слово ЦЕЛИКОМ из заглавных букв (len >= 2) ->
              capital_word_prefix один раз на слово;
            - одиночная заглавная буква (или заглавная внутри
              смешанного слова) -> capital_prefix перед этой буквой;
            - строчные буквы -> без префикса;
            - всё остальное ищется жадно (самый длинный чанк).
        """
        self._reset_output()

        s = self.inp  # ← оригинал, регистр сохраняем
        max_len = self._max_code_len
        value_len = max_len
        i = 0
        n = len(s)

        while i < n:
            ch = s[i]

            if ch.isspace():
                self.out.append(self._word_sep)
                i += 1
                value_len = max_len
                continue

            # --- цифры: один num_prefix на всё число (до не-цифры) ---
            if ch.isdigit() and ch in self._digit_to_code:
                if self._num_prefix is not None:
                    self.out.append(self._num_prefix)
                while i < n and s[i].isdigit() and s[i] in self._digit_to_code:
                    self.out.append(self._digit_to_code[s[i]])
                    i += 1
                value_len = max_len
                continue

            # --- буквы: обрабатываем слово целиком, чтобы понять,
            #     всё ли оно в верхнем регистре ---
            if ch.isalpha() and ch.upper() in self._letter_to_code:
                word_start = i
                while i < n and s[i].isalpha() and s[i].upper() in self._letter_to_code:
                    i += 1
                word = s[word_start:i]
                self._emit_word(word)
                value_len = max_len
                continue

            if value_len <= 0:
                raise exs.UnknownSymbolError(
                    symbol=ch,
                    partial_out="".join(self.out),
                )

            chunk = s[i : i + value_len]
            code = self._char_to_code.get(chunk)
            if code is None:
                value_len -= 1
                continue

            self.out.append(code)
            i += len(chunk)
            value_len = max_len

        return "".join(self.out)

    # --------------------------------------------------------
    #   Кодирование одного слова (буквы)
    # --------------------------------------------------------

    def _emit_word(self, word: str) -> None:
        """
        Кодирует слово из букв с учётом регистра.

        - слово длиной >= 2 и ВСЁ в верхнем регистре ->
          capital_word_prefix один раз + буквы без префиксов;
        - иначе каждая заглавная буква получает capital_prefix,
          строчные идут без префикса.
        """
        is_all_upper = len(word) >= 2 and all(c.isupper() for c in word)

        if is_all_upper and self._cap_word_prefix is not None:
            self.out.append(self._cap_word_prefix)
            for c in word:
                self.out.append(self._letter_to_code[c.upper()])
            return

        for c in word:
            if c.isupper() and self._cap_prefix is not None:
                self.out.append(self._cap_prefix)
            self.out.append(self._letter_to_code[c.upper()])

    # --------------------------------------------------------
    #   Декодирование
    # --------------------------------------------------------

    def encode(self) -> str:
        """
        Декодирует строку символов Брайля в обычный текст.

        Правила:
            - num_prefix включает числовой режим на всё слово
              (до пробела или до не-цифрового символа/пунктуации);
            - capital_prefix делает заглавной следующую букву;
            - capital_word_prefix делает заглавным всё слово;
            - пробел — разделитель слов;
            - неизвестный символ -> UnknownSymbolError.
        """
        self._reset_output()

        if not self.inp.strip():
            return ""

        result: list[str] = []
        s = self.inp
        n = len(s)
        i = 0

        # состояние
        num_mode = False  # числовой режим на слово
        cap_mode = False  # одна буква заглавная
        cap_word_mode = False  # всё слово заглавное

        # префиксы — от самого длинного
        prefix_pairs = [
            (self._cap_word_prefix, "word"),
            (self._num_prefix, "num"),
            (self._cap_prefix, "cap"),
        ]
        prefix_pairs = [(p, k) for p, k in prefix_pairs if p]
        prefix_pairs.sort(key=lambda x: len(x[0]), reverse=True)

        def flush_word_modes():
            """Сбрасывает режимы, действующие на слово."""
            nonlocal num_mode, cap_word_mode
            num_mode = False
            cap_word_mode = False

        while i < n:
            ch = s[i]

            # пробел — конец слова
            if ch.isspace():
                result.append(" ")
                flush_word_modes()
                cap_mode = False
                i += 1
                continue

            # префиксы
            matched_prefix = False
            for prefix, kind in prefix_pairs:
                if s.startswith(prefix, i):
                    if kind == "num":
                        num_mode = True
                    elif kind == "cap":
                        cap_mode = True
                    elif kind == "word":
                        cap_word_mode = True
                    i += len(prefix)
                    matched_prefix = True
                    break
            if matched_prefix:
                continue

            # ищем самый длинный известный код
            code = None
            length = 0
            for ln in range(min(self._max_code_len, n - i), 0, -1):
                candidate = s[i : i + ln]
                if (
                    candidate in self._code_to_letter
                    or candidate in self._code_to_digit
                    or candidate in self._code_to_other
                ):
                    code = candidate
                    length = ln
                    break

            if code is None:
                raise exs.UnknownSymbolError(symbol=ch, partial_out="".join(result))

            # выбор трактовки в зависимости от режима
            out_sym = None

            if num_mode:
                # в числовом режиме сначала пробуем цифру
                if code in self._code_to_digit:
                    out_sym = self._code_to_digit[code]
                else:
                    # цифра кончилась — выходим из числового режима
                    num_mode = False

            if out_sym is None:
                # обычный символ: буква -> прочее
                if code in self._code_to_letter:
                    out_sym = self._code_to_letter[code].lower()
                elif code in self._code_to_other:
                    out_sym = self._code_to_other[code]
                elif code in self._code_to_digit:
                    # цифра вне числового режима — как буква
                    # (в Брайле это одна и та же клетка; выводим цифру)
                    out_sym = self._code_to_digit[code]

            # применение заглавных режимов
            if out_sym is not None and out_sym.isalpha():
                if cap_mode:
                    out_sym = out_sym.upper()
                elif cap_word_mode:
                    out_sym = out_sym.upper()
            # одиночный capital_prefix сбрасывается после буквы
            cap_mode = False

            # символ-разделитель (пунктуация/math) завершает слово
            if code in self._code_to_other:
                flush_word_modes()

            result.append(out_sym)
            i += length

        decoded = "".join(result)
        self.out = [decoded]
        return decoded


# ============================================================
#   Bytes — перевод текста в бинарный код
# ============================================================


class Bytes(Action):
    """
    Перевод текста в бинарный код в указанной кодировке.

    В отличие от других операций, алфавит (JSON) НЕ используется:
    кодировка задаётся явно, а результат — последовательность
    битов ('0'/'1'), разделённая пробелами побайтово (по умолчанию).

    JSON-алфавит не нужен, поэтому в __init__ его нет.

    Параметры:
        inp  — входной текст;
        enc  — целевая кодировка (по умолчанию 'utf-8').

    Поддерживаемые кодировки (как минимум):
        - 'utf-8'
        - 'utf-16'  (по умолчанию с BOM, порядок — системный;
                     можно уточнить: 'utf-16-le', 'utf-16-be')
        - любая другая, известная Python (например 'utf-32', 'cp1251').

    Пример:
        Bytes("Привет", "utf-8").code()
        -> '11010000 11101111 11010001 10000000 ...'
    """

    # разделитель между байтами в выводе
    BYTE_SEP = " "

    def __init__(self, inp: str, enc: str = "utf-8") -> None:
        # ВАЖНО: НЕ вызываем super().__init__(...),
        # т.к. там требуется JSON-алфавит.
        self.inp = inp
        self.enc = enc
        self.out: list[str] = []

        # проверяем, что кодировка известна Python (иначе — понятная ошибка)
        try:
            "".encode(self.enc)
        except LookupError:
            raise exs.ActionError(f"Неизвестная кодировка: {self.enc!r}")

    # --------------------------------------------------------
    #   Вспомогательное
    # --------------------------------------------------------

    def _to_bytes(self) -> bytes:
        """Кодирует self.inp в байты в self.enc."""
        try:
            return self.inp.encode(self.enc)
        except UnicodeEncodeError as e:
            raise exs.ActionError(f"Не удалось закодировать текст в {self.enc!r}: {e}")

    @staticmethod
    def _byte_to_bits(b: int) -> str:
        """Один байт (0..255) -> строка из 8 бит."""
        return format(b, "08b")

    # --------------------------------------------------------
    #   Публичные методы
    # --------------------------------------------------------

    def code(self) -> str:
        """
        Возвращает бинарное представление текста.

        Формат: каждый байт — 8 бит, байты разделены пробелом.
        """
        self._reset_output()

        data = self._to_bytes()
        bits = [self._byte_to_bits(b) for b in data]

        result = self.BYTE_SEP.join(bits)
        self.out = [result]
        return result

    def encode(self) -> str:
        """
        Обратная операция: бинарная строка -> текст в self.enc.

        Принимает строку из '0'/'1' (пробелы, переводы строк и
        прочие разделители игнорируются — они лишь разделяют байты).
        Длина битовой строки должна быть кратна 8.
        """
        self._reset_output()

        # оставляем только 0 и 1
        bits = "".join(ch for ch in self.inp if ch in "01")
        if not bits:
            self.out = [""]
            return ""

        if len(bits) % 8 != 0:
            raise exs.ActionError(f"Длина битовой строки ({len(bits)}) не кратна 8")

        data = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))

        try:
            result = data.decode(self.enc)
        except UnicodeDecodeError as e:
            raise exs.ActionError(f"Не удалось декодировать байты в {self.enc!r}: {e}")

        self.out = [result]
        return result

    # алиас под execute() в MainWindow (если он зовёт .oper())
    def oper(self) -> str:
        return self.code()


# ============================================================
#   Caesar — шифр Цезаря
# ============================================================


class Caesar(Action):
    """
    Шифр Цезаря над произвольным алфавитом.

    JSON-алфавит:
        {
            "meta":    { "shift": <int>, ... },   # сдвиг по умолчанию 3
            "letters": "<строка букв в нужном порядке>"
        }

    Буквы в "letters" гарантированно не повторяются.
    Регистр сохраняется: строчная остаётся строчной, заглавная —
    заглавной (если такая буква есть в алфавите в нужном регистре;
    иначе буква ищется без учёта регистра и регистр восстанавливается).

    Всё, чего нет в алфавите (пробелы, цифры, пунктуация),
    сохраняется без изменений.

    code()   — шифрование (сдвиг вправо на shift);
    encode() — расшифровка (сдвиг влево на shift).
    """

    def __init__(self, alphabet: str, inp: str, shift: int, enc: str = "utf-8") -> None:
        super().__init__(alphabet, inp, enc)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )

        self._letters = letters
        self._n = len(letters)

        if self._n < 2:
            raise exs.ActionError(
                f"Алфавит для шифра Цезаря слишком короткий " f"(длина {self._n})"
            )

        # карта символ -> индекс и обратная
        self._char_to_idx: dict[str, int] = {ch: i for i, ch in enumerate(letters)}
        self._idx_to_char: list[str] = list(letters)

        if shift is not None:
            self.shift = shift
        else:
            meta = self.alphabet.get("meta") or {}
            try:
                self.shift = int(meta.get("shift", 3))
            except (TypeError, ValueError):
                raise ActionError(
                    f"Некорректный сдвиг в meta.shift: {meta.get('shift')!r}"
                )

    # --------------------------------------------------------
    #   Вспомогательное
    # --------------------------------------------------------

    def _find_index(self, ch: str) -> int | None:
        """
        Индекс символа в алфавите.
        Сначала точное совпадение, потом — без учёта регистра.
        """
        if ch in self._char_to_idx:
            return self._char_to_idx[ch]

        # пробуем найти в другом регистре
        for variant in (ch.lower(), ch.upper(), ch.casefold()):
            if variant in self._char_to_idx:
                return self._char_to_idx[variant]
        return None

    def _restore_case(self, original: str, found: str) -> str:
        """Приводит найденный символ к регистру оригинала."""
        if original.isupper():
            return found.upper()
        if original.islower():
            return found.lower()
        return found

    def _convert(self, delta: int) -> str:
        self._reset_output()

        result: list[str] = []
        n = self._n

        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                result.append(ch)
                continue

            new_idx = (idx + delta) % n
            new_ch = self._idx_to_char[new_idx]
            result.append(self._restore_case(ch, new_ch))

        out = "".join(result)
        self.out = [out]
        return out

    # --------------------------------------------------------
    #   Публичные методы
    # --------------------------------------------------------

    def code(self) -> str:
        """Шифрование: сдвиг вправо на self.shift."""
        return self._convert(self.shift)

    def encode(self) -> str:
        """Расшифровка: сдвиг влево на self.shift."""
        return self._convert(-self.shift)

    def oper(self) -> str:
        return self.code()


# ============================================================
#   A1Z26 — числовое кодирование по позиции в алфавите
# ============================================================


class A1Z26(Action):
    """
    Кодирование «буква -> её номер в алфавите» и обратно.

    Работает с ЛЮБЫМ словарём: важен лишь порядок букв в "letters".
    Первая буква получает номер 1, вторая — 2 и т.д.

    JSON-алфавит:
        {
            "meta":    { "sep": "-", ... },   # разделитель чисел по умолч.
            "letters": "<строка букв в нужном порядке>"
        }

    Кодирование (code):
        - каждая буква заменяется своим номером;
        - числа разделяются meta.sep (по умолчанию '-');
        - регистр сохраняется (строчная/заглавная ищется в алфавите);
        - символы вне алфавита сохраняются как есть, а
          последовательность чисел вокруг них разделяется
          тем же разделителем.

    Декодирование (encode):
        - числа, разделённые sep (а также пробелами/переносами),
          превращаются обратно в буквы;
        - всё остальное сохраняется как есть.

    spacer для этой операции НЕ требуется.
    """

    def __init__(
        self, alphabet: str, inp: str, sep: str = None, enc: str = "utf-8"
    ) -> None:
        super().__init__(alphabet, inp, enc)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )

        self._letters = letters
        self._n = len(letters)

        if self._n < 1:
            raise exs.ActionError("Алфавит для A1Z26 пуст")

        self._char_to_num: dict[str, int] = {ch: i + 1 for i, ch in enumerate(letters)}
        self._num_to_char: dict[int, str] = {i + 1: ch for i, ch in enumerate(letters)}

        meta = self.alphabet.get("meta") or {}
        if sep:
            self.sep = sep
        else:
            self.sep = str(meta.get("sep", "-"))

    # --------------------------------------------------------
    #   Вспомогательное
    # --------------------------------------------------------

    def _lookup(self, ch: str) -> tuple[int, str] | None:
        """
        Возвращает (номер, символ_из_алфавита) или None.
        Ищет точное совпадение, затем без учёта регистра.
        """
        if ch in self._char_to_num:
            return self._char_to_num[ch], ch

        for variant in (ch.lower(), ch.upper(), ch.casefold()):
            if variant in self._char_to_num:
                return self._char_to_num[variant], variant
        return None

    def _restore_case(self, original: str, found: str) -> str:
        if original.isupper():
            return found.upper()
        if original.islower():
            return found.lower()
        return found

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
        """
        Буквы -> числа, разделённые self.sep.
        Символы вне алфавита сохраняются, а числа вокруг них
        разделяются self.sep (чтобы декодирование было однозначным).
        Литеральный self.sep в исходном тексте экранируется удвоением.
        """
        self._reset_output()

        parts: list[str] = []
        number_run: list[str] = []

        def flush_numbers() -> None:
            nonlocal number_run
            if number_run:
                parts.append(self.sep.join(number_run))
                number_run = []

        for ch in self.inp:
            found = self._lookup(ch)
            if found is None:
                flush_numbers()
                # экранируем литеральный разделитель
                if ch == self.sep:
                    parts.append(self.sep * 2)
                else:
                    parts.append(ch)
                continue

            num, _ = found
            number_run.append(str(num))

        flush_numbers()

        out = "".join(parts)
        self.out = [out]
        return out

    # --------------------------------------------------------
    #   Декодирование
    # --------------------------------------------------------

    def encode(self) -> str:
        """
        Числа (разделённые self.sep, пробелами или переводами строк)
        -> буквы. Всё прочее сохраняется как есть.

        Одиночный sep между числами — разделитель (не выводится):
            1-2   -> АБ
        Двойной sep — экранированный литеральный sep:
            1--2  -> А-Б
        """
        self._reset_output()

        if not self.inp:
            self.out = [""]
            return ""

        result: list[str] = []
        buf: list[str] = []
        in_number = False

        def flush_number() -> None:
            nonlocal buf, in_number
            if not buf:
                in_number = False
                return
            try:
                num = int("".join(buf))
            except ValueError:
                result.append("".join(buf))
                buf = []
                in_number = False
                return
            ch = self._num_to_char.get(num)
            if ch is None:
                raise exs.UnknownSymbolError(
                    symbol=str(num),
                    partial_out="".join(result),
                )
            result.append(ch)
            buf = []
            in_number = False

        s = self.inp
        n = len(s)
        i = 0
        while i < n:
            ch = s[i]

            if ch.isdigit():
                in_number = True
                buf.append(ch)
                i += 1
                continue

            # sep: одиночный — разделитель, двойной — литерал
            if in_number and ch == self.sep:
                # экранированный литерал: sep + sep
                if i + 1 < n and s[i + 1] == self.sep:
                    flush_number()
                    result.append(self.sep)
                    i += 2
                    continue
                # обычный разделитель чисел
                flush_number()
                i += 1
                continue

            # пробельные символы разделяют числа, но СОХРАНЯЮТСЯ
            if in_number and ch.isspace():
                flush_number()
                result.append(ch)
                i += 1
                continue

            # всё прочее — просто символ
            flush_number()
            result.append(ch)
            i += 1

        flush_number()

        out = "".join(result)
        self.out = [out]
        return out

    def oper(self) -> str:
        return self.code()


# ============================================================
#   Vigenere — шифр Виженёра
# ============================================================


# ============================================================
#   Playfair — биграммный шифр Плейфера
# ============================================================


class Playfair(Action):
    """
    Шифр Плейфера (биграммный шифр).

    JSON-алфавит:
        {
            "meta": {
                "rows":   <int>,   # число строк таблицы
                "cols":   <int>,   # число столбцов таблицы
                "filler": "<символ>"  # заполнитель (по умолчанию "X")
            },
            "letters": "<строка символов алфавита>"
        }

    Таблица заполняется ключом (уникальные символы ключа,
    затем оставшиеся символы алфавита в порядке "letters").
    Размеры таблицы берутся из meta; len(letters) должен
    совпадать с rows * cols.

    Правила (классические):
        - вход приводится к верхнему регистру;
        - пробелы и любые символы, которых нет в алфавите,
          УДАЛЯЮТСЯ (не сохраняются в выводе);
        - текст разбивается на биграммы; если в биграмме
          две одинаковые буквы — между ними вставляется filler;
        - если длина нечётная — в конец добавляется filler;
        - для каждой биграммы:
            * в одной строке  -> сдвиг вправо (code) / влево (encode);
            * в одном столбце -> сдвиг вниз (code) / вверх (encode);
            * прямоугольник   -> замена на символы из тех же строк,
                                 но из столбца партнёра.

    Неизвестные символы (которых нет в алфавите) НЕ вызывают
    ошибку при кодировании — они просто игнорируются (так
    требует классическое правило «пробелы не сохраняются»).
    Если нужно строгое поведение, как в Morse, — см. комментарий
    в _normalize().
    """

    def __init__(self, alphabet: str, inp: str, key: str, enc: str = "utf-8") -> None:
        super().__init__(alphabet, inp, enc)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )
        self._letters = letters
        self._n = len(letters)

        meta = self.alphabet.get("meta") or {}

        # --- размеры таблицы ---
        try:
            self.rows = int(meta["rows"])
            self.cols = int(meta["cols"])
        except (KeyError, TypeError, ValueError):
            raise exs.InvalidAlphabetError(
                self.alphabet_path,
                ["meta.rows", "meta.cols (целые числа)"],
            )
        if self.rows < 1 or self.cols < 1:
            raise exs.ActionError(
                f"Некорректные размеры таблицы: {self.rows}x{self.cols}"
            )

        # --- заполнитель ---
        filler = meta.get("filler", "X")
        if not isinstance(filler, str) or len(filler) != 1:
            raise exs.ActionError(
                f"meta.filler должен быть одним символом, получено: {filler!r}"
            )
        if filler.upper() not in letters.upper():
            raise exs.ActionError(
                f"Символ-заполнитель {filler!r} отсутствует в алфавите"
            )
        self._filler = filler.upper()

        # --- заменяемые буквы (aliases) ---
        aliases = meta.get("aliases") or {}
        if not isinstance(aliases, dict):
            raise exs.InvalidAlphabetError(
                self.alphabet_path,
                ["meta.aliases (должен быть объектом)"],
            )

        letters_upper = letters.upper()
        self._aliases: dict[str, str] = {}
        for src, dst in aliases.items():
            if not isinstance(src, str) or len(src) != 1:
                raise exs.ActionError(
                    f"meta.aliases: ключ должен быть одним символом, получено: {src!r}"
                )
            if not isinstance(dst, str) or len(dst) != 1:
                raise exs.ActionError(
                    f"meta.aliases: значение для {src!r} должно быть одним символом, "
                    f"получено: {dst!r}"
                )
            src_u, dst_u = src.upper(), dst.upper()
            if src_u in letters_upper:
                raise exs.ActionError(
                    f"meta.aliases: символ {src!r} уже есть в алфавите — "
                    f"замена не имеет смысла"
                )
            if dst_u not in letters_upper:
                raise exs.ActionError(
                    f"meta.aliases: целевой символ {dst!r} отсутствует в алфавите"
                )
            if src_u in self._aliases:
                raise exs.ActionError(
                    f"meta.aliases: дублирующийся ключ {src!r}"
                )
            self._aliases[src_u] = dst_u

        # защита от циклов
        for src in self._aliases:
            seen = {src}
            cur = self._aliases[src]
            while cur in self._aliases:
                if cur in seen:
                    raise exs.ActionError(
                        f"meta.aliases: циклическая замена вокруг {src!r}"
                    )
                seen.add(cur)
                cur = self._aliases[cur]

        # --- карта символ -> индекс (по алфавиту) ---
        # В таблицу попадают ВСЕ буквы из "letters", включая те,
        # что могут быть источниками aliases (например, если кто-то
        # оставит J в letters и добавит aliases J->I).
        self._char_to_idx: dict[str, int] = {
            ch.upper(): i for i, ch in enumerate(letters)
        }
        self._idx_to_char: list[str] = [ch.upper() for ch in letters]

        # --- эффективный размер таблицы с учётом aliases ---
        # Ячейки таблицы — это буквы алфавита, КРОМЕ тех, что
        # являются источниками замен (они не занимают ячейку).
        cell_chars = [
            ch for ch in self._idx_to_char
            if ch not in self._aliases
        ]
        n_cells = len(cell_chars)

        if self.rows * self.cols != n_cells:
            raise exs.ActionError(
                f"Размер таблицы {self.rows}x{self.cols} = {self.rows * self.cols} "
                f"не совпадает с числом уникальных ячеек алфавита "
                f"({n_cells} после применения aliases; в letters {self._n})"
            )

        # --- построение таблицы по ключу ---
        if not key:
            raise exs.ActionError("Ключ шифра Плейфера не может быть пустым")

        self.key = key
        self._table: list[list[str]] = []
        self._pos: dict[str, tuple[int, int]] = {}
        self._build_table(key)

        # нормализованный вход
        self._norm = self._normalize(self.inp)

    # --------------------------------------------------------
    #   Построение таблицы
    # --------------------------------------------------------

    def _build_table(self, key: str) -> None:
        seen: set[str] = set()
        ordered: list[str] = []

        # 1) уникальные символы ключа (с применением aliases)
        for ch in key.upper():
            while ch in self._aliases:
                ch = self._aliases[ch]
            if ch in self._char_to_idx and ch not in self._aliases \
                    and ch not in seen:
                seen.add(ch)
                ordered.append(ch)

        # 2) оставшиеся ячейки алфавита (без источников aliases)
        for ch in self._idx_to_char:
            if ch in self._aliases:
                continue
            if ch not in seen:
                seen.add(ch)
                ordered.append(ch)

        expected = self.rows * self.cols
        if len(ordered) != expected:
            raise exs.ActionError(
                f"Не удалось заполнить таблицу {self.rows}x{self.cols}: "
                f"получено {len(ordered)} символов (ожидалось {expected})"
            )

        self._table = [
            ordered[r * self.cols : (r + 1) * self.cols]
            for r in range(self.rows)
        ]

        self._pos = {}
        for r in range(self.rows):
            for c in range(self.cols):
                self._pos[self._table[r][c]] = (r, c)

    # --------------------------------------------------------
    #   Нормализация входа
    # --------------------------------------------------------

    def _normalize(self, text: str) -> str:
        """
        Приводит текст к верхнему регистру, применяет замены
        (meta.aliases, например J -> I) и оставляет только символы
        алфавита. Пробелы и посторонние символы удаляются.
        """
        result: list[str] = []
        for ch in text.upper():
            # 1) замена по aliases (с разрешением цепочек)
            while ch in self._aliases:
                ch = self._aliases[ch]
            # 2) фильтр по алфавиту
            if ch in self._char_to_idx:
                result.append(ch)
            # иначе — молча игнорируем
        return "".join(result)

    # --------------------------------------------------------
    #   Разбиение на биграммы
    # --------------------------------------------------------

    def _split_bigrams(self, text: str) -> list[tuple[str, str]]:
        """
        Разбивает нормализованный текст на биграммы по правилам
        Плейфера:
            - две одинаковые буквы в паре -> между ними filler;
            - нечётная длина -> в конец filler.
        """
        bigrams: list[tuple[str, str]] = []
        i = 0
        n = len(text)

        while i < n:
            a = text[i]
            if i + 1 < n:
                b = text[i + 1]
                if a == b:
                    if a == self._filler:
                        raise exs.ActionError(
                            f"Невозможно разбить биграмму: две подряд {a!r} "
                            f"совпадают с filler — выберите другой filler или "
                            f"другую замену"
                        )
                    bigrams.append((a, self._filler))
                    i += 1
                else:
                    bigrams.append((a, b))
                    i += 2
            else:
                bigrams.append((a, self._filler))
                i += 1

        return bigrams

    # --------------------------------------------------------
    #   Преобразование одной биграммы
    # --------------------------------------------------------

    def _transform_bigram(
        self, a: str, b: str, sign: int
    ) -> tuple[str, str]:
        """
        Преобразует биграмму (a, b) по правилам Плейфера.

        sign = +1 — шифрование (code):
            * одна строка   -> сдвиг вправо;
            * один столбец  -> сдвиг вниз;
            * прямоугольник -> столбец партнёра.
        sign = -1 — расшифровка (encode):
            * одна строка   -> сдвиг влево;
            * один столбец  -> сдвиг вверх;
            * прямоугольник -> столбец партнёра (симметрично).
        """
        ra, ca = self._pos[a]
        rb, cb = self._pos[b]

        if ra == rb:
            # одна строка — сдвиг по столбцам
            new_ca = (ca + sign) % self.cols
            new_cb = (cb + sign) % self.cols
            return self._table[ra][new_ca], self._table[rb][new_cb]

        if ca == cb:
            # один столбец — сдвиг по строкам
            new_ra = (ra + sign) % self.rows
            new_rb = (rb + sign) % self.rows
            return self._table[new_ra][ca], self._table[new_rb][cb]

        # прямоугольник — меняем столбцы
        return self._table[ra][cb], self._table[rb][ca]

    # --------------------------------------------------------
    #   Публичные методы
    # --------------------------------------------------------

    def code(self) -> str:
        """Шифрование: биграммы -> преобразованные биграммы."""
        self._reset_output()

        bigrams = self._split_bigrams(self._norm)
        result: list[str] = []
        for a, b in bigrams:
            na, nb = self._transform_bigram(a, b, +1)
            result.append(na)
            result.append(nb)

        out = "".join(result)
        self.out = [out]
        return out

    def encode(self) -> str:
        """
        Расшифровка.

        ВАЖНО: для корректной расшифровки вход должен быть
        результатом code() — то есть нормализованным (без пробелов)
        и с filler'ами на местах. Метод не удаляет filler'ы
        автоматически, так как они могут быть легитимными буквами
        исходного текста.
        """
        self._reset_output()

        bigrams = self._split_bigrams(self._norm)
        result: list[str] = []
        for a, b in bigrams:
            na, nb = self._transform_bigram(a, b, -1)
            result.append(na)
            result.append(nb)

        out = "".join(result)
        self.out = [out]
        return out

    def oper(self) -> str:
        return self.code()