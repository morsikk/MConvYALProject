# ============================================================
#   ИМПОРТЫ
# ============================================================

import json, sys, os, re
from pathlib import Path

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
    QMessageBox,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
    QFileDialog,
    QStyledItemDelegate,
    QTextEdit,
    QCheckBox,
)
from PyQt6.QtCore import QSize, Qt, pyqtSignal, QUrl, QEvent, QRegularExpression
from PyQt6.QtGui import (
    QFont,
    QPalette,
    QColor,
    QKeyEvent,
    QRegularExpressionValidator,
    QTextOption,
    QAction,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from Paths import data_path, resource_path
from Settings import save_settings, reset_settings, SETTINGS, DEFAULT_SETTINGS

# ============================================================
#   ТЕМА: определение, палитры, QSS
# ============================================================


def detect_system_theme() -> str:
    """Системная схема: 'light' / 'dark' (fallback — 'dark')."""
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
    """Итоговая тема с учётом SETTINGS['theme']."""
    mode = SETTINGS.get("theme", DEFAULT_SETTINGS["theme"])
    if mode == "Светлая":
        return "light"
    if mode == "Тёмная":
        return "dark"
    return detect_system_theme()


# ------------------------------------------------------------
#   Палитры
# ------------------------------------------------------------

DARK_PALETTE: dict[str, str] = {
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

LIGHT_PALETTE: dict[str, str] = {
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


def get_palette() -> dict[str, str]:
    """Палитра цветов для текущей темы."""
    return DARK_PALETTE if detect_theme() == "dark" else LIGHT_PALETTE


def build_app_palette(p: dict[str, str]) -> QPalette:
    """QPalette из словаря цветов."""
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


def build_app_qss(p: dict[str, str]) -> str:
    """
    Строка QSS для текущей палитры.

    Пути к SVG разрешаются через resource_path() и приводятся к '/' —
    иначе Qt ищет url() относительно cwd и в exe иконки не находятся.
    """

    def _rp(key: str) -> str:
        return resource_path(p[key]).replace("\\", "/")

    up_arrow, down_arrow = _rp("up_arrow"), _rp("down_arrow")
    radio_off, radio_off_hover = _rp("radio_off"), _rp("radio_off_hover")
    radio_on, radio_on_hover = _rp("radio_on"), _rp("radio_on_hover")
    play_icon, pause_icon = _rp("play"), _rp("pause")

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
        min-width: 20px; max-width: 20px;
        min-height: 20px; max-height: 20px;
        padding: 0px; border: none;
    }}
    QPushButton#upButton {{ icon: url({up_arrow}); qproperty-iconSize: 8px 8px; }}
    QPushButton#downButton {{ icon: url({down_arrow}); qproperty-iconSize: 8px 8px; }}

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
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {p['button_hover']}; }}
    QSpinBox::up-arrow {{
        image: url({up_arrow}); width: 8px; height: 5px;
        border-left: 4px solid transparent; border-right: 4px solid transparent;
    }}
    QSpinBox::down-arrow {{
        image: url({down_arrow}); width: 8px; height: 5px;
        border-left: 4px solid transparent; border-right: 4px solid transparent;
    }}

    /* --- Комбобоксы: стрелка и выпадающая кнопка --- */
    QComboBox::down-arrow {{
        image: url({down_arrow}); width: 8px; height: 5px;
        border-left: 4px solid transparent; border-right: 4px solid transparent;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding; subcontrol-position: top right;
        width: 20px; border-left: 1px solid {p['input_border']};
        background: {p['button_bg']};
    }}
    QComboBox::drop-down:hover {{ background: {p['button_hover']}; }}

    /* --- Радиокнопки --- */
    QRadioButton {{ background: transparent; spacing: 8px; padding: 2px 0; }}
    QRadioButton:disabled {{ color: {p['fg_muted']}; }}
    QRadioButton::indicator {{ width: 16px; height: 16px; image: url({radio_off}); }}
    QRadioButton::indicator:hover {{ image: url({radio_off_hover}); }}
    QRadioButton::indicator:checked {{ image: url({radio_on}); }}
    QRadioButton::indicator:checked:hover {{ image: url({radio_on_hover}); }}
    QRadioButton::indicator:disabled {{ image: url({radio_off}); }}
    QWidget#directionWidget {{ background: transparent; }}

    /* --- Скроллбары: убираем стрелки, оставляем ползунок --- */
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        width: 0; height: 0; background: transparent; border: none;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0; background: transparent; border: none;
    }}
    QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: {p['scrollbar']}; border-radius: 6px; min-width: 30px; }}
    QScrollBar::handle:horizontal:hover {{ background: {p['scrollbar_hover']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0; background: transparent; border: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
        width: 0; height: 0; background: transparent; border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    /* --- Мини-плеер --- */
    QWidget#miniPlayer {{
        background: {p['panel']};
        border: 1px solid {p['panel_border']};
        border-radius: 6px;
    }}
    QPushButton#playButton, QPushButton#pauseButton {{
        background: {p['button_bg']}; color: {p['fg']};
        border: 1px solid {p['button_border']}; border-radius: 4px;
        padding: 0px; font-size: 14px;
    }}
    QPushButton#playButton {{ icon: url({play_icon}); }}
    QPushButton#pauseButton {{ icon: url({pause_icon}); }}
    QPushButton#playButton:hover, QPushButton#pauseButton:hover {{
        background: {p['accent']}; color: {p['accent_fg']}; border-color: {p['accent']};
    }}
    QPushButton#playButton:pressed, QPushButton#pauseButton:pressed {{
        background: {p['accent_hover']};
    }}

    /* --- Слайдер плеера --- */
    QSlider {{ background: transparent; }}
    QSlider#playerSlider::groove:horizontal {{
        height: 4px; background: {p['input_border']}; border-radius: 2px;
    }}
    QSlider#playerSlider::handle:horizontal {{
        background: {p['accent']}; width: 14px; height: 14px;
        margin: -5px 0; border-radius: 7px;
    }}
    QSlider#playerSlider::handle:horizontal:hover {{ background: {p['accent_hover']}; }}
    QSlider#playerSlider::sub-page:horizontal {{ background: {p['accent']}; border-radius: 2px; }}

    /* --- Превью ввода Брайля --- */
    QLabel#braillePreviewLabel {{
        font-size: 32px; font-weight: bold;
        border: 1px solid {p['panel_border']}; border-radius: 6px; padding: 6px;
        background: {p['input_bg']}; color: {p['fg']};
    }}
    QLabel#braillePendingLabel {{
        font-size: 16px; color: {p['accent_fg']}; background: {p['accent']};
        border-radius: 4px; padding: 2px 6px;
    }}
    """


def apply_theme() -> None:
    """Пересобрать палитру и QSS по текущим настройкам."""
    app = QApplication.instance()
    if app is None:
        return
    p = get_palette()
    app.setPalette(build_app_palette(p))
    app.setStyleSheet(build_app_qss(p))


# ============================================================
#   Хелперы для statusbar
# ============================================================


def _status(widget: QWidget | None, message: str, timeout_ms: int = 0) -> None:
    """Показать сообщение в статусбаре окна-владельца (если он есть)."""
    if widget is None:
        return
    win = widget.window()
    if win is None:
        return
    sb = win.statusBar() if hasattr(win, "statusBar") else None
    if sb is not None:
        sb.showMessage(message, timeout_ms)


# ============================================================
#   OperationForm — форма параметров операции
# ============================================================


class OperationForm(QWidget):
    """
    Форма параметров одной операции.

    Поля:
        typeCombo       — тип операции (Морзе / системы счисления / шифры / Брайль / бинарь);
        operCombo       — конкретная операция (для шифров);
        inpSpin/operSpin — основания ввода/вывода (2..36);
        alphabetCombo   — выбор алфавита;
        keyEdit         — ключ шифра;
        codeRadio/decodeRadio — направление.

    Строки регистрируются в self._rows, чтобы их можно было
    показывать/скрывать через show_only().
    """

    def __init__(self) -> None:
        super().__init__()

        self._rows: dict[str, tuple[QLabel | None, QWidget]] = {}

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

    def _add_row_widget(
        self, name: str, label_text: str | None, widget: QWidget
    ) -> None:
        """Строка без подписи (label_text=None) или с подписью."""
        if label_text is None:
            self.mFLayout.addRow(widget)
            self._rows[name] = (None, widget)
        else:
            label = QLabel(label_text)
            self.mFLayout.addRow(label, widget)
            self._rows[name] = (label, widget)

    def show_only(self, *names: str) -> None:
        """Показать только перечисленные строки, остальные скрыть."""
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


class Ui_MainWindow:
    """Строитель интерфейса главного окна."""

    def setupUi(self, MainWindow: QMainWindow) -> None:
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(928, 563)
        MainWindow.setWindowTitle("Мультиконвертер")

        # --- Корневой виджет ---
        self.mWidget = QWidget(parent=MainWindow)
        self.mWidget.setObjectName("mWidget")
        self.mVLayout = QVBoxLayout(self.mWidget)
        self.mVLayout.setContentsMargins(8, 8, 8, 8)
        self.mVLayout.setSpacing(8)

        # --- Верхняя панель с плеером ---
        self.tBarWidget = QWidget(parent=self.mWidget)
        self.tBarWidget.setMaximumSize(QSize(16777215, 80))
        self.tBarWidget.setObjectName("tBarWidget")
        self.tBarHLayout = QHBoxLayout(self.tBarWidget)
        self.tBarHLayout.setContentsMargins(8, 6, 8, 6)
        self.player = MiniPlayer()
        self.tBarHLayout.addWidget(self.player)
        self.mVLayout.addWidget(self.tBarWidget)
        self.tBarWidget.hide()

        # --- Рабочая область: input | actions | output ---
        self.workspace = QSplitter(parent=self.mWidget)
        self.workspace.setOrientation(Qt.Orientation.Horizontal)
        self.workspace.setObjectName("workspace")

        # input
        self.inpTextWidget = QWidget(parent=self.workspace)
        self.inpTextWidget.setObjectName("inpTextWidget")
        self.inpTextVLayout = QVBoxLayout(self.inpTextWidget)
        self.inpTextVLayout.setContentsMargins(0, 0, 0, 0)
        self.inpText = QPlainTextEdit(parent=self.inpTextWidget)
        self.inpText.setObjectName("inpText")
        self.inpText.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.inpText.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.inpTextVLayout.addWidget(self.inpText)

        # actions
        self.actionListWidget = QWidget(parent=self.workspace)
        self.actionListWidget.setMaximumSize(QSize(275, 16777215))
        self.actionListWidget.setObjectName("actionListWidget")
        self.actionListVLayout = QVBoxLayout(self.actionListWidget)
        self.actionListVLayout.setContentsMargins(0, 0, 0, 0)
        self.actionListVLayout.setSpacing(1)

        self.actionListLabelsWidget = QWidget(parent=self.actionListWidget)
        self.actionListLabelsWidget.setMaximumSize(QSize(16777215, 30))
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

        # output
        self.outTextWidget = QWidget(parent=self.workspace)
        self.outTextWidget.setObjectName("outTextWidget")
        self.outTextVLayout = QVBoxLayout(self.outTextWidget)
        self.outTextVLayout.setContentsMargins(0, 0, 0, 0)
        self.outText = QPlainTextEdit(parent=self.outTextWidget)
        self.outText.setReadOnly(True)
        self.outText.setObjectName("outText")
        self.outText.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.outText.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.outTextVLayout.addWidget(self.outText)

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

        self.statusbar = QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.openAction = QAction(parent=MainWindow)
        self.openAction.setObjectName("openAction")
        self.openAction.setText("Открыть")

        self.saveAction = QAction(parent=MainWindow)
        self.saveAction.setObjectName("saveAction")
        self.saveAction.setText("Сохранить")
        self.saveAction.setEnabled(False)

        self.saveAsAction = QAction(parent=MainWindow)
        self.saveAsAction.setObjectName("saveAsAction")
        self.saveAsAction.setText("Сохранить как...")
        self.saveAsAction.setEnabled(False)

        self.settingsAction = QAction(parent=MainWindow)
        self.settingsAction.setObjectName("settingsAction")
        self.settingsAction.setText("Настройки")

        self.exportAlphabetAction = QAction(parent=MainWindow)
        self.exportAlphabetAction.setObjectName("exportAlphabetAction")
        self.exportAlphabetAction.setText("Экспортировать алфавит")

        self.importAlphabetAction = QAction(parent=MainWindow)
        self.importAlphabetAction.setObjectName("importAlphabetAction")
        self.importAlphabetAction.setText("Импортировать алфавит")

        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.saveAsAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exportAlphabetAction)
        self.fileMenu.addAction(self.importAlphabetAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.settingsAction)
        self.menubar.addAction(self.fileMenu.menuAction())

        self.morsePlayerAction = QAction(parent=MainWindow)
        self.morsePlayerAction.setObjectName("morsePlayerAction")
        self.morsePlayerAction.setText("Плеер морзе")
        self.morsePlayerAction.setEnabled(False)

        self.brailleInputAction = QAction(parent=MainWindow)
        self.brailleInputAction.setObjectName("brailleInputAction")
        self.brailleInputAction.setText("Ввод Брайля")

        self.makeAlphabetAction = QMenu("Создать алфавит...", parent=MainWindow)
        self.makeAlphabetAction.setObjectName("makeAlphabetAction")

        self.makeBrailleAction = QAction("Брайль", parent=MainWindow)
        self.makeBrailleAction.setObjectName("makeBrailleAction")
        self.makeAlphabetAction.addAction(self.makeBrailleAction)

        self.makeMorseAction = QAction("Морзе", parent=MainWindow)
        self.makeMorseAction.setObjectName("makeMorseAction")
        self.makeAlphabetAction.addAction(self.makeMorseAction)

        self.makeNumSysAction = QAction("Системы счисления", parent=MainWindow)
        self.makeNumSysAction.setObjectName("makeNumSysAction")
        self.makeAlphabetAction.addAction(self.makeNumSysAction)

        self.makeCiphersAction = QAction("Шифры", parent=MainWindow)
        self.makeCiphersAction.setObjectName("makeCiphersAction")
        self.makeAlphabetAction.addAction(self.makeCiphersAction)

        self.makeBinaryAction = QAction("Бинарный код", parent=MainWindow)
        self.makeBinaryAction.setObjectName("makeBinaryAction")
        self.makeAlphabetAction.addAction(self.makeBinaryAction)

        self.toolsMenu = QMenu(parent=self.menubar)
        self.toolsMenu.setObjectName("toolsMenu")
        self.toolsMenu.setTitle("Инструменты")
        self.toolsMenu.addAction(self.morsePlayerAction)
        self.toolsMenu.addAction(self.brailleInputAction)
        self.toolsMenu.addSeparator()
        self.toolsMenu.addMenu(self.makeAlphabetAction)
        self.menubar.addAction(self.toolsMenu.menuAction())

        self.statusbar.showMessage("Готово", 3000)


# ============================================================
#   ActionWidget — карточка одного действия
# ============================================================


class ActionWidget(QWidget):
    """Виджет одного действия в списке."""

    removed = pyqtSignal(object)
    move_up = pyqtSignal(object)
    move_down = pyqtSignal(object)

    ALPHABETS_JSON = "alphabets/alphabets.json"

    CIPHER_KEYS: list[str] = [
        "caesar",
        "vigenere",
        "A1Z26",
        "atbash",
        "playfair",
        "reverse",
        "columnar",
    ]

    # Какие поля показывать для каждого шифра
    CIPHER_FIELDS: dict[str, tuple[str, ...]] = {
        "caesar": ("operCombo", "alphabetCombo", "operSpin", "direction"),
        "vigenere": ("operCombo", "alphabetCombo", "keyEdit", "direction"),
        "A1Z26": ("operCombo", "alphabetCombo", "direction"),
        "atbash": ("operCombo", "alphabetCombo", "direction"),
        "playfair": ("operCombo", "alphabetCombo", "keyEdit", "direction"),
        "reverse": ("operCombo", "direction"),
        "columnar": ("operCombo", "alphabetCombo", "operSpin", "direction"),
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

    # ---------- работа с JSON ----------

    @classmethod
    def _load_alps(cls) -> dict:
        """alphabets.json: сначала data_path, затем resource_path."""
        for path in (
            data_path(cls.ALPHABETS_JSON),
            resource_path(cls.ALPHABETS_JSON),
        ):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fp:
                    return json.load(fp)
        raise FileNotFoundError("alphabets.json не найден")

    @staticmethod
    def _fill_combo(combo: QComboBox, items: dict) -> None:
        """Перезаполнить combo парами (name, key)."""
        combo.clear()
        for key, meta in items.items():
            combo.addItem(meta["name"], key)

    # ---------- обработчики ----------

    def on_alphabet_changed(self, index: int) -> None:
        f = self.mFLayout
        if f.typeCombo.currentIndex() != 2:
            return
        if f.operCombo.currentIndex() == 0:
            self._update_caesar_spin_range()
        _status(self, f"Алфавит: {f.alphabetCombo.currentText()}", 2000)

    def on_type_changed(self, index: int) -> None:
        f = self.mFLayout
        alps = self._load_alps()

        match index:
            case 0:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["morse"])
                _status(self, "Тип операции: Морзе", 2000)
            case 1:
                f.show_only("inpSpin", "operSpin", "alphabetCombo")
                label, _ = f._rows["operSpin"]
                if label is not None:
                    label.setText("Основание вывода:")
                f.inpSpin.setRange(2, 36)
                f.operSpin.setRange(2, 36)
                self._fill_combo(f.alphabetCombo, alps["number_systems"])
                _status(self, "Тип операции: Системы счисления", 2000)
            case 2:
                cipher_items = {k: alps["ciphers"][k] for k in self.CIPHER_KEYS}
                self._fill_combo(f.operCombo, cipher_items)
                self._fill_combo(f.alphabetCombo, alps["ciphers"]["alps"])
                self.on_cipher_changed(f.operCombo.currentIndex())
                _status(self, "Тип операции: Шифры", 2000)
            case 3:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["braille"])
                _status(self, "Тип операции: Брайль", 2000)
            case 4:
                f.show_only("alphabetCombo", "direction")
                self._fill_combo(f.alphabetCombo, alps["binary"])
                _status(self, "Тип операции: Бинарный код", 2000)

    def on_cipher_changed(self, index: int) -> None:
        f = self.mFLayout
        if f.typeCombo.currentIndex() != 2:
            return

        cipher_key = self.CIPHER_KEYS[index]
        f.show_only(*self.CIPHER_FIELDS[cipher_key])

        label, _ = f._rows["operSpin"]
        if label is not None:
            label.setText(
                "Сдвиг:"
                if cipher_key in ("caesar", "columnar") is False
                else ("Сдвиг:" if cipher_key == "caesar" else "Символов в строке:")
            )

        if cipher_key == "caesar":
            self._update_caesar_spin_range()
        elif cipher_key == "columnar":
            f.operSpin.setRange(1, 1000)
            if f.operSpin.value() < 1:
                f.operSpin.setValue(1)

        name = f.operCombo.currentText()
        if name:
            _status(self, f"Шифр: {name}", 2000)

    def _update_caesar_spin_range(self) -> None:
        """Диапазон сдвига Цезаря — по длине текущего алфавита."""
        f = self.mFLayout
        filename = f.alphabetCombo.currentData()
        n = 33
        if filename:
            path = None
            for base in (data_path, resource_path):
                p = base(f"alphabets/ciphers/{filename}")
                if os.path.exists(p):
                    path = p
                    break
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        letters = json.load(fp).get("letters", "")
                    if letters:
                        n = len(letters)
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
        f.operSpin.setRange(1, max(1, n - 1))
        if f.operSpin.value() > n - 1:
            f.operSpin.setValue(max(1, n - 1))
        _status(self, f"Сдвиг Цезаря: 1..{max(1, n - 1)}", 2500)

    # ---------- прочее ----------

    def set_number(self, n: int) -> None:
        self.label.setText(f"Действие {n}")

    def set_move_buttons_enabled(self, can_up: bool, can_down: bool) -> None:
        self.upButton.setVisible(can_up)
        self.downButton.setVisible(can_down)

    def delete(self) -> None:
        _status(self, "Действие удалено", 2000)
        self.removed.emit(self)
        self.setParent(None)
        self.deleteLater()

    def reload_alphabets(self) -> None:
        """Перечитать alphabets.json, сохранив текущий выбор, если он есть."""
        f = self.mFLayout
        type_ind = f.typeCombo.currentIndex()
        cur_alps = f.alphabetCombo.currentData()
        cur_oper = f.operCombo.currentData()

        alps = self._load_alps()

        match type_ind:
            case 0:
                self._fill_combo(f.alphabetCombo, alps["morse"])
            case 1:
                self._fill_combo(f.alphabetCombo, alps["number_systems"])
            case 2:
                cipher_items = {k: alps["ciphers"][k] for k in self.CIPHER_KEYS}
                self._fill_combo(f.operCombo, cipher_items)
                self._fill_combo(f.alphabetCombo, alps["ciphers"]["alps"])
            case 3:
                self._fill_combo(f.alphabetCombo, alps["braille"])
            case 4:
                self._fill_combo(f.alphabetCombo, alps["binary"])

        self._restore_combo_selection(f.alphabetCombo, cur_alps)
        self._restore_combo_selection(f.operCombo, cur_oper)

        if type_ind == 2:
            self.on_cipher_changed(f.operCombo.currentIndex())

        _status(self, "Список алфавитов обновлён", 2000)

    @staticmethod
    def _restore_combo_selection(combo: QComboBox, key) -> None:
        if key is None:
            return
        idx = combo.findData(key)
        if idx >= 0:
            combo.setCurrentIndex(idx)


# ============================================================
#   Настройки: страницы, диалог
# ============================================================


class SettingsPage(QWidget):
    """
    Базовый каркас страницы настроек:
    заголовок, QFormLayout для полей, stretch внизу.

    Наследники в __init__ вызывают super().__init__(), добавляют поля
    через add_row()/add_section() и переопределяют load()/save().
    """

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

    # ---------- API для наследников ----------

    def add_row(self, label: str | QWidget, widget: QWidget) -> None:
        self._form.addRow(label, widget)

    def add_section(self, title: str) -> QFormLayout:
        """Добавить подраздел и вернуть его QFormLayout."""
        label = QLabel(title)
        label.setFont(QFont("", 16, QFont.Weight.Bold))
        self._root.insertWidget(self._root.count() - 1, label)  # перед stretch

        form = QFormLayout()
        form.setSpacing(12)
        self._root.insertLayout(self._root.count() - 1, form)
        return form

    # ---------- переопределяемое ----------

    def load(self) -> None:
        """Заполнить виджеты значениями из SETTINGS."""

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
        self.versionLabel.setText(SETTINGS.get("version", DEFAULT_SETTINGS["version"]))

    def save(self) -> dict:
        return {"theme": self.themeCombo.currentText()}


class ConversionPage(SettingsPage):
    """«Конвертация»: неизвестные символы + параметры Морзе."""

    title = "Конвертация"

    def __init__(self) -> None:
        super().__init__()

        self.undCharPolCombo = QComboBox()
        self.undCharPolCombo.addItems(["Предупреждение", "Игнорировать", "Заменить"])
        self.add_row("Действие с неизвестным символом:", self.undCharPolCombo)

        self.replacementEdit = QLineEdit()
        self.replacementEdit.setPlaceholderText("Символ замены...")
        self.replacementEdit.setMaxLength(10)
        self.add_row("Символ замены:", self.replacementEdit)

        self.caseSensitiveCheck = QCheckBox("Операции чувствительны к регистру")
        self.caseSensitiveCheck.setToolTip(
            "Если выключено — буквы ищутся в алфавите без учёта регистра."
        )
        self.add_row("Регистр:", self.caseSensitiveCheck)

        self.undCharPolCombo.currentTextChanged.connect(self._on_policy_changed)
        self._on_policy_changed(self.undCharPolCombo.currentText())

        # --- Морзе → звук ---
        morse_form = self.add_section("Конвертация морзе в звуковой файл")

        self.morseFreqSpin = QSpinBox()
        self.morseFreqSpin.setRange(100, 5000)
        self.morseFreqSpin.setSingleStep(10)
        self.morseFreqSpin.setSuffix(" Гц")
        morse_form.addRow("Частота звука:", self.morseFreqSpin)

        self.morseRateSpin = QSpinBox()
        self.morseRateSpin.setRange(8000, 192000)
        self.morseRateSpin.setSingleStep(100)
        self.morseRateSpin.setSuffix(" Гц")
        morse_form.addRow("Частота дискретизации:", self.morseRateSpin)

        self.morseWpmSpin = QSpinBox()
        self.morseWpmSpin.setRange(1, 100)
        self.morseWpmSpin.setSingleStep(1)
        self.morseWpmSpin.setSuffix(" WPM")
        morse_form.addRow("Слов в минуту:", self.morseWpmSpin)

    def _on_policy_changed(self, text: str) -> None:
        show = text == "Заменить"
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

        self.caseSensitiveCheck.setChecked(
            bool(SETTINGS.get("case_sensitive", DEFAULT_SETTINGS["case_sensitive"]))
        )

        self.replacementEdit.setText(
            SETTINGS.get("replacement", DEFAULT_SETTINGS["replacement"])
        )
        self._on_policy_changed(self.undCharPolCombo.currentText())

        self.morseFreqSpin.setValue(
            int(SETTINGS.get("morse_freq", DEFAULT_SETTINGS["morse_freq"]))
        )
        self.morseRateSpin.setValue(
            int(
                SETTINGS.get("morse_sample_rate", DEFAULT_SETTINGS["morse_sample_rate"])
            )
        )
        self.morseWpmSpin.setValue(
            int(SETTINGS.get("morse_wpm", DEFAULT_SETTINGS["morse_wpm"]))
        )

    def save(self) -> dict:
        result = {
            "und_char_pol": self.undCharPolCombo.currentText(),
            "case_sensitive": self.caseSensitiveCheck.isChecked(),
            "morse_freq": self.morseFreqSpin.value(),
            "morse_sample_rate": self.morseRateSpin.value(),
            "morse_wpm": self.morseWpmSpin.value(),
        }
        if self.undCharPolCombo.currentText() == "Заменить":
            result["replacement"] = self.replacementEdit.text()
        return result


class SettingsDialog(QDialog):
    """Диалог настроек с боковой навигацией."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(760, 520)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(200)
        self.nav.setFrameShape(QFrame.Shape.NoFrame)

        self.stack = QStackedWidget()

        self.pages: list[tuple[str, SettingsPage]] = [
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
        buttons.rejected.connect(self._on_cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
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
        res: dict = {}
        for _, page in self.pages:
            res.update(page.save())
        save_settings(res)
        apply_theme()
        _status(self, "Настройки сохранены", 2500)

    def _on_apply(self) -> None:
        self.collect()

    def _on_cancel(self) -> None:
        _status(self, "Изменение настроек отменено", 2000)
        self.reject()

    def collect_n_close(self) -> None:
        self.collect()
        _status(self, "Настройки применены", 2500)
        self.accept()

    def reset_to_defaults(self) -> None:
        """Сбросить settings.json и все страницы к дефолтам."""
        reset_settings()
        self.load()
        _status(self, "Настройки сброшены до умолчаний", 3000)


class ImportAlphabetDialog(QDialog):
    """Окно выбора типа импортируемого алфавита."""

    OPTIONS: tuple[tuple[str, str], ...] = (
        ("Морзе", "morse"),
        ("Систем счисления", "number_systems"),
        ("Шифров", "ciphers"),
        ("Брайля", "braille"),
        ("Бинарного кода", "binary"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Импорт алфавита")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        self.label = QLabel("Это алфавит для…", parent=self)
        layout.addWidget(self.label)

        self.combo = QComboBox(parent=self)
        for text, _ in self.OPTIONS:
            self.combo.addItem(text)
        layout.addWidget(self.combo)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def result_subdir(self) -> str:
        """Имя подпапки, выбранной пользователем."""
        return self.OPTIONS[self.combo.currentIndex()][1]


# ============================================================
#   Кнопки и мини-плеер
# ============================================================


class SquareButton(QPushButton):
    """Квадратная кнопка, тянущаяся по высоте родителя."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(24, 24)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return w

    def sizeHint(self) -> QSize:
        s = super().sizeHint()
        s.setWidth(s.height())
        return s

    def resizeEvent(self, e: QEvent) -> None:
        super().resizeEvent(e)
        h = self.height()
        if self.width() != h:
            self.setFixedWidth(h)


class MiniPlayer(QWidget):
    """Мини-плеер для воспроизведения сгенерированного WAV."""

    def __init__(self, parent: QWidget | None = None) -> None:
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

    def play(self) -> None:
        self.player.play()
        self.btn_play.hide()
        self.btn_pause.show()
        _status(self, "Воспроизведение", 1500)

    def pause(self) -> None:
        self.player.pause()
        self.btn_pause.hide()
        self.btn_play.show()
        _status(self, "Пауза", 1500)

    def reload_source(self, path: str = "temp_morse.wav") -> None:
        """
        Загрузить новый файл. Относительный path кладётся рядом с exe
        через data_path; абсолютный — используется как есть.
        """
        if not os.path.isabs(path):
            path = data_path(path)

        self.player.stop()
        self.player.setSource(QUrl())
        self.slider.setRange(0, 0)
        self.slider.setValue(0)
        if Path(path).exists():
            self.player.setSource(QUrl.fromLocalFile(path))
            _status(self, f"Плеер: загружен {os.path.basename(path)}", 2500)
        else:
            _status(
                self,
                f"Плеер: файл не найден — {os.path.basename(path)}",
                3000,
            )

    def on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.pause()
            _status(self, "Воспроизведение завершено", 2000)


# ============================================================
#   Делегаты / валидаторы
# ============================================================


class OneCharDelegate(QStyledItemDelegate):
    """Редактор ячейки — ровно один символ."""

    def createEditor(self, parent: QWidget, option, index) -> QLineEdit:
        ed = QLineEdit(parent)
        ed.setMaxLength(1)
        return ed

    def setModelData(self, editor: QLineEdit, model, index) -> None:
        model.setData(index, editor.text()[:1])

    def setEditorData(self, editor: QLineEdit, index) -> None:
        editor.setText(index.data() or "")


class MorseCodeValidator(QRegularExpressionValidator):
    """Разрешает только '.', '-' и '/'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(QRegularExpression(r"[.\-/]*"), parent)


# ============================================================
#   Базовое окно создания алфавита
# ============================================================


class BaseAlphabetDialog(QDialog):
    """
    Базовое окно создания/редактирования JSON-алфавита.

    Наследники задают:
      - alphabet_type / save_subdir / key_header / value_header;
      - _build_meta_form()   — поля meta;
      - _validate_meta()     — проверка meta;
      - _make_row_value_editor() / _read_row_value() / _write_row_value();
      - _serialize()         — итоговый JSON.
    """

    alphabet_type: str = "generic"
    save_subdir: str = "alphabets"
    key_header: str = "Ключ"
    value_header: str = "Значение"

    def __init__(
        self,
        /,
        parent: QWidget | None = None,
        initial: dict | None = None,
        default_filename: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Создание алфавита — {self.alphabet_type}")
        self._initial = initial or {}
        self._result_data: dict | None = None
        self._result_fullpath: str | None = None
        self._result_filename: str = ""

        self._vbox = QVBoxLayout(self)

        # --- Имя файла ---
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Имя JSON-файла:"))
        self.fileEdit = QLineEdit(default_filename or self._default_filename())
        self.fileEdit.setPlaceholderText("например, en6.json")
        file_row.addWidget(self.fileEdit, 1)
        browse = QPushButton("…")
        browse.clicked.connect(self._browse_file)
        file_row.addWidget(browse)
        self._vbox.addLayout(file_row)

        # --- meta ---
        self.meta_form = QFormLayout()
        self._build_meta_form()
        self._vbox.addLayout(self.meta_form)

        # --- Таблица ключ-значение ---
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([self.key_header, self.value_header])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._vbox.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Добавить строку")
        add_btn.clicked.connect(self._add_row_and_notify)
        del_btn = QPushButton("Удалить строку")
        del_btn.clicked.connect(self._remove_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        self._vbox.addLayout(btn_row)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self._on_reject)
        self._vbox.addWidget(self.buttonBox)

        self._load_initial()
        _status(self, f"Создание алфавита — {self.alphabet_type}", 2500)

    # ---------- настройки по умолчанию ----------

    def _default_filename(self) -> str:
        return f"{self.alphabet_type}.json"

    def _build_meta_form(self) -> None:
        raise NotImplementedError

    def _validate_meta(self) -> tuple[bool, str]:
        raise NotImplementedError

    def _make_row_value_editor(self, row: int) -> QWidget:
        return QLineEdit()

    def _read_row_value(self, row: int):
        w = self.table.cellWidget(row, 1)
        return w.text() if isinstance(w, QLineEdit) else ""

    def _write_row_value(self, row: int, value) -> None:
        w = self.table.cellWidget(row, 1)
        if isinstance(w, QLineEdit):
            w.setText("" if value is None else str(value))

    def _serialize(self) -> dict:
        raise NotImplementedError

    # ---------- работа с таблицей ----------

    def _add_row(self, key: str = "", value=None) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(key))
        self.table.setCellWidget(row, 1, self._make_row_value_editor(row))
        self._write_row_value(row, value)
        return row

    def _add_row_and_notify(self) -> None:
        self._add_row()
        _status(self, "Строка добавлена", 1500)

    def _remove_row(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            _status(self, "Не выбрано ни одной строки для удаления", 2000)
            return
        for r in rows:
            self.table.removeRow(r)
        _status(self, f"Удалено строк: {len(rows)}", 1500)

    def _on_reject(self) -> None:
        _status(self, "Создание алфавита отменено", 2000)
        self.reject()

    def _load_initial(self) -> None:
        if not self._initial:
            self._add_row()
            return
        for k, v in self._initial.items():
            self._add_row(k, v)

    # ---------- файл ----------

    def _browse_file(self) -> None:
        start_dir = resource_path(self.save_subdir)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить JSON",
            os.path.join(start_dir, self.fileEdit.text()),
            "JSON (*.json)",
        )
        if path:
            self._result_fullpath = path
            self.fileEdit.setText(os.path.basename(path))
            _status(self, f"Выбран файл: {os.path.basename(path)}", 2500)

    # ---------- принятие ----------

    def _on_accept(self) -> None:
        ok, err = self._validate_meta()
        if not ok:
            QMessageBox.warning(self, "Ошибка", err)
            _status(self, f"Ошибка: {err}", 3000)
            return

        fname = self.fileEdit.text().strip()
        if not fname:
            QMessageBox.warning(self, "Ошибка", "Укажите имя JSON-файла.")
            _status(self, "Ошибка: не указано имя JSON-файла", 3000)
            return
        if not fname.endswith(".json"):
            fname += ".json"
        if not re.fullmatch(r"[\w.\-]+\.json", fname):
            QMessageBox.warning(
                self, "Ошибка", "Имя файла содержит недопустимые символы."
            )
            _status(self, "Ошибка: недопустимые символы в имени файла", 3000)
            return

        # дубликаты ключей
        seen: set[str] = set()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                QMessageBox.warning(self, "Ошибка", f"Строка {r+1}: пустой ключ.")
                _status(self, f"Ошибка: строка {r+1} — пустой ключ", 3000)
                return
            if key in seen:
                QMessageBox.warning(self, "Ошибка", f"Дублирующийся ключ: {key!r}")
                _status(self, f"Ошибка: дублирующийся ключ {key!r}", 3000)
                return
            seen.add(key)

        try:
            data = self._serialize()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", str(e))
            _status(self, f"Ошибка: {e}", 4000)
            return

        self._result_data = data
        self._result_filename = fname
        _status(self, f"Алфавит готов к сохранению: {fname}", 3000)
        self.accept()

    def result_data(self) -> dict | None:
        return self._result_data

    def result_filename(self) -> str:
        return self._result_filename

    def result_fullpath(self) -> str | None:
        return self._result_fullpath


# ============================================================
#   Диалоги алфавитов: шифр / Морзе
# ============================================================


class CipherAlphabetDialog(BaseAlphabetDialog):
    """
    Создание алфавита-шифра (Морзе или шифр подстановки).

    meta:
        name    — обязательно
        sep     — обязательно (для A1Z26)
        shift   — необязательно (по умолчанию 3)
        rows/cols/filler — обязательно для Плейфера
        aliases — необязательно (для Плейфера)

    letters:
        - Morse: {символ: "."/ "-"/ ...}
        - Cipher: строка букв + aliases в meta
    """

    alphabet_type = "cipher"
    save_subdir = "alphabets/ciphers"
    key_header = "Символ"
    value_header = "Код / Алиас"

    _mode = "cipher"  # "morse" | "cipher"

    def __init__(
        self,
        /,
        parent: QWidget | None = None,
        initial: dict | None = None,
        default_filename: str = "",
    ) -> None:
        super().__init__(parent, initial=initial, default_filename=default_filename)
        self.table.setItemDelegateForColumn(0, OneCharDelegate(self.table))

    def _default_filename(self) -> str:
        return "new_morse.json" if self._mode == "morse" else "new_cipher.json"

    # ---------- meta ----------

    def _build_meta_form(self) -> None:
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("например, Английский")
        self.meta_form.addRow("name *:", self.nameEdit)

        self.sepEdit = QLineEdit()
        self.sepEdit.setPlaceholderText("например, -")
        self.meta_form.addRow("sep *:", self.sepEdit)

        self.shiftSpin = QSpinBox()
        self.shiftSpin.setRange(1, 1000)
        self.shiftSpin.setValue(3)
        self.meta_form.addRow("shift:", self.shiftSpin)

        self.rowsSpin = QSpinBox()
        self.rowsSpin.setRange(1, 100)
        self.rowsSpin.setValue(5)
        self.meta_form.addRow("rows *:", self.rowsSpin)

        self.colsSpin = QSpinBox()
        self.colsSpin.setRange(1, 100)
        self.colsSpin.setValue(5)
        self.meta_form.addRow("cols *:", self.colsSpin)

        self.fillerEdit = QLineEdit()
        self.fillerEdit.setMaxLength(1)
        self.fillerEdit.setPlaceholderText("например, x")
        self.meta_form.addRow("filler *:", self.fillerEdit)

    def _validate_meta(self) -> tuple[bool, str]:
        if not self.nameEdit.text().strip():
            return False, "Поле name обязательно."
        if not self.sepEdit.text():
            return False, "Поле sep обязательно."
        filler = self.fillerEdit.text().strip()
        if self._mode == "cipher" and len(filler) != 1:
            return False, "filler должен быть одним символом."
        return True, ""

    # ---------- редактор значения ----------

    def _make_row_value_editor(self, row: int) -> QWidget:
        if self._mode == "morse":
            w = QLineEdit()
            w.setPlaceholderText(". / -")
            w.setValidator(MorseCodeValidator(w))
            return w
        # cipher: алиас (пусто = нет алиаса)
        w = QLineEdit()
        w.setPlaceholderText("алиас (необязательно)")
        w.setMaxLength(1)
        return w

    # ---------- сериализация ----------

    def _serialize(self) -> dict:
        meta = {"name": self.nameEdit.text().strip(), "sep": self.sepEdit.text()}
        return (
            self._serialize_morse(meta)
            if self._mode == "morse"
            else self._serialize_cipher(meta)
        )

    def _serialize_morse(self, meta: dict) -> dict:
        letters: dict[str, str] = {" ": "/"}  # пробел -> "/"
        for r in range(1, self.table.rowCount()):  # 0 — пробел
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                continue
            val = self._read_row_value(r).strip()
            if not val:
                raise ValueError(f"Строка {r+1}: пустой код.")
            if not re.fullmatch(r"[.\-/]+", val):
                raise ValueError(
                    f"Строка {r+1}: код может содержать только '.', '-' и '/'."
                )
            letters[key] = val
        return {"meta": meta, "letters": letters}

    def _serialize_cipher(self, meta: dict) -> dict:
        meta["shift"] = self.shiftSpin.value()
        meta["rows"] = self.rowsSpin.value()
        meta["cols"] = self.colsSpin.value()
        filler = self.fillerEdit.text().strip()
        meta["filler"] = filler

        letters_list: list[str] = []
        aliases: dict[str, str] = {}
        seen: set[str] = set()

        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                raise ValueError(f"Строка {r+1}: пустой символ.")
            if len(key) != 1:
                raise ValueError(f"Строка {r+1}: символ должен быть одним знаком.")
            if key in seen:
                raise ValueError(f"Дублирующийся символ: {key!r}")
            seen.add(key)

            alias = self._read_row_value(r).strip()
            if alias:
                if len(alias) != 1:
                    raise ValueError(f"Строка {r+1}: алиас должен быть одним знаком.")
                aliases[key] = alias
            else:
                letters_list.append(key)

        # filler должен быть среди букв
        if filler not in letters_list:
            raise ValueError(
                f"filler {filler!r} должен быть среди букв шифра "
                f"(не среди алиасов)."
            )

        n_cells = len(letters_list)
        expected = meta["rows"] * meta["cols"]
        if n_cells != expected:
            raise ValueError(
                f"Число уникальных букв ({n_cells}) после применения "
                f"алиасов не совпадает с размером таблицы "
                f"{meta['rows']}x{meta['cols']} = {expected}."
            )

        # защита от цепочек/циклов алиасов
        for src in aliases:
            chain, cur = {src}, aliases[src]
            while cur in aliases:
                if cur in chain:
                    raise ValueError(
                        f"Цепочка/цикл алиасов вокруг {src!r}: "
                        f"{' -> '.join(chain)} -> {cur}"
                    )
                chain.add(cur)
                cur = aliases[cur]
            if cur not in letters_list:
                raise ValueError(
                    f"Алиас {src!r} -> {cur!r}: цель отсутствует среди букв."
                )

        result = {"meta": meta, "letters": "".join(letters_list)}
        if aliases:
            meta["aliases"] = aliases
        return result

    # ---------- загрузка initial ----------

    def _load_initial(self) -> None:
        if not self._initial:
            self._prepare_initial_rows()
            return

        meta = self._initial.get("meta", {})
        self.nameEdit.setText(meta.get("name", ""))
        self.sepEdit.setText(meta.get("sep", ""))
        if "shift" in meta:
            self.shiftSpin.setValue(int(meta["shift"]))
        if "rows" in meta:
            self.rowsSpin.setValue(int(meta["rows"]))
        if "cols" in meta:
            self.colsSpin.setValue(int(meta["cols"]))
        if "filler" in meta:
            self.fillerEdit.setText(meta["filler"])

        letters = self._initial.get("letters", "")
        aliases = meta.get("aliases", {})

        if self._mode == "morse":
            self._prepare_space_row()
            if isinstance(letters, dict):
                for k, v in letters.items():
                    if k == " ":
                        continue
                    self._add_row(k, v)
        else:
            if isinstance(letters, str):
                for ch in letters:
                    self._add_row(ch, aliases.get(ch, ""))
                for src, dst in aliases.items():
                    if src not in letters:
                        self._add_row(src, dst)
            elif isinstance(letters, dict):
                for k, v in letters.items():
                    self._add_row(k, v)

        if self.table.rowCount() == 0:
            self._prepare_initial_rows()

    def _prepare_space_row(self) -> None:
        """Строка «Пробел» -> «/» (нередактируемая). Только для Morse."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QTableWidgetItem("Пробел")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, item)
        w = QLineEdit("/")
        w.setReadOnly(True)
        self.table.setCellWidget(row, 1, w)

    def _prepare_initial_rows(self) -> None:
        if self._mode == "morse":
            self._prepare_space_row()
        else:
            self._add_row()

    # ---------- _on_accept ----------

    def _on_accept(self) -> None:
        if self._mode == "morse":
            self._accept_morse()
        else:
            super()._on_accept()

    def _accept_morse(self) -> None:
        fname = self.fileEdit.text().strip()
        if not fname:
            QMessageBox.warning(self, "Ошибка", "Укажите имя JSON-файла.")
            _status(self, "Ошибка: не указано имя JSON-файла", 3000)
            return
        if not fname.endswith(".json"):
            fname += ".json"
        if not re.fullmatch(r"[\w.\-]+\.json", fname):
            QMessageBox.warning(
                self, "Ошибка", "Имя файла содержит недопустимые символы."
            )
            _status(self, "Ошибка: недопустимые символы в имени файла", 3000)
            return

        try:
            data = self._serialize()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", str(e))
            _status(self, f"Ошибка: {e}", 4000)
            return

        self._result_data = data
        self._result_filename = fname
        _status(self, f"Алфавит Морзе готов: {fname}", 3000)
        self.accept()


class MorseAlphabetDialog(CipherAlphabetDialog):
    """Диалог создания Морзе-алфавита."""

    _mode = "morse"
    alphabet_type = "morse"
    save_subdir = "alphabets/morse"
    key_header = "Символ"
    value_header = "Код"

    def _build_meta_form(self) -> None:
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("например, Английский")
        self.meta_form.addRow("name *:", self.nameEdit)

    def _validate_meta(self) -> tuple[bool, str]:
        if not self.nameEdit.text().strip():
            return False, "Поле name обязательно."
        return True, ""

    def _serialize(self) -> dict:
        meta = {"name": self.nameEdit.text().strip(), "spacer": " "}
        letters: dict[str, str] = {" ": "/"}
        for r in range(1, self.table.rowCount()):  # 0 — пробел
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                continue
            val = self._read_row_value(r).strip()
            if not val:
                raise ValueError(f"Строка {r+1}: пустой код.")
            if not re.fullmatch(r"[.\-/]+", val):
                raise ValueError(
                    f"Строка {r+1}: код может содержать только '.', '-' и '/'."
                )
            letters[key] = val
        return {"meta": meta, "letters": letters}


class CipherAlphaDialog(CipherAlphabetDialog):
    """Диалог создания алфавита для шифров подстановки."""

    _mode = "cipher"
    alphabet_type = "cipher"
    save_subdir = "alphabets/ciphers"
    key_header = "Символ"
    value_header = "Алиас"


# ============================================================
#   Система счисления
# ============================================================


class NumeralAlphabetDialog(BaseAlphabetDialog):
    """
    Алфавит системы счисления.
    meta: только name. Значения цифр вычисляются по порядку (0, 1, ...),
    пользователь вводит только обозначения.
    """

    alphabet_type = "numeral"
    save_subdir = "alphabets/number_systems"
    key_header = "Обозначение"
    value_header = "Значение"

    def _default_filename(self) -> str:
        return "new_numeral.json"

    def _build_meta_form(self) -> None:
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("например, Стандартный (до 36)")
        self.meta_form.addRow("name *:", self.nameEdit)

    def _validate_meta(self) -> tuple[bool, str]:
        if not self.nameEdit.text().strip():
            return False, "Поле name обязательно."
        return True, ""

    # значения вычисляются, а не вводятся

    def _make_row_value_editor(self, row: int) -> QWidget:
        w = QLineEdit()
        w.setReadOnly(True)
        return w

    def _read_row_value(self, row: int) -> int:
        return row

    def _write_row_value(self, row: int, value) -> None:
        w = self.table.cellWidget(row, 1)
        if isinstance(w, QLineEdit):
            w.setText(str(row))

    # пересчёт значений при добавлении/удалении

    def _add_row(self, key: str = "", value=None) -> int:
        row = super()._add_row(key, value)
        self._refresh_values()
        return row

    def _remove_row(self) -> None:
        super()._remove_row()
        self._refresh_values()

    def _refresh_values(self) -> None:
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 1)
            if isinstance(w, QLineEdit):
                w.setText(str(r))

    def _serialize(self) -> dict:
        letters: dict[str, int] = {}
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                raise ValueError(f"Строка {r+1}: пустое обозначение.")
            letters[key] = r
        return {
            "meta": {"name": self.nameEdit.text().strip()},
            "letters": letters,
        }

    def _load_initial(self) -> None:
        if not self._initial:
            self._add_row()
            return
        meta = self._initial.get("meta", {})
        self.nameEdit.setText(meta.get("name", ""))
        letters = self._initial.get("letters", {})
        if isinstance(letters, dict):
            for ch, _ in sorted(letters.items(), key=lambda kv: kv[1]):
                self._add_row(ch)


class BinaryAlphabetDialog(BaseAlphabetDialog):
    """Алфавит для бинарного кода (alphabets/binary)."""

    alphabet_type = "binary"
    save_subdir = "alphabets/binary"
    key_header = "Символ"
    value_header = "HEX-код"

    def _default_filename(self) -> str:
        return "new_binary.json"

    def _build_meta_form(self) -> None:
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("например, Свой UTF-16")
        self.meta_form.addRow("name *:", self.nameEdit)

        self.bytesSpin = QSpinBox()
        self.bytesSpin.setRange(1, 8)
        self.bytesSpin.setValue(1)
        self.meta_form.addRow("bytes *:", self.bytesSpin)

    def _validate_meta(self) -> tuple[bool, str]:
        if not self.nameEdit.text().strip():
            return False, "Поле name обязательно."
        return True, ""

    # ---------- редактор значения: HEX-пары через пробел ----------

    def _make_row_value_editor(self, row: int) -> QWidget:
        w = QLineEdit()
        w.setPlaceholderText("AF 7B 10")
        regex = QRegularExpression(r"([0-9A-Fa-f]{2}( [0-9A-Fa-f]{2})*)?")
        w.setValidator(QRegularExpressionValidator(regex, w))
        return w

    def _read_row_value(self, row: int) -> str:
        w = self.table.cellWidget(row, 1)
        return w.text().strip() if isinstance(w, QLineEdit) else ""

    def _write_row_value(self, row: int, value) -> None:
        w = self.table.cellWidget(row, 1)
        if isinstance(w, QLineEdit):
            w.setText("" if value is None else str(value))

    # ---------- сериализация: HEX -> биты ----------

    @staticmethod
    def _hex_to_bits(hex_str: str, n_bytes: int) -> str:
        parts = hex_str.split()
        if len(parts) != n_bytes:
            raise ValueError(
                f"Ожидалось {n_bytes} HEX-байт через пробел, "
                f"получено {len(parts)}: {hex_str!r}"
            )
        bits: list[str] = []
        for p in parts:
            if len(p) != 2:
                raise ValueError(f"HEX-байт {p!r} должен состоять из двух цифр")
            try:
                val = int(p, 16)
            except ValueError:
                raise ValueError(f"Некорректный HEX-байт: {p!r}")
            bits.append(format(val, "08b"))
        return "".join(bits)

    def _serialize(self) -> dict:
        n_bytes = self.bytesSpin.value()
        letters: dict[str, str] = {}
        seen: set[str] = set()

        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                raise ValueError(f"Строка {r+1}: пустой символ.")
            if len(key) != 1:
                raise ValueError(f"Строка {r+1}: символ должен быть одним знаком.")
            if key in seen:
                raise ValueError(f"Дублирующийся символ: {key!r}")
            seen.add(key)

            hex_str = self._read_row_value(r)
            if not hex_str:
                raise ValueError(f"Строка {r+1}: пустой HEX-код.")

            bits = self._hex_to_bits(hex_str, n_bytes)
            if bits in letters.values():
                raise ValueError(
                    f"Строка {r+1}: код {hex_str!r} уже используется "
                    f"для другого символа."
                )
            letters[key] = bits

        return {
            "meta": {"name": self.nameEdit.text().strip(), "bytes": n_bytes},
            "letters": letters,
        }

    # ---------- загрузка existing ----------

    def _load_initial(self) -> None:
        if not self._initial:
            self._add_row()
            return
        meta = self._initial.get("meta", {})
        self.nameEdit.setText(meta.get("name", ""))
        if "bytes" in meta:
            self.bytesSpin.setValue(int(meta["bytes"]))

        letters = self._initial.get("letters", {})
        for ch, bits in letters.items():
            hex_parts = [
                format(int(bits[i : i + 8], 2), "02X") for i in range(0, len(bits), 8)
            ]
            self._add_row(ch, " ".join(hex_parts))


# ============================================================
#   Брайль: алфавит-диалог и виджет ввода
# ============================================================


class BrailleAlphabetDialog(BaseAlphabetDialog):
    """
    Создание алфавита Брайля.

    meta (все обязательны):
        name                — отображаемое имя;
        num_prefix          — символ числового индикатора;
        capital_prefix      — символ заглавной буквы;
        capital_word_prefix — символ слова с заглавной.

    Таблица:
        колонка 0 — обычный символ (ровно один знак);
        колонка 1 — строка Брайля (read-only, заполняется виджетом).

    JSON: {"meta": {...}, "prefixes": {...}, "letters": {...}}
    """

    alphabet_type = "braille"
    save_subdir = "alphabets/braille"
    key_header = "Символ"
    value_header = "Брайль"

    def __init__(
        self,
        /,
        parent: QWidget | None = None,
        initial: dict | None = None,
        default_filename: str = "",
    ) -> None:
        super().__init__(parent, initial=initial, default_filename=default_filename)
        self.table.setItemDelegateForColumn(0, OneCharDelegate(self.table))
        self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        """Переложить таблицу в HBox: слева виджет Брайля, справа таблица."""
        idx = self._vbox.indexOf(self.table)
        if idx < 0:
            return

        self._vbox.removeWidget(self.table)

        self.braille = BrailleInputWidget(
            target_widget=None,
            parent=self,
            follow_focus=True,  # Enter вставляет в фокус (ячейку таблицы)
            compact=True,
        )
        self.braille.setMinimumWidth(300)

        insert_btn = QPushButton("Вставить в выбранную строку")
        insert_btn.clicked.connect(self._insert_braille_into_selected)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.addWidget(insert_btn)
        right.addWidget(self.table, 1)

        h = QHBoxLayout()
        h.setSpacing(8)
        h.addWidget(self.braille, 0)
        h.addLayout(right, 1)

        self._vbox.insertLayout(idx, h)

    def _default_filename(self) -> str:
        return "new_braille.json"

    # ---------- meta ----------

    def _build_meta_form(self) -> None:
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("например, Английский (6-точечный)")
        self.meta_form.addRow("name *:", self.nameEdit)

        self.numPrefixEdit = self._make_prefix_row("num_prefix *:", "например, ⠼")
        self.capPrefixEdit = self._make_prefix_row("capital_prefix *:", "например, ⠠")
        self.capWordPrefixEdit = self._make_prefix_row(
            "capital_word_prefix *:", "например, ⠠⠠"
        )

    def _make_prefix_row(self, label: str, placeholder: str) -> QLineEdit:
        """Read-only поле префикса + кнопка «взять из буфера виджета»."""
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(placeholder)
        edit.setMaxLength(64)

        btn = QPushButton("→")
        btn.setToolTip("Взять текущий буфер виджета Брайля")
        btn.setFixedWidth(28)
        btn.clicked.connect(lambda: self._take_buffer_into(edit))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(edit, 1)
        row.addWidget(btn, 0)

        container = QWidget()
        container.setLayout(row)
        self.meta_form.addRow(label, container)
        return edit

    def _take_buffer_into(self, edit: QLineEdit) -> None:
        text = self.braille.take_buffer()
        if not text:
            _status(self, "Брайль: буфер пуст", 1500)
            return
        edit.setText(text)
        _status(self, f"Брайль: записано {text!r}", 1500)

    def _validate_meta(self) -> tuple[bool, str]:
        if not self.nameEdit.text().strip():
            return False, "Поле name обязательно."
        for label, edit in (
            ("num_prefix", self.numPrefixEdit),
            ("capital_prefix", self.capPrefixEdit),
            ("capital_word_prefix", self.capWordPrefixEdit),
        ):
            if not edit.text().strip():
                return False, f"Поле {label} обязательно."
            if any(not (0x2800 <= ord(ch) <= 0x28FF) for ch in edit.text()):
                return False, (
                    f"Поле {label} должно содержать только Брайль-символы "
                    f"(U+2800..U+28FF)."
                )
        return True, ""

    # ---------- редактор значения таблицы ----------

    def _make_row_value_editor(self, row: int) -> QWidget:
        w = QLineEdit()
        w.setReadOnly(True)
        w.setPlaceholderText("кликните и наберите Брайль / кнопка выше")
        return w

    def _read_row_value(self, row: int) -> str:
        w = self.table.cellWidget(row, 1)
        return w.text() if isinstance(w, QLineEdit) else ""

    def _write_row_value(self, row: int, value) -> None:
        w = self.table.cellWidget(row, 1)
        if isinstance(w, QLineEdit):
            w.setText("" if value is None else str(value))

    def _insert_braille_into_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            _status(self, "Брайль: выберите строку таблицы", 2000)
            return
        text = self.braille.take_buffer()
        if not text:
            _status(self, "Брайль: буфер пуст", 1500)
            return
        self._write_row_value(row, text)
        _status(self, f"Брайль: код записан в строку {row + 1}", 1500)

    # ---------- сериализация ----------

    def _serialize(self) -> dict:
        meta = {
            "dots": 6,
            "name": self.nameEdit.text().strip(),
            "dot_index_base": 0,
            "note": (
                "точка 1 -> 0, точка 2 -> 1, точка 3 -> 2, "
                "точка 4 -> 3, точка 5 -> 4, точка 6 -> 5"
            ),
        }

        prefixes = {
            "num_prefix": self._make_prefix_entry(
                self.numPrefixEdit, "числовой индикатор"
            ),
            "capital_prefix": self._make_prefix_entry(
                self.capPrefixEdit, "индикатор заглавной буквы"
            ),
            "capital_word_prefix": self._make_prefix_entry(
                self.capWordPrefixEdit, "индикатор слова с заглавной буквы"
            ),
        }

        letters: dict[str, dict] = {}
        seen_chars: set[str] = set()
        seen_braille: set[str] = set()

        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            key = item.text().strip() if item else ""
            if not key:
                raise ValueError(f"Строка {r+1}: пустой символ.")
            if len(key) != 1:
                raise ValueError(f"Строка {r+1}: символ должен быть одним знаком.")
            if key in seen_chars:
                raise ValueError(f"Дублирующийся символ: {key!r}")
            seen_chars.add(key)

            braille = self._read_row_value(r).strip()
            if not braille:
                raise ValueError(f"Строка {r+1}: пустой Брайль-код.")
            if len(braille) != 1:
                raise ValueError(
                    f"Строка {r+1}: Брайль-код должен быть одним символом."
                )
            if any(not (0x2800 <= ord(ch) <= 0x28FF) for ch in braille):
                raise ValueError(
                    f"Строка {r+1}: Брайль-код должен быть символом " f"U+2800..U+28FF."
                )
            if braille in seen_braille:
                raise ValueError(
                    f"Строка {r+1}: Брайль-код {braille!r} уже используется."
                )
            seen_braille.add(braille)

            letters[key] = {
                "char": braille,
                "dots": self._braille_str_to_dots(braille),
            }

        return {"meta": meta, "prefixes": prefixes, "letters": letters}

    def _make_prefix_entry(self, edit: QLineEdit, description: str) -> dict:
        char = edit.text().strip()
        return {
            "char": char,
            "dots": self._braille_str_to_dots(char),
            "description": description,
        }

    @staticmethod
    def _braille_str_to_dots(braille: str) -> list[int]:
        """
        Строка Брайль-символов -> список индексов точек (0..5).

        Для многоклеточных префиксов (напр. ⠠⠠) возвращает конкатенацию
        точек каждой клетки: [5, 5].
        """
        result: list[int] = []
        for ch in braille:
            code = ord(ch)
            if not (0x2800 <= code <= 0x28FF):
                raise ValueError(f"Символ {ch!r} не является Брайль-символом Unicode.")
            mask = code - 0x2800
            result.extend(i for i in range(6) if mask & (1 << i))
        return result

    # ---------- загрузка initial ----------

    def _load_initial(self) -> None:
        if not self._initial:
            self._add_row()
            return

        meta = self._initial.get("meta", {})
        self.nameEdit.setText(meta.get("name", ""))

        prefixes = self._initial.get("prefixes", {})
        for key, edit in (
            ("num_prefix", self.numPrefixEdit),
            ("capital_prefix", self.capPrefixEdit),
            ("capital_word_prefix", self.capWordPrefixEdit),
        ):
            edit.setText(prefixes.get(key, {}).get("char", ""))

        letters = self._initial.get("letters", {})
        if isinstance(letters, dict):
            for ch, info in letters.items():
                braille = info.get("char", "") if isinstance(info, dict) else ""
                self._add_row(ch, braille)

        if self.table.rowCount() == 0:
            self._add_row()


# ============================================================
#   Брайль: виджет ввода
# ============================================================


class BrailleInputWidget(QWidget):
    """
    Виджет ввода символов Брайля.

    Сетка 3x3:
        00 01 02
        10 11 12
        20 21 22

    Точки: [00, 10, 20, 01, 11, 21] -> dots [0, 1, 2, 3, 4, 5]
    12 = "+" (зафиксировать символ, начать новый)
    02 = "←" (Backspace)
    22 = "Enter" (вставить в целевой виджет)

    Клавиши: 1/2/4/5/7/8 соответствуют точкам (см. _KEY_TO_DOT).
    """

    character_committed = pyqtSignal(str)

    DOT_CHAR = "●"

    DOT_BUTTONS: dict[tuple[int, int], int] = {
        (0, 0): 0,
        (1, 0): 1,
        (2, 0): 2,
        (0, 1): 3,
        (1, 1): 4,
        (2, 1): 5,
    }

    PLUS_BUTTON = (1, 2)
    BACKSPACE_BUTTON = (0, 2)
    ENTER_BUTTON = (2, 2)

    ALPHABETS_JSON = "alphabets/alphabets.json"
    BRAILLE_DIR = "alphabets/braille"
    BRAILLE_BASE = 0x2800

    _KEY_TO_DOT: dict[Qt.Key, int] = {
        Qt.Key.Key_1: 2,
        Qt.Key.Key_2: 5,
        Qt.Key.Key_4: 1,
        Qt.Key.Key_5: 4,
        Qt.Key.Key_7: 0,
        Qt.Key.Key_8: 3,
    }

    def __init__(
        self,
        target_widget: QWidget | None = None,
        parent: QWidget | None = None,
        follow_focus: bool = False,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self.target_widget = target_widget
        self.follow_focus = follow_focus
        self.compact = compact

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Текущий набор точек и зафиксированные символы
        self._current_dots: set[int] = set()
        self._committed_chars: list[frozenset[int]] = []

        # Загруженный алфавит
        self._alphabet_data: dict = {}
        self._alphabet_name: str = ""
        self._dots_to_char: dict[frozenset[int], str] = {}
        self._char_to_dots: dict[str, frozenset[int]] = {}
        self._prefixes: dict = {}

        # «Намерения» между наборами (Enter их не сбрасывает)
        self._pending_capital = False  # ⇧ одна буква
        self._pending_capital_word = False  # ⇧⇧ до пробела
        self._pending_number = False  # № до пробела

        self._build_ui()
        self._load_alphabet_list()
        self._load_alphabet(self.alphabet_combo.currentData())

    # ---------- UI ----------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Combo всегда существует — на него ссылаются методы.
        self.alphabet_combo = QComboBox()
        if self.compact:
            self.alphabet_combo.setVisible(False)
        else:
            top_layout = QHBoxLayout()
            top_layout.addWidget(QLabel("Алфавит Брайля:"))
            self.alphabet_combo.currentIndexChanged.connect(self._on_alphabet_changed)
            top_layout.addWidget(self.alphabet_combo, 1)
            main_layout.addLayout(top_layout)

        self._build_display(main_layout)
        self._build_grid(main_layout)

        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        if self.compact:
            self.hint_label.setVisible(False)
        main_layout.addWidget(self.hint_label)

    def _build_display(self, root: QVBoxLayout) -> None:
        """Панель предпросмотра: центр — символы, низ — буфер Брайля."""
        self.display_frame = QFrame()
        self.display_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.display_frame.setMinimumHeight(100)
        self.display_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        display_layout = QVBoxLayout(self.display_frame)
        display_layout.setContentsMargins(8, 8, 8, 8)

        if self.compact:
            # Компакт: центр — крупные Брайль-символы
            self.buffer_label = QLabel("")
            self.buffer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            buf_font = QFont("Monospace")
            buf_font.setPointSize(28)
            buf_font.setBold(True)
            self.buffer_label.setFont(buf_font)
            display_layout.addWidget(self.buffer_label, 1)

            # center_label не используется, но на него ссылаются методы
            self.center_label = QLabel("")
            self.center_label.setVisible(False)
            display_layout.addWidget(self.center_label, 0)
        else:
            # Полный: центр — нормальная буква, угол — Брайль
            self.center_label = QLabel("")
            self.center_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont()
            font.setPointSize(28)
            font.setBold(True)
            self.center_label.setFont(font)
            display_layout.addWidget(self.center_label, 1)

            self.buffer_label = QLabel("")
            self.buffer_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
            )
            buf_font = QFont("Monospace")
            buf_font.setPointSize(14)
            self.buffer_label.setFont(buf_font)
            display_layout.addWidget(self.buffer_label, 0)

        root.addWidget(self.display_frame, 1)

    def _build_grid(self, root: QVBoxLayout) -> None:
        """3x3 сетка: точки, «+», «←», «Enter» (кроме compact)."""
        grid = QGridLayout()
        grid.setSpacing(6)

        self.dot_buttons: dict[int, QPushButton] = {}
        self.special_buttons: dict[str, QPushButton] = {}

        for (row, col), dot_idx in self.DOT_BUTTONS.items():
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setMinimumSize(60, 60)
            btn.setFont(QFont("Sans", 22))
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(
                lambda checked, d=dot_idx: self._on_dot_toggled(d, checked)
            )
            grid.addWidget(btn, row, col)
            self.dot_buttons[dot_idx] = btn

        plus_btn = QPushButton("+")
        plus_btn.setMinimumSize(60, 60)
        plus_btn.setFont(QFont("Sans", 20, QFont.Weight.Bold))
        plus_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        plus_btn.clicked.connect(self._on_plus)
        grid.addWidget(plus_btn, *self.PLUS_BUTTON)
        self.special_buttons["plus"] = plus_btn

        back_btn = QPushButton("←")
        back_btn.setMinimumSize(60, 60)
        back_btn.setFont(QFont("Sans", 18, QFont.Weight.Bold))
        back_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        back_btn.clicked.connect(self._on_backspace)
        grid.addWidget(back_btn, *self.BACKSPACE_BUTTON)
        self.special_buttons["backspace"] = back_btn

        if not self.compact:
            enter_btn = QPushButton("Enter")
            enter_btn.setMinimumSize(60, 60)
            enter_btn.setFont(QFont("Sans", 12, QFont.Weight.Bold))
            enter_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            enter_btn.clicked.connect(self._on_enter)
            grid.addWidget(enter_btn, *self.ENTER_BUTTON)
            self.special_buttons["enter"] = enter_btn

        root.addLayout(grid, 0)

    # ---------- загрузка алфавитов ----------

    def _resource_path(self, relative_path: str) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, relative_path)

    def _load_alphabet_list(self) -> None:
        self.alphabet_combo.blockSignals(True)
        self.alphabet_combo.clear()
        try:
            with open(
                self._resource_path(self.ALPHABETS_JSON),
                "r",
                encoding="utf-8",
            ) as fp:
                data = json.load(fp)
            for filename, meta in data.get("braille", {}).items():
                self.alphabet_combo.addItem(meta.get("name", filename), filename)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            self.alphabet_combo.addItem(f"Ошибка: {exc}", None)
            _status(self, f"Брайль: ошибка загрузки — {exc}", 4000)
        self.alphabet_combo.blockSignals(False)

    def _on_alphabet_changed(self, index: int) -> None:
        self._load_alphabet(self.alphabet_combo.currentData())
        _status(
            self,
            f"Брайль: выбран алфавит «{self.alphabet_combo.currentText()}»",
            2500,
        )

    def _load_alphabet(self, filename: str | None) -> None:
        self._alphabet_data = {}
        self._dots_to_char = {}
        self._char_to_dots = {}
        self._prefixes = {}
        self._alphabet_name = ""

        if not filename:
            self._update_display()
            return

        path = self._resource_path(os.path.join(self.BRAILLE_DIR, filename))
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            self.hint_label.setText(f"Не удалось загрузить {filename}: {exc}")
            _status(self, f"Брайль: не удалось загрузить {filename}", 4000)
            self._update_display()
            return

        self._alphabet_data = data
        self._alphabet_name = data.get("meta", {}).get("name", filename)
        self._prefixes = data.get("prefixes", {})

        for section in ("letters", "digits", "punctuation", "math"):
            for char, meta in data.get(section, {}).items():
                dots = meta.get("dots")
                if dots is None:
                    continue
                key = frozenset(dots)
                self._dots_to_char.setdefault(key, char)
                self._char_to_dots.setdefault(char, key)

        self._update_hint()
        self._update_display()

    # ---------- логика ввода ----------

    def _on_dot_toggled(self, dot_idx: int, checked: bool) -> None:
        if checked:
            self._current_dots.add(dot_idx)
        else:
            self._current_dots.discard(dot_idx)
        self._update_button_states()
        self._update_display()

    def _update_button_states(self) -> None:
        """Синхронизировать текст и checked всех кнопок с _current_dots."""
        for dot_idx, btn in self.dot_buttons.items():
            is_on = dot_idx in self._current_dots
            btn.blockSignals(True)  # избегаем рекурсии
            btn.setChecked(is_on)
            btn.setText(self.DOT_CHAR if is_on else "")
            btn.blockSignals(False)

    def _reset_pending_if_prefix(self, dots: frozenset[int]) -> None:
        """Сбросить persistent-флаг, если стираемый набор — его префикс."""
        cap_prefix = self._get_prefix_dots("capital_prefix")
        cap_word_prefix = self._get_prefix_dots("capital_word_prefix")
        num_prefix = self._get_prefix_dots("num_prefix")

        if cap_prefix and dots == cap_prefix:
            self._pending_capital = False
            self._pending_capital_word = False
        elif cap_word_prefix and dots == cap_word_prefix:
            self._pending_capital_word = False
        elif num_prefix and dots == num_prefix:
            self._pending_number = False

    def _on_plus(self) -> None:
        self._committed_chars.append(frozenset(self._current_dots))
        self._current_dots.clear()
        self._update_button_states()
        self._update_display()
        _status(
            self,
            f"Брайль: символ зафиксирован " f"(буфер: {len(self._committed_chars)})",
            1500,
        )

    def _on_backspace(self) -> None:
        if self._current_dots:
            # Стираем текущий набор; если это был префикс — сбрасываем флаг.
            self._reset_pending_if_prefix(frozenset(self._current_dots))
            self._current_dots.clear()
            self._update_button_states()
            _status(self, "Брайль: текущий набор очищен", 1500)
        elif self._committed_chars:
            # Возвращаем предыдущий символ в редактируемое состояние.
            prev = self._committed_chars.pop()
            self._current_dots = set(prev)
            self._update_button_states()
            _status(self, "Брайль: возвращён предыдущий символ", 1500)
        else:
            _status(self, "Брайль: нечего стирать", 1500)
        self._update_display()

    def _on_enter(self) -> None:
        """
        Вставить Брайль-символы (Unicode) в целевой виджет.
        Пустой текущий набор = пробел U+2800, вставляется всегда.
        """
        text = self._render_braille_text(include_current_always=True)
        if not text:
            return

        if not self._insert_text(text):
            _status(
                self,
                "Брайль: нет активного текстового поля для вставки",
                2500,
            )
            return

        self.character_committed.emit(text)
        _status(self, "Брайль: текст вставлен в целевое поле", 2000)

        self._committed_chars.clear()
        self._current_dots.clear()
        self._update_button_states()
        self._update_display()

    # ---------- точки <-> Брайль (Unicode) ----------

    def _dots_to_braille_char(self, dots) -> str:
        """Набор точек (0..5) -> Unicode-символ Брайля; пусто -> U+2800."""
        mask = 0
        for d in dots:
            if 0 <= d <= 5:
                mask |= 1 << d
        return chr(self.BRAILLE_BASE + mask)

    def _render_braille_text(self, include_current_always: bool = False) -> str:
        """
        Буфер (committed + current) -> строка Брайль-символов.

        include_current_always=True — текущий набор добавляется даже
        пустым (тогда он превращается в U+2800).
        """
        chars = list(self._committed_chars)
        if self._current_dots or include_current_always:
            chars.append(frozenset(self._current_dots))
        return "".join(self._dots_to_braille_char(d) for d in chars)

    # ---------- отображение ----------

    def _dots_to_char_safe(self, dots: frozenset[int]) -> str:
        if not dots:
            return " "
        return self._dots_to_char.get(dots, "?")

    def _get_prefix_dots(self, prefix_key: str) -> frozenset[int]:
        p = self._prefixes.get(prefix_key)
        if not p:
            return frozenset()
        return frozenset(p.get("dots", []))

    def _render_buffer_text(self) -> str:
        """
        Текст для центрального предпросмотра.

        Пустой набор -> '␣'. Префиксы -> 'pref⇧' / 'pref⇧⇧' / 'pref№' / 'pref¹'.
        Заглавность/цифровой режим сохраняются между Enter'ами.
        """
        chars = list(self._committed_chars)
        chars.append(frozenset(self._current_dots))  # пустой -> пробел
        if not chars:
            return ""

        cap_prefix = self._get_prefix_dots("capital_prefix")
        cap_word_prefix = self._get_prefix_dots("capital_word_prefix")
        num_prefix = self._get_prefix_dots("num_prefix")
        grade1_prefix = self._get_prefix_dots("grade1_symbol")

        # Рабочие копии persistent-флагов
        in_number = self._pending_number
        capitalize_next = self._pending_capital
        capitalize_word = self._pending_capital_word

        # Значения, которые сохраним после прохода
        new_capital, new_capital_word = capitalize_next, capitalize_word
        new_number = in_number

        result: list[str] = []
        for dots in chars:
            # --- пустой набор: пробел ---
            if not dots:
                result.append("␣")
                in_number = capitalize_next = capitalize_word = False
                new_number = new_capital = new_capital_word = False
                continue

            # --- префиксы ---
            if cap_prefix and dots == cap_prefix:
                result.append("pref⇧")
                if capitalize_next or capitalize_word:
                    capitalize_word = True
                    capitalize_next = False
                    new_capital_word, new_capital = True, False
                else:
                    capitalize_next = True
                    new_capital = True
                continue

            if cap_word_prefix and dots == cap_word_prefix:
                result.append("pref⇧⇧")
                capitalize_word = True
                capitalize_next = False
                new_capital_word, new_capital = True, False
                continue

            if num_prefix and dots == num_prefix:
                result.append("pref№")
                in_number = True
                new_number = True
                continue

            if grade1_prefix and dots == grade1_prefix:
                result.append("pref¹")
                continue

            # --- обычный символ ---
            char = self._dots_to_char_safe(dots)

            if in_number:
                digit = self._digit_for_dots(dots)
                if digit is not None:
                    char = digit
                else:
                    in_number = False
                    new_number = False

            if capitalize_word or capitalize_next:
                char = char.upper() if char.isalpha() else char
                capitalize_next = False
                new_capital = False
            else:
                char = char.lower() if char.isalpha() else char

            # caps-слово сбрасывается на не-букве (пробел уже обработан выше)
            if capitalize_word and not char.isalpha():
                capitalize_word = False
                new_capital_word = False

            result.append(char)

        # Сохраняем «намерение» на будущее
        self._pending_capital = new_capital
        self._pending_capital_word = new_capital_word
        self._pending_number = new_number

        return "".join(result)

    def _digit_for_dots(self, dots: frozenset[int]) -> str | None:
        digits = self._alphabet_data.get("digits", {})
        for d_char, meta in digits.items():
            if frozenset(meta.get("dots", [])) == dots:
                return d_char
        return None

    def _char_for_current(self) -> str:
        if not self._current_dots:
            return ""
        return self._dots_to_char_safe(frozenset(self._current_dots))

    def _update_display(self) -> None:
        full_text = self._render_buffer_text()
        self.center_label.setText(full_text if full_text else "␣")

        buffer_parts: list[str] = [
            self._dots_to_braille_char(d) for d in self._committed_chars
        ]
        if self._current_dots:
            buffer_parts.append(
                f"[{self._dots_to_braille_char(frozenset(self._current_dots))}]"
            )
        elif self._committed_chars:
            buffer_parts.append("[ ]")

        self.buffer_label.setText(" ".join(buffer_parts))

    def _update_hint(self) -> None:
        if not self._alphabet_name:
            self.hint_label.setText("")
            return
        cur = self._char_for_current()
        if cur and cur != "?":
            self.hint_label.setText(
                f"Алфавит: {self._alphabet_name}   |   " f"Текущий символ: «{cur}»"
            )
        else:
            self.hint_label.setText(f"Алфавит: {self._alphabet_name}")

    # ---------- целевой виджет ----------

    def _resolve_target(self) -> QWidget | None:
        """
        Виджет для вставки. Приоритет:
            1. follow_focus — текущий фокус (QLineEdit/QPlainTextEdit/QTextEdit);
            2. иначе self.target_widget.
        """
        if self.follow_focus:
            fw = QApplication.focusWidget()
            if isinstance(fw, (QLineEdit, QPlainTextEdit, QTextEdit)):
                return fw
        return self.target_widget

    def _insert_text(self, text: str) -> bool:
        """Вставить text в целевой виджет. True при успехе."""
        target = self._resolve_target()
        if target is None:
            return False
        try:
            if isinstance(target, QLineEdit):
                target.insert(text)
            elif isinstance(target, (QPlainTextEdit, QTextEdit)):
                target.insertPlainText(text)
            elif hasattr(target, "insertPlainText"):
                target.insertPlainText(text)
            elif hasattr(target, "insert"):
                target.insert(text)
            elif hasattr(target, "setText"):
                cur = target.text() if hasattr(target, "text") else ""
                target.setText(cur + text)
            else:
                return False
            return True
        except Exception:
            return False

    # ---------- клавиатура ----------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key in self._KEY_TO_DOT:
            if not event.isAutoRepeat():
                dot = self._KEY_TO_DOT[key]
                if dot in self._current_dots:
                    self._current_dots.discard(dot)
                else:
                    self._current_dots.add(dot)
                self._update_button_states()
                self._update_display()
            event.accept()
            return

        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) and (
            key == Qt.Key.Key_Plus
            or event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._on_plus()
            event.accept()
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_enter()
            event.accept()
            return

        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Minus):
            self._on_backspace()
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        # Гасим auto-repeat для точек, чтобы не дёргалось дважды.
        if event.key() in self._KEY_TO_DOT and event.isAutoRepeat():
            event.accept()
            return
        super().keyReleaseEvent(event)

    # ---------- публичные методы ----------

    def set_target_widget(self, widget: QWidget | None) -> None:
        self.target_widget = widget

    def take_buffer(self) -> str:
        """Вернуть текущий буфер Брайля и очистить его."""
        text = self._render_braille_text(include_current_always=True)
        self._committed_chars.clear()
        self._current_dots.clear()
        self._update_button_states()
        self._update_display()
        return text

    def clear(self) -> None:
        self._current_dots.clear()
        self._committed_chars.clear()
        self._update_button_states()
        self._update_display()
        _status(self, "Брайль: буфер очищен", 1500)


class BrailleWindow(QWidget):
    """Отдельное окно с виджетом ввода Брайля."""

    def __init__(
        self,
        target_widget: QWidget | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Ввод Брайля")

        layout = QVBoxLayout(self)
        self.braille = BrailleInputWidget(target_widget=target_widget, parent=self)
        layout.addWidget(self.braille)
        self.resize(420, 520)
        _status(self, "Открыто окно ввода Брайля", 2000)


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
