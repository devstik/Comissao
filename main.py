"""
Sistema de Comissões STIK
Ponto de entrada da aplicação
"""
import sys
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer
from ui import LoginDialog, MainWindow
from ui.themes import ThemeManager
from ui.update_dialog import UpdateDialog
from utils.updater import has_update
from constants import APP_VERSION


def check_for_updates(main_window):
    """Verifica atualizações em segundo plano"""
    try:
        update_info = has_update()
        
        if update_info:
            version, url, notes = update_info
            dialog = UpdateDialog(version, url, notes, main_window)
            dialog.exec()
    except Exception as e:
        print(f"Erro ao verificar atualizações: {e}")


def main():
    """Função principal - Inicializa a aplicação"""
    app = QApplication(sys.argv)
    
    # APLICAR TEMA MODERNO
    ThemeManager.set_theme(app, "dark")
    
    # Login
    dlg = LoginDialog()
    
    if dlg.exec() == QDialog.Accepted:
        win = MainWindow(dlg.username, dlg.role)
        
        # Atualizar título com versão
        win.setWindowTitle(f"Comissys - v{APP_VERSION}")
        
        win.show()
        
        # Verificar atualizações após 2 segundos (não bloqueia a inicialização)
        QTimer.singleShot(2000, lambda: check_for_updates(win))
        
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()