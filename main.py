
"""
Sistema de Comissões STIK
Ponto de entrada da aplicação
"""
import sys
from PySide6.QtWidgets import QApplication, QDialog
from ui import LoginDialog, MainWindow, apply_theme

def main():
    """Função principal - Inicializa a aplicação"""
    app = QApplication(sys.argv)
    apply_theme(app)
    dlg = LoginDialog()
    
    if dlg.exec() == QDialog.Accepted:
        win = MainWindow(dlg.username, dlg.role)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()