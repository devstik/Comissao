from PySide6.QtWidgets import QApplication


DARK_MODERN_THEME = """
QWidget {
    background-color: #07131f;
    color: #e8eef2;
    font-size: 13px;
    font-family: "Segoe UI";
}

QMainWindow, QDialog {
    background-color: #07131f;
}

QWidget#appShell {
    background-color: #07131f;
}

QFrame#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0e2235,
        stop:0.55 #112b40,
        stop:1 #173954);
    border: 1px solid #244862;
    border-radius: 18px;
}

QFrame#contentHeader {
    background-color: #0f2232;
    border: 1px solid #18354c;
    border-radius: 14px;
}

QFrame#syncBanner {
    border-radius: 12px;
    border: 1px solid #2a5979;
    background-color: #102637;
}

QFrame#syncBanner[state="warning"] {
    background-color: rgba(213, 140, 82, 0.12);
    border: 1px solid rgba(213, 140, 82, 0.55);
}

QFrame#syncBanner[state="success"] {
    background-color: rgba(56, 161, 105, 0.12);
    border: 1px solid rgba(72, 187, 120, 0.48);
}

QFrame#syncBanner[state="danger"] {
    background-color: rgba(215, 83, 74, 0.12);
    border: 1px solid rgba(215, 83, 74, 0.48);
}

QLabel#syncBannerText {
    color: #dce8ef;
    font-size: 12px;
    font-weight: 700;
}

QLabel {
    color: #f3f6f8;
    font-weight: 600;
    background: transparent;
}

QLabel#windowEyebrow {
    color: #8dc8d8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QLabel#windowTitle {
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
}

QLabel#windowSubtitle {
    color: #b8c7d1;
    font-size: 12px;
    font-weight: 500;
}

QLabel#sidebarSectionTitle {
    color: #86a9ba;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel#sectionTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: 800;
}

QLabel#sectionSubtitle {
    color: #9fb2bf;
    font-size: 10px;
    font-weight: 500;
}

QLabel#identityBadge {
    border-radius: 12px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 700;
    background-color: rgba(141, 200, 216, 0.10);
    color: #d8eef5;
    border: 1px solid rgba(141, 200, 216, 0.24);
}

QPushButton#navButton {
    background: transparent;
    color: #b8cad4;
    border: 1px solid #244862;
    border-radius: 12px;
    padding: 8px 10px;
    text-align: left;
    font-weight: 700;
    min-height: 34px;
}

QPushButton#navButton:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: #3a6a8c;
    color: #eef5f8;
}

QPushButton#navButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #cf7d44,
        stop:1 #e3ab79);
    color: #10202d;
    border-color: #e3ab79;
}

QWidget#filtrosContainer,
QFrame#actionsCard,
QFrame#filtersCard,
QFrame#filtersPanel,
QFrame#filtersHeader {
    background-color: #0f2232;
    border: 1px solid #18354c;
    border-radius: 14px;
}

QFrame#filtersHeader {
    background-color: transparent;
    border: none;
}

QLineEdit, QDateEdit, QSpinBox, QComboBox {
    background: #081724;
    color: #f4f7f9;
    border: 1px solid #1e3a51;
    border-radius: 10px;
    padding: 6px 10px;
    min-height: 30px;
    font-weight: 600;
}

QLineEdit:hover, QDateEdit:hover, QSpinBox:hover, QComboBox:hover {
    border-color: #2a5979;
}

QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #d58c52;
    background: #0c1d2c;
}

QComboBox {
    padding-right: 30px;
}

QComboBox::drop-down, QDateEdit::drop-down {
    border: none;
    width: 24px;
    background: transparent;
}

QComboBox::down-arrow, QDateEdit::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjRThFRUYyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
    width: 12px;
    height: 8px;
}

QSpinBox::up-button, QSpinBox::down-button {
    background: transparent;
    width: 20px;
    border-left: 1px solid #1e3a51;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #153049;
}

QSpinBox::up-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTExIDdMNiAyTDEgNyIgc3Ryb2tlPSIjRThFRUYyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
    width: 12px;
    height: 8px;
}

QSpinBox::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjRThFRUYyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
    width: 12px;
    height: 8px;
}

QComboBox QAbstractItemView,
QCalendarWidget,
QCalendarWidget QMenu {
    background-color: #0d1d2c;
    color: #e8eef2;
    border: 1px solid #1c3a53;
    selection-background-color: #d58c52;
    selection-color: #0f1d29;
    border-radius: 12px;
    outline: none;
}

QCalendarWidget QToolButton {
    color: #f3f6f8;
    background-color: #132a3d;
    border-radius: 8px;
    padding: 6px;
}

QCalendarWidget QToolButton:hover {
    background-color: #1a3951;
}

QTableView {
    background-color: #0a1825;
    alternate-background-color: #102232;
    gridline-color: #163145;
    border: 1px solid #18354c;
    border-radius: 14px;
    selection-background-color: #d58c52;
    selection-color: #0f1d29;
    padding: 6px;
}

QTableView::item {
    padding: 6px;
}

QTableView::item:focus {
    outline: none;
    border: none;
}

QHeaderView::section {
    background-color: #112738;
    color: #f5f7f8;
    border: none;
    border-right: 1px solid #18354c;
    border-bottom: 1px solid #244862;
    padding: 8px 6px;
    font-weight: 800;
}

QPushButton {
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
    min-height: 32px;
    border: 1px solid transparent;
    background: #16314a;
    color: #eff5f8;
}

QPushButton:hover {
    background: #1a3b59;
}

QPushButton:pressed {
    background: #11283a;
}

QPushButton:disabled {
    background: #0d1a26;
    color: #648091;
    border-color: #142b3f;
}

QPushButton#btnPrimary, QPushButton#btnLoginPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #cf7d44,
        stop:1 #e3ab79);
    color: #10202d;
}

QPushButton#btnPrimary:hover, QPushButton#btnLoginPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #dc8f56,
        stop:1 #ebb88d);
}

QPushButton#btnSuccess {
    background: #2d8f7b;
    color: #f5fbfa;
}

QPushButton#btnSuccess:hover {
    background: #39a08b;
}

QPushButton#btnSecondary {
    background: #1a2f42;
    border-color: #27445e;
}

QPushButton#btnSecondary:hover {
    background: #23415c;
}

QPushButton#btnGhost, QPushButton#btnLoginGhost {
    background: transparent;
    border: 1px solid #2b4b63;
    color: #d8e4ea;
}

QPushButton#btnGhost:hover, QPushButton#btnLoginGhost:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: #d58c52;
}

QToolButton#btnGhost {
    background: transparent;
    border: 1px solid #2b4b63;
    color: #d8e4ea;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
}

QToolButton#btnGhost:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: #d58c52;
}

QToolButton#btnGhost::menu-indicator {
    subcontrol-position: right center;
    width: 10px;
}

QPushButton#btnDanger {
    background: #b44b4b;
}

QPushButton#btnDanger:hover {
    background: #c85d5d;
}

QPushButton#btnWarning {
    background: #c8a14d;
    color: #10202d;
}

QPushButton#btnWarning:hover {
    background: #d8b566;
}

QCheckBox {
    color: #e8eef2;
    font-weight: 600;
    spacing: 8px;
    background: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #2a4d66;
    background: #081724;
}

QCheckBox::indicator:checked {
    background: #d58c52;
    border-color: #d58c52;
}

QMenu {
    background-color: #0f2232;
    color: #e8eef2;
    border: 1px solid #244862;
    border-radius: 12px;
    padding: 8px;
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 8px;
}

QMenu::item:selected {
    background-color: #d58c52;
    color: #10202d;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    width: 12px;
}

QScrollBar:horizontal {
    height: 12px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #31506a;
    border-radius: 6px;
    min-height: 28px;
    min-width: 28px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #446b8a;
}

QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {
    border: none;
    background: none;
}

QMessageBox {
    background-color: #0d1d2c;
}

QLabel#loginTitle {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}

QLabel#loginSubtitle {
    color: #afc0ca;
    font-size: 14px;
    font-weight: 500;
}

QLabel#fieldLabel {
    color: #ebf2f6;
    font-size: 13px;
    font-weight: 700;
}

QWidget#inputContainer {
    background-color: #0f2232;
    border: 1px solid #21415a;
    border-radius: 14px;
    min-height: 48px;
    max-height: 48px;
}

QWidget#inputContainer:hover {
    border-color: #306282;
}

QLineEdit#inputField {
    background: transparent;
    border: none;
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
}

QLineEdit#inputField::placeholder {
    color: #6f8a99;
}
"""


LIGHT_MODERN_THEME = """
QWidget {
    background-color: #eef3f6;
    color: #17232d;
    font-size: 13px;
    font-family: "Segoe UI";
}
"""


class ThemeManager:
    current_theme = "dark"

    @classmethod
    def set_theme(cls, app: QApplication, theme_name: str):
        cls.current_theme = theme_name.lower()
        if cls.current_theme == "light":
            app.setStyleSheet(LIGHT_MODERN_THEME)
        else:
            app.setStyleSheet(DARK_MODERN_THEME)

    @classmethod
    def toggle(cls, app: QApplication):
        cls.set_theme(app, "light" if cls.current_theme == "dark" else "dark")
