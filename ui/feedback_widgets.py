"""
Componentes de Feedback Visual
Toast notifications, spinners, badges, etc.
"""
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QFrame, QGraphicsOpacityEffect, QPushButton
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QPainter, QPen


class ToastNotification(QWidget):
    """Toast notification moderna e animada"""
    
    def __init__(self, parent, message, toast_type="info", duration=3000):
        super().__init__(parent)
        self.duration = duration
        self.toast_type = toast_type
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setup_ui(message)
        self.setup_animation()
        
        # Auto-close timer
        QTimer.singleShot(duration, self.fade_out)
    
    def setup_ui(self, message):
        """Configura interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Frame com sombra
        frame = QFrame()
        frame.setObjectName("toastFrame")
        
        # Cores por tipo
        colors = {
            "success": ("#10b981", "#d1fae5", "#047857"),
            "error": ("#ef4444", "#fee2e2", "#dc2626"),
            "warning": ("#f59e0b", "#fef3c7", "#d97706"),
            "info": ("#3b82f6", "#dbeafe", "#2563eb")
        }
        
        bg_color, text_bg, text_color = colors.get(self.toast_type, colors["info"])
        
        frame.setStyleSheet(f"""
            QFrame#toastFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(12, 8, 12, 8)
        frame_layout.setSpacing(12)
        
        # Ícone
        icon_label = QLabel(self._get_icon())
        icon_label.setStyleSheet(f"color: white; font-size: 20px;")
        frame_layout.addWidget(icon_label)
        
        # Mensagem
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"""
            color: white;
            font-weight: 600;
            font-size: 13px;
        """)
        msg_label.setWordWrap(True)
        frame_layout.addWidget(msg_label, 1)
        
        # Botão fechar
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        btn_close.clicked.connect(self.fade_out)
        frame_layout.addWidget(btn_close)
        
        layout.addWidget(frame)
    
    def _get_icon(self):
        """Retorna ícone baseado no tipo"""
        icons = {
            "success": "✓",
            "error": "✕",
            "warning": "⚠",
            "info": "ℹ"
        }
        return icons.get(self.toast_type, "ℹ")
    
    def setup_animation(self):
        """Configura animações"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Fade in
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def show(self):
        """Mostra com animação"""
        super().show()
        
        # Posicionar no centro-superior do parent
        parent_rect = self.parent().rect()
        x = (parent_rect.width() - self.sizeHint().width()) // 2
        y = 20
        self.move(x, y)
        
        self.fade_in_animation.start()
    
    def fade_out(self):
        """Fade out e fecha"""
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        fade_out.finished.connect(self.close)
        fade_out.start()
    
    @staticmethod
    def show_success(parent, message, duration=3000):
        """Atalho para toast de sucesso"""
        toast = ToastNotification(parent, message, "success", duration)
        toast.show()
        return toast
    
    @staticmethod
    def show_error(parent, message, duration=4000):
        """Atalho para toast de erro"""
        toast = ToastNotification(parent, message, "error", duration)
        toast.show()
        return toast
    
    @staticmethod
    def show_warning(parent, message, duration=3000):
        """Atalho para toast de aviso"""
        toast = ToastNotification(parent, message, "warning", duration)
        toast.show()
        return toast
    
    @staticmethod
    def show_info(parent, message, duration=3000):
        """Atalho para toast de info"""
        toast = ToastNotification(parent, message, "info", duration)
        toast.show()
        return toast


class LoadingSpinner(QWidget):
    """Spinner de loading animado"""
    
    def __init__(self, parent=None, size=40, color="#3b82f6"):
        super().__init__(parent)
        self.size = size
        self.color = QColor(color)
        self.angle = 0
        
        self.setFixedSize(size, size)
        
        # Timer para animação
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # 20 FPS
    
    def rotate(self):
        """Rotaciona o spinner"""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """Desenha o spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Centro
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = (self.size - 10) // 2
        
        # Desenha arco
        pen = QPen(self.color, 4, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)
        
        # Arco de 270 graus
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0, 270 * 16)


