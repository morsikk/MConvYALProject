# ============================================================
#   ИМПОРТЫ
# ============================================================

import sys
import math
import struct
import wave
from functools import partial
from pathlib import Path
from shutil import copy2

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QFileDialog,
    QMessageBox,
    QLabel,
    QInputDialog,
    QLineEdit
)

from ConverterWidgets import (
    Ui_MainWindow,
    ActionWidget,
    OperationForm,
    BrailleDialog,
    SettingsDialog,
    get_palette,
    build_app_palette,
    build_app_qss,
    resource_path,
    data_path,
    apply_theme,
    DEFAULT_SETTINGS,
    SETTINGS
)
from Actions import (
    Morse,
    NumberSystem,
    Braille,
    Bytes,
    Caesar,
    A1Z26,
    Vigenere,
    Atbash,
    Playfair,
)
from Exceptions import (  # noqa: F401
    ActionError,
    CardCancelled,
    UnknownSymbolError,
    MissingSpaceSymbolError,
    InvalidAlphabetError,
    MissingSpacerError,
)

from Settings import (
    SETTINGS,
    UnknownPolicy,
    UnknownSymbolPolicyError,
    POLICY_IGNORE,
    POLICY_REPLACE,
    POLICY_WARN,
    load_settings
)


# ============================================================
#   MainWindow
# ============================================================


