"""
Tela de Login do Sistema
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QApplication, QWidget
)
from PySide6.QtCore import Qt
from constants import USERS


def center_widget(widget):
    """Centraliza widget na tela"""
    screen = QApplication.primaryScreen().availableGeometry()
    fg = widget.frameGeometry()
    fg.moveCenter(screen.center())
    widget.move(fg.topLeft())


class LoginDialog(QDialog):
    """Diálogo de autenticação do sistema"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login do Sistema")
        self.setFixedSize(420, 520)  # ✅ Reduzido de 520 para 480
        
        # Variáveis de resultado
        self.username = None
        self.role = None
        
        self._setup_ui()
        center_widget(self)
    
    def _setup_ui(self):
        """Configura a interface"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)
        
        # Header (título + subtítulo)
        self._create_header(main_layout)
        
        # Campo Usuário
        self._create_user_field(main_layout)
        
        # Campo Senha (SEM BOTÃO DE TOGGLE)
        self._create_password_field(main_layout)
        
        # Botões
        self._create_buttons(main_layout)
    
    def _create_header(self, layout):
        """Cria o cabeçalho com título e subtítulo"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Login do Sistema")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Bem-vindo de volta! Entre com suas credenciais")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(30)
        
        layout.addLayout(header_layout)
    
    def _create_user_field(self, layout):
        """Cria o campo de usuário"""
        user_label = QLabel("Usuário")
        user_label.setObjectName("fieldLabel")

        user_container = QWidget()
        user_container.setObjectName("inputContainer")
        user_layout = QHBoxLayout(user_container)
        user_layout.setContentsMargins(12, 0, 12, 0)
        user_layout.setSpacing(10)

        self.ed_user = QLineEdit()
        self.ed_user.setObjectName("inputField")
        self.ed_user.setPlaceholderText("Usuário (ex: admin/karen/jessica)")
        self.ed_user.setFrame(False)

        user_layout.addWidget(self.ed_user)

        layout.addWidget(user_label)
        layout.addSpacing(8)
        layout.addWidget(user_container)
        layout.addSpacing(20)
        
        # Conecta Enter para ir para o campo de senha
        self.ed_user.returnPressed.connect(self._focus_password)
    
    def _create_password_field(self, layout):
        """Cria o campo de senha SEM botão de toggle"""
        pass_label = QLabel("Senha")
        pass_label.setObjectName("fieldLabel")

        pass_container = QWidget()
        pass_container.setObjectName("inputContainer")
        pass_layout = QHBoxLayout(pass_container)
        pass_layout.setContentsMargins(12, 0, 12, 0)
        pass_layout.setSpacing(10)

        self.ed_pass = QLineEdit()
        self.ed_pass.setObjectName("inputField")
        self.ed_pass.setPlaceholderText("Senha")
        self.ed_pass.setEchoMode(QLineEdit.Password)  # ✅ Sempre oculta
        self.ed_pass.setFrame(False)

        pass_layout.addWidget(self.ed_pass)
        # ❌ REMOVIDO: self.toggle_pass_btn

        layout.addWidget(pass_label)
        layout.addSpacing(8)
        layout.addWidget(pass_container)
        layout.addSpacing(30)
        
        # Conecta Enter para fazer login
        self.ed_pass.returnPressed.connect(self._do_login)
    
    def _create_buttons(self, layout):
        """Cria os botões de ação"""
        btn_ok = QPushButton("Entrar")
        btn_ok.setObjectName("btnLoginPrimary")
        btn_ok.setFixedHeight(48)
        btn_ok.setCursor(Qt.PointingHandCursor)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnLoginGhost")
        btn_cancel.setFixedHeight(48)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        
        layout.addStretch()
        layout.addWidget(btn_ok)
        layout.addSpacing(12)
        layout.addWidget(btn_cancel)
        layout.addStretch()
        
        # Conectar eventos
        btn_ok.clicked.connect(self._do_login)
        btn_cancel.clicked.connect(self.reject)
    
    # ❌ REMOVIDO: _toggle_password()
    
    def _focus_password(self):
        """Move o foco para o campo de senha"""
        self.ed_pass.setFocus()
    
    def _do_login(self):
        """Valida credenciais e faz login"""
        u = self.ed_user.text().strip().lower()
        p = self.ed_pass.text()
        
        if u in USERS and USERS[u]["pwd"] == p:
            self.username = u
            self.role = USERS[u]["role"]
            self.accept()
        else:
            QMessageBox.warning(self, "Login", "Usuário ou senha inválidos.")
