# ============================================================
#   actions.py
# ============================================================

import json
from fractions import Fraction

import Exceptions as exs
from Settings import UnknownPolicy


# ============================================================
#   Action — базовый класс
# ============================================================

class Action:
    """Загрузка/валидация алфавита, self.inp, self.out."""

    REQUIRED_KEYS: tuple[str, ...] = ("meta", "letters")

    def __init__(self, alphabet: str, inp: str, enc: str = "utf-8") -> None:
        self.alphabet_path = alphabet
        with open(alphabet, encoding=enc) as fh:
            self.alphabet = json.load(fh)
        self._validate_alphabet()
        self.inp = inp
        self.out: list[str] = []

    def _validate_alphabet(self) -> None:
        missing = [k for k in self.REQUIRED_KEYS if not self.alphabet.get(k)]
        if missing:
            raise exs.InvalidAlphabetError(self.alphabet_path, missing)

    def _reset_output(self) -> None:
        self.out = []

    def _finish(self, text: str) -> str:
        """Сохранить результат и вернуть его же (удобно для return)."""
        self.out = [text]
        return text


# ============================================================
#   AlphabetAction — общий слой
# ============================================================

class AlphabetAction(Action):
    """
    Общий предок операций над "letters".

    Даёт наследникам:
        - _char_to_idx / _idx_to_char;
        - _find_index (точный и регистронезависимый поиск);
        - _restore_case;
        - политику обработки неизвестных символов;
        - проверку входных символов с учётом направления (code/encode).
    """

    _policy: UnknownPolicy
    _direction: str = "code"  # "code" | "encode"; наследники могут уточнять

    def __init__(
        self,
        alphabet: str,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        super().__init__(alphabet, inp, enc)
        self._policy = policy if policy is not None else UnknownPolicy.current()
        self._build_char_maps()

    # ---------- карта символов ----------

    def _build_char_maps(self) -> None:
        """Построить карты «символ <-> индекс» из self.alphabet['letters'].

        Поддерживает три формата letters:
          - {"A": "...", "B": "..."}       — символ -> значение (dict)
          - ["A", "B", "C"]               — просто список символов
          - "ABC"                         — строка (как в шифрах)
        """
        letters = self.alphabet["letters"]
        self._idx_to_char: list[str] = []
        self._char_to_idx: dict[str, int] = {}

        if isinstance(letters, dict):
            items = list(letters.keys())
        elif isinstance(letters, (list, str)):
            items = list(letters)
        else:
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (объект, массив или строка)"]
            )

        for idx, ch in enumerate(items):
            if not isinstance(ch, str) or len(ch) == 0:
                continue
            # первый символ побеждает при дубликатах
            if ch in self._char_to_idx:
                continue
            self._char_to_idx[ch] = idx
            self._idx_to_char.append(ch)

    # ---------- направление ----------

    def set_direction(self, direction: str) -> None:
        """Задать направление проверки входных символов: 'code' | 'encode'."""
        if direction not in ("code", "encode"):
            raise ValueError(f"direction must be 'code' or 'encode', got {direction!r}")
        self._direction = direction

    # ---------- неизвестные ----------

    def _known(self, ch: str) -> bool:
        return self._find_index(ch) is not None

    def _resolve_unknown(self, ch: str, partial_out: str = "") -> str | None:
        return self._policy.resolve(ch, self.alphabet_path, partial_out)

    def _emit_unknown(self, target: list[str], ch: str) -> None:
        repl = self._resolve_unknown(ch, partial_out="".join(target))
        if repl is not None:
            target.append(repl)

    # ---------- проверка входа ----------

    def _check_unknown_chars(self) -> list[str]:
        """
        Уникальные символы входа, которые не будут обработаны
        в текущем направлении.

        Для 'code'  — символы, отсутствующие в _char_to_idx (кодируемый текст).
        Для 'encode' — символы/коды, не разбираемые декодером.
        Базовая реализация корректна только для 'code';
        направления с декодером переопределяют _check_undecodable().
        """
        if self._direction == "encode":
            return self._check_undecodable()
        return self._check_unknown_chars_code()

    def _check_unknown_chars_code(self) -> list[str]:
        unknown: list[str] = []
        seen: set[str] = set()
        for ch in self.inp:
            if ch in seen:
                continue
            seen.add(ch)
            if self._find_index(ch) is None:
                unknown.append(ch)
        return unknown

    def _check_undecodable(self) -> list[str]:
        """
        Для наследников без собственного декодера encode() совпадает
        с code(), поэтому проверка та же.
        """
        return self._check_unknown_chars_code()

    def _lookup_key(self, chunk: str) -> str | None:
        letters = self.alphabet["letters"]
        if chunk in letters:
            return chunk
        folded = chunk.casefold()
        for key in letters:
            if key.casefold() == folded:
                return key
        return None

    def _find_index(self, ch: str) -> int | None:
        """Точный поиск, затем регистронезависимый."""
        idx = self._char_to_idx.get(ch)
        if idx is not None:
            return idx
        folded = ch.casefold()
        for key, i in self._char_to_idx.items():
            if key.casefold() == folded:
                return i
        return None

    def _restore_case(self, source: str, target: str) -> str:
        """Перенести регистр source на target (для одного символа)."""
        if not source or not target:
            return target
        if source.isupper():
            return target.upper()
        if source.islower():
            return target.lower()
        return target

    def _require_str_letters(self) -> list[str]:
        """Проверить, что letters — плоский набор одиночных символов.

        Возвращает список символов. Нужен шифрам (Caesar, Vigenere,
        Atbash, A1Z26, Playfair), где letters обязан быть простым
        алфавитом, а не картой «символ -> код».
        """
        letters = self.alphabet["letters"]
        if isinstance(letters, dict):
            items = list(letters.keys())
        elif isinstance(letters, (list, str)):
            items = list(letters)
        else:
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["letters (объект, массив или строка)"]
            )
        if not items:
            raise exs.ActionError("Алфавит пуст")
        for ch in items:
            if not isinstance(ch, str) or len(ch) != 1:
                raise exs.ActionError(
                    f"Алфавит должен состоять из одиночных символов, "
                    f"встретился {ch!r}"
                )
        return items