class MainWindow(QMainWindow, Ui_MainWindow):
    """Главное окно приложения."""

    # Классы действий по индексу typeCombo — чтобы не плодить match-case
    CIPHERS = (Caesar, Vigenere, A1Z26, Atbash, Playfair)

    def __init__(self) -> None:
        super().__init__()

        self.file_name = ""
        self._morse_text = ""
        self._morse_ready = False
        self._player_used = False

        self.setupUi(self)

        # --- Версия справа в статус-баре ---
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

        # Базовые форматы; аудио добавляются в execute(), если в цепочке есть Морзе
        self._base_formats = ["Text Files (*.txt)", "All Files (*)"]
        self._audio_formats = ["MP3 Files (*.mp3)", "WAV Files (*.wav)"]
        self.saveFormats = list(self._base_formats)

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
        if idx <= 0:
            return
        self._swap_cards(cards, idx, idx - 1)

    def _move_action_down(self, widget: ActionWidget) -> None:
        cards = self._cards()
        idx = cards.index(widget)
        if idx < 0 or idx >= len(cards) - 1:
            return
        self._swap_cards(cards, idx, idx + 1)

    def refresh_action_numbers(self) -> None:
        cards = self._cards()
        last = len(cards) - 1
        for n, w in enumerate(cards, start=1):
            w.set_number(n)
            w.set_move_buttons_enabled(can_up=(n > 1), can_down=(n <= last))

    def _cards(self) -> list[ActionWidget]:
        result = []
        for i in range(self.actionsLayout.count()):
            w = self.actionsLayout.itemAt(i).widget()
            if isinstance(w, ActionWidget):
                result.append(w)
        return result

    def _swap_cards(self, cards: list[ActionWidget], i: int, j: int) -> None:
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
            # явно, без магии индексов
            if "MP3" in selected:
                dst = dst.with_suffix(".mp3")
            elif "WAV" in selected:
                dst = dst.with_suffix(".wav")

        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dst)

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

    def connect_tools_menu(self) -> None:
        self.morsePlayerAction.triggered.connect(self.open_morse_player)
        self.brailleInputAction.triggered.connect(self.open_braille_input)

    def open_braille_input(self) -> None:
        dialog = BrailleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            braille_text = dialog.brailleOut.toPlainText()
            if braille_text:
                current = self.inpText.toPlainText()
                self.inpText.setPlainText(current + braille_text)

    def _on_color_scheme_changed(self, scheme) -> None:
        if SETTINGS.get("theme", DEFAULT_SETTINGS["theme"]) != "Системная":
            return
        apply_theme()
        app = QApplication.instance()
        p = get_palette()
        app.setPalette(build_app_palette(p))
        app.setStyleSheet(build_app_qss(p))

    # --------------------------------------------------------
    #   Генерация WAV
    # --------------------------------------------------------

    def _generate_morse_wav(self) -> None:
        SAMPLE_RATE = 44100
        FREQ = 800.0
        WPM = 25
        UNIT = 1.2 / WPM

        def tone(duration: float) -> list[float]:
            n = int(SAMPLE_RATE * duration)
            return [0.5 * math.sin(2 * math.pi * FREQ * i / SAMPLE_RATE) for i in range(n)]

        def silence(duration: float) -> list[float]:
            return [0.0] * int(SAMPLE_RATE * duration)

        # Разбиваем на «символы» по пробелам, слова — по '/'
        # Внутри символа: . = 1 unit, - = 3 unit, между элементами — 1 unit
        # Между символами — 3 unit, между словами — 7 unit
        samples: list[float] = []
        first_word = True

        for word in self._morse_text.split("/"):
            word = word.strip()
            if not word:
                continue
            if not first_word:
                samples += silence(UNIT * 7)
            first_word = False

            for sym_idx, sym in enumerate(word.split()):
                if sym_idx > 0:
                    samples += silence(UNIT * 3)  # между символами
                for elem_idx, ch in enumerate(sym):
                    if elem_idx > 0:
                        samples += silence(UNIT * 1)  # между элементами
                    if ch == ".":
                        samples += tone(UNIT)
                    elif ch == "-":
                        samples += tone(UNIT * 3)
                    # прочие символы игнорируем

        wav_path = data_path("temp_morse.wav")
        with wave.open(wav_path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            frames = b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples
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

    def _alphabet_path_for(self, f: OperationForm, type_ind: int) -> str:
        """Путь к JSON-алфавиту для текущей карточки (для сообщений)."""
        match type_ind:
            case 0:
                return resource_path(
                    f"alphabets/morse/{f.alphabetCombo.currentData()}.json"
                )
            case 2:
                return resource_path(
                    f"alphabets/ciphers/{f.alphabetCombo.currentData()}.json"
                )
            case 3:
                return resource_path(
                    f"alphabets/braille/{f.alphabetCombo.currentData()}.json"
                )
            case _:
                return ""


    def _probe_unknown(
        self,
        type_ind: int,
        f: OperationForm,
        text: str,
        alphabet_path: str,
        policy: UnknownPolicy,
    ) -> list[str]:
        try:
            match type_ind:
                case 0:
                    obj = Morse(alphabet_path, text, policy=policy)
                case 2:
                    params = dict(
                        alphabet=alphabet_path,
                        inp=text,
                        shift=f.operSpin.value(),
                        key=f.keyEdit.text(),
                        policy=policy,
                    )
                    idx = f.operCombo.currentIndex()
                    if not (0 <= idx < len(self.CIPHERS)):
                        return []
                    obj = self.CIPHERS[idx](**params)
                case 3:
                    obj = Braille(alphabet_path, text, policy=policy)
                case _:
                    return []
            return obj._check_unknown_chars()
        except Exception as e:
            # Конструктор упал — не скрываем это от пользователя.
            # Возвращаем непустой маркер, чтобы execute() показал диалог
            # и пользователь сам решил: игнор / замена / отмена.
            QMessageBox.warning(
                self,
                "Не удалось проверить алфавит",
                f"Проверка неизвестных символов не удалась:\n{e}\n\n"
                f"Будет использована текущая политика «{policy.mode}».",
            )
            return []


    def _ask_unknown_policy(
        self,
        unknown: list[str],
        alphabet_path: str,
    ) -> UnknownPolicy | None:
        sample = "".join(unknown[:10])
        more = f" и ещё {len(unknown) - 10}" if len(unknown) > 10 else ""

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Неизвестные символы")
        box.setText(
            f"В тексте есть символы, отсутствующие в алфавите "
            f"«{alphabet_path}»:\n{sample}{more}"
        )
        btn_abort = box.addButton("До первой ошибки", QMessageBox.ButtonRole.AcceptRole)
        btn_ignore = box.addButton("Игнорировать", QMessageBox.ButtonRole.ActionRole)
        btn_replace = box.addButton("Заменить", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
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
            # Пустая строка — осознанная замена на пустоту.
            # Если пользователь хотел именно игнор — есть кнопка выше.
            return UnknownPolicy(mode=POLICY_REPLACE, replacement=text)
        # «До первой ошибки» — оставляем Warn
        return UnknownPolicy(mode=POLICY_WARN)

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
            code_radio = f.codeRadio.isChecked()

            while True:   # ← цикл для повтора карточки при UnknownSymbolPolicyError
                # ---- предварительная проверка (только в режиме WARN) ----
                if base_policy.mode == POLICY_WARN and type_ind in (0, 2, 3):
                    alphabet_path = self._alphabet_path_for(f, type_ind)
                    unknown = self._probe_unknown(type_ind, f, text, alphabet_path, base_policy)
                    if unknown:
                        chosen = self._ask_unknown_policy(unknown, alphabet_path)
                        if chosen is None:
                            return                      # отмена всей операции
                        effective_policy = chosen
                    else:
                        effective_policy = base_policy
                else:
                    effective_policy = base_policy

                retry = False

                match type_ind:
                    case 0:  # Морзе
                        has_morse = True
                        try:
                            morse = Morse(
                                resource_path(
                                    f"alphabets/morse/{f.alphabetCombo.currentData()}.json"
                                ),
                                text,
                                policy=effective_policy,
                            )
                            if code_radio:
                                text = morse.code()
                                self._morse_text = text
                                self._morse_ready = False
                            else:
                                text = morse.encode()
                                self._morse_text = ""
                                self._morse_ready = False
                        except UnknownSymbolPolicyError as e:
                            alphabet_path = self._alphabet_path_for(f, type_ind)
                            chosen = self._ask_unknown_policy([e.symbol], alphabet_path)
                            if chosen is None:
                                return
                            if chosen.mode == POLICY_WARN:
                                QMessageBox.critical(self, "Ошибка", e.message)
                                return
                            base_policy = chosen          # запомнить на будущее
                            retry = True
                        except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                            text = f"{e.partial_out}\n[{e.message}]"
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True
                        except (InvalidAlphabetError, MissingSpacerError) as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка алфавита", e.message)
                            error_shown = True
                        except ActionError as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True

                    case 1:  # Системы счисления
                        try:
                            conv = NumberSystem(
                                resource_path(
                                    f"alphabets/number_systems/"
                                    f"{f.alphabetCombo.currentData()}.json"
                                ),
                                f.inpSpin.value(),
                                f.operSpin.value(),
                                text,
                            )
                            text = conv.oper()
                        except ActionError as e:
                            partial_out = getattr(e, "partial_out", "")
                            self.outText.setPlainText(
                                f"{partial_out}\n[{e.message}]" if partial_out else e.message
                            )
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True

                    case 2:  # Шифры
                        try:
                            params = {
                                "alphabet": resource_path(
                                    f"alphabets/ciphers/"
                                    f"{f.alphabetCombo.currentData()}.json"
                                ),
                                "inp": text,
                                "shift": f.operSpin.value(),
                                "key": f.keyEdit.text(),
                                "policy": effective_policy,
                            }
                            idx = f.operCombo.currentIndex()
                            if not (0 <= idx < len(self.CIPHERS)):
                                raise ActionError(f"Неверный индекс шифра: {idx}")
                            cipher = self.CIPHERS[idx](**params)
                            text = cipher.code() if code_radio else cipher.encode()
                        except UnknownSymbolPolicyError as e:
                            alphabet_path = self._alphabet_path_for(f, type_ind)
                            chosen = self._ask_unknown_policy([e.symbol], alphabet_path)
                            if chosen is None:
                                return
                            if chosen.mode == POLICY_WARN:
                                QMessageBox.critical(self, "Ошибка", e.message)
                                return
                            base_policy = chosen
                            retry = True
                        except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                            text = f"{e.partial_out}\n[{e.message}]"
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True
                        except (InvalidAlphabetError, MissingSpacerError) as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка алфавита", e.message)
                            error_shown = True
                        except ActionError as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True

                    case 3:  # Брайль
                        try:
                            braille = Braille(
                                resource_path(
                                    f"alphabets/braille/{f.alphabetCombo.currentData()}.json"
                                ),
                                text,
                                policy=effective_policy,
                            )
                            text = braille.code() if code_radio else braille.encode()
                        except UnknownSymbolPolicyError as e:
                            alphabet_path = self._alphabet_path_for(f, type_ind)
                            chosen = self._ask_unknown_policy([e.symbol], alphabet_path)
                            if chosen is None:
                                return
                            if chosen.mode == POLICY_WARN:
                                QMessageBox.critical(self, "Ошибка", e.message)
                                return
                            base_policy = chosen
                            retry = True
                        except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                            self.outText.setPlainText(f"{e.partial_out}\n[{e.message}]")
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True
                        except (InvalidAlphabetError, MissingSpacerError) as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка алфавита", e.message)
                            error_shown = True
                        except ActionError as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True

                    case 4:  # Бинарный код
                        try:
                            binary = Bytes(text, f.alphabetCombo.currentData())
                            text = binary.code() if code_radio else binary.encode()
                        except ActionError as e:
                            self.outText.setPlainText(e.message)
                            QMessageBox.critical(self, "Ошибка", e.message)
                            error_shown = True

                if not retry:
                    break
                # retry=True — повторяем ту же карточку с новой base_policy

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
    app = QApplication(sys.argv)
    app.setStyle("fusion")

    load_settings()
    
    app.setStyleSheet(build_app_qss(get_palette()))
    app.setPalette(build_app_palette(get_palette()))
    app.setStyleSheet(build_app_qss(get_palette()))


    window = MainWindow()
    window.show()

    sys.exit(app.exec())