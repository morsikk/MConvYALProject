# ============================================================
#   actions.py
# ============================================================

import json
from fractions import Fraction

import Exceptions as exs
from Settings import UnknownPolicy


# ============================================================
#   Action — базовый класс (без изменений по сути)
# ============================================================

class Action:
    """Базовый класс: загрузка/валидация алфавита, self.inp, self.out."""

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
#   AlphabetAction — общий слой для алфавитных операций
# ============================================================

class AlphabetAction(Action):
    """
    Общий предок для всех операций, работающих с алфавитом
    из поля "letters" (строка или словарь).

    Предоставляет:
        - нормализованные карты _char_to_idx / _idx_to_char
          (работают и когда letters — строка, и когда — словарь);
        - _find_index(ch) с точным и регистронезависимым поиском;
        - _restore_case(original, found);
        - единую политику обработки неизвестных символов
          (см. settings.UnknownPolicy);
        - _check_unknown_chars() — предварительная проверка
          для режима "Предупреждение";
        - _resolve_unknown(ch) — вернуть строку-замену
          (или "" — пропустить) либо бросить
          UnknownSymbolPolicyError.

    Наследники должны:
        - в __init__ вызвать super().__init__(...),
          затем _setup_alphabet() (или сразу _build_char_maps());
        - в code()/encode() использовать _iter_input()
          или явно вызывать _resolve_unknown / _find_index.
    """

    # Политика по умолчанию — «Предупреждение» (как в settings.json).
    # Может быть переопределена в __init__ из переданного policy.
    _policy: UnknownPolicy

    def __init__(
        self,
        alphabet: str,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        super().__init__(alphabet, inp, enc)
        self._policy = policy if policy is not None else UnknownPolicy.current()
        self._char_to_idx: dict[str, int] = {}
        self._idx_to_char: list[str] = []
        self._letters_raw = self.alphabet.get("letters")
        self._build_char_maps()

    # --------------------------------------------------------
    #   Построение карт
    # --------------------------------------------------------

    def _build_char_maps(self) -> None:
        """
        Заполняет _char_to_idx и _idx_to_char.

        Поддерживает оба формата "letters":
            - строка (порядок букв задаёт индексы);
            - словарь { символ: вес } (индексы — по порядку вставки,
              что совместимо с NumberSystem, где важен вес, а не порядок;
              для NumberSystem карты пересобираются отдельно).
        """
        letters = self._letters_raw
        if isinstance(letters, str):
            self._idx_to_char = list(letters)
            self._char_to_idx = {ch: i for i, ch in enumerate(letters)}
        elif isinstance(letters, dict):
            self._idx_to_char = list(letters.keys())
            self._char_to_idx = {ch: i for i, ch in enumerate(letters)}
        else:
            raise exs.InvalidAlphabetError(
                self.alphabet_path,
                ["letters (строка или объект)"],
            )

    # --------------------------------------------------------
    #   Поиск символа и восстановление регистра
    # --------------------------------------------------------

    def _find_index(self, ch: str) -> int | None:
        """Индекс символа в алфавите (точно, затем без учёта регистра)."""
        if ch in self._char_to_idx:
            return self._char_to_idx[ch]

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

    # --------------------------------------------------------
    #   Что считается «известным» для данной операции
    # --------------------------------------------------------

    def _known(self, ch: str) -> bool:
        """
        Базовая реализация — «есть в letters».

        Morse и Braille переопределяют это, потому что у них
        реальные карты кодирования шире, чем просто letters.
        """
        return self._find_index(ch) is not None

    # --------------------------------------------------------
    #   Политика неизвестных символов
    # --------------------------------------------------------

    def _check_unknown_chars(self) -> list[str]:
        """
        Предварительная проверка (для режима "Предупреждение").

        Возвращает список уникальных символов входа,
        которых нет в алфавите (с сохранением порядка появления).
        Пустой список — всё хорошо.

        Не бросает исключений: решение принимает вызывающий
        (ConverterLogic.execute), который может перезапустить
        операцию с другой политикой.
        """
        unknown: list[str] = []
        seen: set[str] = set()
        for ch in self.inp:
            if ch in seen:
                continue
            seen.add(ch)
            if self._find_index(ch) is None:
                unknown.append(ch)
        return unknown

    def _resolve_unknown(self, ch: str) -> str | None:
        """None — игнорировать; str (возможно "") — замена."""
        return self._policy.resolve(ch, self.alphabet_path)

    def _convert_char(self, ch: str) -> str | None:
        if self._find_index(ch) is not None:
            return None
        return self._resolve_unknown(ch)

    def _lookup_key(self, chunk: str) -> str | None:
        """Вернуть ключ из letters, совпадающий с chunk (точно или без учёта регистра)."""
        letters = self.alphabet["letters"]
        if chunk in letters:
            return chunk
        folded = chunk.casefold()
        for key in letters:
            if key.casefold() == folded:
                return key
        return None

# ============================================================
#   Morse — кодирование/декодирование азбукой Морзе
# ============================================================


class Morse(AlphabetAction):
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

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8",
                 policy: UnknownPolicy | None = None) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        if self.alphabet["meta"].get("spacer") is None:
            raise exs.MissingSpacerError(self.alphabet_path)

        self._has_space_symbol = " " in self.alphabet["letters"]

        # карта «код -> символ» (при дубликатах — первый встреченный)
        self._code_to_char: dict[str, str] = {}
        for ch, code in self.alphabet["letters"].items():
            self._code_to_char.setdefault(code, ch)

        self._max_code_len = max((len(c) for c in self._code_to_char), default=1)
        self._max_char_len = max((len(c) for c in self.alphabet["letters"]), default=1)

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
        self._reset_output()
        spacer = self.alphabet["meta"]["spacer"]
        letters = self.alphabet["letters"]
        max_len = self._max_char_len
        i = 0
        n = len(self.inp)

        while i < n:
            ch = self.inp[i]

            # пробел — тоже «неизвестный», если его нет в letters
            if ch == " " and not self._has_space_symbol:
                repl = self._resolve_unknown(ch)
                if repl is not None:
                    self.out.append(repl)
                i += 1
                continue

            # 1) Пытаемся найти самый длинный чанк (регистронезависимо)
            matched = False
            for length in range(min(max_len, n - i), 0, -1):
                chunk = self.inp[i : i + length]
                key = self._lookup_key(chunk)
                if key is not None:
                    self.out.append(letters[key])
                    i += length
                    matched = True
                    break

            if matched:
                continue

            # 2) Не нашли — обрабатываем как неизвестный символ
            repl = self._resolve_unknown(ch)
            if repl is not None:
                self.out.append(repl)
            i += 1

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
        segments = self.inp.split(" ")

        for idx, seg in enumerate(segments):
            if seg == "":
                if 0 < idx < len(segments) - 1:
                    if not self._has_space_symbol:
                        raise exs.MissingSpaceSymbolError(" ", "".join(result_parts))
                    result_parts.append(" ")
                continue

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


