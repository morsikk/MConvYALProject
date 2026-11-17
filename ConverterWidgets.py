# ============================================================
#   ИМПОРТЫ
# ============================================================

import json
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QDialogButtonBox,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QLabel,
    QScrollArea,
    QMenuBar,
    QMenu,
    QStatusBar,
    QDialog,
    QListWidget,
    QFormLayout,
    QComboBox,
    QFrame,
    QStackedWidget,
    QHBoxLayout,
    QSplitter,
    QLineEdit,
    QSpinBox,
    QMainWindow,
    QRadioButton,
    QSlider,
    QSizePolicy
)
from PyQt6.QtCore import QSize, Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


# ============================================================
#   ТЕМА: определение, палитры, QSS
# ============================================================

def detect_theme() -> str:
    """
    Определяет текущую системную цветовую схему.

    Возвращает:
        "light" — если система сообщает о светлой схеме;
        "dark"  — если система сообщает о тёмной схеме
                  ИЛИ если определить не удалось (fallback).

    Примечание:
        Используется Qt.ColorScheme из PyQt6. Если метод недоступен
        (старая версия Qt / платформа не поддерживает), срабатывает
        блок try/except и возвращается "dark".
    """
    try:
        scheme = QApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass

    return "dark"


# ------------------------------------------------------------
#   Палитры.
#   Каждый словарь — это набор цветов и путей к SVG-иконкам
#   для соответствующей темы. Ключи используются в build_app_qss
#   и build_app_palette через f-строки.
# ------------------------------------------------------------

DARK_PALETTE = {
    # Иконки стрелок (для тёмной темы используются СВЕТЛЫЕ иконки)
    "up_arrow": "svg/arrow_up_light.svg",
    "down_arrow": "svg/arrow_down_light.svg",

    # Иконки радиокнопок для тёмной темы
    "radio_off":       "svg/radio_off_dark.svg",
    "radio_off_hover": "svg/radio_off_hover_dark.svg",
    "radio_on":        "svg/radio_on_dark.svg",
    "radio_on_hover":  "svg/radio_on_hover_dark.svg",

    # Иконки кнопок плеера
    "play": "svg/play_light.svg",
    "pause": "svg/pause_light.svg",

    # Основные цвета
    "bg": "#1e1e1e",              # общий фон окна
    "panel": "#252526",           # фон панелей
    "fg": "#e0e0e0",              # основной цвет текста
    "accent": "#0e639c",          # акцентный цвет (кнопки, фокус)
    "accent_fg": "#ffffff",       # текст на акцентном фоне
    "input_bg": "#1b1b1c",        # фон полей ввода
    "input_border": "#3c3c3c",    # рамка полей ввода
    "button_bg": "#2d2d30",       # фон кнопок
    "button_border": "#3c3c3c",   # рамка кнопок
    "button_hover": "#3a3a3d",    # фон кнопок при наведении
    "sel_bg": "#264f78",          # фон выделения текста
    "sel_fg": "#ffffff",          # цвет текста в выделении
    "panel_border": "#3c3c3c",    # рамка панелей
    "fg_muted": "#9a9a9a",        # приглушённый текст
    "header_bg": "#252526",       # фон заголовков панелей
    "header_border": "#3c3c3c",   # рамка заголовков панелей
    "scrollbar": "#3c3c3c",       # ползунок скроллбара
    "scrollbar_hover": "#4a4a4a", # ползунок при наведении
    "accent_hover": "#1177bb",    # акцент при наведении
}

LIGHT_PALETTE = {
    # Для светлой темы — тёмные иконки стрелок
    "up_arrow": "svg/arrow_up_dark.svg",
    "down_arrow": "svg/arrow_down_dark.svg",

    # Иконки радиокнопок для светлой темы
    "radio_off":       "svg/radio_off_light.svg",
    "radio_off_hover": "svg/radio_off_hover_light.svg",
    "radio_on":        "svg/radio_on_light.svg",
    "radio_on_hover":  "svg/radio_on_hover_light.svg",

    # Иконки кнопок плеера
    "play": "svg/play_dark.svg",
    "pause": "svg/pause_dark.svg",

    "bg": "#ffffff",
    "panel": "#f5f5f7",
    "fg": "#1a1a1a",
    "accent": "#0078d4",
    "accent_fg": "#ffffff",
    "input_bg": "#ffffff",
    "input_border": "#cfcfcf",
    "button_bg": "#f0f0f0",
    "button_border": "#d0d0d0",
    "button_hover": "#e5e5ea",
    "sel_bg": "#cce4f7",
    "sel_fg": "#000000",
    "panel_border": "#e0e0e0",
    "fg_muted": "#6b6b6b",
    "header_bg": "#f5f5f7",
    "header_border": "#e0e0e0",
    "scrollbar": "#cfcfcf",
    "scrollbar_hover": "#b0b0b0",
    "accent_hover": "#106ebe",
}