# ============================================================
#   _OperIsCode — удобная примесь: oper() == code()
# ============================================================

class _OperIsCode(AlphabetAction):
    """Если у наследника нет своего oper(), он равен code()."""

    def _oper(self) -> str:
        return self.code()

    def oper(self) -> str:
        return self._oper()


# ============================================================
#   Morse
# ============================================================

class Morse(_OperIsCode):
    """Азбука Морзе: code() — в Морзе, encode() — обратно."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        if self.alphabet["meta"].get("spacer") is None:
            raise exs.MissingSpacerError(self.alphabet_path)

        letters = self.alphabet["letters"]
        self._has_space_symbol = " " in letters

        # карта «код -> символ»; при дубликатах побеждает первый встреченный
        self._code_to_char: dict[str, str] = {}
        for ch, code in letters.items():
            self._code_to_char.setdefault(code, ch)

        self._max_code_len = max((len(c) for c in self._code_to_char), default=1)
        self._max_char_len = max((len(c) for c in letters), default=1)

    # ---------- кодирование ----------

    def code(self) -> str:
        self._reset_output()
        spacer = self.alphabet["meta"]["spacer"]
        letters = self.alphabet["letters"]
        s, n = self.inp, len(self.inp)
        i = 0

        while i < n:
            ch = s[i]

            # пробел без символа в алфавите — сразу политика
            if ch == " " and not self._has_space_symbol:
                self._emit_unknown(self.out, ch)
                i += 1
                continue

            key = self._match_longest(s, i)
            if key is not None:
                self.out.append(letters[key])
                i += len(key)
                continue

            self._emit_unknown(self.out, ch)
            i += 1

        return spacer.join(self.out)

    def _match_longest(self, s: str, i: int) -> str | None:
        """Самый длинный ключ letters, начинающийся в s[i] (регистронезависимо)."""
        limit = min(self._max_char_len, len(s) - i)
        for length in range(limit, 0, -1):
            key = self._lookup_key(s[i : i + length])
            if key is not None:
                return key
        return None

    # ---------- декодирование ----------

    def _check_undecodable(self) -> list[str]:
        """
        Проверка входа для encode(): символа нет ни в одном коде,
        ни среди пробелов/разделителей.
        """
        if not self.inp.strip():
            return []
        spacer = self.alphabet["meta"]["spacer"]
        unknown: list[str] = []
        seen: set[str] = set()

        for ch in self.inp:
            if ch == " " or ch == spacer:
                continue
            if ch in self._code_to_char or ch in seen:
                continue
            seen.add(ch)
            unknown.append(ch)
        return unknown

    def encode(self) -> str:
        self._reset_output()
        if not self.inp.strip():
            return ""

        spacer = self.alphabet["meta"]["spacer"]
        parts: list[str] = []
        segments = self.inp.split(" ")

        for idx, seg in enumerate(segments):
            if seg == "":
                # пустой сегмент между двумя непустыми — это пробел в тексте
                if 0 < idx < len(segments) - 1:
                    if not self._has_space_symbol:
                        raise exs.MissingSpaceSymbolError(" ", "".join(parts))
                    parts.append(" ")
                continue

            codes = seg.split(spacer) if spacer != " " and spacer in seg else [seg]
            for code in codes:
                if not code:
                    continue
                ch = self._code_to_char.get(code)
                if ch is None:
                    raise exs.UnknownSymbolError(code, "".join(parts))
                parts.append(ch)

        return self._finish("".join(parts))


# ============================================================
#   NumberSystem
# ============================================================

class NumberSystem(_OperIsCode):
    """
    Перевод чисел между системами счисления.

    Поддерживает целые, отрицательные и дробные ('.') числа.
    Всё, что не является цифрой/знаком/точкой в нужном контексте,
    считается разделителем и сохраняется в выводе.
    """

    def __init__(
        self,
        alphabet: str,
        inpSys: int,
        outSys: int,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        self.inpSys, self.outSys = int(inpSys), int(outSys)
        if self.inpSys < 2 or self.outSys < 2:
            raise exs.ActionError(
                f"Основание системы счисления должно быть >= 2 "
                f"(получено {self.inpSys} -> {self.outSys})"
            )

        self.max_frac_digits = 20
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

    # ---------- токенизация ----------

    def _tokenize(self) -> list[tuple[str, bool]]:
        """Разбить вход на (фрагмент, is_number)."""
        tokens: list[tuple[str, bool]] = []
        buf: list[str] = []
        is_num: bool | None = None

        def flush() -> None:
            nonlocal buf, is_num
            if buf and is_num is not None:
                tokens.append(("".join(buf), is_num))
            buf, is_num = [], None

        def is_digit(ch: str) -> bool:
            return ch.upper() in self._allowed

        s, n, i = self.inp, len(self.inp), 0
        while i < n:
            ch = s[i]
            nxt = s[i + 1] if i + 1 < n else ""

            if is_digit(ch):
                if is_num is not True:
                    flush()
                    is_num = True
                buf.append(ch)
                i += 1
            elif ch == "-" and is_num is not True and is_digit(nxt):
                # минус — только в начале числа
                flush()
                is_num = True
                buf.append("-")
                i += 1
            elif (
                ch == "."
                and is_num is True
                and buf
                and is_digit(buf[-1])
                and "." not in buf
                and is_digit(nxt)
            ):
                buf.append(".")
                i += 1
            else:
                if is_num is not True:
                    if is_num is None:
                        is_num = False
                    buf.append(ch)
                else:
                    flush()
                    is_num = False
                    buf.append(ch)
                i += 1

        flush()
        return tokens

    # ---------- разбор / вывод ----------

    def _parse_number(self, token: str) -> Fraction:
        sign = -1 if token.startswith("-") else 1
        s = token.lstrip("-")
        int_part, _, frac_part = s.partition(".")

        def digits_to_int(part: str) -> int:
            value = 0
            for ch in part:
                v = self._digit_value.get(ch.upper())
                if v is None or v >= self.inpSys:
                    repl = self._resolve_unknown(ch, partial_out="".join(self.out))
                    if repl == "":
                        continue
                    raise exs.ActionError(
                        f"Замена {ch!r} на {repl!r} внутри числа не поддерживается "
                        f"— используйте Ignore"
                    )
                value = value * self.inpSys + v
            return value

        int_val = digits_to_int(int_part) if int_part else 0
        frac_val = Fraction(0, 1)
        if frac_part:
            frac_val = Fraction(digits_to_int(frac_part), self.inpSys ** len(frac_part))
        return sign * (int_val + frac_val)

    def _format_number(self, value: Fraction) -> str:
        sign = ""
        if value < 0:
            sign, value = "-", -value

        int_part = value.numerator // value.denominator
        frac_part = value - int_part

        def sym_of(d: int, partial: str) -> str:
            sym = self._value_digit.get(d)
            if sym is None:
                raise exs.UnknownSymbolError(str(d), partial)
            return sym

        if int_part == 0:
            int_digits = [sym_of(0, "")]
        else:
            int_digits = []
            n = int_part
            while n > 0:
                n, r = divmod(n, self.outSys)
                int_digits.append(sym_of(r, "".join(reversed(int_digits))))
            int_digits.reverse()

        result = sign + "".join(int_digits)

        if frac_part > 0:
            frac_digits: list[str] = []
            for _ in range(self.max_frac_digits):
                frac_part *= self.outSys
                d = frac_part.numerator // frac_part.denominator
                frac_part -= d
                frac_digits.append(sym_of(d, result + "." + "".join(frac_digits)))
                if frac_part == 0:
                    break
            result += "." + "".join(frac_digits)

        return result

    # ---------- публичные ----------

    def convert(self, n: Fraction) -> str:
        return self._format_number(n)

    def _oper(self) -> str:
        self._reset_output()
        parts = [
            self.convert(self._parse_number(frag)) if is_num else frag
            for frag, is_num in self._tokenize()
        ]
        return self._finish("".join(parts))

    def code(self) -> str:
        return self._oper()

    def encode(self) -> str:
        return self._oper()


# ============================================================
#   Braille
# ============================================================

class Braille(_OperIsCode):
    """Шрифт Брайля: code() — в Брайль, encode() — обратно."""

    _BRAILLE_BLANK = "\u2800"
    _NORMAL_SPACE = " "

    def __init__(
        self,
        alphabet: str,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)

        prefixes = self.alphabet.get("prefixes") or {}
        self._num_prefix = self._prefix_char(prefixes, "num_prefix")
        self._cap_prefix = self._prefix_char(prefixes, "capital_prefix")
        self._cap_word_prefix = self._prefix_char(prefixes, "capital_word_prefix")

        self._letter_to_code: dict[str, str] = {}
        self._digit_to_code: dict[str, str] = {}
        self._code_to_letter: dict[str, str] = {}
        self._code_to_digit: dict[str, str] = {}
        self._other_to_code: dict[str, str] = {}
        self._code_to_other: dict[str, str] = {}

        self._load_section("letters", self._letter_to_code, self._code_to_letter)
        self._load_section("digits", self._digit_to_code, self._code_to_digit)
        self._load_section("punctuation", self._other_to_code, self._code_to_other)
        self._load_section("math", self._other_to_code, self._code_to_other)

        # общая карта для «жадного» кодирования
        self._char_to_code: dict[str, str] = {}
        for mapping in (
            self._letter_to_code,
            self._digit_to_code,
            self._other_to_code,
        ):
            for sym, code in mapping.items():
                self._char_to_code.setdefault(sym, code)

        self._word_sep = self._BRAILLE_BLANK
        self._max_code_len = max(
            (len(c) for c in self._char_to_code),
            default=1,
        )
        if self._word_sep:
            self._max_code_len = max(self._max_code_len, len(self._word_sep))

        # префиксы — от длинных к коротким, чтобы «жадно» ловить cap_word
        self._prefix_pairs: list[tuple[str, str]] = sorted(
            (
                (p, kind)
                for p, kind in (
                    (self._cap_word_prefix, "word"),
                    (self._num_prefix, "num"),
                    (self._cap_prefix, "cap"),
                )
                if p
            ),
            key=lambda item: len(item[0]),
            reverse=True,
        )


    def _check_undecodable(self) -> list[str]:
        """
        Проверка входа для encode(): каждый непробельный фрагмент должен
        быть либо префиксом, либо известным кодом.
        Повторяет разбор encode(), но не строит выход.
        """
        s, n = self.inp, len(self.inp)
        i = 0
        unknown: list[str] = []
        seen: set[str] = set()

        while i < n:
            ch = s[i]
            if ch.isspace():
                i += 1
                continue

            hit = next(
                ((p, _kind) for p, _kind in self._prefix_pairs if s.startswith(p, i)),
                None,
            )
            if hit is not None:
                i += len(hit[0])
                continue

            _code, length = self._match_code(s, i)
            if _code is None:
                if ch not in seen:
                    seen.add(ch)
                    unknown.append(ch)
                i += 1
                continue
            i += length

        return unknown

    def _load_section(
        self,
        name: str,
        to_code: dict[str, str],
        from_code: dict[str, str],
    ) -> None:
        for sym, info in (self.alphabet.get(name) or {}).items():
            code = self._code_of(info)
            if code:
                to_code.setdefault(sym, code)
                from_code.setdefault(code, sym)

    @staticmethod
    def _code_of(info: object) -> str | None:
        return info.get("char") if isinstance(info, dict) else info  # type: ignore[return-value]

    @staticmethod
    def _prefix_char(prefixes: dict, key: str) -> str | None:
        info = prefixes.get(key)
        if not info:
            return None
        return info.get("char") if isinstance(info, dict) else info

    # ---------- кодирование ----------

    def code(self) -> str:
        self._reset_output()
        s, n, max_len = self.inp, len(self.inp), self._max_code_len
        i = 0

        while i < n:
            ch = s[i]

            if ch.isspace():
                self.out.append(self._word_sep)
                i += 1
                continue

            # цифры: один num_prefix на всё число
            if ch.isdigit() and ch in self._digit_to_code:
                if self._num_prefix:
                    self.out.append(self._num_prefix)
                while i < n and s[i].isdigit() and s[i] in self._digit_to_code:
                    self.out.append(self._digit_to_code[s[i]])
                    i += 1
                continue

            # буквы: слово целиком (для capital_word_prefix)
            if ch.isalpha() and ch.upper() in self._letter_to_code:
                start = i
                while i < n and s[i].isalpha() and s[i].upper() in self._letter_to_code:
                    i += 1
                self._emit_word(s[start:i])
                continue

            # произвольный чанк — жадный поиск
            matched = False
            for ln in range(min(max_len, n - i), 0, -1):
                code = self._char_to_code.get(s[i : i + ln])
                if code is not None:
                    self.out.append(code)
                    i += ln
                    matched = True
                    break
            if matched:
                continue

            self._emit_unknown(self.out, ch)
            i += 1

        return "".join(self.out)

    def _emit_word(self, word: str) -> None:
        if len(word) >= 2 and all(c.isupper() for c in word) and self._cap_word_prefix:
            self.out.append(self._cap_word_prefix)
            for c in word:
                self.out.append(self._letter_to_code[c.upper()])
            return

        for c in word:
            if c.isupper() and self._cap_prefix:
                self.out.append(self._cap_prefix)
            self.out.append(self._letter_to_code[c.upper()])

    # ---------- декодирование ----------

    def encode(self) -> str:
        self._reset_output()
        if not self.inp.strip():
            return ""

        s, n = self.inp, len(self.inp)
        i = 0
        num_mode = cap_mode = cap_word_mode = False
        result: list[str] = []

        def flush_modes() -> None:
            nonlocal num_mode, cap_word_mode
            num_mode = cap_word_mode = False

        while i < n:
            ch = s[i]

            if ch.isspace():
                result.append(" ")
                flush_modes()
                cap_mode = False
                i += 1
                continue

            # префикс?
            hit = next(
                ((p, kind) for p, kind in self._prefix_pairs if s.startswith(p, i)),
                None,
            )
            if hit is not None:
                prefix, kind = hit
                if kind == "num":
                    num_mode = True
                elif kind == "cap":
                    cap_mode = True
                else:
                    cap_word_mode = True
                i += len(prefix)
                continue

            code, length = self._match_code(s, i)
            if code is None:
                self._emit_unknown(result, ch)
                i += 1
                continue

            out_sym = self._decode_code(code, num_mode)
            if out_sym is None:
                # цифровой режим не сработал — выходим из него и пробуем ещё раз
                num_mode = False
                out_sym = self._decode_code(code, False)

            if out_sym is not None and out_sym.isalpha() and (cap_mode or cap_word_mode):
                out_sym = out_sym.upper()
            cap_mode = False

            if code in self._code_to_other:
                flush_modes()

            result.append(out_sym)
            i += length

        return self._finish("".join(result))

    def _match_code(self, s: str, i: int) -> tuple[str | None, int]:
        """Найти самый длинный код в s[i:]."""
        for ln in range(min(self._max_code_len, len(s) - i), 0, -1):
            cand = s[i : i + ln]
            if (
                cand in self._code_to_letter
                or cand in self._code_to_digit
                or cand in self._code_to_other
            ):
                return cand, ln
        return None, 0

    def _decode_code(self, code: str, num_mode: bool) -> str | None:
        """Интерпретировать код с учётом цифрового режима."""
        if num_mode and code in self._code_to_digit:
            return self._code_to_digit[code]
        if code in self._code_to_letter:
            return self._code_to_letter[code].lower()
        if code in self._code_to_other:
            return self._code_to_other[code]
        if code in self._code_to_digit:
            return self._code_to_digit[code]
        return None


# ============================================================
#   Bytes
# ============================================================

class Bytes(AlphabetAction):
    """Текст <-> битовая строка. Стандартные кодировки и кастомные
    алфавиты из alphabets/binary (символ <-> фиксированное число байт)."""

    BYTE_SEP: str = " "

    def __init__(
        self,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
    ) -> None:
        self.inp = inp
        self.enc = enc
        self.out: list[str] = []
        self.alphabet_path: str | None = None
        self.alphabet: dict | None = None

        self._custom = False
        self._char_to_code: dict[str, str] = {}
        self._code_to_char: dict[str, str] = {}
        self._bytes_per_char: int = 0

        if enc.endswith(".json"):
            self._load_custom_alphabet(enc)
        else:
            try:
                "".encode(self.enc)
            except LookupError:
                raise exs.ActionError(f"Неизвестная кодировка: {self.enc!r}")

        self._policy = policy if policy is not None else UnknownPolicy.current()
        self._direction = "code"

    # ---------- загрузка ----------

    def _load_custom_alphabet(self, path: str) -> None:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise exs.ActionError(f"Не удалось загрузить алфавит: {exc}")

        meta = data.get("meta") or {}
        letters = data.get("letters") or {}
        n_bytes = meta.get("bytes")
        if not isinstance(n_bytes, int) or n_bytes < 1:
            raise exs.ActionError(
                "В алфавите отсутствует или некорректно поле meta.bytes"
            )

        self._bytes_per_char = n_bytes
        self.alphabet_path = path
        self.alphabet = data

        for ch, code in letters.items():
            if not isinstance(code, str) or len(code) != n_bytes * 8 or any(
                c not in "01" for c in code
            ):
                raise exs.ActionError(
                    f"Код для {ch!r} должен быть строкой из {n_bytes * 8} бит (0/1)"
                )
            self._char_to_code[ch] = code
            self._code_to_char[code] = ch

        self._custom = True

    # ---------- проверка неизвестных (code) ----------

    def _casefold_match(self, ch: str) -> str | None:
        folded = ch.casefold()
        for k in self._char_to_code:
            if k.casefold() == folded:
                return k
        return None

    def _check_unknown_chars_code(self) -> list[str]:
        unknown: list[str] = []
        seen: set[str] = set()
        for ch in self.inp:
            if ch in seen:
                continue
            seen.add(ch)
            if self._custom:
                if ch not in self._char_to_code and self._casefold_match(ch) is None:
                    unknown.append(ch)
            else:
                try:
                    ch.encode(self.enc)
                except UnicodeEncodeError:
                    unknown.append(ch)
        return unknown

    # ---------- проверка неизвестных (encode) ----------

    def _check_undecodable(self) -> list[str]:
        bits = "".join(c for c in self.inp if c in "01")
        unknown: list[str] = []
        seen: set[str] = set()

        if self._custom:
            chunk_len = self._bytes_per_char * 8
            if len(bits) % chunk_len:
                return [bits[-(len(bits) % chunk_len):]]
            for i in range(0, len(bits), chunk_len):
                chunk = bits[i:i + chunk_len]
                if chunk in seen:
                    continue
                seen.add(chunk)
                if chunk not in self._code_to_char:
                    unknown.append(chunk)
            return unknown

        if len(bits) % 8:
            return [bits[-(len(bits) % 8):]]
        for i in range(0, len(bits), 8):
            byte = bits[i:i + 8]
            if byte in seen:
                continue
            seen.add(byte)
            try:
                int(byte, 2).to_bytes(1, "big").decode(self.enc)
            except UnicodeDecodeError:
                unknown.append(byte)
        return unknown

    # ---------- code (текст -> биты) ----------

    def _code_custom(self) -> str:
        self._reset_output()
        out_chunks: list[str] = []
        for ch in self.inp:
            code = self._char_to_code.get(ch)
            if code is None:
                match = self._casefold_match(ch)
                if match is not None:
                    code = self._char_to_code[match]
            if code is None:
                repl = self._resolve_unknown(
                    ch, partial_out=self.BYTE_SEP.join(out_chunks)
                )
                if repl is not None:
                    out_chunks.append(repl)
                continue
            
            # --- ИЗМЕНЕНИЕ: разбиваем код на байты ---
            # code — строка длиной N*8, разбиваем её на 8-битные куски
            bytes_split = [code[i:i+8] for i in range(0, len(code), 8)]
            out_chunks.extend(bytes_split) 
            
        return self._finish(self.BYTE_SEP.join(out_chunks))

    def code(self) -> str:
        if self._custom:
            return self._code_custom()
        # Стандартная кодировка: WARN не поддерживаем — кидаем ActionError
        self._reset_output()
        try:
            data = self.inp.encode(self.enc)
        except UnicodeEncodeError as exc:
            raise exs.ActionError(
                f"Не удалось закодировать текст в {self.enc!r}: {exc}"
            )
        return self._finish(self.BYTE_SEP.join(format(b, "08b") for b in data))

    # ---------- encode (биты -> текст) ----------

    def _encode_custom(self) -> str:
        self._reset_output()
        bits = "".join(c for c in self.inp if c in "01")
        if not bits:
            return self._finish("")
        chunk_len = self._bytes_per_char * 8
        if len(bits) % chunk_len:
            raise exs.ActionError(
                f"Длина битовой строки ({len(bits)}) не кратна {chunk_len} бит"
            )
        out_chars: list[str] = []
        for i in range(0, len(bits), chunk_len):
            chunk = bits[i:i + chunk_len]
            ch = self._code_to_char.get(chunk)
            if ch is None:
                repl = self._resolve_unknown(chunk, partial_out="".join(out_chars))
                if repl is not None:
                    out_chars.append(repl)
                continue
            out_chars.append(ch)
        return self._finish("".join(out_chars))

    def encode(self) -> str:
        if self._custom:
            return self._encode_custom()
        self._reset_output()
        bits = "".join(c for c in self.inp if c in "01")
        if not bits:
            return self._finish("")
        if len(bits) % 8:
            raise exs.ActionError(
                f"Длина битовой строки ({len(bits)}) не кратна 8"
            )
        data = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
        try:
            result = data.decode(self.enc)
        except UnicodeDecodeError as exc:
            raise exs.ActionError(
                f"Не удалось декодировать байты в {self.enc!r}: {exc}"
            )
        return self._finish(result)

    def oper(self) -> str:
        return self.code()


# ============================================================
#   Caesar
# ============================================================

class Caesar(_OperIsCode):
    """Шифр Цезаря."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        shift: int | None,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        self._require_str_letters()

        if len(self._idx_to_char) < 2:
            raise exs.ActionError("Алфавит для шифра Цезаря слишком короткий")

        self.shift = self._read_shift(shift)

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
        n = len(self._idx_to_char)

        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                self._emit_unknown(result, ch)
                continue
            new_ch = self._idx_to_char[(idx + delta) % n]
            result.append(self._restore_case(ch, new_ch))

        return self._finish("".join(result))

    # ---------- публичные ----------

    def code(self) -> str:
        return self._convert(self.shift)

    def encode(self) -> str:
        return self._convert(-self.shift)


