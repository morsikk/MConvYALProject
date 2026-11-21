# ============================================================
#   ИМПОРТЫ
# ============================================================

import json
import os
import sys
from pathlib import Path

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
    QSizePolicy,
    QGridLayout,
)
from PyQt6.QtCore import QSize, Qt, pyqtSignal, QUrl, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor, QKeyEvent
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from Paths import data_path, resource_path
from Settings import save_settings, reset_settings, SETTINGS, DEFAULT_SETTINGS


# ============================================================
#   ТЕМА: определение, палитры, QSS
# ============================================================


def detect_system_theme() -> str:
    """
    Определяет ТОЛЬКО системную схему ("light"/"dark").
    Fallback — "dark".
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


def detect_theme() -> str:
    """
    Итоговая тема с учётом настройки SETTINGS["theme"]:
        "Системная" -> системная схема
        "Светлая"   -> "light"
        "Тёмная"    -> "dark"
    """
    mode = SETTINGS.get("theme", DEFAULT_SETTINGS["theme"])
    if mode == "Светлая":
        return "light"
    if mode == "Тёмная":
        return "dark"
    # "Системная" или что-то неизвестное
    return detect_system_theme()


# ------------------------------------------------------------
#   Палитры
# ------------------------------------------------------------

DARK_PALETTE = {
    "up_arrow": "svg/arrow_up_light.svg",
    "down_arrow": "svg/arrow_down_light.svg",
    "radio_off": "svg/radio_off_dark.svg",
    "radio_off_hover": "svg/radio_off_hover_dark.svg",
    "radio_on": "svg/radio_on_dark.svg",
    "radio_on_hover": "svg/radio_on_hover_dark.svg",
    "play": "svg/play_light.svg",
    "pause": "svg/pause_light.svg",
    "bg": "#1e1e1e",
    "panel": "#252526",
    "fg": "#e0e0e0",
    "accent": "#0e639c",
    "accent_fg": "#ffffff",
    "input_bg": "#1b1b1c",
    "input_border": "#3c3c3c",
    "button_bg": "#2d2d30",
    "button_border": "#3c3c3c",
    "button_hover": "#3a3a3d",
    "sel_bg": "#264f78",
    "sel_fg": "#ffffff",
    "panel_border": "#3c3c3c",
    "fg_muted": "#9a9a9a",
    "header_bg": "#252526",
    "header_border": "#3c3c3c",
    "scrollbar": "#3c3c3c",
    "scrollbar_hover": "#4a4a4a",
    "accent_hover": "#1177bb",
}

LIGHT_PALETTE = {
    "up_arrow": "svg/arrow_up_dark.svg",
    "down_arrow": "svg/arrow_down_dark.svg",
    "radio_off": "svg/radio_off_light.svg",
    "radio_off_hover": "svg/radio_off_hover_light.svg",
    "radio_on": "svg/radio_on_light.svg",
    "radio_on_hover": "svg/radio_on_hover_light.svg",
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
    """Возвращает словарь цветов для текущей темы."""
    return DARK_PALETTE if detect_theme() == "dark" else LIGHT_PALETTE


def build_app_palette(p: dict) -> QPalette:
    """Строит QPalette из словаря цветов."""
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
    Строит строку QSS.

    ВАЖНО: пути к SVG-иконкам подставляются через resource_path(),
    чтобы QSS содержал абсолютные пути. Иначе Qt ищет url()
    относительно текущей рабочей директории, и в exe иконки
    не находятся.
    """

    # Разрешаем относительные пути палитры в абсолютные (для QSS url()).
    # Разделитель в QSS — всегда '/' (прямой слэш), даже на Windows.
    def _rp(rel_key: str) -> str:
        return resource_path(p[rel_key]).replace("\\", "/")

    up_arrow = _rp("up_arrow")
    down_arrow = _rp("down_arrow")
    radio_off = _rp("radio_off")
    radio_off_hover = _rp("radio_off_hover")
    radio_on = _rp("radio_on")
    radio_on_hover = _rp("radio_on_hover")
    play_icon = _rp("play")
    pause_icon = _rp("pause")

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
        icon: url({up_arrow});
        qproperty-iconSize: 8px 8px;
    }}
    QPushButton#downButton {{
        icon: url({down_arrow});
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
        image: url({up_arrow});
        width: 8px;
        height: 5px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
    }}
    QSpinBox::down-arrow {{
        image: url({down_arrow});
        width: 8px;
        height: 5px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
    }}

    /* --- Комбобоксы: стрелка и выпадающая кнопка --- */
    QComboBox::down-arrow {{
        image: url({down_arrow});
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
        image: url({radio_off});
    }}
    QRadioButton::indicator:hover {{
        image: url({radio_off_hover});
    }}
    QRadioButton::indicator:checked {{
        image: url({radio_on});
    }}
    QRadioButton::indicator:checked:hover {{
        image: url({radio_on_hover});
    }}
    QRadioButton::indicator:disabled {{
        image: url({radio_off});
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
        icon: url({play_icon});
    }}
    QPushButton#pauseButton{{
        icon: url({pause_icon});
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