def get_palette() -> dict:
    """
    Возвращает словарь цветов для текущей темы.

    Возвращает:
        DARK_PALETTE, если detect_theme() == "dark";
        LIGHT_PALETTE иначе.
    """
    return DARK_PALETTE if detect_theme() == "dark" else LIGHT_PALETTE


def build_app_palette(p: dict) -> QPalette:
    """
    Строит QPalette из словаря цветов.

    Аргументы:
        p: словарь палитры (например, DARK_PALETTE или LIGHT_PALETTE).

    Возвращает:
        QPalette с установленными основными ролями цветов:
        Window, WindowText, Base, AlternateBase, Text, Button,
        ButtonText, Highlight, HighlightedText.
    """
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(p["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(p["fg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(p["input_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(p["panel"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(p["fg"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(p["button_bg"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(p["fg"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(p["sel_bg"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(p["sel_fg"]))
    return pal


def build_app_qss(p: dict) -> str:
    """
    Строит строку QSS (Qt Style Sheets) из словаря палитры.

    Аргументы:
        p: словарь палитры (DARK_PALETTE или LIGHT_PALETTE).

    Возвращает:
        Строку со стилями для QApplication.setStyleSheet().

    Примечание:
        Внутри f-строки подставляются значения из словаря p.
        Стилизуются: окна, меню, статусбар, текстовые редакторы,
        скроллбары, кнопки, поля ввода, комбобоксы, радиокнопки,
        спинбоксы, навигация в настройках.
    """
    return f"""
    QMainWindow, QDialog {{ background: {p['bg']}; color: {p['fg']}; }}
    QWidget {{ color: {p['fg']}; background: {p['bg']}; }}
    QWidget#mWidget,
    QWidget#inpTextWidget,
    QWidget#outTextWidget,
    QWidget#actionListWidget,
    QWidget#actionsWidget,
    QWidget#tBarWidget,
    QWidget#actionListLabelsWidget {{ background: {p['panel']}; }}
    QWidget#inpTextWidget,
    QWidget#outTextWidget {{ background: {p['bg']}; }}
    QLabel {{ background: transparent; color: {p['fg']}; }}
    QLabel#actionsLabel {{ color: {p['fg_muted']}; font-weight: bold; font-size: 12px; }}

    /* --- Меню --- */
    QMenuBar {{ background: {p['panel']}; border-bottom: 1px solid {p['panel_border']}; padding: 2px 6px; }}
    QMenuBar::item {{ padding: 6px 10px; border-radius: 4px; background: transparent; }}
    QMenuBar::item:selected {{ background: {p['button_hover']}; }}
    QMenu {{ background: {p['panel']}; border: 1px solid {p['panel_border']}; padding: 4px; }}
    QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {p['accent']}; color: {p['accent_fg']}; }}

    /* --- Статусбар --- */
    QStatusBar {{ background: {p['panel']}; border-top: 1px solid {p['panel_border']}; color: {p['fg_muted']}; }}

    /* --- Верхняя панель инструментов --- */
    QWidget#tBarWidget {{ background: {p['panel']}; border-bottom: 1px solid {p['panel_border']}; }}

    /* --- Текстовые редакторы --- */
    QPlainTextEdit {{
        background: {p['input_bg']}; color: {p['fg']};
        border: 1px solid {p['input_border']}; border-radius: 6px; padding: 8px;
        selection-background-color: {p['sel_bg']}; selection-color: {p['sel_fg']};
        font-family: "Consolas", "Cascadia Mono", monospace; font-size: 13px;
    }}
    QPlainTextEdit:focus {{ border: 1px solid {p['accent']}; }}

    /* --- Сплиттер --- */
    QSplitter {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    QSplitter::handle:horizontal {{ width: 4px; }}

    /* --- Панель списка действий --- */
    QWidget#actionListWidget {{ background: {p['panel']}; border: 1px solid {p['panel_border']}; border-radius: 6px; }}
    QWidget#actionListLabelsWidget {{ background: {p['header_bg']}; border-bottom: 1px solid {p['header_border']}; }}
    QLabel#actionsLabel {{ color: {p['fg_muted']}; font-weight: bold; font-size: 12px; }}

    /* --- Область прокрутки --- */
    QScrollArea {{ background: transparent; border: none; }}

    /* --- Вертикальный скроллбар --- */
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {p['scrollbar']}; border-radius: 6px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['scrollbar_hover']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    /* --- Кнопки --- */
    QPushButton {{
        background: {p['button_bg']}; color: {p['fg']};
        border: 1px solid {p['button_border']}; border-radius: 6px;
        padding: 6px 14px; min-width: 70px;
    }}
    QPushButton:hover {{ background: {p['button_hover']}; border-color: {p['accent']}; }}
    QPushButton:default {{ background: {p['accent']}; color: {p['accent_fg']}; border-color: {p['accent']}; }}

    /* --- Маленькие кнопки в ActionWidget: up / down / delete --- */
    QPushButton#upButton, QPushButton#downButton, QPushButton#delButton {{
        min-width: 20px;
        max-width: 20px;
        min-height: 20px;
        max-height: 20px;
        padding: 0px;
        border: none;
    }}
    QPushButton#upButton {{
        icon: url({p['up_arrow']});
        qproperty-iconSize: 8px 8px;
    }}
    QPushButton#downButton {{
        icon: url({p['down_arrow']});
        qproperty-iconSize: 8px 8px;
    }}

    /* --- Поля ввода / спинбоксы / комбобоксы --- */
    QLineEdit, QSpinBox, QComboBox {{
        background: {p['input_bg']}; color: {p['fg']};
        border: 1px solid {p['input_border']}; border-radius: 4px; padding: 4px 6px; min-height: 22px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {p['accent']}; }}

    /* --- Навигация в диалоге настроек --- */
    QListWidget#settingsNav {{ background: {p['panel']}; border: none; border-right: 1px solid {p['panel_border']}; padding: 6px; outline: 0; }}
    QListWidget#settingsNav::item {{ padding: 10px 12px; border-radius: 6px; }}
    QListWidget#settingsNav::item:selected {{ background: {p['accent']}; color: {p['accent_fg']}; }}
    QListWidget#settingsNav::item:hover:!selected {{ background: {p['button_hover']}; }}

    /* --- Спинбоксы: кнопки и стрелки --- */
    QSpinBox::up-button, QSpinBox::down-button {{
        background: {p['button_bg']};
        border: 1px solid {p['button_border']};
        width: 19px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background: {p['button_hover']};
    }}
    QSpinBox::up-arrow {{
        image: url({p['up_arrow']});
        width: 8px;
        height: 5px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
    }}
    QSpinBox::down-arrow {{
        image: url({p['down_arrow']});
        width: 8px;
        height: 5px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
    }}

    /* --- Комбобоксы: стрелка и выпадающая кнопка --- */
    QComboBox::down-arrow {{
        image: url({p['down_arrow']});
        width: 8px;
        height: 5px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {p['input_border']};
        background: {p['button_bg']};
    }}
    QComboBox::drop-down:hover {{
        background: {p['button_hover']};
    }}

    /* --- Радиокнопки --- */
    QRadioButton {{
        background: transparent;
        spacing: 8px;
        padding: 2px 0;
    }}
    QRadioButton:disabled {{
        color: {p['fg_muted']};
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        image: url({p['radio_off']});
    }}
    QRadioButton::indicator:hover {{
        image: url({p['radio_off_hover']});
    }}
    QRadioButton::indicator:checked {{
        image: url({p['radio_on']});
    }}
    QRadioButton::indicator:checked:hover {{
        image: url({p['radio_on_hover']});
    }}
    QRadioButton::indicator:disabled {{
        image: url({p['radio_off']});
    }}
    QWidget#directionWidget {{
        background: transparent;
    }}

    /* --- Скроллбары: убираем стрелки, оставляем ползунок --- */
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        width: 0; height: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p['scrollbar']};
        border-radius: 6px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
        width: 0; height: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
        /* --- Мини-плеер --- */
    QWidget#miniPlayer {{
        background: {p['panel']};
        border: 1px solid {p['panel_border']};
        border-radius: 6px;
    }}
    QPushButton#playButton, QPushButton#pauseButton {{
        background: {p['button_bg']};
        color: {p['fg']};
        border: 1px solid {p['button_border']};
        border-radius: 4px;
        padding: 0px;
        font-size: 14px;
    }}
    QPushButton#playButton{{
        icon: url({p['play']});
    }}
    QPushButton#pauseButton{{
        icon: url({p['pause']});
    }}
    QPushButton#playButton:hover, QPushButton#pauseButton:hover {{
        background: {p['accent']};
        color: {p['accent_fg']};
        border-color: {p['accent']};
    }}
    QPushButton#playButton:pressed, QPushButton#pauseButton:pressed {{
        background: {p['accent_hover']};
    }}

    /* --- Слайдер плеера --- */
    QSlider {{
        background: transparent;
    }}
    QSlider#playerSlider::groove:horizontal {{
        height: 4px;
        background: {p['input_border']};
        border-radius: 2px;
    }}
    QSlider#playerSlider::handle:horizontal {{
        background: {p['accent']};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider#playerSlider::handle:horizontal:hover {{
        background: {p['accent_hover']};
    }}
    QSlider#playerSlider::sub-page:horizontal {{
        background: {p['accent']};
        border-radius: 2px;
    }}
    """


# ============================================================
#   OperationForm — форма параметров операции
# ============================================================

class OperationForm(QWidget):
    """
    Форма с параметрами одной операции.

    Содержит:
        typeCombo       — тип операции (Морзе, системы счисления, шифры, Брайль);
        operCombo       — выбор конкретной операции (для шифров);
        inpSpin         — основание вводимой системы счисления (2..36);
        operSpin        — основание выводимой системы счисления (2..36);
        alphabetCombo   — выбор алфавита;
        keyEdit         — поле для ключа шифра;
        codeRadio/decodeRadio — направление (кодировать/декодировать).

    Все поля, кроме typeCombo и направления, регистрируются в self._rows,
    чтобы их можно было показывать/скрывать через show_only/hide_row/show_row.
    """

    def __init__(self) -> None:
        super().__init__()

        # name -> (label, widget)
        # Хранит пары «подпись — виджет» для управления видимостью строк формы.
        self._rows: dict[str, tuple[QLabel, QWidget]] = {}

        self.mFLayout = QFormLayout(self)
        self.mFLayout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        # --- Создание виджетов ---
        self.typeCombo = QComboBox()                 # тип операции
        self.operCombo = QComboBox()                 # конкретная операция (для шифров)
        self.inpSpin = QSpinBox()                    # основание вводимой системы счисления
        self.inpSpin.setRange(2, 36)
        self.operSpin = QSpinBox()                   # основание выводимой системы счисления
        self.operSpin.setRange(2, 36)
        self.alphabetCombo = QComboBox()             # выбор алфавита
        self.keyEdit = QLineEdit()                   # ключ шифра
        self.keyEdit.setPlaceholderText("Ключ...")

        # --- Направление: кодировать / декодировать ---
        self.directionLayout = QHBoxLayout()
        self.codeRadio = QRadioButton("Кодировать")
        self.codeRadio.setObjectName("codeRadio")
        self.decodeRadio = QRadioButton("Декодировать")
        self.decodeRadio.setChecked(True)
        self.directionLayout.addWidget(self.codeRadio)
        self.directionLayout.addWidget(self.decodeRadio)

        # Контейнер для направления, чтобы строку можно было скрывать
        self.directionWidget = QWidget()
        self.directionWidget.setObjectName('directionWidget')
        self.directionWidget.setLayout(self.directionLayout)
        self.directionLayout.setContentsMargins(0, 0, 0, 0)

        # --- Добавление строк в форму ---
        self.mFLayout.addRow("Тип:", self.typeCombo)
        self._add_row("operCombo", "Операция:", self.operCombo)
        self._add_row("inpSpin", "Основание ввода:", self.inpSpin)
        self._add_row("operSpin", "Основание вывода:", self.operSpin)
        self._add_row("alphabetCombo", "Алфавит:", self.alphabetCombo)
        self._add_row("keyEdit", "Ключ:", self.keyEdit)
        self._add_row_widget("direction", None, self.directionWidget)

    def _add_row(self, name: str, label_text: str, widget: QWidget) -> None:
        """
        Добавляет строку в форму и запоминает её в self._rows.

        Аргументы:
            name:       ключ, по которому строку можно будет скрыть/показать;
            label_text: текст подписи слева;
            widget:     виджет поля справа.
        """
        label = QLabel(label_text)
        self.mFLayout.addRow(label, widget)
        self._rows[name] = (label, widget)

    def _add_row_widget(self, name: str, label_text, widget: QWidget) -> None:
        """
        Добавляет строку с готовым виджетом и запоминает её в self._rows.

        Аргументы:
            name:       ключ строки;
            label_text: текст подписи слева, либо None — тогда строка
                        добавляется без подписи (виджет занимает всю ширину);
            widget:     виджет-контейнер справа.
        """
        if label_text is None:
            self.mFLayout.addRow(widget)
            self._rows[name] = (None, widget)
        else:
            label = QLabel(label_text)
            self.mFLayout.addRow(label, widget)
            self._rows[name] = (label, widget)

    def show_only(self, *names: str) -> None:
        """
        Показывает только перечисленные строки, остальные скрывает.

        Аргументы:
            *names: имена строк (ключи из self._rows), которые нужно оставить видимыми.
        """
        wanted = set(names)
        for name, (label, widget) in self._rows.items():
            visible = name in wanted
            if label is not None:
                label.setVisible(visible)
            widget.setVisible(visible)

    def hide_row(self, name: str) -> None:
        """Скрывает строку формы по её имени."""
        label, widget = self._rows[name]
        if label is not None:
            label.hide()
        widget.hide()

    def show_row(self, name: str) -> None:
        """Показывает строку формы по её имени."""
        label, widget = self._rows[name]
        if label is not None:
            label.show()
        widget.show()


# ============================================================
#   Ui_MainWindow — сборка главного окна
# ============================================================

class Ui_MainWindow(object):
    """
    Класс-строитель интерфейса главного окна.

    Не наследуется от QMainWindow: получает окно аргументом setupUi
    и наполняет его виджетами. Это классический паттерн из pyuic.
    """

    def setupUi(self, MainWindow: QMainWindow) -> None:
        """
        Создаёт и размещает все виджеты главного окна.

        Аргументы:
            MainWindow: экземпляр QMainWindow, который нужно наполнить.
        """
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(928, 563)
        MainWindow.setWindowTitle("Мультиконвертер")

        # --- Корневой контейнер ---
        self.mWidget = QWidget(parent=MainWindow)
        self.mWidget.setObjectName("mWidget")
        self.mVLayout = QVBoxLayout(self.mWidget)
        self.mVLayout.setContentsMargins(8, 8, 8, 8)
        self.mVLayout.setSpacing(8)

        # --- Верхняя панель инструментов (пока пустая) ---
        self.tBarWidget = QWidget(parent=self.mWidget)
        self.tBarWidget.setMaximumSize(QtCore.QSize(16777215, 80))
        self.tBarWidget.setObjectName("tBarWidget")
        self.tBarHLayout = QHBoxLayout(self.tBarWidget)
        self.tBarHLayout.setContentsMargins(8, 6, 8, 6)
        self.player = MiniPlayer()
        self.tBarHLayout.addWidget(self.player)
        self.mVLayout.addWidget(self.tBarWidget)
        self.tBarWidget.hide()

        # --- Рабочее пространство: три панели в QSplitter ---
        self.workspace = QSplitter(parent=self.mWidget)
        self.workspace.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.workspace.setObjectName("workspace")

        # --- Левая панель: ввод текста ---
        self.inpTextWidget = QWidget(parent=self.workspace)
        self.inpTextWidget.setObjectName("inpTextWidget")
        self.inpTextVLayout = QVBoxLayout(self.inpTextWidget)
        self.inpTextVLayout.setContentsMargins(0, 0, 0, 0)
        self.inpText = QPlainTextEdit(parent=self.inpTextWidget)
        self.inpText.setObjectName("inpText")
        self.inpText.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.inpText.setWordWrapMode(
            QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.inpTextVLayout.addWidget(self.inpText)

        # --- Средняя панель: список действий ---
        self.actionListWidget = QWidget(parent=self.workspace)
        self.actionListWidget.setMaximumSize(QtCore.QSize(275, 16777215))
        self.actionListWidget.setObjectName("actionListWidget")
        self.actionListVLayout = QVBoxLayout(self.actionListWidget)
        self.actionListVLayout.setContentsMargins(0, 0, 0, 0)
        self.actionListVLayout.setSpacing(1)

        # Заголовок панели действий
        self.actionListLabelsWidget = QWidget(parent=self.actionListWidget)
        self.actionListLabelsWidget.setMaximumSize(QtCore.QSize(16777215, 30))
        self.actionListLabelsWidget.setObjectName("actionListLabelsWidget")
        labelsLayout = QHBoxLayout(self.actionListLabelsWidget)
        labelsLayout.setContentsMargins(6, 4, 6, 4)

        self.actionsLabel = QLabel(parent=self.actionListLabelsWidget)
        self.actionsLabel.setObjectName("actionsLabel")
        self.actionsLabel.setText("Действия")
        labelsLayout.addWidget(self.actionsLabel)

        self.actionListVLayout.addWidget(self.actionListLabelsWidget)

        # Прокручиваемая область со списком действий
        self.scrollArea = QScrollArea(parent=self.actionListWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.actionsWidget = QWidget()
        self.actionsWidget.setObjectName("actionsWidget")
        self.scrollArea.setWidget(self.actionsWidget)
        self.actionListVLayout.addWidget(self.scrollArea)

        # Кнопки внизу панели действий
        self.addActionButton = QPushButton()
        self.addActionButton.setText("Добавить действие...")

        self.executeButton = QPushButton()
        self.executeButton.setText("Выполнить")
        self.executeButton.setStyleSheet("font-weight: bold;")

        # Layout для самих ActionWidget + кнопок
        self.actionsLayout = QVBoxLayout(self.actionsWidget)
        self.actionsLayout.setContentsMargins(5, 5, 5, 5)
        self.actionsLayout.setSpacing(5)
        self.actionsLayout.addWidget(self.executeButton)
        self.actionsLayout.addWidget(self.addActionButton)
        self.actionsLayout.addStretch()

        # --- Правая панель: вывод текста ---
        self.outTextWidget = QWidget(parent=self.workspace)
        self.outTextWidget.setObjectName("outTextWidget")
        self.outTextVLayout = QVBoxLayout(self.outTextWidget)
        self.outTextVLayout.setContentsMargins(0, 0, 0, 0)
        self.outText = QPlainTextEdit(parent=self.outTextWidget)
        self.outText.setReadOnly(True)  # только для чтения
        self.outText.setObjectName("outText")
        self.outText.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.outText.setWordWrapMode(
            QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.outTextVLayout.addWidget(self.outText)

        # Добавляем панели в сплиттер и задаём начальные размеры
        self.workspace.addWidget(self.inpTextWidget)
        self.workspace.addWidget(self.actionListWidget)
        self.workspace.addWidget(self.outTextWidget)
        self.workspace.setSizes([400, 345, 400])

        self.mVLayout.addWidget(self.workspace)
        MainWindow.setCentralWidget(self.mWidget)

        # --- Меню ---
        self.menubar = QMenuBar(parent=MainWindow)
        self.menubar.setObjectName("menubar")
        self.fileMenu = QMenu(parent=self.menubar)
        self.fileMenu.setObjectName("fileMenu")
        self.fileMenu.setTitle("Файл")
        MainWindow.setMenuBar(self.menubar)

        # --- Статусбар ---
        self.statusbar = QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # --- Действия меню ---
        self.openAction = QtGui.QAction(parent=MainWindow)
        self.openAction.setObjectName("openAction")
        self.openAction.setText("Открыть")

        self.saveAction = QtGui.QAction(parent=MainWindow)
        self.saveAction.setObjectName("saveAction")
        self.saveAction.setText("Сохранить")
        self.saveAction.setEnabled(False)

        self.saveAsAction = QtGui.QAction(parent=MainWindow)
        self.saveAsAction.setObjectName("saveAsAction")
        self.saveAsAction.setText("Сохранить как...")
        self.saveAsAction.setEnabled(False)

        self.settingsAction = QtGui.QAction(parent=MainWindow)
        self.settingsAction.setObjectName("settingsAction")
        self.settingsAction.setText("Настройки")

        # Собираем меню «Файл»
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.saveAsAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.settingsAction)
        self.menubar.addAction(self.fileMenu.menuAction())


# ============================================================
#   ActionWidget — карточка одного действия
# ============================================================

class ActionWidget(QWidget):
    """
    Виджет одного действия в списке.

    Содержит:
        - заголовок «Действие N»;
        - кнопки перемещения вверх/вниз и удаления;
        - встроенную OperationForm с параметрами операции.

    Сигнал removed испускается при удалении, чтобы родитель мог
    перестроить нумерацию оставшихся действий.
    """

    removed = pyqtSignal(object)  # испускается при удалении (передаёт self)
    move_up = pyqtSignal(object)   # запрос переместить вверх (передаёт self)
    move_down = pyqtSignal(object) # запрос переместить вниз  (передаёт self)

    def __init__(self) -> None:
        super().__init__()

        # Форма параметров операции
        self.mFLayout = OperationForm()
        self.mFLayout.setObjectName("mFLayout")

        vLayout = QVBoxLayout(self)
        hLayout = QHBoxLayout()
        hLayout.setSpacing(6)

        # Заголовок «Действие N»
        self.label = QLabel()
        self.set_number(1)

        # Кнопки управления
        self.upButton = QPushButton()
        self.upButton.setObjectName("upButton")
        self.upButton.setToolTip("Переместить вверх")
        self.upButton.clicked.connect(
            lambda: self.move_up.emit(self)
        )      
        self.downButton = QPushButton()
        self.downButton.setObjectName("downButton")
        self.downButton.setToolTip("Переместить вниз")
        self.downButton.clicked.connect(
            lambda: self.move_down.emit(self)
        )   
        self.delButton = QPushButton()
        self.delButton.setObjectName("delButton")
        self.delButton.setText("-")
        self.delButton.setToolTip("Удалить действие")
        self.delButton.clicked.connect(self.delete)

        hLayout.addWidget(self.label)
        hLayout.addWidget(self.upButton)
        hLayout.addWidget(self.downButton)
        hLayout.addWidget(self.delButton)

        vLayout.setContentsMargins(6, 6, 6, 6)
        vLayout.setSpacing(6)
        vLayout.addLayout(hLayout)
        vLayout.addWidget(self.mFLayout)
        vLayout.addStretch()

        # Заполняем список типов и подключаем обработчик
        self.mFLayout.typeCombo.addItems(
            ["Морзе", "Системы счисления", "Шифры", "Брайль", "Бинарный код"]
        )
        self.mFLayout.typeCombo.currentIndexChanged.connect(self.on_type_changed)
        self.mFLayout.typeCombo.setCurrentIndex(0)
        self.on_type_changed(0)  # ручной вызов, т.к. сигнал не сработает, если индекс уже 0

        self.mFLayout.typeCombo.currentIndexChanged.connect(self.on_type_changed)
        self.mFLayout.typeCombo.setCurrentIndex(0)
        self.on_type_changed(0)

        self.mFLayout.operCombo.currentIndexChanged.connect(self.on_cipher_changed)
        self.on_cipher_changed(self.mFLayout.operCombo.currentIndex())

        self.mFLayout.alphabetCombo.currentIndexChanged.connect(self.on_alphabet_changed)

    def on_alphabet_changed(self, index: int) -> None:
        """
        Пересчитывает ограничения operSpin при смене алфавита.

        Актуально только для шифра Цезаря — у него сдвиг зависит от длины
        выбранного алфавита.
        """
        f = self.mFLayout
        if f.typeCombo.currentIndex() != 2:
            return
        if f.operCombo.currentIndex() == 0:  # Цезарь
            self._update_caesar_spin_range()

    def on_type_changed(self, index: int) -> None:
        """
        Обновляет состав полей формы в зависимости от выбранного типа.

        Аргументы:
            index: индекс выбранного типа в typeCombo:
                0 — Морзе;
                1 — Системы счисления;
                2 — Шифры;
                3 — Брайль;
                4 — Бинарный код.

        Примечание:
            Данные алфавитов читаются из файла "alphabets/alphabets.json"
            при каждом переключении типа (без кэширования).
        """
        f = self.mFLayout
        with open("alphabets/alphabets.json", "r", encoding="utf-8") as alps_j:
            alps = json.load(alps_j)

        match index:
            case 0:  # Морзе — алфавит + направление
                f.show_only("alphabetCombo", "direction")
                f.alphabetCombo.clear()
                for meta in alps["morse"].values():
                    f.alphabetCombo.addItem(meta["name"], meta["data"])

            case 1:  # Системы счисления — основания + алфавит
                f.show_only("inpSpin", "operSpin", "alphabetCombo")

                # возвращаем подпись «Основание вывода:» (могли остаться от Цезаря)
                label, _ = f._rows["operSpin"]
                if label is not None:
                    label.setText("Основание вывода:")

                f.inpSpin.setRange(2, 36)
                f.operSpin.setRange(2, 36)

                f.alphabetCombo.clear()
                for meta in alps["number_systems"].values():
                    f.alphabetCombo.addItem(meta["name"], meta["data"])

            case 2:  # Шифры — операция + алфавит + ключ + направление
                f.show_only("operCombo", "alphabetCombo", "keyEdit", "direction")
                f.operCombo.clear()
                f.alphabetCombo.clear()
                for meta in alps["ciphers"].values():
                    f.operCombo.addItem(meta["name"], meta["data"])
                self.on_cipher_changed(f.operCombo.currentIndex())

            case 3:  # Брайль — алфавит + направление
                f.show_only("alphabetCombo", "direction")
                f.alphabetCombo.clear()
                for meta in alps["braille"].values():
                    f.alphabetCombo.addItem(meta["name"], meta["data"])

            case 4: # Бинарный код — кодировка + направление
                f.show_only("alphabetCombo", "direction")
                f.alphabetCombo.clear()
                for meta in alps["binary"].values():
                    f.alphabetCombo.addItem(meta["name"], meta["data"])

    def on_cipher_changed(self, index: int) -> None:
        """
        Настраивает форму под выбранный шифр.

        Аргументы:
            index: индекс выбранного шифра в operCombo.

        Примечание:
            Шифр Цезаря — всегда индекс 0. Для него:
                - прячется поле «Ключ»;
                - alphabetCombo заполняется из alps['ciphers']['alps'];
                - подпись operSpin меняется на «Сдвиг»;
                - диапазон operSpin — 1..(длина алфавита - 1).
            Для остальных шифров:
                - поле «Ключ» показывается;
                - operSpin скрывается.
        """
        f = self.mFLayout

        # Поле имеет смысл только внутри типа «Шифры»
        if f.typeCombo.currentIndex() != 2:
            return

        if index == 0:  # Цезарь
            # прячем ключ
            f.hide_row("keyEdit")

            # заполняем алфавит доступными для Цезаря
            f.alphabetCombo.clear()
            with open("alphabets/alphabets.json", "r", encoding="utf-8") as alps_j:
                alps = json.load(alps_j)
            for meta in alps["ciphers"]["caesar"]["alps"].values():
                f.alphabetCombo.addItem(meta["name"], meta["data"])

            # подпись «Сдвиг»
            label, _ = f._rows["operSpin"]
            if label is not None:
                label.setText("Сдвиг:")

            # ограничения — по длине алфавита
            self._update_caesar_spin_range()

            f.show_row("operSpin")
        else:
            # обычный шифр — ключ нужен, сдвиг не нужен
            f.show_row("keyEdit")
            f.hide_row("operSpin")

    def _update_caesar_spin_range(self) -> None:
        """
        Ставит диапазон operSpin для шифра Цезаря по длине выбранного алфавита.

        Длина берётся из файла алфавита (поле "letters"), а не из currentData():
        в currentData() для Цезаря лежит только код ("ru"/"en").
        """
        f = self.mFLayout
        code = f.alphabetCombo.currentData()          # "ru" / "en"
        n = 33                                        # запасное значение по умолчанию
        if code:
            try:
                with open(f"alphabets/ciphers/caesar/{code}.json", "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                letters = data.get("letters", "")
                if letters:
                    n = len(letters)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        f.operSpin.setRange(1, max(1, n - 1))
        if f.operSpin.value() > n - 1:
            f.operSpin.setValue(max(1, n - 1))

    def set_number(self, n: int) -> None:
        """Устанавливает отображаемый номер действия."""
        self.label.setText(f"Действие {n}")

    def set_move_buttons_enabled(self, can_up: bool, can_down: bool) -> None:
        """
        Включает/выключает (скрывает) кнопки перемещения.

        Аргументы:
            can_up:   True — показать кнопку «вверх»;
            can_down: True — показать кнопку «вниз».
        """
        self.upButton.setVisible(can_up)
        self.downButton.setVisible(can_down)

    def delete(self) -> None:
        """
        Удаляет действие: испускает сигнал removed, отвязывает от родителя
        и помечает виджет на удаление через deleteLater().
        """
        self.removed.emit(self)
        self.setParent(None)
        self.deleteLater()


# ============================================================
#   Настройки: страница, диалог
# ============================================================

class Page(QWidget):
    """
    Одна страница настроек.

    Содержит:
        undCharPolCombo — поведение при неизвестном символе
                          (Ошибка / Игнорировать / Заменить).

    Методы load/save читают и пишут settings.json.
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок страницы
        title = QLabel("Страница")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # Форма с настройками
        form = QFormLayout()
        form.setSpacing(12)

        self.undCharPolCombo = QComboBox()
        self.undCharPolCombo.addItems(["Ошибка", "Игнорировать", "Заменить"])
        form.addRow("Действие с неизвестным символом:", self.undCharPolCombo)

        layout.addLayout(form)
        layout.addStretch()

    def load(self) -> None:
        """
        Загружает настройки из settings.json и применяет их к виджетам.

        Если файла нет или он повреждён — молча выходит (настройки
        остаются по умолчанию).
        """
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        undCharPolIdx = self.undCharPolCombo.findText(
            data.get("und_char_pol", "Ошибка")
        )
        if undCharPolIdx >= 0:
            self.undCharPolCombo.setCurrentIndex(undCharPolIdx)

    def save(self) -> dict:
        """
        Собирает настройки со страницы в словарь.

        Возвращает:
            dict с ключом "und_char_pol" — текущее выбранное значение.
        """
        data = {}
        data["und_char_pol"] = self.undCharPolCombo.currentText()
        return data


class SettingsDialog(QDialog):
    """
    Диалог настроек с боковой навигацией и стеком страниц.

    Содержит:
        nav   — QListWidget с названиями страниц;
        stack — QStackedWidget с самими страницами;
        pages — список пар (имя, страница).

    Кнопки:
        Ok       — сохранить и закрыть;
        Cancel   — закрыть без сохранения;
        Apply    — сохранить, не закрывая.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(760, 520)

        # --- Боковая навигация ---
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(200)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)

        # --- Стек страниц ---
        self.stack = QStackedWidget()

        # Список страниц: пока одна, но структура готова к расширению
        self.pages = [("Страница", Page())]

        for name, page in self.pages:
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(0, 40))
            self.nav.addItem(item)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        # --- Кнопки диалога ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отменить")
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Применить")
        buttons.accepted.connect(self.collect_n_close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.collect
        )

        # --- Компоновка: навигация + стек ---
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.nav)
        content_layout.addWidget(self.stack, 1)

        # --- Нижняя панель с кнопками ---
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.addStretch()
        footer_layout.addWidget(buttons)

        # --- Главный layout диалога ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(content_layout, 1)
        main_layout.addWidget(footer)

        # Загружаем текущие настройки
        self.load()

    def load(self) -> None:
        """Загружает настройки во все страницы диалога."""
        for _, page in self.pages:
            page.load()

    def collect(self) -> None:
        """
        Собирает данные со всех страниц и записывает их в settings.json.

        Формат файла:
            {
                "und_char_pol": "Ошибка" | "Игнорировать" | "Заменить"
            }
        """
        res = {}
        for _, page in self.pages:
            res.update(page.save())
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=4, ensure_ascii=False)

    def collect_n_close(self) -> None:
        """Сохраняет настройки и закрывает диалог с результатом Accepted."""
        self.collect()
        self.accept()


class SquareButton(QPushButton):
    """Кнопка, которая всегда квадратная, но тянется по высоте родителя."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(24, 24)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return w

    def sizeHint(self):
        s = super().sizeHint()
        s.setWidth(s.height())
        return s

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # держим ширину равной высоте (квадрат по меньшей стороне)
        h = self.height()
        if self.width() != h:
            self.setFixedWidth(h)


class MiniPlayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("miniPlayer")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        self.btn_play = SquareButton()
        self.btn_play.setObjectName("playButton")
        self.btn_pause = SquareButton()
        self.btn_pause.setObjectName("pauseButton")
        self.btn_pause.hide()

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("playerSlider")
        self.slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.slider.setRange(0, 0)

        lay.addWidget(self.btn_play, 0)
        lay.addWidget(self.btn_pause, 0)
        lay.addWidget(self.slider, 1)

        self.btn_play.clicked.connect(self.play)
        self.btn_pause.clicked.connect(self.pause)
        self.player.positionChanged.connect(self.slider.setValue)
        self.player.durationChanged.connect(self.slider.setMaximum)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.player.mediaStatusChanged.connect(self.on_media_status)

    def play(self):
        self.player.play()
        self.btn_play.hide()
        self.btn_pause.show()

    def pause(self):
        self.player.pause()
        self.btn_pause.hide()
        self.btn_play.show()

    def reload_source(self, path: str = "temp_morse.wav"):
        from pathlib import Path
        self.player.stop()
        self.player.setSource(QUrl())        # сброс старого
        self.slider.setRange(0, 0)           # чтобы не остался максимум от прошлого файла
        self.slider.setValue(0)
        if Path(path).exists():
            self.player.setSource(QUrl.fromLocalFile(path))

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.pause()
# ============================================================
#   Точка входа
# ============================================================

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setStyleSheet(build_app_qss(get_palette()))

    # Создаём главное окно и наполняем его через Ui_MainWindow
    win = QMainWindow()

    ui = Ui_MainWindow()
    ui.setupUi(win)

    win.show()
    sys.exit(app.exec())