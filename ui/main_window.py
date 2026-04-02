"""
Janela principal com navegacao lateral.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from tabs import TabConsulta, TabConsolidados, TabExtrato
from ui.loading_overlay import QuickFeedback
from ui.themes import ThemeManager


def center_widget(widget):
    screen = QApplication.primaryScreen().availableGeometry()
    fg = widget.frameGeometry()
    fg.moveCenter(screen.center())
    widget.move(fg.topLeft())


class MainWindow(QMainWindow):
    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = role
        self.nav_buttons = []

        self.setWindowTitle(f"Comissoes STIK - {username.title()} ({role.title()})")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 600)
        center_widget(self)

        shell = QWidget()
        shell.setObjectName("appShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(14, 14, 14, 14)
        shell_layout.setSpacing(14)

        shell_layout.addWidget(self._build_sidebar())
        shell_layout.addWidget(self._build_content_area(), 1)

        self.setCentralWidget(shell)
        self._init_pages()
        self._setup_table_context_menus()
        self._activate_page(0)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        eyebrow = QLabel("PAINEL DE OPERACOES")
        eyebrow.setObjectName("windowEyebrow")

        title = QLabel("Comissoes STIK")
        title.setObjectName("windowTitle")
        title.setWordWrap(True)

        subtitle = QLabel("Consulta, valida e consolida comissoes sem desperdiçar area util.")
        subtitle.setObjectName("windowSubtitle")
        subtitle.setWordWrap(True)

        identity_badge = QLabel(f"{self.username.title()}  |  {self.role.title()}")
        identity_badge.setObjectName("identityBadge")

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(identity_badge)

        nav_title = QLabel("Navegacao")
        nav_title.setObjectName("sidebarSectionTitle")
        layout.addWidget(nav_title)

        self.nav_container = QVBoxLayout()
        self.nav_container.setSpacing(8)
        layout.addLayout(self.nav_container)
        layout.addStretch()
        return sidebar

    def _build_content_area(self):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(10)

        self.content_header = QFrame()
        self.content_header.setObjectName("contentHeader")
        header_layout = QVBoxLayout(self.content_header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(1)

        self.section_title = QLabel("")
        self.section_title.setObjectName("sectionTitle")
        self.section_subtitle = QLabel("")
        self.section_subtitle.setObjectName("sectionSubtitle")
        self.section_subtitle.setWordWrap(True)

        header_layout.addWidget(self.section_title)
        header_layout.addWidget(self.section_subtitle)

        self.stack = QStackedWidget()

        wrapper_layout.addWidget(self.content_header)
        wrapper_layout.addWidget(self.stack, 1)
        return wrapper

    def _add_nav_button(self, text: str, index: int):
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda checked=False, i=index: self._activate_page(i))
        self.nav_buttons.append(btn)
        self.nav_container.addWidget(btn)

    def _init_pages(self):
        self.page_meta = []

        if self.role == "admin":
            self.tab_consulta = TabConsulta(parent=self, role=self.role)
            self.stack.addWidget(self.tab_consulta)
            self.page_meta.append(("Consulta", "Busque recebimentos e adicione lancamentos ao extrato."))
            self._add_nav_button("Consulta", len(self.page_meta) - 1)
            self.tab_consulta.btn_add.clicked.connect(self._on_add_to_extrato)

        self.tab_extrato = TabExtrato(parent=self, role=self.role, username=self.username)
        self.stack.addWidget(self.tab_extrato)
        self.page_meta.append(("Extrato", "Valide, ajuste regras e prepare as comissoes para consolidacao."))
        self._add_nav_button("Extrato", len(self.page_meta) - 1)
        self.tab_extrato.btn_consol.clicked.connect(self._on_consolidar)

        self.tab_consolidados = TabConsolidados(parent=self, role=self.role, username=self.username)
        self.stack.addWidget(self.tab_consolidados)
        self.page_meta.append(("Consolidados", "Acompanhe o historico final, gere PDF e envie por e-mail."))
        self._add_nav_button("Consolidados", len(self.page_meta) - 1)

        self.tab_extrato.refresh_extrato()

    def _activate_page(self, index: int):
        if index < 0 or index >= self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

        title, subtitle = self.page_meta[index]
        self.section_title.setText(title)
        self.section_subtitle.setText(subtitle)

    def _setup_table_context_menus(self):
        if hasattr(self, "tab_consulta"):
            self.tab_consulta.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_consulta.tbl.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_consulta.tbl, pos)
            )

        if hasattr(self, "tab_extrato"):
            self.tab_extrato.tbl_extrato.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_extrato.tbl_extrato.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_extrato.tbl_extrato, pos)
            )

        if hasattr(self, "tab_consolidados"):
            self.tab_consolidados.tbl_consolidados.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tab_consolidados.tbl_consolidados.customContextMenuRequested.connect(
                lambda pos: self._show_selection_menu(self.tab_consolidados.tbl_consolidados, pos)
            )

    def _show_selection_menu(self, table: QTableView, pos):
        menu = QMenu(self)
        menu.addSection("Modo de selecao")
        action_rows = menu.addAction("Selecionar linhas")
        action_columns = menu.addAction("Selecionar colunas")
        action_cells = menu.addAction("Selecionar celulas")

        current_behavior = table.selectionBehavior()
        if current_behavior == QAbstractItemView.SelectRows:
            action_rows.setEnabled(False)
        elif current_behavior == QAbstractItemView.SelectColumns:
            action_columns.setEnabled(False)
        elif current_behavior == QAbstractItemView.SelectItems:
            action_cells.setEnabled(False)

        menu.addSeparator()
        menu.addSection("Copiar dados")

        action_copy = menu.addAction("Copiar selecao")
        action_copy_with_header = menu.addAction("Copiar com cabecalho")
        action_copy_all = menu.addAction("Copiar tabela visivel")

        has_selection = len(table.selectionModel().selectedIndexes()) > 0
        action_copy.setEnabled(has_selection)
        action_copy_with_header.setEnabled(has_selection)

        action = menu.exec(table.viewport().mapToGlobal(pos))

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

            lines = []
            if include_header:
                if isinstance(model, EditableTableModel):
                    lines.append("\t".join(model.headers[col] for col in cols))
                else:
                    lines.append(
                        "\t".join(str(model.headerData(col, Qt.Horizontal, Qt.DisplayRole) or "") for col in cols)
                    )

            for row in rows:
                row_data = []
                for col in cols:
                    index = model.index(row, col)
                    value = model.data(index, Qt.DisplayRole)
                    row_data.append(str(value) if value is not None else "")
                lines.append("\t".join(row_data))

            QApplication.clipboard().setText("\n".join(lines))
            msg = f"Tabela copiada ({len(rows)} linhas)" if all_visible else f"{len(rows)} linha(s) x {len(cols)} coluna(s) copiadas"
            QuickFeedback.show(self, msg, success=True)
        except Exception as e:
            print(f"Erro ao copiar: {e}")
            QuickFeedback.show(self, "Erro ao copiar dados", success=False)

    def _on_add_to_extrato(self):
        if not hasattr(self, "tab_consulta"):
            return

        sel = self.tab_consulta.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Selecao", "Selecione uma ou mais linhas.")
            return

        try:
            self.tab_consulta.add_to_extrato([s.row() for s in sel])
            self.tab_extrato.refresh_extrato()
            self._activate_page(1 if self.role == "admin" else 0)
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def _on_consolidar(self):
        if self.role not in ("controladoria", "admin"):
            QMessageBox.warning(self, "Permissao", "Apenas a controladoria ou o admin podem consolidar.")
            return

        if not self.tab_extrato.ensure_current_data_synced("consolidar"):
            return

        df = self.tab_extrato.get_filtered_data()
        success, message = self.tab_consolidados.consolidar_registros(df)

        if success:
            self.tab_extrato.refresh_extrato()
            self.tab_consolidados.refresh_consolidados()
            target = 2 if self.role == "admin" else 1
            self._activate_page(target)
        else:
            QMessageBox.warning(self, "Consolidacao", message)

    def _toggle_theme(self):
        app = QApplication.instance()
        ThemeManager.toggle(app)