class NumberSystem(AlphabetAction):
    """
    Перевод чисел между системами счисления.

    Поддерживает целые, отрицательные и дробные числа (разделитель '.').

    JSON-алфавит:
        {
            "meta":    { "spacer": " ", "name": ... },
            "letters": { "<символ>": <вес>, ... }
        }

    Допустимые цифры входной системы — те, у которых 0 <= вес < inpSys.
    Всё, что не является цифрой/знаком/точкой в нужном контексте,
    считается разделителем между числами и сохраняется в выводе.

    Точность перевода дробей ограничена self.max_frac_digits.
    """

    def __init__(self, alphabet, inpSys, outSys, inp, enc="utf-8",
                 policy: UnknownPolicy | None = None) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        self.inpSys = int(inpSys)
        self.outSys = int(outSys)

        if self.inpSys < 2 or self.outSys < 2:
            raise exs.ActionError(
                f"Основание системы счисления должно быть >= 2 "
                f"(получено {self.inpSys} -> {self.outSys})"
            )

        self.max_frac_digits = 20

        # ВАЖНО: сохраняем оригинал (регистр приводим только при сравнении)
        self.inp = inp
        self._inp_upper = inp.upper()

        # карта символ -> вес и обратная
        self._digit_value: dict[str, int] = {
            sym.upper(): int(val) for sym, val in self.alphabet["letters"].items()
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

            if ch == "-" and buf_is_num is not True:
                nxt = self.inp[i + 1] if i + 1 < n else ""
                if is_digit(nxt):
                    flush()
                    buf_is_num = True
                    buf.append("-")
                    i += 1
                    continue

            if ch == "." and buf_is_num is True and buf and is_digit(buf[-1]):
                nxt = self.inp[i + 1] if i + 1 < n else ""
                if "." not in buf and is_digit(nxt):
                    buf.append(".")
                    i += 1
                    continue

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
                    repl = self._resolve_unknown(ch)
                    if repl == "":
                        continue
                    raise exs.ActionError(
                        f"Замена {ch!r} на {repl!r} внутри числа "
                        f"не поддерживается — используйте Ignore"
                    )
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
        sign = ""
        if value < 0:
            sign = "-"
            value = -value

        int_part = value.numerator // value.denominator
        frac_part = value - int_part

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
        return self._format_number(n)

    def oper(self) -> str:
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

    def code(self) -> str:
        return self.oper()

    def encode(self) -> str:
        return self.oper()


# ============================================================
#   Braille — кодирование/декодирование шрифтом Брайля
# ============================================================


class Braille(AlphabetAction):
    """
    Кодирование и декодирование шрифтом Брайля.

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
        - num_prefix действует на всё слово до разделителя;
        - capital_word_prefix действует на слово целиком;
        - capital_prefix действует на следующую букву;
        - всё остальное — буквы/пунктуация/математика.

    spacer для этой операции НЕ требуется.
    """

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8",
                 policy: UnknownPolicy | None = None) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        # ---- префиксы ----
        prefixes = self.alphabet.get("prefixes") or {}
        self._num_prefix = self._prefix_char(prefixes, "num_prefix")
        self._cap_prefix = self._prefix_char(prefixes, "capital_prefix")
        self._cap_word_prefix = self._prefix_char(prefixes, "capital_word_prefix")

        # ---- отдельные карты: буквы и цифры ----
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

        self._max_code_len = max((len(c) for c in self._char_to_code), default=1)
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
        return ch.isalnum()

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
        self._reset_output()

        s = self.inp
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

            # --- цифры: один num_prefix на всё число ---
            if ch.isdigit() and ch in self._digit_to_code:
                if self._num_prefix is not None:
                    self.out.append(self._num_prefix)
                while i < n and s[i].isdigit() and s[i] in self._digit_to_code:
                    self.out.append(self._digit_to_code[s[i]])
                    i += 1
                value_len = max_len
                continue

            # --- буквы: обрабатываем слово целиком ---
            if ch.isalpha() and ch.upper() in self._letter_to_code:
                word_start = i
                while i < n and s[i].isalpha() and s[i].upper() in self._letter_to_code:
                    i += 1
                word = s[word_start:i]
                self._emit_word(word)
                value_len = max_len
                continue

            if value_len <= 0:
                repl = self._resolve_unknown(ch)
                if repl is not None:          # ← было `if repl:`
                    self.out.append(repl)
                i += 1
                value_len = max_len
                continue

            chunk = s[i : i + value_len]
            code = self._char_to_code.get(chunk)
            if code is None:
                value_len -= 1
                continue

            self.out.append(code)
            i += len(chunk)
            value_len = max_len

        return "".join(self.out)

    def _emit_word(self, word: str) -> None:
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
        self._reset_output()

        if not self.inp.strip():
            return ""

        result: list[str] = []
        s = self.inp
        n = len(s)
        i = 0

        num_mode = False
        cap_mode = False
        cap_word_mode = False

        prefix_pairs = [
            (self._cap_word_prefix, "word"),
            (self._num_prefix, "num"),
            (self._cap_prefix, "cap"),
        ]
        prefix_pairs = [(p, k) for p, k in prefix_pairs if p]
        prefix_pairs.sort(key=lambda x: len(x[0]), reverse=True)

        def flush_word_modes():
            nonlocal num_mode, cap_word_mode
            num_mode = False
            cap_word_mode = False

        while i < n:
            ch = s[i]

            if ch.isspace():
                result.append(" ")
                flush_word_modes()
                cap_mode = False
                i += 1
                continue

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
                repl = self._resolve_unknown(ch)
                if repl is not None:          # ← было `if repl:`
                    result.append(repl)
                i += 1
                continue

            out_sym = None

            if num_mode:
                if code in self._code_to_digit:
                    out_sym = self._code_to_digit[code]
                else:
                    num_mode = False

            if out_sym is None:
                if code in self._code_to_letter:
                    out_sym = self._code_to_letter[code].lower()
                elif code in self._code_to_other:
                    out_sym = self._code_to_other[code]
                elif code in self._code_to_digit:
                    out_sym = self._code_to_digit[code]

            if out_sym is not None and out_sym.isalpha():
                if cap_mode:
                    out_sym = out_sym.upper()
                elif cap_word_mode:
                    out_sym = out_sym.upper()
            cap_mode = False

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
        self.inp = inp
        self.enc = enc
        self.out: list[str] = []

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


