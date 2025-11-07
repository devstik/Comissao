
# =====================================================
# ARQUIVO 1: ui/__init__.py
# =====================================================
"""
Pacote de interface do usuário
Exporta todos os componentes da UI
"""

from .login_dialog import LoginDialog, center_widget
from .main_window import MainWindow
from .styles import apply_theme, DARK_PURPLE_THEME
from .icons import Icons, icon_button_text
from .loading_overlay import LoadingOverlay, QuickFeedback

__all__ = [
    "LoginDialog",
    "center_widget",
    "MainWindow",
    "apply_theme",
    "DARK_PURPLE_THEME",
    "Icons",
    "icon_button_text",
    "LoadingOverlay",
    "QuickFeedback"
]
