# ============================================================
#   ИМПОРТЫ
# ============================================================

import json, math, os, struct, sys, wave
from functools import partial
from pathlib import Path
from shutil import copy2

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QFileDialog, QMessageBox,
    QLabel, QInputDialog, QLineEdit,
)

from Paths import update_alphabets, alphabet_file, data_path

from ConverterWidgets import (
    Ui_MainWindow, ActionWidget, OperationForm, BrailleWindow,
    SettingsDialog, ImportAlphabetDialog, CipherAlphaDialog,
    NumeralAlphabetDialog, MorseAlphabetDialog, BinaryAlphabetDialog,
    BrailleAlphabetDialog,
    get_palette, build_app_palette, build_app_qss, apply_theme,
    DEFAULT_SETTINGS, SETTINGS,
)
from Actions import (
    AlphabetAction, Morse, NumberSystem, Braille, Bytes,
    Caesar, A1Z26, Vigenere, Atbash, Playfair, Reverse,
    ColumnarTransposition,
)
from Exceptions import ActionError, UnknownSymbolPolicyError
from Settings import (
    UnknownPolicy, POLICY_IGNORE, POLICY_REPLACE, POLICY_WARN,
    load_settings,
)


# ============================================================
#   MainWindow
# ============================================================

class MainWindow(QMainWindow, Ui_MainWindow):
    """Главное окно приложения."""

    # Классы шифров по индексу operCombo — чтобы не плодить match-case
    CIPHERS: tuple[type, ...] = (
        Caesar, Vigenere, A1Z26, Atbash, Playfair, Reverse,
        ColumnarTransposition,
    )

    def __init__(self) -> None:
        super().__init__()

        self.file_name: str = ""
        self._morse_text: str = ""
        self._morse_ready: bool = False
        self._player_used: bool = False
        self.braille_window: BrailleWindow | None = None

        self.setupUi(self)

        # Версия справа в статусбаре
        self.versionLabel = QLabel(f"v{SETTINGS['version']}")
        self.versionLabel.setStyleSheet("padding-right: 8px;")
        self.statusbar.addPermanentWidget(self.versionLabel)

        self.connect_file_menu()
        self.connect_tools_menu()

        self.addActionButton.clicked.connect(self.add_action)
        self.executeButton.clicked.connect(self.execute)

        QApplication.styleHints().colorSchemeChanged.connect(
            self._on_color_scheme_changed
        )

        # Базовые форматы; аудио добавляются в execute(), если в цепочке
        # есть Морзе.
        self._base_formats: list[str] = ["Text Files (*.txt)", "All Files (*)"]
        self._audio_formats: list[str] = ["MP3 Files (*.mp3)", "WAV Files (*.wav)"]
        self.saveFormats: list[str] = list(self._base_formats)

    # --------------------------------------------------------
    #   Список действий
    # --------------------------------------------------------

    def add_action(self) -> None:
        w = ActionWidget()
        w.removed.connect(self._on_action_removed)
        w.move_up.connect(self._move_action_up)
        w.move_down.connect(self._move_action_down)

        # stretch — последний элемент, вставляем перед ним
        self.actionsLayout.insertWidget(self.actionsLayout.count() - 1, w)
        self.refresh_action_numbers()

    def _on_action_removed(self, widget: ActionWidget) -> None:
        self.actionsLayout.removeWidget(widget)
        self.refresh_action_numbers()

    def _move_action_up(self, widget: ActionWidget) -> None:
        cards = self._cards()
        idx = cards.index(widget)
        if idx > 0:
            self._swap_cards(cards, idx, idx - 1)

    def _move_action_down(self, widget: ActionWidget) -> None:
        cards = self._cards()
        idx = cards.index(widget)
        if 0 <= idx < len(cards) - 1:
            self._swap_cards(cards, idx, idx + 1)

    def refresh_action_numbers(self) -> None:
        cards = self._cards()
        last = len(cards) - 1
        for n, w in enumerate(cards, start=1):
            w.set_number(n)
            w.set_move_buttons_enabled(can_up=(n > 1), can_down=(n <= last))

    def _cards(self) -> list[ActionWidget]:
        result: list[ActionWidget] = []
        for i in range(self.actionsLayout.count()):
            w = self.actionsLayout.itemAt(i).widget()
            if isinstance(w, ActionWidget):
                result.append(w)
        return result

    def _swap_cards(
        self, cards: list[ActionWidget], i: int, j: int
    ) -> None:
        cards[i], cards[j] = cards[j], cards[i]
        for w in cards:
            self.actionsLayout.removeWidget(w)
        for w in cards:
            self.actionsLayout.insertWidget(self.actionsLayout.count() - 1, w)
        self.refresh_action_numbers()

    # --------------------------------------------------------
    #   Файлы
    # --------------------------------------------------------

    def _reset_morse_state(self) -> None:
        self._morse_text = ""
        self._morse_ready = False
        self.morsePlayerAction.setEnabled(False)

    def open_file(self) -> None:
        self._reset_morse_state()
        self._player_used = False

        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть текст", "", "Text Files (*.txt);;All Files (*)"
        )
        if not file_name:
            return
        with open(file_name, "r", encoding="utf-8") as f:
            self.inpText.setPlainText(f.read())
        self.file_name = file_name

    def save_file(self, saveAs: bool = False) -> None:
        if not self.file_name or saveAs:
            file_name, selected = QFileDialog.getSaveFileName(
                self, "Сохранить текст", "", ";;".join(self.saveFormats)
            )
        else:
            file_name = self.file_name
            selected = "Text Files (*.txt)"

        if not file_name:
            return

        text = self.outText.toPlainText()

        # --- текст ---
        if selected in ("Text Files (*.txt)", "All Files (*)"):
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(text)
            self.file_name = file_name
            return

        # --- аудио ---
        if not self._player_used or not self._morse_ready:
            QMessageBox.warning(
                self,
                "Сохранение звука",
                "Звуковой файл ещё не создан. Откройте "
                "«Инструменты → Плеер морзе», чтобы сгенерировать его.",
            )
            return

        src = Path(data_path("temp_morse.wav"))
        if not src.exists():
            QMessageBox.warning(
                self, "Сохранение звука",
                "Файл temp_morse.wav не найден. Откройте плеер морзе ещё раз.",
            )
            return

        dst = Path(file_name)
        if not dst.suffix:
            if "MP3" in selected:
                dst = dst.with_suffix(".mp3")
            elif "WAV" in selected:
                dst = dst.with_suffix(".wav")

        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dst)

    def export_alphabet(self) -> None:
        """Открыть системный файловый менеджер на ./alphabets."""
        folder = data_path("alphabets")
        os.makedirs(folder, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{folder}"')
        else:
            os.system(f'xdg-open "{folder}"')

    def import_alphabet(self) -> None:
        """Импортировать выбранный JSON-алфавит в подпапку по типу."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать алфавит",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_name:
            return

        dialog = ImportAlphabetDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        subdir = dialog.result_subdir()
        target_dir = Path(data_path(f"alphabets/{subdir}"))
        target_dir.mkdir(parents=True, exist_ok=True)

        dst = target_dir / Path(file_name).name

        # Защита от случайной перезаписи
        if dst.exists():
            reply = QMessageBox.question(
                self,
                "Файл уже существует",
                f"Файл «{dst.name}» уже есть в папке «{subdir}».\n"
                "Перезаписать?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            copy2(file_name, dst)
        except OSError as e:
            QMessageBox.critical(
                self, "Ошибка импорта", f"Не удалось скопировать файл:\n{e}"
            )
            return

        update_alphabets()
        self._reload_all_alphabets()
        self.statusbar.showMessage(f"Алфавит импортирован: {dst}", 5000)

    # --------------------------------------------------------
    #   Меню и диалоги
    # --------------------------------------------------------

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.statusbar.showMessage("Сохранено")

    def connect_file_menu(self) -> None:
        self.openAction.triggered.connect(self.open_file)
        self.saveAction.triggered.connect(self.save_file)
        self.saveAsAction.triggered.connect(partial(self.save_file, saveAs=True))
        self.settingsAction.triggered.connect(self.open_settings)
        self.exportAlphabetAction.triggered.connect(self.export_alphabet)
        self.importAlphabetAction.triggered.connect(self.import_alphabet)

    def connect_tools_menu(self) -> None:
        self.morsePlayerAction.triggered.connect(self.open_morse_player)
        self.brailleInputAction.triggered.connect(self.open_braille_input)

        for action, cls in (
            (self.makeBrailleAction, BrailleAlphabetDialog),
            (self.makeMorseAction, MorseAlphabetDialog),
            (self.makeNumSysAction, NumeralAlphabetDialog),
            (self.makeCiphersAction, CipherAlphaDialog),
            (self.makeBinaryAction, BinaryAlphabetDialog),
        ):
            action.triggered.connect(
                partial(self.open_alphabet_dialog, cls)
            )

    def open_alphabet_dialog(self, dialog_cls: type) -> None:
        """Открыть диалог создания алфавита и сохранить результат в JSON."""
        dlg = dialog_cls(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.result_data()
        fname = dlg.result_filename()
        if not data or not fname:
            return

        # Ручной путь — используем его, иначе — save_subdir класса.
        full = dlg.result_fullpath()
        if full:
            target = Path(full)
        else:
            subdir = getattr(dialog_cls, "save_subdir", "alphabets")
            target_dir = Path(data_path(subdir))
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / fname

        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(target, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
            return

        update_alphabets()
        self._reload_all_alphabets()
        self.statusbar.showMessage(f"Алфавит сохранён: {target}", 5000)

    def open_braille_input(self) -> None:
        if self.braille_window is None:
            self.braille_window = BrailleWindow(
                target_widget=self.inpText, parent=self
            )
        self.braille_window.show()
        self.braille_window.raise_()
        self.braille_window.activateWindow()

    def _reload_all_alphabets(self) -> None:
        """Перечитать alphabets.json и обновить все карточки действий."""
        for w in self._cards():
            w.reload_alphabets()

    def _on_color_scheme_changed(self, scheme) -> None:
        if SETTINGS.get("theme", DEFAULT_SETTINGS["theme"]) != "Системная":
            return
        apply_theme()

    # --------------------------------------------------------
    #   Генерация WAV
    # --------------------------------------------------------

    def _generate_morse_wav(self) -> None:
        sample_rate = int(SETTINGS.get("morse_sample_rate", 44100))
        freq = float(SETTINGS.get("morse_freq", 800.0))
        wpm = float(SETTINGS.get("morse_wpm", 25)) or 25.0
        unit = 1.2 / wpm

        def tone(duration: float) -> list[float]:
            n = int(sample_rate * duration)
            return [
                0.5 * math.sin(2 * math.pi * freq * i / sample_rate)
                for i in range(n)
            ]

        def silence(duration: float) -> list[float]:
            return [0.0] * int(sample_rate * duration)

        samples: list[float] = []
        first_word = True

        for word in self._morse_text.split("/"):
            word = word.strip()
            if not word:
                continue
            if not first_word:
                samples += silence(unit * 7)
            first_word = False

            for sym_idx, sym in enumerate(word.split()):
                if sym_idx > 0:
                    samples += silence(unit * 3)
                for elem_idx, ch in enumerate(sym):
                    if elem_idx > 0:
                        samples += silence(unit)
                    if ch == ".":
                        samples += tone(unit)
                    elif ch == "-":
                        samples += tone(unit * 3)

        wav_path = data_path("temp_morse.wav")
        with wave.open(wav_path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            frames = b"".join(
                struct.pack(
                    "<h", int(max(-1.0, min(1.0, s)) * 32767)
                )
                for s in samples
            )
            w.writeframes(frames)

        self._morse_ready = True

    def open_morse_player(self) -> None:
        if not self._morse_text:
            return
        if not self._morse_ready:
            self._generate_morse_wav()
        self._player_used = True
        self.player.reload_source()
        self.tBarWidget.show()

    # --------------------------------------------------------
    #   Путь к алфавиту и его имя
    # --------------------------------------------------------

    def _alphabet_path_for(self, f: OperationForm, type_ind: int) -> str:
        match type_ind:
            case 0:
                return alphabet_file("morse", f.alphabetCombo.currentData())
            case 2:
                return alphabet_file("ciphers", f.alphabetCombo.currentData())
            case 3:
                return alphabet_file("braille", f.alphabetCombo.currentData())
            case 4:
                key = f.alphabetCombo.currentData()
                return alphabet_file("binary", key) if key.endswith(".json") else ""
            case _:
                return ""

    @staticmethod
    def _alphabet_display_name(alphabet_path: str) -> str:
        if not alphabet_path:
            return "—"
        try:
            with open(alphabet_path, encoding="utf-8") as fh:
                meta = json.load(fh).get("meta") or {}
            if name := meta.get("name"):
                return str(name)
        except (OSError, ValueError):
            pass
        return Path(alphabet_path).name

    # --------------------------------------------------------
    #   Диалог неизвестных символов
    # --------------------------------------------------------

    def _ask_unknown_policy(
        self, unknown: list[str], alphabet_path: str
    ) -> UnknownPolicy | None:
        """Спросить политику для неизвестных символов. None — отмена."""
        sample = "".join(unknown[:10])
        more = f" и ещё {len(unknown) - 10}" if len(unknown) > 10 else ""
        display = self._alphabet_display_name(alphabet_path)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Неизвестные символы")
        box.setText(
            f"В тексте есть символы, отсутствующие в алфавите "
            f"«{display}»:\n{sample}{more}"
        )
        btn_abort = box.addButton(
            "До первой ошибки", QMessageBox.ButtonRole.AcceptRole
        )
        btn_ignore = box.addButton(
            "Игнорировать", QMessageBox.ButtonRole.ActionRole
        )
        btn_replace = box.addButton(
            "Заменить", QMessageBox.ButtonRole.ActionRole
        )
        btn_cancel = box.addButton(
            "Отмена", QMessageBox.ButtonRole.RejectRole
        )
        box.exec()

        clicked = box.clickedButton()
        if clicked is btn_cancel:
            return None
        if clicked is btn_ignore:
            return UnknownPolicy(mode=POLICY_IGNORE)
        if clicked is btn_replace:
            text, ok = QInputDialog.getText(
                self,
                "Замена неизвестных символов",
                "На что заменять отсутствующие в алфавите символы?",
                QLineEdit.EchoMode.Normal,
                SETTINGS.get("replacement", "") or "?",
            )
            if not ok:
                return None
            # Пустая строка — осознанная замена на пустоту;
            # для игнора есть отдельная кнопка.
            return UnknownPolicy(mode=POLICY_REPLACE, replacement=text)
        # «До первой ошибки» — оставляем Warn
        return UnknownPolicy(mode=POLICY_WARN)

    # --------------------------------------------------------
    #   Хелперы выполнения цепочки
    # --------------------------------------------------------

    def _probe_unknown(
        self,
        type_ind: int,
        f: OperationForm,
        text: str,
        alphabet_path: str,
        policy: UnknownPolicy,
    ) -> list[str]:
        """Найти неизвестные символы до выполнения (best-effort)."""
        direction = "code" if f.codeRadio.isChecked() else "encode"

        try:
            match type_ind:
                case 0:
                    obj = Morse(alphabet_path, text, policy=policy)
                case 2:
                    idx = f.operCombo.currentIndex()
                    if not (0 <= idx < len(self.CIPHERS)):
                        return []
                    cipher_cls = self.CIPHERS[idx]
                    if cipher_cls is Reverse:
                        return []  # алфавит не нужен
                    obj = cipher_cls(
                        alphabet=alphabet_path,
                        inp=text,
                        shift=f.operSpin.value(),
                        key=f.keyEdit.text(),
                        cols=f.operSpin.value(),
                        policy=policy,
                    )
                case 3:
                    obj = Braille(alphabet_path, text, policy=policy)
                case 4:
                    key = f.alphabetCombo.currentData()
                    enc = (
                        alphabet_file("binary", key)
                        if key.endswith(".json")
                        else key
                    )
                    obj = Bytes(text, enc, policy=policy)
                    obj.set_direction(direction)
                    return obj._check_unknown_chars()
                case _:
                    return []

            if isinstance(obj, AlphabetAction):
                obj.set_direction(direction)

            return obj._check_unknown_chars()
        except UnknownSymbolPolicyError:
            # Это и есть «неизвестный символ» — пусть обработает execute().
            raise
        except ActionError:
            # Иная ошибка конструктора (битый алфавит, неверный ключ)
            # всплывёт в _run_action — не маскируем её под «неизвестный».
            return []

    def _resolve_policy(
        self,
        type_ind: int,
        f: OperationForm,
        text: str,
        base_policy: UnknownPolicy,
        card_policy: UnknownPolicy | None,
    ) -> tuple[UnknownPolicy, UnknownPolicy | None, bool]:
        """
        Определить политику для карточки.

        Возвращает (effective_policy, card_policy, cancelled).
        """
        if card_policy is not None:
            return card_policy, card_policy, False

        if base_policy.mode != POLICY_WARN or type_ind not in (0, 2, 3, 4):
            return base_policy, card_policy, False

        alphabet_path = self._alphabet_path_for(f, type_ind)
        try:
            unknown = self._probe_unknown(
                type_ind, f, text, alphabet_path, base_policy
            )
        except UnknownSymbolPolicyError as e:
            chosen = self._ask_unknown_policy([e.symbol], alphabet_path)
            if chosen is None:
                return base_policy, card_policy, True
            return chosen, chosen, False

        if not unknown:
            return base_policy, card_policy, False

        chosen = self._ask_unknown_policy(unknown, alphabet_path)
        if chosen is None:
            return base_policy, card_policy, True
        return chosen, chosen, False

    def _handle_unknown_policy_error(
        self,
        exc: UnknownSymbolPolicyError,
        type_ind: int,
        f: OperationForm,
        base_policy: UnknownPolicy,
        card_policy: UnknownPolicy | None,
    ) -> tuple[UnknownPolicy, UnknownPolicy | None, bool, bool]:
        """
        Реакция на UnknownSymbolPolicyError.

        Возвращает (base_policy, card_policy, retry, cancelled).
        """
        if card_policy is not None:
            # Политика для карточки уже выбрана — второй раз не спрашиваем.
            self._show_action_error(exc)
            return base_policy, card_policy, False, True

        alphabet_path = self._alphabet_path_for(f, type_ind)
        chosen = self._ask_unknown_policy([exc.symbol], alphabet_path)
        if chosen is None:
            return base_policy, card_policy, False, True
        if chosen.mode == POLICY_WARN:
            self._show_action_error(exc)
            return base_policy, card_policy, False, True
        return chosen, chosen, True, False

    def _show_partial(self, partial: str, message: str) -> str:
        """Записать в outText partial + сообщение; вернуть итоговый текст."""
        text = f"{partial}\n[{message}]" if partial else message
        self.outText.setPlainText(text)
        return text

    # --------------------------------------------------------
    #   Показ ошибок
    # --------------------------------------------------------

    _ICONS = {
        "critical": QMessageBox.Icon.Critical,
        "warning": QMessageBox.Icon.Warning,
        "info": QMessageBox.Icon.Information,
    }

    def _show_action_error(self, exc: ActionError) -> None:
        """Единая точка показа ActionError: partial_out + диалог."""
        title, message, icon = exc.dialog_spec()
        partial = getattr(exc, "partial_out", "")
        self._show_partial(partial, message)

        box = QMessageBox(self)
        box.setIcon(self._ICONS.get(icon, QMessageBox.Icon.Critical))
        box.setWindowTitle(title)
        box.setText(message)
        box.exec()

    # --------------------------------------------------------
    #   Выполнение одного действия
    # --------------------------------------------------------

    def _run_action(
        self,
        type_ind: int,
        f: OperationForm,
        text: str,
        effective_policy: UnknownPolicy,
    ) -> str:
        """Выполнить одно действие над текстом (исключения — наружу)."""
        code_radio = f.codeRadio.isChecked()

        match type_ind:
            case 0:  # Морзе
                morse = Morse(
                    alphabet_file("morse", f.alphabetCombo.currentData()),
                    text,
                    policy=effective_policy,
                )
                if code_radio:
                    out = morse.code()
                    self._morse_text = out
                    self._morse_ready = False
                    return out
                self._morse_text = ""
                self._morse_ready = False
                return morse.encode()

            case 1:  # Системы счисления
                return NumberSystem(
                    alphabet_file(
                        "number_systems", f.alphabetCombo.currentData()
                    ),
                    f.inpSpin.value(),
                    f.operSpin.value(),
                    text,
                ).oper()

            case 2:  # Шифры
                idx = f.operCombo.currentIndex()
                if not (0 <= idx < len(self.CIPHERS)):
                    raise ActionError(f"Неверный индекс шифра: {idx}")
                cipher_cls = self.CIPHERS[idx]

                if cipher_cls is Reverse:
                    cipher = Reverse(inp=text, policy=effective_policy)
                else:
                    cipher = cipher_cls(
                        alphabet=alphabet_file(
                            "ciphers", f.alphabetCombo.currentData()
                        ),
                        inp=text,
                        shift=f.operSpin.value(),
                        key=f.keyEdit.text(),
                        cols=f.operSpin.value(),
                        policy=effective_policy,
                    )
                return cipher.code() if code_radio else cipher.encode()

            case 3:  # Брайль
                braille = Braille(
                    alphabet_file("braille", f.alphabetCombo.currentData()),
                    text,
                    policy=effective_policy,
                )
                return braille.code() if code_radio else braille.encode()

            case 4:  # Бинарный код
                key = f.alphabetCombo.currentData()
                enc = (
                    alphabet_file("binary", key)
                    if key.endswith(".json")
                    else key
                )
                binary = Bytes(text, enc, policy=effective_policy)
                return binary.code() if code_radio else binary.encode()

        raise ActionError(f"Неизвестный тип операции: {type_ind}")

    # --------------------------------------------------------
    #   Выполнение цепочки
    # --------------------------------------------------------

    def execute(self) -> None:
        self.saveAction.setEnabled(True)
        self.saveAsAction.setEnabled(True)

        text = self.inpText.toPlainText()
        self._reset_morse_state()

        base_policy = UnknownPolicy.current()
        has_morse = False
        error_shown = False

        for widget in self._cards():
            f = widget.findChild(OperationForm, "mFLayout")
            if f is None:
                continue

            type_ind = f.typeCombo.currentIndex()
            card_policy: UnknownPolicy | None = None

            while True:
                effective_policy, card_policy, cancelled = self._resolve_policy(
                    type_ind, f, text, base_policy, card_policy
                )
                if cancelled:
                    return

                try:
                    text = self._run_action(
                        type_ind, f, text, effective_policy
                    )
                    if type_ind == 0:
                        has_morse = True
                except UnknownSymbolPolicyError as e:
                    if card_policy is not None:
                        self._show_action_error(e)
                        return

                    base_policy, card_policy, retry, cancelled = (
                        self._handle_unknown_policy_error(
                            e, type_ind, f, base_policy, card_policy
                        )
                    )
                    if cancelled:
                        return
                    if retry:
                        continue
                except ActionError as e:
                    self._show_action_error(e)
                    error_shown = True

                break

        self.outText.setPlainText(text)

        self.saveFormats = list(self._base_formats)
        if has_morse:
            self.saveFormats = self._audio_formats + self.saveFormats

        if error_shown:
            self.statusbar.showMessage("Выполнение завершено с ошибками")
        else:
            self.statusbar.showMessage("Готово")

        self.morsePlayerAction.setEnabled(bool(self._morse_text))
        if self._morse_text:
            self._morse_ready = False
            self._player_used = False
            self.tBarWidget.hide()


# ============================================================
#   Точка входа
# ============================================================

if __name__ == "__main__":
    update_alphabets()
    app = QApplication(sys.argv)
    app.setStyle("fusion")

    load_settings()

    app.setPalette(build_app_palette(get_palette()))
    app.setStyleSheet(build_app_qss(get_palette()))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())