class Caesar(AlphabetAction):
    def __init__(self, alphabet, inp, shift, enc="utf-8",
                 policy: UnknownPolicy | None = None, **kwargs) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )
        if self._n_letters() < 2:
            raise exs.ActionError("Алфавит для шифра Цезаря слишком короткий")

        self.shift = self._read_shift(shift)

    def _n_letters(self) -> int:
        return len(self._idx_to_char)

    def _read_shift(self, shift: int | None) -> int:
        if shift is not None:
            return int(shift)
        meta = self.alphabet.get("meta") or {}
        try:
            return int(meta.get("shift", 3))
        except (TypeError, ValueError):
            raise exs.ActionError(
                f"Некорректный сдвиг в meta.shift: {meta.get('shift')!r}"
            )

    def _convert(self, delta: int) -> str:
        self._reset_output()
        result: list[str] = []
        n = self._n_letters()

        for ch in self.inp:
            replacement = self._convert_char(ch)
            if replacement is not None:
                result.append(replacement)
                continue

            idx = self._find_index(ch)  # точно есть
            new_ch = self._idx_to_char[(idx + delta) % n]
            result.append(self._restore_case(ch, new_ch))

        out = "".join(result)
        self.out = [out]
        return out

    def code(self) -> str:
        return self._convert(self.shift)

    def encode(self) -> str:
        return self._convert(-self.shift)

    def oper(self) -> str:
        return self.code()