def apply_theme() -> None:
    """Пересобирает палитру и QSS по текущим настройкам."""
    app = QApplication.instance()
    if app is None:
        return
    p = get_palette()
    app.setPalette(build_app_palette(p))
    app.setStyleSheet(build_app_qss(p))


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
    """

    def __init__(self) -> None:
        super().__init__()

        self._rows: dict[str, tuple[QLabel, QWidget]] = {}

        self.mFLayout = QFormLayout(self)
        self.mFLayout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        self.typeCombo = QComboBox()
        self.operCombo = QComboBox()
        self.inpSpin = QSpinBox()
        self.inpSpin.setRange(2, 36)
        self.operSpin = QSpinBox()
        self.operSpin.setRange(2, 36)
        self.alphabetCombo = QComboBox()
        self.keyEdit = QLineEdit()
        self.keyEdit.setPlaceholderText("Ключ...")

        self.directionLayout = QHBoxLayout()
        self.codeRadio = QRadioButton("Кодировать")
        self.codeRadio.setObjectName("codeRadio")
        self.decodeRadio = QRadioButton("Декодировать")
        self.decodeRadio.setChecked(True)
        self.directionLayout.addWidget(self.codeRadio)
        self.directionLayout.addWidget(self.decodeRadio)

        self.directionWidget = QWidget()
        self.directionWidget.setObjectName("directionWidget")
        self.directionWidget.setLayout(self.directionLayout)
        self.directionLayout.setContentsMargins(0, 0, 0, 0)

        self.mFLayout.addRow("Тип:", self.typeCombo)
        self._add_row("operCombo", "Операция:", self.operCombo)
        self._add_row("inpSpin", "Основание ввода:", self.inpSpin)
        self._add_row("operSpin", "Основание вывода:", self.operSpin)
        self._add_row("alphabetCombo", "Алфавит:", self.alphabetCombo)
        self._add_row("keyEdit", "Ключ:", self.keyEdit)
        self._add_row_widget("direction", None, self.directionWidget)

    def _add_row(self, name: str, label_text: str, widget: QWidget) -> None:
        label = QLabel(label_text)
        self.mFLayout.addRow(label, widget)
        self._rows[name] = (label, widget)

    def _add_row_widget(self, name: str, label_text, widget: QWidget) -> None:
        if label_text is None:
            self.mFLayout.addRow(widget)
            self._rows[name] = (None, widget)
        else:
            label = QLabel(label_text)
            self.mFLayout.addRow(label, widget)
            self._rows[name] = (label, widget)

    def show_only(self, *names: str) -> None:
        wanted = set(names)
        for name, (label, widget) in self._rows.items():
            visible = name in wanted
            if label is not None:
                label.setVisible(visible)
            widget.setVisible(visible)

    def hide_row(self, name: str) -> None:
        label, widget = self._rows[name]
        if label is not None:
            label.hide()
        widget.hide()

    def show_row(self, name: str) -> None:
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
    """

    def setupUi(self, MainWindow: QMainWindow) -> None:
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(928, 563)
        MainWindow.setWindowTitle("Мультиконвертер")

        self.mWidget = QWidget(parent=MainWindow)
        self.mWidget.setObjectName("mWidget")
        self.mVLayout = QVBoxLayout(self.mWidget)
        self.mVLayout.setContentsMargins(8, 8, 8, 8)
        self.mVLayout.setSpacing(8)

        self.tBarWidget = QWidget(parent=self.mWidget)
        self.tBarWidget.setMaximumSize(QtCore.QSize(16777215, 80))
        self.tBarWidget.setObjectName("tBarWidget")
        self.tBarHLayout = QHBoxLayout(self.tBarWidget)
        self.tBarHLayout.setContentsMargins(8, 6, 8, 6)
        self.player = MiniPlayer()
        self.tBarHLayout.addWidget(self.player)
        self.mVLayout.addWidget(self.tBarWidget)
        self.tBarWidget.hide()

        self.workspace = QSplitter(parent=self.mWidget)
        self.workspace.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.workspace.setObjectName("workspace")

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

        self.actionListWidget = QWidget(parent=self.workspace)
        self.actionListWidget.setMaximumSize(QtCore.QSize(275, 16777215))
        self.actionListWidget.setObjectName("actionListWidget")
        self.actionListVLayout = QVBoxLayout(self.actionListWidget)
        self.actionListVLayout.setContentsMargins(0, 0, 0, 0)
        self.actionListVLayout.setSpacing(1)

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

        self.scrollArea = QScrollArea(parent=self.actionListWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.actionsWidget = QWidget()
        self.actionsWidget.setObjectName("actionsWidget")
        self.scrollArea.setWidget(self.actionsWidget)
        self.actionListVLayout.addWidget(self.scrollArea)

        self.addActionButton = QPushButton()
        self.addActionButton.setText("Добавить действие...")

        self.executeButton = QPushButton()
        self.executeButton.setText("Выполнить")
        self.executeButton.setStyleSheet("font-weight: bold;")

        self.actionsLayout = QVBoxLayout(self.actionsWidget)
        self.actionsLayout.setContentsMargins(5, 5, 5, 5)
        self.actionsLayout.setSpacing(5)
        self.actionsLayout.addWidget(self.executeButton)
        self.actionsLayout.addWidget(self.addActionButton)
        self.actionsLayout.addStretch()

        self.outTextWidget = QWidget(parent=self.workspace)
        self.outTextWidget.setObjectName("outTextWidget")
        self.outTextVLayout = QVBoxLayout(self.outTextWidget)
        self.outTextVLayout.setContentsMargins(0, 0, 0, 0)
        self.outText = QPlainTextEdit(parent=self.outTextWidget)
        self.outText.setReadOnly(True)
        self.outText.setObjectName("outText")
        self.outText.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.outText.setWordWrapMode(
            QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.outTextVLayout.addWidget(self.outText)

        self.workspace.addWidget(self.inpTextWidget)
        self.workspace.addWidget(self.actionListWidget)
        self.workspace.addWidget(self.outTextWidget)
        self.workspace.setSizes([400, 345, 400])

        self.mVLayout.addWidget(self.workspace)
        MainWindow.setCentralWidget(self.mWidget)

        self.menubar = QMenuBar(parent=MainWindow)
        self.menubar.setObjectName("menubar")
        self.fileMenu = QMenu(parent=self.menubar)
        self.fileMenu.setObjectName("fileMenu")
        self.fileMenu.setTitle("Файл")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

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

        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.saveAsAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.settingsAction)
        self.menubar.addAction(self.fileMenu.menuAction())

        self.morsePlayerAction = QtGui.QAction(parent=MainWindow)
        self.morsePlayerAction.setObjectName("morsePlayerAction")
        self.morsePlayerAction.setText("Плеер морзе")
        self.morsePlayerAction.setEnabled(False)

        self.brailleInputAction = QtGui.QAction(parent=MainWindow)
        self.brailleInputAction.setObjectName("brailleInputAction")
        self.brailleInputAction.setText("Ввод Брайля")

        self.makeAlphabetAction = QMenu("Создать алфавит...", parent=MainWindow)
        self.makeAlphabetAction.setObjectName("makeAlphabetAction")

        self.makeBrailleAction = QtGui.QAction("Брайль", parent=MainWindow)
        self.makeBrailleAction.setObjectName("makeBrailleAction")
        self.makeAlphabetAction.addAction(self.makeBrailleAction)

        self.makeMorseAction = QtGui.QAction("Морзе", parent=MainWindow)
        self.makeMorseAction.setObjectName("makeMorseAction")
        self.makeAlphabetAction.addAction(self.makeMorseAction)

        self.makeNumSysAction = QtGui.QAction("Системы счисления", parent=MainWindow)
        self.makeNumSysAction.setObjectName("makeNumSysAction")
        self.makeAlphabetAction.addAction(self.makeNumSysAction)

        self.makeCiphersAction = QtGui.QAction("Шифры", parent=MainWindow)
        self.makeCiphersAction.setObjectName("makeCiphersAction")
        self.makeAlphabetAction.addAction(self.makeCiphersAction)

        self.toolsMenu = QMenu(parent=self.menubar)
        self.toolsMenu.setObjectName("toolsMenu")
        self.toolsMenu.setTitle("Инструменты")
        self.toolsMenu.addAction(self.morsePlayerAction)
        self.toolsMenu.addAction(self.brailleInputAction)
        self.toolsMenu.addSeparator()
        self.toolsMenu.addMenu(self.makeAlphabetAction)
        self.menubar.addAction(self.toolsMenu.menuAction())


# ============================================================
#   ActionWidget — карточка одного действия
# ============================================================


class ActionWidget(QWidget):
    """
    Виджет одного действия в списке.
    """

    removed = pyqtSignal(object)
    move_up = pyqtSignal(object)
    move_down = pyqtSignal(object)

    # Относительные пути (разрешаются через resource_path при обращении)
    ALPHABETS_JSON = "alphabets/alphabets.json"

    CIPHER_KEYS = ["caesar", "vigenere", "A1Z26", "atbash", "playfair"]

    CIPHER_FIELDS = {
        "caesar": ("operCombo", "alphabetCombo", "operSpin", "direction"),
        "vigenere": ("operCombo", "alphabetCombo", "keyEdit", "direction"),
        "A1Z26": ("operCombo", "alphabetCombo", "direction"),
        "atbash": ("operCombo", "alphabetCombo", "direction"),
        "playfair": ("operCombo", "alphabetCombo", "keyEdit", "direction"),
    }

    def __init__(self) -> None:
        super().__init__()

        self.mFLayout = OperationForm()
        self.mFLayout.setObjectName("mFLayout")

        vLayout = QVBoxLayout(self)
        hLayout = QHBoxLayout()
        hLayout.setSpacing(6)

        self.label = QLabel()
        self.set_number(1)

        self.upButton = QPushButton()
        self.upButton.setObjectName("upButton")
        self.upButton.setToolTip("Переместить вверх")
        self.upButton.clicked.connect(lambda: self.move_up.emit(self))

        self.downButton = QPushButton()
        self.downButton.setObjectName("downButton")
        self.downButton.setToolTip("Переместить вниз")
        self.downButton.clicked.connect(lambda: self.move_down.emit(self))

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

        self.mFLayout.typeCombo.addItems(
            ["Морзе", "Системы счисления", "Шифры", "Брайль", "Бинарный код"]
        )
        self.mFLayout.typeCombo.currentIndexChanged.connect(self.on_type_changed)
        self.mFLayout.typeCombo.setCurrentIndex(0)
        self.on_type_changed(0)

        self.mFLayout.operCombo.currentIndexChanged.connect(self.on_cipher_changed)
        self.mFLayout.alphabetCombo.currentIndexChanged.connect(
            self.on_alphabet_changed
        )

        self.on_cipher_changed(self.mFLayout.operCombo.currentIndex())

    # ------------------------------------------------------------------ #
    #  Вспомогательные методы чтения json
    # ------------------------------------------------------------------ #

    @classmethod
    def _load_alps(cls) -> dict:
        """Читает единый файл alphabets.json (из упакованных ресурсов)."""
        with open(resource_path(cls.ALPHABETS_JSON), "r", encoding="utf-8") as fp:
            return json.load(fp)

    @staticmethod
    def _fill_combo(combo, items: dict) -> None:
        combo.clear()
        for meta in items.values():
            combo.addItem(meta["name"], meta["data"])

    # ------------------------------------------------------------------ #
    #  Обработчики
    # ------------------------------------------------------------------ #

    def on_alphabet_changed(self, index: int) -> None:
        f = self.mFLayout
        if f.typeCombo.currentIndex() != 2:
            return
        if f.operCombo.currentIndex() == 0:
            self._update_caesar_spin_range()

    def on_type_changed(self, index: int) -> None:
        f = self.mFLayout
        alps = self._load_alps()

        match index:
            case 0:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["morse"])

            case 1:
                f.show_only("inpSpin", "operSpin", "alphabetCombo")
                label, _ = f._rows["operSpin"]
                if label is not None:
                    label.setText("Основание вывода:")
                f.inpSpin.setRange(2, 36)
                f.operSpin.setRange(2, 36)
                self._fill_combo(f.alphabetCombo, alps["number_systems"])

            case 2:
                self._fill_combo(
                    f.operCombo,
                    {k: alps["ciphers"][k] for k in self.CIPHER_KEYS},
                )
                self._fill_combo(f.alphabetCombo, alps["ciphers"]["alps"])
                self.on_cipher_changed(f.operCombo.currentIndex())

            case 3:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["braille"])

            case 4:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["binary"])

    def on_cipher_changed(self, index: int) -> None:
        f = self.mFLayout
        if f.typeCombo.currentIndex() != 2:
            return

        cipher_key = self.CIPHER_KEYS[index]
        f.show_only(*self.CIPHER_FIELDS[cipher_key])

        label, _ = f._rows["operSpin"]
        if label is not None:
            label.setText("Сдвиг:")

        if cipher_key == "caesar":
            self._update_caesar_spin_range()

    def _update_caesar_spin_range(self) -> None:
        """Длина алфавита берётся из упакованного ресурса."""
        f = self.mFLayout
        code = f.alphabetCombo.currentData()  # "ru" / "en"
        n = 33
        if code:
            try:
                # ВАЖНО: файл алфавита — read-only ресурс -> resource_path
                with open(
                    resource_path(f"alphabets/ciphers/{code}.json"),
                    "r",
                    encoding="utf-8",
                ) as fp:
                    data = json.load(fp)
                letters = data.get("letters", "")
                if letters:
                    n = len(letters)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        f.operSpin.setRange(1, max(1, n - 1))
        if f.operSpin.value() > n - 1:
            f.operSpin.setValue(max(1, n - 1))

    # ------------------------------------------------------------------ #
    #  Прочее
    # ------------------------------------------------------------------ #

    def set_number(self, n: int) -> None:
        self.label.setText(f"Действие {n}")

    def set_move_buttons_enabled(self, can_up: bool, can_down: bool) -> None:
        self.upButton.setVisible(can_up)
        self.downButton.setVisible(can_down)

    def delete(self) -> None:
        self.removed.emit(self)
        self.setParent(None)
        self.deleteLater()


