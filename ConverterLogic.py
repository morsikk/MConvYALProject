# ============================================================
#   ИМПОРТЫ
# ============================================================

import sys
from functools import partial

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QDialog,
    QMessageBox,
)

import actions  # модуль с реализацией самих преобразований (Morse и т.д.)

from ConverterWidgets import (
    Ui_MainWindow,        # строитель интерфейса главного окна
    SettingsDialog,       # диалог настроек
    ActionWidget,         # карточка одного действия в списке
    OperationForm,        # форма параметров операции
    get_palette,          # получить палитру текущей темы
    build_app_qss,        # собрать QSS из палитры
    build_app_palette,    # собрать QPalette из палитры
)

from exceptions import (
    ActionError,
    UnknownSymbolError,
    InvalidAlphabetError,
    MissingSpacerError,
    MissingSpaceSymbolError,
)


# ============================================================
#   MainWindow — главное окно приложения
# ============================================================

class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Главное окно приложения.

    Наследует:
        QMainWindow — базовое окно Qt (меню, статусбар, центральный виджет);
        Ui_MainWindow — класс-строитель интерфейса из ConverterWidgets.

    Ответственность:
        - связать кнопки и пункты меню с обработчиками;
        - управлять списком действий (добавление, удаление, нумерация);
        - открывать/сохранять файлы;
        - открывать диалог настроек;
        - реагировать на смену системной темы;
        - запускать выполнение цепочки действий (execute).
    """

    def __init__(self) -> None:
        """
        Конструктор окна.

        Порядок действий:
            1. Инициализация QMainWindow;
            2. Сброс имени файла (документ ещё не связан с файлом);
            3. Построение интерфейса через setupUi (из Ui_MainWindow);
            4. Подключение меню «Файл»;
            5. Подключение кнопок «Добавить действие» и «Выполнить»;
            6. Подписка на изменение системной цветовой схемы.
        """
        super().__init__()

        # Имя текущего открытого/сохранённого файла ("" — не связан)
        self.file_name = ""

        # Наполняем окно виджетами (метод из Ui_MainWindow)
        self.setupUi(self)

        # Связываем пункты меню «Файл» с обработчиками
        self.connect_file_menu()

        # Кнопки панели действий
        self.addActionButton.clicked.connect(self.add_action)
        self.executeButton.clicked.connect(self.execute)

        # Реакция на смену системной темы (light <-> dark)
        QApplication.styleHints().colorSchemeChanged.connect(
            self._on_color_scheme_changed
        )

        self.saveFormats = ['Text Files (*.txt)', 'All Files (*)']

    # --------------------------------------------------------
    #   Управление списком действий
    # --------------------------------------------------------

    def add_action(self) -> None:
        """
        Добавляет новое действие в список.

        Новый ActionWidget вставляется ПЕРЕД последним элементом layout
        (там лежит stretch, добавленный в Ui_MainWindow), поэтому карточки
        всегда идут выше распорки. После вставки нумерация пересчитывается.
        """
        w = ActionWidget()
        w.removed.connect(self._on_action_removed)
        w.move_up.connect(self._move_action_up)
        w.move_down.connect(self._move_action_down) 

        # count() - 1 — позиция stretch; вставляем перед ним
        self.actionsLayout.insertWidget(self.actionsLayout.count() - 1, w)
        self.refresh_action_numbers()

    def _on_action_removed(self, widget: ActionWidget) -> None:
        """
        Обработчик сигнала removed от ActionWidget.

        Аргументы:
            widget: удаляемый виджет действия.

        Убирает виджет из layout и пересчитывает нумерацию оставшихся.
        Сам виджет удаляется внутри ActionWidget.delete() через deleteLater().
        """
        self.actionsLayout.removeWidget(widget)
        self.refresh_action_numbers()

    def _move_action_up(self, widget: ActionWidget) -> None:
        cards = self._cards()
        idx = cards.index(widget)
        if idx <= 0:
            return
        # Меняем местами ссылки в layout: сначала убираем оба, потом вставляем обратно
        self._swap_cards(cards, idx, idx - 1)

    def _move_action_down(self, widget: ActionWidget) -> None:
        cards = self._cards()
        idx = cards.index(widget)
        if idx < 0 or idx >= len(cards) - 1:
            return
        self._swap_cards(cards, idx, idx + 1)

    def refresh_action_numbers(self) -> None:
        """
        Перенумеровывает все ActionWidget в списке: «Действие 1», «Действие 2», ...

        Примечание:
            В layout кроме ActionWidget лежат ещё две кнопки (executeButton,
            addActionButton) и stretch. Поэтому номер = i - 1 (первый
            ActionWidget идёт после executeButton с индексом 1).
        """
        cards = []
        for i in range(self.actionsLayout.count()):
            w = self.actionsLayout.itemAt(i).widget()
            if isinstance(w, ActionWidget):
                cards.append(w)

        last = len(cards) - 1
        for n, w in enumerate(cards, start=1):
            w.set_number(n)
            w.set_move_buttons_enabled(can_up=(n > 1), can_down=(n <= last))

    def _cards(self) -> list[ActionWidget]:
        """Возвращает список ActionWidget в порядке их следования в layout."""
        result = []
        for i in range(self.actionsLayout.count()):
            w = self.actionsLayout.itemAt(i).widget()
            if isinstance(w, ActionWidget):
                result.append(w)
        return result

    def _swap_cards(self, cards, i, j):
        # Меняем местами в списке
        cards[i], cards[j] = cards[j], cards[i]

        # Убираем все карточки из layout
        for w in cards:
            self.actionsLayout.removeWidget(w)

        # Вставляем заново в новом порядке ПЕРЕД stretch
        # (stretch всегда последний, поэтому insertWidget(count()-1, w))
        for w in cards:
            self.actionsLayout.insertWidget(self.actionsLayout.count() - 1, w)

        self.refresh_action_numbers()

    # --------------------------------------------------------
    #   Файловые операции
    # --------------------------------------------------------

    def open_file(self) -> None:
        """
        Открывает текстовый файл и загружает его содержимое в inpText.

        Если пользователь отменил диалог — ничего не делает.
        При успехе запоминает путь в self.file_name.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть текст", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_name:
            with open(file_name, "r", encoding="utf-8") as f:
                text = f.read()
                self.inpText.setPlainText(text)
            self.file_name = file_name

    def save_file(self, saveAs: bool = False) -> None:
        """
        Сохраняет содержимое outText в файл.

        Аргументы:
            saveAs: если True — всегда показывает диалог выбора файла
                    (режим «Сохранить как...»). Если False и файл уже
                    открыт/сохранён — пишет в него без диалога.

        Если пользователь отменил диалог — ничего не делает.
        """
        if not self.file_name or saveAs:
            file_name, filter = QFileDialog.getSaveFileName(
                self, "Сохранить текст", "", ';;'.join(self.saveFormats)
            )
        else:
            file_name = self.file_name

        if file_name:
            text = self.outText.toPlainText()
            if filter == 'Text Files (*.txt)':
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(text)
                self.file_name = file_name
            else:
                from shutil import copy2
                from pathlib import Path
                src = Path('temp_morse.wav')
                dst = Path(file_name)
                if not dst.suffix:
                    dst = dst.with_suffix(filter[-5:-1])
                dst.parent.mkdir(parents=True, exist_ok=True)
                copy2(src, dst)


    # --------------------------------------------------------
    #   Настройки
    # --------------------------------------------------------

    def open_settings(self) -> None:
        """
        Открывает модальный диалог настроек.

        Если пользователь подтвердил (Ok), показывает в статусбаре
        сообщение «Сохранено». Сам диалог сохраняет настройки
        в settings.json внутри collect().
        """
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.statusbar.showMessage("Сохранено")

    def connect_file_menu(self) -> None:
        """
        Подключает пункты меню «Файл» к соответствующим обработчикам.

        Для «Сохранить как...» используется partial, чтобы передать
        saveAs=True, не создавая отдельный метод-обёртку.
        """
        self.openAction.triggered.connect(self.open_file)
        self.saveAction.triggered.connect(self.save_file)
        self.saveAsAction.triggered.connect(partial(self.save_file, saveAs=True))
        self.settingsAction.triggered.connect(self.open_settings)

    # --------------------------------------------------------
    #   Реакция на смену темы
    # --------------------------------------------------------

    def _on_color_scheme_changed(self, scheme) -> None:
        """
        Перестраивает QPalette и QSS при смене системной темы.

        Аргументы:
            scheme: новое значение Qt.ColorScheme (не используется напрямую —
                    палитра определяется заново через get_palette()).

        Примечание:
            Метод вызывается автоматически по сигналу
            QApplication.styleHints().colorSchemeChanged.
        """
        app = QApplication.instance()
        p = get_palette()
        app.setPalette(build_app_palette(p))
        app.setStyleSheet(build_app_qss(p))

    def audio_morse(self, morse: str):
        import wave
        import struct
        import math


        SAMPLE_RATE = 44100
        FREQ = 800.0
        WPM = 25
        UNIT = 1.2 / WPM

        def tone(duration, freq=FREQ, sr=SAMPLE_RATE, volume=0.5):
            n = int(sr * duration)
            return [volume * math.sin(2 * math.pi * freq * i / sr) for i in range(n)]

        def silence(duration, sr=SAMPLE_RATE):
            return [0.0] * int(sr * duration)

        def morse_to_audio(morse=morse):
            samples = []
            i = 0
            for ch in morse:
                match ch:
                    case '.':
                        samples += tone(UNIT)
                        samples += silence(UNIT)
                    case '-':
                        samples += tone(UNIT * 3)
                        samples += silence(UNIT)
                    case ' ':
                        samples += silence(UNIT * 2)
                    case '/':
                        samples += silence(UNIT * 6)
                samples += silence(UNIT * 2)

            with wave.open('temp_morse.wav', 'w') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                frames = b''.join(
                    struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767))
                    for s in samples
                )
                w.writeframes(frames)
        morse_to_audio()

        self.player.reload_source()
        self.tBarWidget.show()
                    

    # --------------------------------------------------------
    #   Выполнение цепочки действий
    # --------------------------------------------------------

    def execute(self) -> None:
        """
        Проходит по всем ActionWidget и выполняет выбранные операции.

        Обработка ошибок:
            - UnknownSymbolError / MissingSpaceSymbolError — показываем
            пользователю уже закодированную часть и проблемный символ;
            - InvalidAlphabetError / MissingSpacerError — сообщаем
            о проблеме с файлом алфавита;
            - ActionError (базовый) — ловим на случай новых наследников.
        """

        self.saveAsAction.setEnabled(True)
        self.saveAction.setEnabled(True)
        text = self.inpText.toPlainText()
        for action_ind in range(2, self.actionsLayout.count() - 1):
            widget = self.actionsLayout.itemAt(action_ind).widget()
            f = widget.findChild(OperationForm, "mFLayout")
            if not f:
                continue

            type_ind = f.typeCombo.currentIndex()
            code_radio = f.codeRadio.isChecked()

            if 'MP3 Files (*.mp3)' in self.saveFormats:
                self.saveFormats.remove('MP3 Files (*.mp3)')
                self.saveFormats.remove('WAV Files (*.wav)')
            self.tBarWidget.hide()

            match type_ind:
                case 0:  # Морзе
                    try:
                        morse = actions.Morse(f"alphabets/morse/{f.alphabetCombo.currentData()}.json", text)
                        if code_radio:
                            text = morse.code()
                            self.audio_morse(text)
                            if 'MP3 Files (*.mp3)' not in self.saveFormats:
                                self.saveFormats.insert(1, 'MP3 Files (*.mp3)')
                                self.saveFormats.insert(2, 'WAV Files (*.wav)')
                        else:
                            text = morse.encode()

                    except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                        # Показываем уже закодированную часть + пояснение
                        text = f"{e.partial_out}\n[{e.message}]"
                        QMessageBox.critical(self, "Ошибка", e.message)

                    except (InvalidAlphabetError, MissingSpacerError) as e:
                        # Проблема с самим файлом алфавита
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка алфавита", e.message)

                    except ActionError as e:
                        # Общий fallback на будущее
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка", e.message)

                case 1:
                    try:
                        conv = actions.NumberSystem(
                            f"alphabets/number_systems/{f.alphabetCombo.currentData()}.json",
                            f.inpSpin.value(),
                            f.operSpin.value(),
                            text
                        )
                        text = conv.oper()
                    except ActionError as e:
                        partial = getattr(e, "partial_out", "")
                        self.outText.setPlainText(
                            f"{partial}\n[{e.message}]" if partial else e.message
                        )
                        QMessageBox.critical(self, "Ошибка", e.message)
                case 2:  # Шифры
                    try:
                        oper_ind = f.operCombo.currentIndex()
                        alphabet_path = f"alphabets/ciphers/{'caesar' if oper_ind == 0 else 'A1Z26'}/{f.alphabetCombo.currentData()}.json"

                        if oper_ind == 0:  # Цезарь
                            shift = f.operSpin.value()
                            cipher = actions.Caesar(alphabet_path, text, shift)
                        elif oper_ind == 1:  # A1Z26
                            cipher = actions.A1Z26(alphabet_path, text)
                        else:
                            continue

                        if code_radio:
                            text = cipher.code()
                        else:
                            text = cipher.encode()

                    except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                        text = f"{e.partial_out}\n[{e.message}]"
                        QMessageBox.critical(self, "Ошибка", e.message)

                    except (InvalidAlphabetError, MissingSpacerError) as e:
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка алфавита", e.message)

                    except ActionError as e:
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка", e.message)
                case 3:
                    try:
                        braille = actions.Braille(f"alphabets/braille/{f.alphabetCombo.currentData()}.json", text)
                        if code_radio:
                            text = braille.code()
                        else:
                            text = braille.encode()

                    except (UnknownSymbolError, MissingSpaceSymbolError) as e:
                        # Показываем уже закодированную часть + пояснение
                        self.outText.setPlainText(
                            f"{e.partial_out}\n"
                            f"[{e.message}]"
                        )
                        QMessageBox.critical(self, "Ошибка", e.message)

                    except (InvalidAlphabetError, MissingSpacerError) as e:
                        # Проблема с самим файлом алфавита
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка алфавита", e.message)

                    except ActionError as e:
                        # Общий fallback на будущее
                        self.outText.setPlainText(e.message)
                        QMessageBox.critical(self, "Ошибка", e.message)
                case 4:
                    try:
                        binary = actions.Bytes(text, f.alphabetCombo.currentData())
                        if code_radio:
                            text = binary.code()
                        else:
                            text = binary.encode()
                    except:
                        pass
                        
        self.outText.setPlainText(text)


# ============================================================
#   Точка входа
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("fusion")

    # Глобальный QSS — по текущей теме (dark — базовая)
    app.setStyleSheet(build_app_qss(get_palette()))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())