# ============================================================
#   A1Z26
# ============================================================

class A1Z26(_OperIsCode):
    """Буква <-> её номер в алфавите."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        sep: str | None = None,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        letters = self._require_str_letters()
        if not letters:
            raise exs.ActionError("Алфавит для A1Z26 пуст")

        self._char_to_num: dict[str, int] = {ch: i + 1 for i, ch in enumerate(letters)}
        self._num_to_char: dict[int, str] = {i + 1: ch for i, ch in enumerate(letters)}

        meta = self.alphabet.get("meta") or {}
        self.sep = sep or str(meta.get("sep", "-"))

    # ---------- вспомогательное ----------

    def _lookup(self, ch: str) -> int | None:
        if ch in self._char_to_num:
            return self._char_to_num[ch]
        for variant in (ch.lower(), ch.upper(), ch.casefold()):
            if variant in self._char_to_num:
                return self._char_to_num[variant]
        return None

    # ---------- публичные ----------

    def code(self) -> str:
        self._reset_output()
        parts: list[str] = []
        run: list[str] = []

        def flush() -> None:
            nonlocal run
            if run:
                parts.append(self.sep.join(run))
                run = []

        for ch in self.inp:
            num = self._lookup(ch)
            if num is None:
                flush()
                self._emit_unknown(parts, ch)
                continue
            run.append(str(num))

        flush()
        return self._finish("".join(parts))

    def encode(self) -> str:
        self._reset_output()
        if not self.inp:
            return self._finish("")

        result: list[str] = []
        buf: list[str] = []
        in_number = False

        def flush_number() -> None:
            nonlocal buf, in_number
            if not buf:
                in_number = False
                return
            raw = "".join(buf)
            try:
                num = int(raw)
            except ValueError:
                result.append(raw)
                buf, in_number = [], False
                return
            ch = self._num_to_char.get(num)
            if ch is None:
                raise exs.UnknownSymbolError(str(num), "".join(result))
            result.append(ch)
            buf, in_number = [], False

        s, n, i = self.inp, len(self.inp), 0
        while i < n:
            ch = s[i]
            if ch.isdigit():
                in_number = True
                buf.append(ch)
                i += 1
            elif in_number and ch == self.sep:
                # двойной sep — «литеральный» sep в тексте
                if i + 1 < n and s[i + 1] == self.sep:
                    flush_number()
                    result.append(self.sep)
                    i += 2
                else:
                    flush_number()
                    i += 1
            elif in_number and ch.isspace():
                flush_number()
                result.append(ch)
                i += 1
            else:
                flush_number()
                result.append(ch)
                i += 1

        flush_number()
        return self._finish("".join(result))


# ============================================================
#   Vigenere
# ============================================================

class Vigenere(_OperIsCode):
    """Шифр Виженёра над произвольным алфавитом."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        key: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        self._require_str_letters()

        n = len(self._idx_to_char)
        if n < 2:
            raise exs.ActionError(
                f"Алфавит для шифра Виженёра слишком короткий (длина {n})"
            )
        if not key:
            raise exs.ActionError("Ключ шифра Виженёра не может быть пустым")

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
        n = len(self._idx_to_char)
        key_len = len(self._key_indices)
        key_pos = 0

        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                # ключ не двигаем на неизвестных символах
                self._emit_unknown(result, ch)
                continue
            shift = self._key_indices[key_pos % key_len]
            new_ch = self._idx_to_char[(idx + sign * shift) % n]
            result.append(self._restore_case(ch, new_ch))
            key_pos += 1

        return self._finish("".join(result))

    # ---------- публичные ----------

    def code(self) -> str:
        return self._convert(+1)

    def encode(self) -> str:
        return self._convert(-1)


