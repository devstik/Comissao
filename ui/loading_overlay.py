"""
Overlay de carregamento e feedback rapido da interface.
"""
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsOpacityEffect, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer


class LoadingOverlay(QDialog):
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

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            font-size: 18px;
            color: #f3f6f8;
            background-color: rgba(12, 29, 44, 224);
            border: 1px solid rgba(213, 140, 82, 120);
            padding: 22px 34px;
            border-radius: 18px;
            font-weight: 700;
        """)
        layout.addWidget(self.label)

        self.effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.effect)

        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.35)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)

        self.dots_timer = QTimer(self)
        self.dots_timer.timeout.connect(self._animate_dots)
        self.base_message = message
        self.dots_count = 0

    def show_overlay(self):
        self.show()
        self.animation.start()
        self.dots_timer.start(500)
        QApplication.processEvents()

    def close_overlay(self):
        self.animation.stop()
        self.dots_timer.stop()
        self.close()

    def update_message(self, message: str):
        self.base_message = message
        self.dots_count = 0
        self.label.setText(message)

    def _animate_dots(self):
        self.dots_count = (self.dots_count + 1) % 4
        self.label.setText(f"{self.base_message}{'.' * self.dots_count}")


class QuickFeedback:
    @staticmethod
    def show(parent, message: str, duration: int = 2000, success: bool = True):
        feedback = QLabel(message, parent)

        bg_color = "rgba(45, 143, 123, 235)" if success else "rgba(180, 75, 75, 235)"
        border_color = "rgba(139, 225, 206, 120)" if success else "rgba(255, 214, 214, 120)"
        prefix = "OK" if success else "ERRO"

        feedback.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                color: white;
                padding: 12px 22px;
                border-radius: 14px;
                font-size: 13px;
                font-weight: 700;
            }}
        """)
        feedback.setText(f"{prefix}  {message}")
        feedback.setAlignment(Qt.AlignCenter)
        feedback.adjustSize()

        parent_rect = parent.rect()
        x = (parent_rect.width() - feedback.width()) // 2
        y = parent_rect.height() - feedback.height() - 60
        feedback.move(x, y)
        feedback.show()

        QTimer.singleShot(duration, feedback.deleteLater)
