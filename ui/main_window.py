"""
Janela Principal do Sistema
RESPONSIVA | COM ÍCONES | COM FEEDBACKS | MENU DE CONTEXTO
"""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QMenu,
    QTableView, QAbstractItemView, QApplication, QStackedWidget
)
from PySide6.QtCore import Qt
from ui.themes import ThemeManager
from tabs import TabConsulta, TabExtrato, TabConsolidados
from ui.loading_overlay import QuickFeedback


def center_widget(widget):
    """Centraliza widget na tela"""
    screen = QApplication.primaryScreen().availableGeometry()
    fg = widget.frameGeometry()
    fg.moveCenter(screen.center())
    widget.move(fg.topLeft())


class MainWindow(QMainWindow):
    """
    Janela Principal do Sistema de Comissões
    Gerencia as 3 abas principais: Consulta, Extrato e Consolidados
    """
    
    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = role

        self.setWindowTitle(f"Comissões STIK - {username.title()} ({role.title()})")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 600)  # Tamanho mínimo para responsividade
        center_widget(self)

        # Cria as abas
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Inicializa as abas
        self._init_tabs()

        # Configura menus de contexto nas tabelas
        self._setup_table_context_menus()
    
    def _init_tabs(self):
        """Inicializa as abas do sistema"""
        # Tab Consulta (apenas para admin)
        if self.role == "admin":
            self.tab_consulta = TabConsulta(parent=self, role=self.role)
            self.tabs.addTab(self.tab_consulta, "📋 Consulta")
            
            # Conecta o botão de adicionar ao extrato
            self.tab_consulta.btn_add.clicked.connect(self._on_add_to_extrato)
        
        # Tab Extrato
        self.tab_extrato = TabExtrato(parent=self, role=self.role, username=self.username)
        self.tabs.addTab(self.tab_extrato, "📊 Extrato")
        
        # Conecta botão de consolidar
        self.tab_extrato.btn_consol.clicked.connect(self._on_consolidar)
        
        # Tab Consolidados
        self.tab_consolidados = TabConsolidados(parent=self, role=self.role, username=self.username)
        self.tabs.addTab(self.tab_consolidados, "🔒 Consolidados")
        
        # Carrega dados iniciais do extrato
        self.tab_extrato.refresh_extrato()
    
    def _setup_table_context_menus(self):
        """Adiciona menu de contexto (botão direito) nas tabelas"""
        # Tabela de consulta
        if hasattr(self, 'tab_consulta'):
            self.tab_consulta.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_consulta.tbl.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_consulta.tbl, pos)
            )
        
        # Tabela de extrato
        if hasattr(self, 'tab_extrato'):
            self.tab_extrato.tbl_extrato.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_extrato.tbl_extrato.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_extrato.tbl_extrato, pos)
            )
        
        # Tabela de consolidados
        if hasattr(self, 'tab_consolidados'):
            self.tab_consolidados.tbl_consolidados.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_consolidados.tbl_consolidados.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_consolidados.tbl_consolidados, pos)
            )
    
    def _show_selection_menu(self, table: QTableView, pos):
        """Exibe menu de contexto para escolher modo de seleção e copiar dados"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1c2e;
                color: #E5E7EB;
                border: 1px solid #4c1d95;
                padding: 5px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 8px 30px 8px 15px;
                border-radius: 4px;
                margin: 2px 5px;
            }
            QMenu::item:selected {
                background-color: #6D28D9;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2d4a;
                margin: 5px 10px;
            }
        """)
        
        # ===== SEÇÃO: MODO DE SELEÇÃO =====
        menu.addSection("Modo de Seleção")
        
        action_rows = menu.addAction("📋 Selecionar Linhas")
        action_columns = menu.addAction("📊 Selecionar Colunas")
        action_cells = menu.addAction("🔲 Selecionar Células")
        
        # Marca o modo atual
        current_behavior = table.selectionBehavior()
        if current_behavior == QAbstractItemView.SelectRows:
            action_rows.setText("✓ Selecionar Linhas")
            action_rows.setEnabled(False)
        elif current_behavior == QAbstractItemView.SelectColumns:
            action_columns.setText("✓ Selecionar Colunas")
            action_columns.setEnabled(False)
        elif current_behavior == QAbstractItemView.SelectItems:
            action_cells.setText("✓ Selecionar Células")
            action_cells.setEnabled(False)
        
        menu.addSeparator()
        
        # ===== SEÇÃO: COPIAR DADOS =====
        menu.addSection("Copiar para Área de Transferência")
        
        action_copy = menu.addAction("📄 Copiar Seleção")
        action_copy_with_header = menu.addAction("📑 Copiar com Cabeçalho")
        action_copy_all = menu.addAction("📋 Copiar Tudo (visível)")
        
        # Desabilita se não houver seleção
        has_selection = len(table.selectionModel().selectedIndexes()) > 0
        action_copy.setEnabled(has_selection)
        action_copy_with_header.setEnabled(has_selection)
        
        # Executa o menu
        action = menu.exec(table.viewport().mapToGlobal(pos))
        
        # ===== AÇÕES =====
        if action == action_rows:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        elif action == action_columns:
            table.setSelectionBehavior(QAbstractItemView.SelectColumns)
            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        elif action == action_cells:
            table.setSelectionBehavior(QAbstractItemView.SelectItems)
            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        elif action == action_copy:
            self._copy_table_selection(table, include_header=False, all_visible=False)
        
        elif action == action_copy_with_header:
            self._copy_table_selection(table, include_header=True, all_visible=False)
        
        elif action == action_copy_all:
            self._copy_table_selection(table, include_header=True, all_visible=True)
    
    def _copy_table_selection(self, table: QTableView, include_header: bool = False, all_visible: bool = False):
        """Copia dados da tabela para a área de transferência"""
        from models import EditableTableModel
        
        try:
            model = table.model()
            if model is None:
                return
            
            if all_visible:
                rows = range(model.rowCount())
                cols = range(model.columnCount())
            else:
                selection = table.selectionModel().selectedIndexes()
                if not selection:
                    return
                
                rows = sorted(set(index.row() for index in selection))
                cols = sorted(set(index.column() for index in selection))
            
            # Monta o texto
            lines = []
            
            # Cabeçalho
            if include_header:
                if isinstance(model, EditableTableModel):
                    header_line = "\t".join(model.headers[col] for col in cols)
                    lines.append(header_line)
                else:
                    header_line = "\t".join(
                        str(model.headerData(col, Qt.Horizontal, Qt.DisplayRole) or "")
                        for col in cols
                    )
                    lines.append(header_line)
            
            # Dados
            for row in rows:
                row_data = []
                for col in cols:
                    index = model.index(row, col)
                    value = model.data(index, Qt.DisplayRole)
                    row_data.append(str(value) if value is not None else "")
                lines.append("\t".join(row_data))
            
            # Copia para clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(lines))
            
            # Feedback visual
            if all_visible:
                msg = f"✓ Toda a tabela copiada ({len(rows)} linhas)"
            else:
                msg = f"✓ {len(rows)} linha(s) × {len(cols)} coluna(s) copiadas"
            
            QuickFeedback.show(self, msg, success=True)
        
        except Exception as e:
            print(f"Erro ao copiar: {e}")
            QuickFeedback.show(self, "Erro ao copiar dados", success=False)
    
    def _on_add_to_extrato(self):
        """Handler para adicionar selecionados ao extrato"""
        if not hasattr(self, 'tab_consulta'):
            return
        
        sel = self.tab_consulta.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Seleção", "Selecione uma ou mais linhas.")
            return
        
        try:
            inserted, errors = self.tab_consulta.add_to_extrato([s.row() for s in sel])
            
            # Atualiza o extrato e muda para aba
            self.tab_extrato.refresh_extrato()
            self.tabs.setCurrentWidget(self.tab_extrato)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
    
    def _on_consolidar(self):
        """Handler para consolidar registros validados"""
        if self.role not in ("controladoria", "admin"):
            QMessageBox.warning(
                self, 
                "Permissão", 
                "Apenas a controladoria (Jessica) ou admin podem consolidar."
            )
            return
        
        df = self.tab_extrato.get_filtered_data()
        
        success, message = self.tab_consolidados.consolidar_registros(df)
        
        if success:
            self.tab_extrato.refresh_extrato()
            self.tab_consolidados.refresh_consolidados()
            self.tabs.setCurrentWidget(self.tab_consolidados)
        else:
            QMessageBox.warning(self, "Consolidação", message)

    def _toggle_theme(self):
        """Alterna entre tema claro e escuro"""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        ThemeManager.toggle_theme(app)
        
        # Salvar preferência (opcional)
        is_dark = ThemeManager.is_dark_mode()        

       