# ============================================================
#   A1Z26 — числовое кодирование по позиции в алфавите
# ============================================================


class A1Z26(AlphabetAction):
    """
    Кодирование «буква -> её номер в алфавите» и обратно.

    Работает с ЛЮБЫМ словарём: важен лишь порядок букв в "letters".
    Первая буква получает номер 1, вторая — 2 и т.д.

    JSON-алфавит:
        {
            "meta":    { "sep": "-", ... },
            "letters": "<строка букв в нужном порядке>"
        }

    Кодирование (code):
        - каждая буква заменяется своим номером;
        - числа разделяются meta.sep (по умолчанию '-');
        - регистр сохраняется;
        - символы вне алфавита обрабатываются политикой.

    Декодирование (encode):
        - числа, разделённые sep (а также пробелами/переносами),
          превращаются обратно в буквы;
        - всё остальное сохраняется как есть.

    spacer для этой операции НЕ требуется.
    """

    def __init__(
        self, alphabet: str, inp: str, sep: str = None, enc: str = "utf-8",
        policy: UnknownPolicy | None = None, **kwargs
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

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
        if ch in self._char_to_num:
            return self._char_to_num[ch], ch

        for variant in (ch.lower(), ch.upper(), ch.casefold()):
            if variant in self._char_to_num:
                return self._char_to_num[variant], variant
        return None

    # --------------------------------------------------------
    #   Кодирование
    # --------------------------------------------------------

    def code(self) -> str:
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
                repl = self._resolve_unknown(ch)
                if repl is not None:
                    parts.append(repl)
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

            if in_number and ch == self.sep:
                if i + 1 < n and s[i + 1] == self.sep:
                    flush_number()
                    result.append(self.sep)
                    i += 2
                    continue
                flush_number()
                i += 1
                continue

            if in_number and ch.isspace():
                flush_number()
                result.append(ch)
                i += 1
                continue

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


class Vigenere(AlphabetAction):
    """
    Шифр Виженёра над произвольным алфавитом.

    JSON-алфавит:
        {
            "meta":    { ... },
            "letters": "<строка букв в нужном порядке>"
        }

    Ключ — строка из символов алфавита (регистр не важен).
    Символы входа, которых нет в алфавите, обрабатываются
    политикой и НЕ сдвигают ключ.

    code()   — шифрование (сдвиг вправо на индекс ключа);
    encode() — расшифровка (сдвиг влево на индекс ключа).
    """

    def __init__(self, alphabet: str, inp: str, key: str, enc: str = "utf-8",
                 policy: UnknownPolicy | None = None, **kwargs) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )

        self._letters = letters
        self._n = len(letters)

        if self._n < 2:
            raise exs.ActionError(
                f"Алфавит для шифра Виженёра слишком короткий (длина {self._n})"
            )

        if not key:
            raise exs.ActionError("Ключ шифра Виженёра не может быть пустым")

        # _char_to_idx / _idx_to_char уже построены в AlphabetAction
        self.key = key
        self._key_indices: list[int] = []
        for pos, ch in enumerate(key):
            idx = self._find_index(ch)
            if idx is None:
                raise exs.InvalidKeySymbolError(
                    symbol=ch,
                    position=pos,
                    key=key,
                    alphabet_path=self.alphabet_path,
                )
            self._key_indices.append(idx)

    def _convert(self, sign: int) -> str:
        self._reset_output()

        result: list[str] = []
        n = self._n
        key_len = len(self._key_indices)
        key_pos = 0

        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                # политика для неизвестного символа; ключ не двигаем
                repl = self._resolve_unknown(ch)
                if repl is not None:
                    result.append(repl)
                continue

            shift = self._key_indices[key_pos % key_len]
            new_idx = (idx + sign * shift) % n
            new_ch = self._idx_to_char[new_idx]
            result.append(self._restore_case(ch, new_ch))

            key_pos += 1

        out = "".join(result)
        self.out = [out]
        return out

    def code(self) -> str:
        return self._convert(+1)

    def encode(self) -> str:
        return self._convert(-1)

    def oper(self) -> str:
        return self.code()


