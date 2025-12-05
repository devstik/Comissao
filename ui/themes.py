from PySide6.QtWidgets import QApplication
# =========================================
#  TEMA DARK — SEU CSS COMPLETO AQUI
# =========================================

DARK_PURPLE_THEME = """
    /* ==================== ESTILOS BASE ==================== */
    QWidget { 
        background-color: #0f1020; 
        color: #E5E7EB; 
        font-size: 13px; 
    }
    
    QLabel { 
        color: #ffffff; 
        font-weight: 700; 
    }
    
    /* ==================== TABS ==================== */
    QTabWidget::pane { 
        border: 1px solid #4c1d95; 
        background: #1a1c2e; 
    }
    
    QTabBar::tab { 
        background: #4c1d95; 
        color: #ffffff; 
        padding: 10px 16px; 
        font-weight: 700; 
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    
    QTabBar::tab:selected { 
        background: #6D28D9; 
    }
    
    QTabBar::tab:hover { 
        background: #7C3AED; 
    }
    
    QTabBar::tab:!selected {
        margin-top: 2px;
    }

    /* ==================== INPUTS ==================== */
    QLineEdit, QDateEdit, QSpinBox {
        background: #1a1c2e; 
        color: #E5E7EB; 
        border: 1px solid #2a2d4a; 
        border-radius: 8px; 
        padding: 6px 10px;
        font-weight: 600;
        min-height: 28px;
    }
    
    QLineEdit:focus, QDateEdit:focus, QSpinBox:focus {
        border-color: #6D28D9;
        background: #1f2137;
    }
    
    QLineEdit:hover, QDateEdit:hover, QSpinBox:hover {
        border-color: #4c1d95;
    }
    
    /* ==================== COMBOBOX COMPLETO ==================== */
    QComboBox {
        background: #1a1c2e; 
        color: #E5E7EB; 
        border: 1px solid #2a2d4a; 
        border-radius: 8px; 
        padding: 6px 10px;
        padding-right: 35px;
        font-weight: 600;
        min-height: 28px;
    }
    
    QComboBox:hover {
        border-color: #4c1d95;
    }
    
    QComboBox:focus {
        border-color: #6D28D9;
        background: #1f2137;
    }
    
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        border: none;
        width: 25px;
        background: transparent;
    }

    /* ✅ SETA DO COMBOBOX - SVG inline (chevron down branco) */
    QComboBox::down-arrow {
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
        width: 12px;
        height: 8px;
    }

    /* Estilo do dropdown (lista) */
    QComboBox QAbstractItemView {
        background-color: #1a1c2e;
        color: #E5E7EB;
        selection-background-color: #6D28D9;
        selection-color: #ffffff;
        border: 1px solid #4c1d95;
        border-radius: 8px;
        padding: 5px;
        outline: none;
    }
    
    QComboBox QAbstractItemView::item {
        padding: 8px 12px;
        min-height: 30px;
        border-radius: 4px;
    }
    
    QComboBox QAbstractItemView::item:hover {
        background-color: #7C3AED;
    }
    
    QComboBox QAbstractItemView::item:selected {
        background-color: #6D28D9;
    }

    /* ==================== TABELAS ==================== */
    QTableView { 
        gridline-color: #2a2d4a; 
        selection-background-color: #4c1d95; 
        selection-color: #ffffff; 
        background-color: #1a1c2e;
        border: 1px solid #2a2d4a;
        border-radius: 8px;
    }
    
    QTableView::item:hover {
        background-color: #1f2137;
    }
    
    QTableView::item:selected {
        background-color: #4c1d95;
    }
    
    QHeaderView::section {
        background: #1b1e33; 
        color: #ffffff; 
        padding: 8px; 
        border: 0px; 
        border-right: 1px solid #2a2d4a; 
        border-bottom: 2px solid #4c1d95;
        font-weight: 700;
    }
    
    QHeaderView::section:hover {
        background: #252842;
    }

    /* ==================== SCROLLBARS VERTICAIS ==================== */
    QScrollBar:vertical {
        background: #1a1c2e;
        width: 12px;
        border-radius: 6px;
        margin: 2px;
    }
    
    QScrollBar::handle:vertical {
        background: #4b5563;
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #6b7280;
    }
    
    QScrollBar::handle:vertical:pressed {
        background: #9ca3af;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    /* ==================== SCROLLBARS HORIZONTAIS ==================== */
    QScrollBar:horizontal {
        background: #1a1c2e;
        height: 12px;
        border-radius: 6px;
        margin: 2px;
    }
    
    QScrollBar::handle:horizontal {
        background: #4b5563;
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #6b7280;
    }
    
    QScrollBar::handle:horizontal:pressed {
        background: #9ca3af;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }

    /* ==================== BOTÕES BASE ==================== */
    QPushButton {
        border-radius: 10px; 
        padding: 10px 16px; 
        font-weight: 700; 
        border: 1px solid transparent;
        background: #2a2d4a; 
        color: #ffffff;
        min-height: 32px;
    }
    
    QPushButton:hover {
        background: #353854;
    }
    
    QPushButton:pressed {
        background: #1f2237;
    }
    
    QPushButton:disabled {
        background: #1a1c2e;
        color: #6b7280;
    }
    
    QPushButton:focus {
        outline: none;
        border: 1px solid #6D28D9;
    }

    /* ==================== CLASSES DE BOTÕES ==================== */
    QPushButton#btnPrimary { 
        background: #6D28D9; 
    }
    
    QPushButton#btnPrimary:hover { 
        background: #7C3AED; 
    }
    
    QPushButton#btnPrimary:pressed { 
        background: #5B21B6; 
    }
    
    QPushButton#btnSuccess { 
        background: #0ea5e9; 
    }
    
    QPushButton#btnSuccess:hover { 
        background: #22a6f0; 
    }
    
    QPushButton#btnSuccess:pressed { 
        background: #0284c7; 
    }
    
    QPushButton#btnSecondary { 
        background: #374151; 
    }
    
    QPushButton#btnSecondary:hover { 
        background: #4b5563; 
    }
    
    QPushButton#btnSecondary:pressed { 
        background: #1f2937; 
    }
    
    QPushButton#btnGhost { 
        background: transparent; 
        border: 1px solid #374151; 
    }
    
    QPushButton#btnGhost:hover { 
        background: #1a1c2e; 
        border-color: #4b5563;
    }
    
    QPushButton#btnGhost:pressed { 
        background: #252842; 
    }
    
    QPushButton#btnDanger { 
        background: #dc2626; 
    }
    
    QPushButton#btnDanger:hover { 
        background: #ef4444; 
    }
    
    QPushButton#btnDanger:pressed { 
        background: #b91c1c; 
    }
    
    QPushButton#btnWarning { 
        background: #f59e0b; 
        color: #1f2937;
    }
    
    QPushButton#btnWarning:hover { 
        background: #fbbf24; 
    }
    
    QPushButton#btnWarning:pressed { 
        background: #d97706; 
    }

    /* ==================== CHECKBOX ==================== */
    QCheckBox {
        color: #E5E7EB;
        font-weight: 600;
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border: 2px solid #2a2d4a;
        border-radius: 5px;
        background: #1a1c2e;
    }
    
    QCheckBox::indicator:hover {
        border-color: #6D28D9;
        background: #1f2137;
    }
    
    QCheckBox::indicator:checked {
        background: #6D28D9;
        border-color: #6D28D9;
    }
    
    QCheckBox::indicator:checked:hover {
        background: #7C3AED;
        border-color: #7C3AED;
    }
    
    QCheckBox::indicator:disabled {
        background: #1a1c2e;
        border-color: #374151;
    }

    /* ==================== SPINBOX SETAS (SVG) ==================== */
    QSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #2a2d4a;
        border-top-right-radius: 8px;
        background: transparent;
    }
    
    QSpinBox::up-button:hover {
        background: #4c1d95;
    }
    
    /* ✅ Seta PARA CIMA - SVG inline (chevron up branco) */
    QSpinBox::up-arrow {
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTExIDdMNiAyTDEgNyIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
        width: 12px;
        height: 8px;
    }
    
    QSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid #2a2d4a;
        border-bottom-right-radius: 8px;
        background: transparent;
    }
    
    QSpinBox::down-button:hover {
        background: #4c1d95;
    }
    
    /* ✅ Seta PARA BAIXO - SVG inline (chevron down branco) */
    QSpinBox::down-arrow {
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
        width: 12px;
        height: 8px;
    }

    /* ==================== DATEEDIT CALENDÁRIO ==================== */
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 25px;
        border: none;
        background: transparent;
    }
    
    /* ✅ SETA DO DATEEDIT - SVG inline (chevron down branco) */
    QDateEdit::down-arrow {
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
        width: 12px;
        height: 8px;
    }
    
    QCalendarWidget {
        background-color: #1a1c2e;
        color: #E5E7EB;
    }
    
    QCalendarWidget QToolButton {
        color: #E5E7EB;
        background-color: #2a2d4a;
        border-radius: 4px;
        padding: 5px;
    }
    
    QCalendarWidget QToolButton:hover {
        background-color: #4c1d95;
    }
    
    QCalendarWidget QMenu {
        background-color: #1a1c2e;
        color: #E5E7EB;
    }
    
    QCalendarWidget QSpinBox {
        background-color: #2a2d4a;
        selection-background-color: #6D28D9;
    }
    
    QCalendarWidget QAbstractItemView {
        background-color: #1a1c2e;
        selection-background-color: #6D28D9;
        selection-color: #ffffff;
    }

    /* ==================== MESSAGEBOX ==================== */
    QMessageBox {
        background-color: #1a1c2e;
    }
    
    QMessageBox QLabel {
        color: #E5E7EB;
        font-weight: 500;
    }
    
    QMessageBox QPushButton {
        min-width: 80px;
        padding: 8px 16px;
    }

    /* ==================== ESTILOS DO LOGIN ==================== */
    QDialog {
        background-color: #0f1020;
    }
    
    QLabel#loginTitle {
        color: #ffffff;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    QLabel#loginSubtitle {
        color: #8b8b9f;
        font-size: 14px;
        font-weight: 400;
    }
    
    QLabel#fieldLabel {
        color: #ffffff;
        font-size: 14px;
        font-weight: 600;
    }
    
    QWidget#inputContainer {
        background-color: #16213e;
        border: 2px solid #2a2f4f;
        border-radius: 10px;
        min-height: 54px;
        max-height: 54px;
    }
    
    QWidget#inputContainer:hover {
        border-color: #4c1d95;
    }
    
    QLabel#inputIcon {
        font-size: 20px;
        min-width: 24px;
        max-width: 24px;
    }
    
    QLineEdit#inputField {
        background: transparent;
        border: none;
        color: #ffffff;
        font-size: 15px;
        font-weight: 500;
    }
    
    QLineEdit#inputField::placeholder {
        color: #6b6b7f;
    }
    
    QPushButton#togglePassBtn {
        background: transparent;
        border: none;
        font-size: 20px;
        color: #8b8b9f;
        border-radius: 6px;
        padding: 5px;
    }
    
    QPushButton#togglePassBtn:hover {
        color: #ffffff;
        background: rgba(124, 58, 237, 0.2);
    }
    
    QPushButton#btnLoginPrimary {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #7c3aed,
            stop:1 #9333ea
        );
        color: #ffffff;
        border: none;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 700;
    }
    
    QPushButton#btnLoginPrimary:hover {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #8b44ff,
            stop:1 #a444ff
        );
    }
    
    QPushButton#btnLoginPrimary:pressed {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #6d28d9,
            stop:1 #7c3aed
        );
    }
    
    QPushButton#btnLoginGhost {
        background: transparent;
        color: #8b8b9f;
        border: 2px solid #2a2f4f;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 600;
    }
    
    QPushButton#btnLoginGhost:hover {
        border-color: #7c3aed;
        color: #7c3aed;
        background: rgba(124, 58, 237, 0.1);
    }
    
    QPushButton#btnLoginGhost:pressed {
        border-color: #6d28d9;
        color: #6d28d9;
        background: rgba(109, 40, 217, 0.2);
    }
"""
# =========================================
#  TEMA LIGHT — MESMA ESTRUTURA DO DARK
#  Paleta clara: branco, cinza claro, roxo suave
# =========================================
LIGHT_PURPLE_APPLE_THEME = """
    /* ============================== LIGHT SOFT THEME (Apple Style) ============================== */

QWidget {
    background-color: #F4F6FA;
    color: #1E1E1E;
    font-size: 13px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

/* Cards */
QFrame#card, QFrame[objectName="card"], QWidget.card {
    background-color: #FFFFFF;
    border-radius: 8px;
    border: 1px solid #E4E6EB;
    padding: 12px;
    box-shadow: 0 6px 18px rgba(30,30,30,0.05);
}

/* Labels */
QLabel { color: #1E1E1E; }
QLabel[objectName="lblTitle"] { font-size: 18px; font-weight: 700; }

/* ============================== INPUTS ============================== */
QLineEdit, QDateEdit, QSpinBox {
    background: #FFFFFF;
    color: #1E1E1E;
    border: 1px solid #D6D8E0;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 34px;
}

QLineEdit:focus, QDateEdit:focus, QSpinBox:focus {
    border-color: #8B5CF6;
    box-shadow: 0 0 0 3px rgba(139,92,246,0.18);
}

/* ============================== COMBOBOX (Apple Style) ============================== */

QComboBox {
    background: #ffffff;
    border: 1px solid #D6D8E0;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 34px;
    color: #1E1E1E;
}

QComboBox::down-arrow {
    image: url(:/icons/chevron-down.png);
    width: 12px;
    height: 12px;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
    background: transparent;
}

/* Popup */
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #D6D8E0;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}

/* Items dentro do dropdown */
QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #1E1E1E;
}

/* Hover estilo Apple */
QComboBox QAbstractItemView::item:hover {
    background: #F2F3F7;
}

/* Selecionado estilo suave */
QComboBox QAbstractItemView::item:selected {
    background: #EAE5FF;
    color: #1E1E1E;
}

/* ============================== TABS ============================== */
QTabBar::tab {
    background: #eef0f6;
    color: #555A6E;
    padding: 8px 14px;
    margin-right: 4px;
    border-radius: 8px 8px 0 0;
    border: 1px solid transparent;
    min-height: 36px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #ffffff;
    border-bottom: 2px solid #8B5CF6;
    color: #8B5CF6;
}

/* ============================== BOTÕES ============================== */
QPushButton {
    border-radius: 8px;
    padding: 10px 16px;
    min-height: 32px;
    border: 1px solid transparent;
    background: #F0F2FA;
    color: #1E1E1E;
    font-weight: 600;
    transition: 0.15s ease;
    box-shadow: 0 4px 12px rgba(30,30,30,0.06);
}

QPushButton:hover { background: #E9EBF5; }
QPushButton:pressed { background: #E0E3F0; }

/* Botão primário */
QPushButton#btnPrimary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8B5CF6, stop:1 #A78BFA);
    color: #ffffff;
    border: none;
    box-shadow: 0 8px 20px rgba(139,92,246,0.18);
}

/* Ghost */
QPushButton#btnGhost {
    background: transparent;
    border: 1px solid #E6E8EE;
    color: #555A6E;
}

/* ============================== TABLES ============================== */
QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F8F9FB;
    border: 1px solid #E6E8EE;
    border-radius: 6px;
    selection-background-color: #EAE5FF;
    selection-color: #1E1E1E;
}

QHeaderView::section {
    background-color: #F3F4F8;
    color: #4B5563;
    padding: 8px;
    font-weight: 700;
    border-right: 1px solid #E6E8EE;
}

/* ============================== SCROLL ============================== */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #D1D5DB;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #BFC6D1;
}

/* ==================== HORIZONTAL SCROLLBAR ==================== */
QScrollBar:horizontal {
    background: transparent;
    height: 15px;                /* altura discreta */
    margin: 0 12px 0 12px;       /* espaço entre bordas e cantos */
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background: #D1D5DB;         /* cor do "polegar" */
    min-width: 30px;
    height: 15px;
    border-radius: 6px;
    margin: 2px 0;               /* deixar um pequeno espaçamento */
}

/* Hover do handle */
QScrollBar::handle:horizontal:hover {
    background: #BFC6D1;
}

/* Pressed / arrastando */
QScrollBar::handle:horizontal:pressed {
    background: #AEB6C3;
}

/* Remover setas e linhas desnecessárias */
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
    height: 0;
}

/* Ajuste fino para QTableView / QAbstractScrollArea (garante que a barra horizontal fique mais alinhada) */
QTableView QScrollBar:horizontal,
QAbstractScrollArea QScrollBar:horizontal {
    margin: 0 8px 8px 8px;
}

/* Se quiser que a barra apareça com leve sombra quando existir overflow */
QScrollBar:horizontal:enabled {
    /* pequena sombra apenas para evidenciar a presença do controle */
    box-shadow: 0 4px 10px rgba(30,30,30,0.03);
}

/* ============================== DIALOGS ============================== */
QDialog {
    background-color: #F4F6FA;
    border-radius: 12px;
}

QLabel#loginTitle {
    color: #111827;
    font-size: 26px;
    font-weight: 700;
}

"""

# =========================
# THEME MANAGER
# =========================
class ThemeManager:
    """
    ThemeManager simples — aplica DARK_PURPLE_THEME ou LIGHT_SOFT_THEME.
    Uso:
        ThemeManager.set_theme(app, "dark")
        ThemeManager.set_theme(app, "light")
        ThemeManager.toggle(app)
    """
    current_theme = "dark"

    @classmethod
    def set_theme(cls, app: QApplication, theme_name: str):
        cls.current_theme = theme_name.lower()
        if cls.current_theme == "light":
            app.setStyleSheet(LIGHT_PURPLE_APPLE_THEME)
        else:
            app.setStyleSheet(DARK_PURPLE_THEME)

    @classmethod
    def toggle(cls, app: QApplication):
        new_theme = "light" if cls.current_theme == "dark" else "dark"
        cls.set_theme(app, new_theme)