# ============================================================
#   Настройки: страница, диалог
# ============================================================

# ============================================================
#   Настройки: базовый каркас страницы
# ============================================================


class SettingsPage(QWidget):
    """
    Базовый каркас страницы настроек.

    Даёт:
        - стандартные отступы и spacing;
        - крупный заголовок страницы;
        - готовый QFormLayout для полей;
        - stretch внизу.

    Наследники:
        - в __init__ вызывают super().__init__(title);
        - добавляют поля через self.add_row(...) / self.add_section(...);
        - переопределяют load() / save().
    """

    # Заголовок страницы. Переопределяется в наследниках.
    title: str = "Страница"

    def __init__(self, title: str | None = None) -> None:
        super().__init__()

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(24, 24, 24, 24)
        self._root.setSpacing(16)

        page_title = title if title is not None else self.title
        self._title_label = QLabel(page_title)
        self._title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        self._root.addWidget(self._title_label)

        self._form = QFormLayout()
        self._form.setSpacing(12)
        self._root.addLayout(self._form)

        self._root.addStretch()

    # ------------------------------------------------------------------ #
    #  API для наследников
    # ------------------------------------------------------------------ #

    def add_row(self, label: str | QWidget, widget: QWidget) -> None:
        """Добавляет строку в основную форму страницы."""
        self._form.addRow(label, widget)

    def add_section(self, title: str) -> QFormLayout:
        """
        Добавляет подраздел с собственным заголовком и возвращает
        его QFormLayout, чтобы наследник добавил туда строки.
        """
        label = QLabel(title)
        label.setFont(QFont("", 16, QFont.Weight.Bold))
        self._root.insertWidget(self._root.count() - 1, label)  # перед stretch

        form = QFormLayout()
        form.setSpacing(12)
        self._root.insertLayout(self._root.count() - 1, form)
        return form

    # ------------------------------------------------------------------ #
    #  Переопределяемое
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Заполнить виджеты значениями из SETTINGS."""
        pass

    def save(self) -> dict:
        """Вернуть словарь значений из виджетов."""
        return {}


class GeneralPage(SettingsPage):
    """«Приложение»: тема и версия."""

    title = "Приложение"

    def __init__(self) -> None:
        super().__init__()

        self.themeCombo = QComboBox()
        self.themeCombo.addItems(["Системная", "Светлая", "Тёмная"])
        self.add_row("Тема оформления:", self.themeCombo)

        # Подраздел «Версия» — только для чтения
        version_form = self.add_section("Версия")
        self.versionLabel = QLabel(DEFAULT_SETTINGS["version"])
        self.versionLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        version_form.addRow("Текущая версия:", self.versionLabel)

    def load(self) -> None:
        theme = SETTINGS.get("theme", DEFAULT_SETTINGS["theme"])
        idx = self.themeCombo.findText(theme)
        if idx >= 0:
            self.themeCombo.setCurrentIndex(idx)

        self.versionLabel.setText(
            SETTINGS.get("version", DEFAULT_SETTINGS["version"])
        )

    def save(self) -> dict:
        return {"theme": self.themeCombo.currentText()}


class ConversionPage(SettingsPage):
    """«Конвертация»: поведение при неизвестных символах."""

    title = "Конвертация"

    def __init__(self) -> None:
        super().__init__()

        self.undCharPolCombo = QComboBox()
        self.undCharPolCombo.addItems(["Предупреждение", "Игнорировать", "Заменить"])
        self.add_row("Действие с неизвестным символом:", self.undCharPolCombo)

        # Поле для ввода символа замены
        self.replacementEdit = QLineEdit()
        self.replacementEdit.setPlaceholderText("Символ замены...")
        self.replacementEdit.setMaxLength(10)
        self._replacement_row = self._form.rowCount()
        self.add_row("Символ замены:", self.replacementEdit)

        # Показываем/скрываем поле в зависимости от выбора
        self.undCharPolCombo.currentTextChanged.connect(self._on_policy_changed)
        self._on_policy_changed(self.undCharPolCombo.currentText())

    def _on_policy_changed(self, text: str) -> None:
        """Показывает поле замены только при выборе 'Заменить'."""
        show = text == "Заменить"
        # Находим label и widget в форме и скрываем/показываем
        label = self._form.labelForField(self.replacementEdit)
        if label is not None:
            label.setVisible(show)
        self.replacementEdit.setVisible(show)
        if show:
            self.replacementEdit.setFocus()

    def load(self) -> None:
        pol = SETTINGS.get("und_char_pol", DEFAULT_SETTINGS["und_char_pol"])
        idx = self.undCharPolCombo.findText(pol)
        if idx >= 0:
            self.undCharPolCombo.setCurrentIndex(idx)

        replacement = SETTINGS.get("replacement", DEFAULT_SETTINGS["replacement"])
        self.replacementEdit.setText(replacement)

        self._on_policy_changed(self.undCharPolCombo.currentText())

    def save(self) -> dict:
        result = {"und_char_pol": self.undCharPolCombo.currentText()}
        if self.undCharPolCombo.currentText() == "Заменить":
            result["replacement"] = self.replacementEdit.text()
        return result


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(760, 520)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(200)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)

        self.stack = QStackedWidget()

        self.pages = [
            ("Приложение", GeneralPage()),
            ("Конвертация", ConversionPage()),
        ]

        for name, page in self.pages:
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(0, 40))
            self.nav.addItem(item)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

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

        self.resetButton = QPushButton("Сбросить до умолчаний")
        self.resetButton.clicked.connect(self.reset_to_defaults)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.nav)
        content_layout.addWidget(self.stack, 1)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.addWidget(self.resetButton)
        footer_layout.addStretch()
        footer_layout.addWidget(buttons)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(content_layout, 1)
        main_layout.addWidget(footer)

        self.load()

    def load(self) -> None:
        for _, page in self.pages:
            page.load()

    def collect(self) -> None:
        res = {}
        for _, page in self.pages:
            res.update(page.save())
        save_settings(res)
        apply_theme()   # мгновенно применяем тему

    def collect_n_close(self) -> None:
        self.collect()
        self.accept()

    def reset_to_defaults(self) -> None:
        """Удаляет settings.json и откатывает все страницы к дефолтам."""
        reset_settings()
        self.load()


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
        self.slider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
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
        """
        temp_morse.wav — ИЗМЕНЯЕМЫЙ файл, генерируется во время работы.
        Если path относительный — кладём рядом с exe через data_path.
        Если абсолютный — используем как есть.
        """
        if not os.path.isabs(path):
            path = data_path(path)

        self.player.stop()
        self.player.setSource(QUrl())
        self.slider.setRange(0, 0)
        self.slider.setValue(0)
        if Path(path).exists():
            self.player.setSource(QUrl.fromLocalFile(path))

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.pause()


# ============================================================
#   Диалог для ввода Брайля
# ============================================================


class BrailleDialog(QDialog):
    def __init__(self, /, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ввод Брайля")
        self._SEPARATORS = set(" .,!?;:-—()[]{}«»\"'\n\t")

        self._NUMPAD_TO_DOT = {
            Qt.Key.Key_7: 0,
            Qt.Key.Key_8: 1,
            Qt.Key.Key_4: 2,
            Qt.Key.Key_5: 3,
            Qt.Key.Key_1: 4,
            Qt.Key.Key_2: 5,
        }

        self.mHBoxLayout = QHBoxLayout(self)

        self.leftVLayout = QVBoxLayout()
        self.mHBoxLayout.addLayout(self.leftVLayout, 1)

        self.leftVLayout.addWidget(QLabel("Алфавит:"))
        self.alphabetCombo = QComboBox()
        self.leftVLayout.addWidget(self.alphabetCombo)

        self.previewLabel = QLabel("—")
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setMinimumHeight(56)
        self.previewLabel.setStyleSheet(
            "font-size: 28px; font-weight: bold; "
            "border: 1px solid palette(mid); border-radius: 6px; padding: 4px;"
        )
        self.leftVLayout.addWidget(self.previewLabel)

        self.modeLabel = QLabel("")
        self.modeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.modeLabel.setStyleSheet("color: palette(mid);")
        self.leftVLayout.addWidget(self.modeLabel)

        self.rightGLayout = QGridLayout()
        self.leftVLayout.addLayout(self.rightGLayout, 1)

        self.brailleOut = QPlainTextEdit()
        self.brailleOut.setReadOnly(True)
        self.mHBoxLayout.addWidget(self.brailleOut, 1)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)
        self.leftVLayout.addWidget(self.buttonBox)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.pressed = [False] * 6
        self._buffer: list[str] = []
        self._alphabet: dict = {}
        self._dot_index: dict[frozenset[int], str] = {}
        self._digits: dict = {}
        self._prefixes: dict = {}

        self._num_mode = False
        self._capital_word_mode = False
        self._capital_one = False
        self._grade1_one = False

        for col in range(3):
            self.rightGLayout.setColumnStretch(col, 1)
        for row in range(3):
            self.rightGLayout.setRowStretch(row, 1)

        for i in range(6):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setObjectName(f"dot_{i}")
            btn.toggled.connect(self.on_dot_toggled)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.rightGLayout.addWidget(btn, i // 2, i % 2)

        bspaceBtn = QPushButton("<-")
        bspaceBtn.clicked.connect(self.backspace)
        bspaceBtn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.rightGLayout.addWidget(bspaceBtn, 0, 2)

        enterBtn = QPushButton("↵")
        enterBtn.clicked.connect(self.enter)
        enterBtn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.rightGLayout.addWidget(enterBtn, 1, 2, 2, 1)

        self._load_alphabets()

    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def hideEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        super().hideEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and self.isVisible():
            if self._handle_key(event):
                return True
        return super().eventFilter(obj, event)

    def _handle_key(self, event: QKeyEvent) -> bool:
        key = event.key()

        if key in self._NUMPAD_TO_DOT:
            idx = self._NUMPAD_TO_DOT[key]
            btn = self.findChild(QPushButton, f"dot_{idx}")
            if btn is not None:
                btn.toggle()
            return True

        if key == Qt.Key.Key_Backspace:
            self.backspace()
            return True

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enter()
            return True

        return False

    # ------------------------------------------------------------------ #
    #  Загрузка алфавитов (все пути — через resource_path)
    # ------------------------------------------------------------------ #
    def _alphabets_dir(self) -> str:
        return resource_path("alphabets/braille")

    def _load_alphabets(self):
        meta_path = resource_path("alphabets/alphabets.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                alps = json.load(f)
            braille_meta = alps.get("braille", {})
        except (OSError, json.JSONDecodeError):
            braille_meta = {}

        if not braille_meta:
            d = self._alphabets_dir()
            if os.path.isdir(d):
                for fname in sorted(os.listdir(d)):
                    if fname.endswith(".json"):
                        data = os.path.splitext(fname)[0]
                        braille_meta[data] = {"name": data, "data": data}

        self.alphabetCombo.clear()
        for meta in braille_meta.values():
            self.alphabetCombo.addItem(meta["name"], meta["data"])

        self.alphabetCombo.currentIndexChanged.connect(self._on_alphabet_changed)
        if self.alphabetCombo.count() > 0:
            self._on_alphabet_changed(0)

    def _on_alphabet_changed(self, index: int):
        if index < 0:
            return
        data = self.alphabetCombo.itemData(index)
        path = resource_path(f"alphabets/braille/{data}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._alphabet = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._alphabet = {}
        self._rebuild_dot_index()
        self._update_preview()

    def _rebuild_dot_index(self):
        self._dot_index.clear()
        if not self._alphabet:
            return
        for section in ("letters", "punctuation", "math"):
            for sym, info in self._alphabet.get(section, {}).items():
                dots = info.get("dots")
                if dots is None:
                    continue
                self._dot_index.setdefault(frozenset(dots), sym)
        self._digits = self._alphabet.get("digits", {})
        self._prefixes = self._alphabet.get("prefixes", {})

    def on_dot_toggled(self, checked):
        btn: QPushButton = self.sender()
        idx = int(btn.objectName().split("_")[1])
        self.pressed[idx] = checked
        btn.setText("•" if checked else "")
        self._update_preview()

    def _current_dots(self) -> frozenset[int]:
        return frozenset(i for i, v in enumerate(self.pressed) if v)

    def _current_dots_list(self) -> list[int]:
        return [i for i, v in enumerate(self.pressed) if v]

    def _reset_dots(self):
        for i in range(6):
            btn = self.findChild(QPushButton, f"dot_{i}")
            if btn is not None:
                btn.setChecked(False)

    def _prefix_kind(self, dots_list: list[int]) -> str | None:
        if not dots_list or not self._prefixes:
            return None
        for key, pmeta in self._prefixes.items():
            if dots_list == list(pmeta["dots"]):
                return {
                    "num_prefix": "num",
                    "capital_prefix": "capital",
                    "capital_word_prefix": "capital_word",
                    "grade1_symbol": "grade1",
                }.get(key)
        return None

    def _char_from_dots(self, dots: frozenset[int]) -> str | None:
        if not dots:
            return None

        if self._num_mode:
            for digit, info in self._digits.items():
                if frozenset(info["dots"]) == dots:
                    return digit
            return None

        ch = self._dot_index.get(dots)
        if ch is None:
            return None

        if ch.isalpha():
            if self._capital_word_mode or self._capital_one:
                return ch.upper()
            return ch.lower()
        return ch

    def backspace(self):
        if self._grade1_one:
            self._grade1_one = False
        elif self._capital_one:
            self._capital_one = False
        elif self._num_mode or self._capital_word_mode:
            self._num_mode = False
            self._capital_word_mode = False
        elif self._buffer:
            self._buffer.pop()
            self.brailleOut.setPlainText("".join(self._buffer))
        self._reset_dots()
        self._update_preview()

    def enter(self):
        dots = self._current_dots()
        dots_list = self._current_dots_list()

        if not dots:
            self._buffer.append("\n")
            self._reset_all_modes()
            self.brailleOut.setPlainText("".join(self._buffer))
            self._reset_dots()
            self._update_preview()
            return

        kind = self._prefix_kind(dots_list)
        if kind is not None:
            if kind == "num":
                self._num_mode = True
                self._capital_word_mode = False
                self._capital_one = False
                self._grade1_one = False
            elif kind == "capital_word":
                self._capital_word_mode = True
                self._num_mode = False
                self._capital_one = False
                self._grade1_one = False
            elif kind == "capital":
                if self._capital_word_mode:
                    self._reset_dots()
                    self._update_preview()
                    return
                if self._capital_one:
                    self._capital_word_mode = True
                    self._capital_one = False
                else:
                    self._capital_one = True
                self._num_mode = False
                self._grade1_one = False
            elif kind == "grade1":
                self._grade1_one = True
            self._reset_dots()
            self._update_preview()
            return

        ch = self._char_from_dots(dots)
        if ch is not None:
            self._buffer.append(ch)
            self.brailleOut.setPlainText("".join(self._buffer))

            if ch in self._SEPARATORS:
                self._num_mode = False
                self._capital_word_mode = False

            self._capital_one = False
            self._grade1_one = False

        self._reset_dots()
        self._update_preview()

    def _reset_all_modes(self):
        self._num_mode = False
        self._capital_word_mode = False
        self._capital_one = False
        self._grade1_one = False

    def _update_preview(self):
        dots = self._current_dots()
        dots_list = self._current_dots_list()

        modes = []
        if self._num_mode:
            modes.append("№ цифры")
        if self._capital_word_mode:
            modes.append("⇧⇧ слово")
        if self._capital_one:
            modes.append("⇧ одна")
        if self._grade1_one:
            modes.append("G1")
        self.modeLabel.setText(" | ".join(modes))

        if not dots:
            if self._num_mode:
                self.previewLabel.setText("№")
            elif self._capital_word_mode:
                self.previewLabel.setText("⇧⇧")
            elif self._capital_one:
                self.previewLabel.setText("⇧")
            elif self._grade1_one:
                self.previewLabel.setText("G1")
            else:
                self.previewLabel.setText("—")
            return

        kind = self._prefix_kind(dots_list)
        if kind is not None:
            self.previewLabel.setText(
                {
                    "num": "№",
                    "capital": "⇧",
                    "capital_word": "⇧⇧",
                    "grade1": "G1",
                }.get(kind, "?")
            )
            return

        ch = self._char_from_dots(dots)
        if ch is None:
            self.previewLabel.setText("?")
            return

        if self._num_mode:
            self.previewLabel.setText(f"{ch} (цифра)")
        elif ch.isalpha() and (self._capital_word_mode or self._capital_one):
            self.previewLabel.setText(f"{ch} (заглавная)")
        else:
            self.previewLabel.setText(ch)

    def _on_accept(self):
        text = self.brailleOut.toPlainText()
        parent = self.parent()
        out_edit = getattr(parent, "outText", None) if parent is not None else None
        if out_edit is not None and text:
            out_edit.insertPlainText(text)
        self.accept()


# ============================================================
#   Точка входа
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(build_app_qss(get_palette()))

    win = QMainWindow()

    ui = Ui_MainWindow()
    ui.setupUi(win)

    win.show()
    sys.exit(app.exec())
