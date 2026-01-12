"""
Dialog de atualização do sistema
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from ui.icons import Icons
from utils.updater import download_update, install_update


class DownloadThread(QThread):
    """Thread para download da atualização"""
    progress = Signal(int, int)  # bytes_downloaded, total_bytes
    finished = Signal(str)  # filepath
    error = Signal(str)  # error_message
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            filepath = download_update(
                self.url, 
                lambda down, total: self.progress.emit(down, total)
            )
            
            if filepath:
                self.finished.emit(filepath)
            else:
                self.error.emit("Falha ao baixar atualização")
        except Exception as e:
            self.error.emit(str(e))


class UpdateDialog(QDialog):
    """Dialog para notificar e instalar atualizações"""
    
    def __init__(self, version: str, url: str, notes: str, parent=None):
        super().__init__(parent)
        self.version = version
        self.url = url
        self.notes = notes
        self.download_thread = None
        self.update_file = None
        
        self.setWindowTitle("Atualização Disponível")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel(f"{Icons.INFO} Nova versão disponível!")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Versão
        version_label = QLabel(f"Versão {self.version}")
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        layout.addWidget(version_label)
        
        # Notas da versão
        notes_label = QLabel("O que há de novo:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(notes_label)
        
        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(150)
        self.notes_text.setPlainText(self.notes)
        layout.addWidget(self.notes_text)
        
        # Barra de progresso (inicialmente oculta)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_later = QPushButton("Agora Não")
        self.btn_later.setMinimumWidth(120)
        self.btn_later.clicked.connect(self.reject)
        
        self.btn_update = QPushButton(f"{Icons.DOWNLOAD} Baixar e Instalar")
        self.btn_update.setObjectName("btnPrimary")
        self.btn_update.setMinimumWidth(150)
        self.btn_update.clicked.connect(self.start_download)
        
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_update)
        
        layout.addLayout(btn_layout)
    
    def start_download(self):
        """Inicia o download da atualização"""
        self.btn_update.setEnabled(False)
        self.btn_later.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Baixando atualização...")
        
        self.download_thread = DownloadThread(self.url)
        self.download_thread.progress.connect(self.on_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_error)
        self.download_thread.start()
    
    def on_progress(self, downloaded: int, total: int):
        """Atualiza a barra de progresso"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            
            # Formata os tamanhos
            mb_down = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(
                f"Baixando: {mb_down:.1f} MB de {mb_total:.1f} MB ({percent}%)"
            )
    
    def on_download_finished(self, filepath: str):
        """Quando o download termina"""
        self.update_file = filepath
        self.progress_bar.setValue(100)
        self.status_label.setText("Download concluído! Instalando...")
        
        # Instala a atualização
        success = install_update(filepath)
        
        if success:
            self.status_label.setText("Atualização instalada! O sistema será reiniciado...")
            # O aplicativo será fechado pelo script batch
        else:
            self.on_error("Falha ao instalar atualização")
    
    def on_error(self, error: str):
        """Quando ocorre um erro"""
        self.status_label.setText(f"Erro: {error}")
        self.status_label.setStyleSheet("color: red; font-size: 11px;")
        self.btn_later.setEnabled(True)
        self.btn_update.setText("Tentar Novamente")
        self.btn_update.setEnabled(True)
        self.download_thread = None