# ============================================================
#   Atbash — шифр Атбаш
# ============================================================


class Atbash(AlphabetAction):
    """
    Шифр Атбаш («зеркальная» замена букв в алфавите).

    JSON-алфавит:
        {
            "meta":    { ... },
            "letters": "<строка букв в нужном порядке>"
        }

    Правила:
        - буква с индексом i заменяется на букву с индексом (n-1-i);
        - регистр сохраняется;
        - символы вне алфавита обрабатываются политикой.

    Атбаш — инволюция: code() и encode() дают одинаковый результат.
    """

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8",
                 policy: UnknownPolicy | None = None, **kwargs) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        letters = self.alphabet.get("letters")
        if not isinstance(letters, str):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (должна быть строкой)"]
            )

        self._letters = letters
        self._n = len(letters)

        if self._n < 2:
            raise exs.ActionError(
                f"Алфавит для шифра Атбаш слишком короткий (длина {self._n})"
            )

    def _convert(self) -> str:
        self._reset_output()

        result: list[str] = []
        n = self._n

        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                repl = self._resolve_unknown(ch)
                if repl is not None:
                    result.append(repl)
                continue

            new_idx = n - 1 - idx
            new_ch = self._idx_to_char[new_idx]
            result.append(self._restore_case(ch, new_ch))

        out = "".join(result)
        self.out = [out]
        return out

    def code(self) -> str:
        return self._convert()

    def encode(self) -> str:
        return self._convert()

    def oper(self) -> str:
        return self.code()


# ============================================================
#   Playfair — биграммный шифр Плейфера
# ============================================================


