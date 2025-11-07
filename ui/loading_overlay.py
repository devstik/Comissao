"""
Overlay de carregamento com animação e estados diferentes
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer


class LoadingOverlay(QDialog):
    """
    Overlay modal com animação de loading
    Suporta diferentes mensagens e estados
    """
    
    def __init__(self, parent=None, message: str = "Carregando dados..."):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        if parent:
            self.setFixedSize(parent.size())
            self.move(parent.pos())
        else:
            self.setFixedSize(800, 600)

        # Layout centralizado
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Label com texto
        self.label = QLabel(message)
        self.label.setStyleSheet("""
            font-size: 18px;
            color: white;
            background-color: rgba(0, 0, 0, 160);
            padding: 25px 40px;
            border-radius: 12px;
            font-weight: 600;
        """)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Efeito de opacidade animado
        self.effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.effect)

        # Animação de fade in/out
        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(1000)  # 1 segundo
        self.animation.setStartValue(0.3)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)  # Loop infinito
        
        # Timer para pontos animados (...)
        self.dots_timer = QTimer(self)
        self.dots_timer.timeout.connect(self._animate_dots)
        self.base_message = message
        self.dots_count = 0

    def show_overlay(self):
        """Exibe o overlay e inicia animações"""
        self.show()
        self.animation.start()
        self.dots_timer.start(500)  # Atualiza a cada 500ms
        QApplication.processEvents()

    def close_overlay(self):
        """Para as animações e fecha o overlay"""
        self.animation.stop()
        self.dots_timer.stop()
        self.close()
    
    def update_message(self, message: str):
        """
        Atualiza a mensagem do overlay
        
        Args:
            message: Nova mensagem a exibir
        """
        self.base_message = message
        self.dots_count = 0
        self.label.setText(message)
    
    def _animate_dots(self):
        """Anima os pontos de loading (...) """
        self.dots_count = (self.dots_count + 1) % 4
        dots = "." * self.dots_count
        self.label.setText(f"{self.base_message}{dots}")


class QuickFeedback:
    """
    Classe auxiliar para feedbacks rápidos na interface
    Exibe mensagens temporárias sem bloquear a UI
    """
    
    @staticmethod
    def show(parent, message: str, duration: int = 2000, success: bool = True):
        """
        Mostra um feedback rápido na tela
        
        Args:
            parent: Widget pai
            message: Mensagem a exibir
            duration: Duração em ms (padrão: 2s)
            success: True para sucesso (verde), False para erro (vermelho)
        """
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import QTimer
        
        # Cria label flutuante
        feedback = QLabel(message, parent)
        
        bg_color = "rgba(16, 185, 129, 200)" if success else "rgba(239, 68, 68, 200)"
        icon = "✓" if success else "✗"
        
        feedback.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        feedback.setText(f"{icon} {message}")
        feedback.setAlignment(Qt.AlignCenter)
        feedback.adjustSize()
        
        # Posiciona no centro inferior
        parent_rect = parent.rect()
        x = (parent_rect.width() - feedback.width()) // 2
        y = parent_rect.height() - feedback.height() - 60
        feedback.move(x, y)
        
        feedback.show()
        
        # Remove após duration
        QTimer.singleShot(duration, feedback.deleteLater)