class Badge(QLabel):
    """Badge colorido para status"""
    
    def __init__(self, text, badge_type="default", parent=None):
        super().__init__(text, parent)
        
        colors = {
            "default": ("#64748b", "#f1f5f9"),
            "primary": ("#3b82f6", "#dbeafe"),
            "success": ("#10b981", "#d1fae5"),
            "warning": ("#f59e0b", "#fef3c7"),
            "danger": ("#ef4444", "#fee2e2"),
            "info": ("#06b6d4", "#cffafe")
        }
        
        text_color, bg_color = colors.get(badge_type, colors["default"])
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
            }}
        """)
        
        self.setAlignment(Qt.AlignCenter)


class StatCard(QFrame):
    """Card de estatística/KPI"""
    
    def __init__(self, title, value, icon="", trend=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header com ícone e título
        header = QHBoxLayout()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("""
                font-size: 24px;
                color: #3b82f6;
            """)
            header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #64748b;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        header.addWidget(title_label, 1)
        
        layout.addLayout(header)
        
        # Valor principal
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
            color: #0f172a;
        """)
        layout.addWidget(value_label)
        
        # Trend (opcional)
        if trend:
            trend_layout = QHBoxLayout()
            
            trend_icon = "↑" if trend > 0 else "↓"
            trend_color = "#10b981" if trend > 0 else "#ef4444"
            
            trend_label = QLabel(f"{trend_icon} {abs(trend):.1f}%")
            trend_label.setStyleSheet(f"""
                color: {trend_color};
                font-size: 13px;
                font-weight: 600;
            """)
            trend_layout.addWidget(trend_label)
            trend_layout.addStretch()
            
            layout.addLayout(trend_layout)
        
        # Estilo do card
        self.setStyleSheet("""
            QFrame#card {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
            }
            QFrame#card:hover {
                border-color: #3b82f6;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }
        """)
        
        self.setMinimumHeight(140)


class ProgressIndicator(QWidget):
    """Indicador de progresso com percentual"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Label superior (título + percentual)
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel("Processando...")
        self.lbl_title.setStyleSheet("font-weight: 600; color: #475569;")
        top_layout.addWidget(self.lbl_title)
        
        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setStyleSheet("font-weight: 700; color: #3b82f6;")
        top_layout.addWidget(self.lbl_percent)
        
        layout.addLayout(top_layout)
        
        # Barra de progresso
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QFrame {
                background-color: #e2e8f0;
                border-radius: 4px;
            }
        """)
        
        self.progress_fill = QFrame(self.progress_bar)
        self.progress_fill.setFixedHeight(8)
        self.progress_fill.setStyleSheet("""
            QFrame {
                background-color: #3b82f6;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.progress_bar)
    
    def set_value(self, value):
        """Define valor do progresso (0-100)"""
        self.value = max(0, min(100, value))
        self.lbl_percent.setText(f"{self.value}%")
        
        # Atualiza largura da barra
        bar_width = self.progress_bar.width()
        fill_width = int((bar_width * self.value) / 100)
        self.progress_fill.setFixedWidth(fill_width)
    
    def set_title(self, title):
        """Define título"""
        self.lbl_title.setText(title)


# Exemplo de uso
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
    import sys
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Componentes de Feedback")
    window.resize(800, 600)
    
    central = QWidget()
    layout = QVBoxLayout(central)
    layout.setSpacing(20)
    layout.setContentsMargins(20, 20, 20, 20)
    
    # Cards de estatística
    cards_layout = QHBoxLayout()
    cards_layout.addWidget(StatCard("Total Vendas", "R$ 125.430,00", "💰", trend=12.5))
    cards_layout.addWidget(StatCard("Comissões", "R$ 6.271,50", "📊", trend=-3.2))
    cards_layout.addWidget(StatCard("Títulos", "1.248", "📄", trend=8.7))
    layout.addLayout(cards_layout)
    
    # Badges
    badges_layout = QHBoxLayout()
    badges_layout.addWidget(Badge("PAGO", "success"))
    badges_layout.addWidget(Badge("PENDENTE", "warning"))
    badges_layout.addWidget(Badge("VENCIDO", "danger"))
    badges_layout.addWidget(Badge("EM ANÁLISE", "info"))
    badges_layout.addStretch()
    layout.addLayout(badges_layout)
    
    # Spinner
    spinner = LoadingSpinner(size=50, color="#3b82f6")
    layout.addWidget(spinner)
    
    # Indicador de progresso
    progress = ProgressIndicator()
    progress.set_value(65)
    progress.set_title("Sincronizando dados...")
    layout.addWidget(progress)
    
    # Botões para testar toasts
    btn_layout = QHBoxLayout()
    
    btn_success = QPushButton("Toast Sucesso")
    btn_success.clicked.connect(
        lambda: ToastNotification.show_success(window, "Operação concluída com sucesso!")
    )
    btn_layout.addWidget(btn_success)
    
    btn_error = QPushButton("Toast Erro")
    btn_error.clicked.connect(
        lambda: ToastNotification.show_error(window, "Erro ao processar operação!")
    )
    btn_layout.addWidget(btn_error)
    
    btn_warning = QPushButton("Toast Aviso")
    btn_warning.clicked.connect(
        lambda: ToastNotification.show_warning(window, "Atenção! Verifique os dados.")
    )
    btn_layout.addWidget(btn_warning)
    
    btn_info = QPushButton("Toast Info")
    btn_info.clicked.connect(
        lambda: ToastNotification.show_info(window, "3 novos títulos disponíveis.")
    )
    btn_layout.addWidget(btn_info)
    
    layout.addLayout(btn_layout)
    layout.addStretch()
    
    window.setCentralWidget(central)
    window.show()
    
    sys.exit(app.exec())