class Playfair(AlphabetAction):
    """
    Шифр Плейфера (биграммный шифр).

    JSON-алфавит:
        {
            "meta": {
                "rows":   <int>,
                "cols":   <int>,
                "filler": "<символ>"  # по умолчанию "X"
            },
            "letters": "<строка символов алфавита>"
        }

    Таблица заполняется ключом (уникальные символы ключа,
    затем оставшиеся символы алфавита в порядке "letters").
    Размеры таблицы берутся из meta; len(letters) должен
    совпадать с rows * cols (с учётом aliases).

    Неизвестные символы обрабатываются политикой.
    """

    def __init__(self, alphabet: str, inp: str, key: str, enc: str = "utf-8",
                 policy: UnknownPolicy | None = None, **kwargs) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

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
            if dst_u not in letters_upper:
                raise exs.ActionError(
                    f"meta.aliases: целевой символ {dst!r} отсутствует в алфавите"
                )
            if dst_u in self._aliases:
                raise exs.ActionError(
                    f"meta.aliases: целевой символ {dst!r} сам является источником "
                    f"замены — цепочки замен не поддерживаются"
                )
            if src_u in self._aliases:
                raise exs.ActionError(f"meta.aliases: дублирующийся ключ {src!r}")
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
        # AlphabetAction уже построил _char_to_idx / _idx_to_char
        # по "letters". Но Playfair работает в верхнем регистре,
        # поэтому перестраиваем локально (для ясности).
        self._char_to_idx = {ch.upper(): i for i, ch in enumerate(letters)}
        self._idx_to_char = [ch.upper() for ch in letters]

        # --- эффективный размер таблицы с учётом aliases ---
        cell_chars = [ch for ch in self._idx_to_char if ch not in self._aliases]
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

        for ch in key.upper():
            while ch in self._aliases:
                ch = self._aliases[ch]
            if ch in self._char_to_idx and ch not in self._aliases and ch not in seen:
                seen.add(ch)
                ordered.append(ch)

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
            ordered[r * self.cols : (r + 1) * self.cols] for r in range(self.rows)
        ]

        self._pos = {}
        for r in range(self.rows):
            for c in range(self.cols):
                self._pos[self._table[r][c]] = (r, c)

    # --------------------------------------------------------
    #   Нормализация входа
    # --------------------------------------------------------

    def _normalize(self, text: str) -> str:
        result: list[str] = []
        for ch in text.upper():
            while ch in self._aliases:
                ch = self._aliases[ch]
            if ch in self._char_to_idx:
                result.append(ch)
                continue

            repl = self._resolve_unknown(ch)
            if repl is None:                          # игнорировать
                continue
            if repl == "":
                continue                              # осознанная пустая замена

            kept = 0
            for rc in repl.upper():
                while rc in self._aliases:
                    rc = self._aliases[rc]
                if rc in self._char_to_idx:
                    result.append(rc)
                    kept += 1
            if kept == 0:
                raise exs.ActionError(
                    f"Замена {repl!r} для символа {ch!r} не содержит "
                    f"ни одного символа алфавита Плейфера — "
                    f"используйте «Игнорировать» или корректную замену"
                )
        return "".join(result)

    # --------------------------------------------------------
    #   Разбиение на биграммы
    # --------------------------------------------------------

    def _split_bigrams(self, text: str) -> list[tuple[str, str]]:
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
                            f"совпадают с filler — выберите другой filler"
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

    def _transform_bigram(self, a: str, b: str, sign: int) -> tuple[str, str]:
        ra, ca = self._pos[a]
        rb, cb = self._pos[b]

        if ra == rb:
            new_ca = (ca + sign) % self.cols
            new_cb = (cb + sign) % self.cols
            return self._table[ra][new_ca], self._table[rb][new_cb]

        if ca == cb:
            new_ra = (ra + sign) % self.rows
            new_rb = (rb + sign) % self.rows
            return self._table[new_ra][ca], self._table[new_rb][cb]

        return self._table[ra][cb], self._table[rb][ca]

    # --------------------------------------------------------
    #   Публичные методы
    # --------------------------------------------------------

    def code(self) -> str:
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