# ============================================================
#   Atbash
# ============================================================

class Atbash(_OperIsCode):
    """Шифр Атбаш (инволюция: code == encode)."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        self._require_str_letters()

        n = len(self._idx_to_char)
        if n < 2:
            raise exs.ActionError(
                f"Алфавит для шифра Атбаш слишком короткий (длина {n})"
            )

    def _convert(self) -> str:
        self._reset_output()
        result: list[str] = []
        n = len(self._idx_to_char)
        for ch in self.inp:
            idx = self._find_index(ch)
            if idx is None:
                self._emit_unknown(result, ch)
                continue
            new_ch = self._idx_to_char[n - 1 - idx]
            result.append(self._restore_case(ch, new_ch))
        return self._finish("".join(result))

    # ---------- публичные ----------

    def code(self) -> str:
        return self._convert()

    def encode(self) -> str:
        return self._convert()


# ============================================================
#   Playfair
# ============================================================

class Playfair(_OperIsCode):
    """Биграммный шифр Плейфера."""

    def __init__(
        self,
        alphabet: str,
        inp: str,
        key: str,
        enc: str = "utf-8",
        policy: UnknownPolicy | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(alphabet, inp, enc, policy=policy)
        self._require_str_letters()
        meta = self.alphabet.get("meta") or {}

        # размер таблицы
        try:
            self.rows, self.cols = int(meta["rows"]), int(meta["cols"])
        except (KeyError, TypeError, ValueError):
            raise exs.InvalidAlphabetError(
                self.alphabet_path,
                ["meta.rows", "meta.cols (целые числа)"],
            )
        if self.rows < 1 or self.cols < 1:
            raise exs.ActionError(
                f"Некорректные размеры таблицы: {self.rows}x{self.cols}"
            )

        self._filler = self._read_filler(meta)
        self._aliases = self._read_aliases(meta)

        # Playfair работает в верхнем регистре
        letters = self.alphabet["letters"]
        self._char_to_idx = {ch.upper(): i for i, ch in enumerate(letters)}
        self._idx_to_char = [ch.upper() for ch in letters]

        n_cells = sum(1 for ch in self._idx_to_char if ch not in self._aliases)
        if self.rows * self.cols != n_cells:
            raise exs.ActionError(
                f"Размер таблицы {self.rows}x{self.cols} = {self.rows * self.cols} "
                f"не совпадает с числом уникальных ячеек алфавита "
                f"({n_cells} после применения aliases; "
                f"в letters {len(self._idx_to_char)})"
            )

        if not key:
            raise exs.ActionError("Ключ шифра Плейфера не может быть пустым")

        self.key = key
        self._build_table(key)
        self._norm = self._normalize(self.inp)

    # ---------- мета ----------

    def _check_unknown_chars_code(self) -> list[str]:
        """
        Символы, которые Playfair не сможет обработать.

        Отличие от базовой проверки: символ, являющийся алиасом
        (например, 'J' -> 'I' или 'ё' -> 'е'), считается известным —
        _normalize всё равно заменит его до шифрования.
        """
        known = set(self._char_to_idx) | set(self._aliases)
        unknown: list[str] = []
        seen: set[str] = set()
        for ch in self.inp:
            up = ch.upper()
            if up in seen:
                continue
            seen.add(up)
            if up not in known:
                unknown.append(ch)
        return unknown

    def _read_filler(self, meta: dict) -> str:
        filler = meta.get("filler", "X")
        if not isinstance(filler, str) or len(filler) != 1:
            raise exs.ActionError(
                f"meta.filler должен быть одним символом, получено: {filler!r}"
            )
        if filler.upper() not in self.alphabet["letters"].upper():
            raise exs.ActionError(
                f"Символ-заполнитель {filler!r} отсутствует в алфавите"
            )
        return filler.upper()

    def _read_aliases(self, meta: dict) -> dict[str, str]:
        """Прочитать и провалидировать meta.aliases; защита от цепочек и циклов."""
        aliases = meta.get("aliases") or {}
        if not isinstance(aliases, dict):
            raise exs.InvalidAlphabetError(
                self.alphabet_path, ["meta.aliases (объект)"]
            )

        letters_upper = self.alphabet["letters"].upper()
        result: dict[str, str] = {}

        for src, dst in aliases.items():
            if not (isinstance(src, str) and len(src) == 1):
                raise exs.ActionError(
                    f"meta.aliases: ключ должен быть одним символом: {src!r}"
                )
            if not (isinstance(dst, str) and len(dst) == 1):
                raise exs.ActionError(
                    f"meta.aliases: значение для {src!r} должно быть "
                    f"одним символом: {dst!r}"
                )
            src_u, dst_u = src.upper(), dst.upper()
            if dst_u not in letters_upper:
                raise exs.ActionError(
                    f"meta.aliases: целевой символ {dst!r} отсутствует в алфавите"
                )
            if dst_u in result:
                raise exs.ActionError(
                    f"meta.aliases: целевой символ {dst!r} сам является "
                    f"источником замены"
                )
            if src_u in result:
                raise exs.ActionError(f"meta.aliases: дублирующийся ключ {src!r}")
            result[src_u] = dst_u

        # защита от циклов A->B->A
        for src in result:
            seen, cur = {src}, result[src]
            while cur in result:
                if cur in seen:
                    raise exs.ActionError(
                        f"meta.aliases: циклическая замена вокруг {src!r}"
                    )
                seen.add(cur)
                cur = result[cur]
        return result

    # ---------- таблица ----------

    def _build_table(self, key: str) -> None:
        seen: set[str] = set()
        ordered: list[str] = []

        # сначала уникальные символы ключа (с учётом aliases)
        for ch in key.upper():
            while ch in self._aliases:
                ch = self._aliases[ch]
            if ch in self._char_to_idx and ch not in seen:
                seen.add(ch)
                ordered.append(ch)

        # затем оставшиеся символы алфавита
        for ch in self._idx_to_char:
            if ch not in self._aliases and ch not in seen:
                seen.add(ch)
                ordered.append(ch)

        expected = self.rows * self.cols
        if len(ordered) != expected:
            raise exs.ActionError(
                f"Не удалось заполнить таблицу {self.rows}x{self.cols}: "
                f"получено {len(ordered)} (ожидалось {expected})"
            )

        self._table: list[list[str]] = [
            ordered[r * self.cols : (r + 1) * self.cols]
            for r in range(self.rows)
        ]
        self._pos: dict[str, tuple[int, int]] = {
            self._table[r][c]: (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
        }

    # ---------- нормализация ----------

    def _normalize(self, text: str) -> str:
        """Привести вход к алфавиту Плейфера с учётом aliases и политики."""
        result: list[str] = []
        for ch in text.upper():
            while ch in self._aliases:
                ch = self._aliases[ch]
            if ch in self._char_to_idx:
                result.append(ch)
                continue

            repl = self._resolve_unknown(ch, partial_out="".join(result))
            if not repl:
                continue

            kept = 0
            for rc in repl.upper():
                while rc in self._aliases:
                    rc = self._aliases[rc]
                if rc in self._char_to_idx:
                    result.append(rc)
                    kept += 1
            if not kept:
                raise exs.ActionError(
                    f"Замена {repl!r} для {ch!r} не содержит "
                    f"символов алфавита Плейфера"
                )
        return "".join(result)

    # ---------- биграммы ----------

    def _split_bigrams(self, text: str) -> list[tuple[str, str]]:
        """Разбить текст на биграммы, вставляя filler при повторе и в конце."""
        bigrams: list[tuple[str, str]] = []
        i, n = 0, len(text)
        while i < n:
            a = text[i]
            if i + 1 < n:
                b = text[i + 1]
                if a == b:
                    if a == self._filler:
                        raise exs.ActionError(
                            f"Две подряд {a!r} совпадают с filler — "
                            f"выберите другой filler"
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

    def _transform_bigram(self, a: str, b: str, sign: int) -> tuple[str, str]:
        ra, ca = self._pos[a]
        rb, cb = self._pos[b]
        if ra == rb:
            return (
                self._table[ra][(ca + sign) % self.cols],
                self._table[rb][(cb + sign) % self.cols],
            )
        if ca == cb:
            return (
                self._table[(ra + sign) % self.rows][ca],
                self._table[(rb + sign) % self.rows][cb],
            )
        return self._table[ra][cb], self._table[rb][ca]

    # ---------- публичные ----------

    def _run(self, sign: int) -> str:
        self._reset_output()
        result: list[str] = []
        for a, b in self._split_bigrams(self._norm):
            na, nb = self._transform_bigram(a, b, sign)
            result.append(na)
            result.append(nb)
        return self._finish("".join(result))

    def code(self) -> str:
        return self._run(+1)

    def encode(self) -> str:
        return self._run(-1)