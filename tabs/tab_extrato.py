# tabs/tab_extrato.py
"""
Aba de Extrato - Validação e gerenciamento de comissões
RESPONSIVA | OTIMIZADA | COM FEEDBACKS | LAYOUT PADRONIZADO
"""

from __future__ import annotations

import os
from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

import pandas as pd
from PySide6.QtCore import QDate, Qt, QTimer, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QDateEdit, QSpinBox, QPushButton,
    QMessageBox, QHeaderView, QAbstractItemView, QCheckBox,
    QApplication, QSizePolicy, QAbstractItemDelegate,
    QFrame, QDialog, QToolButton, QMenu,
)

from config import DBConfig, get_conn
from models import EditableTableModel, DecimalDelegate, ExcelLikeTableView
from utils.formatters import br_to_decimal, apply_display_formats, comp_br
from constants import PT_BR_MONTHS, VENDEDOR_EMAIL_NORMALIZADO
from utils.email_sender import enviar_email_comissao
from ui.loading_overlay import LoadingOverlay, QuickFeedback
from ui.icons import Icons

from rules.rules_engine import Rule, Condition, apply_rules_to_row
from rules.rules_store import load_rules
from rules.rules_audit import append_jsonl, build_edit_event, generate_session_id
from ui.rule_editor_dialog import RuleEditorDialog
from tabs.sincronizacao import SyncService, SyncWorker


class SyncApplyWorker(QThread):
    finished = Signal(dict)

    def __init__(self, cfg, resultado):
        super().__init__()
        self.cfg = cfg
        self.resultado = resultado

    def run(self):
        try:
            resumo = SyncService(self.cfg).sync_result(self.resultado)
            self.finished.emit({"ok": True, "resumo": resumo})
        except Exception as e:
            self.finished.emit({"ok": False, "erro": str(e)})


class TabExtrato(QWidget):
    """
    Aba de Extrato de Comissões
    Permite validar, editar e enviar comissões para os vendedores
    """

    def __init__(self, parent=None, role: str = "admin", username: str = "admin"):
        super().__init__(parent)
        self.role = role
        self.username = username
        self.cfg = DBConfig()
        self.df_extrato = pd.DataFrame()

        base_dir = os.path.dirname(os.path.dirname(__file__))  # .../Comissao_teste

        # auditoria
        self.audit_log_path = os.path.join(base_dir, "logs", "comissoes_audit.jsonl")

        # rules.json
        self.rules_path = os.path.join(base_dir, "rules", "rules.json")

        # carrega regras do JSON (fonte única)
        self.rules_memoria: List[Rule] = self._load_rules_from_json()

        # Cache para otimização
        self._cache_competencias = set()
        self._cache_vendedores = set()
        self._cache_artigos = set()
        self._cache_ufs = set()
        self._sync_check_running = False
        self._pending_sync_result = None
        self._sync_check_force_feedback = False
        self._sync_check_worker = None
        self._sync_apply_worker = None
        self._sync_apply_overlay = None

        self._setup_ui()
        self._setup_sync_monitor()

    # ============================================================
    # UI
    # ============================================================

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(10, 10, 10, 10)

        # Painel de filtros recolhível
        self._create_filters_panel(lay)
        self._create_sync_banner(lay)

        # Botões
        self._create_action_buttons(lay)

        # Tabela
        self._create_table(lay)

        # Rodapé
        self._create_footer(lay)

    def _create_filters_panel(self, layout):
        panel = QFrame()
        panel.setObjectName("filtersPanel")
        panel.setFrameShape(QFrame.NoFrame)

        panel_lay = QVBoxLayout(panel)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(6)

        header = QFrame()
        header.setObjectName("filtersHeader")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(4, 0, 4, 0)

        self.lbl_filters_title = QLabel("☑  Filtros")
        self.lbl_filters_title.setStyleSheet("font-size: 14px; font-weight: 800;")

        self.btn_toggle_filters = QPushButton("Expandir")
        self.btn_toggle_filters.setObjectName("btnGhost")
        self.btn_toggle_filters.setFixedWidth(96)

        header_lay.addWidget(self.lbl_filters_title)
        header_lay.addStretch()
        header_lay.addWidget(self.btn_toggle_filters)

        self.filters_body = QFrame()
        self.filters_body.setObjectName("filtrosContainer")
        body_lay = QVBoxLayout(self.filters_body)
        body_lay.setContentsMargins(0, 0, 0, 0)

        self._create_filters(body_lay)

        panel_lay.addWidget(header)
        panel_lay.addWidget(self.filters_body)

        self._filters_collapsed = True

        def toggle():
            self._filters_collapsed = not self._filters_collapsed
            self.filters_body.setVisible(not self._filters_collapsed)
            self.btn_toggle_filters.setText("Expandir" if self._filters_collapsed else "Recolher")

        self.btn_toggle_filters.clicked.connect(toggle)
        self.filters_body.setVisible(False)
        layout.addWidget(panel)

    def _create_sync_banner(self, layout):
        self.sync_banner = QFrame()
        self.sync_banner.setObjectName("syncBanner")
        self.sync_banner.setProperty("state", "info")

        banner_lay = QHBoxLayout(self.sync_banner)
        banner_lay.setContentsMargins(10, 8, 10, 8)
        banner_lay.setSpacing(8)

        self.lbl_sync_banner = QLabel("Extrato sincronizado.")
        self.lbl_sync_banner.setObjectName("syncBannerText")

        self.btn_sync_check_now = QPushButton("Verificar agora")
        self.btn_sync_check_now.setObjectName("btnGhost")
        self.btn_sync_check_now.setMinimumHeight(30)

        self.btn_sync_apply_now = QPushButton("Sincronizar agora")
        self.btn_sync_apply_now.setObjectName("btnWarning")
        self.btn_sync_apply_now.setMinimumHeight(30)

        banner_lay.addWidget(self.lbl_sync_banner, 1)
        banner_lay.addWidget(self.btn_sync_check_now)
        banner_lay.addWidget(self.btn_sync_apply_now)

        self.btn_sync_check_now.clicked.connect(lambda: self.check_sync_status(force=True))
        self.btn_sync_apply_now.clicked.connect(self.sync_from_banner)

        self.sync_banner.setVisible(False)
        layout.addWidget(self.sync_banner)

    def _create_filters(self, layout):
        filtros_container = QWidget()
        filtros_container.setObjectName("filtrosContainer")
        filtros_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        filtros_layout = QGridLayout(filtros_container)
        filtros_layout.setSpacing(8)
        filtros_layout.setContentsMargins(12, 10, 12, 10)

        # LINHA 0: Emissão + Artigo
        row = 0

        self.chk_filtrar_emissao = QCheckBox(f"{Icons.CALENDAR} Filtrar por emissão:")
        self.chk_filtrar_emissao.setChecked(False)

        self.dt_emissao_ini = QDateEdit()
        self.dt_emissao_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao_ini.setCalendarPopup(True)
        self.dt_emissao_ini.setDate(QDate.currentDate().addMonths(-1))
        self.dt_emissao_ini.setMinimumWidth(96)
        self.dt_emissao_ini.setEnabled(False)

        self.lbl_ate_emissao = QLabel("até")
        self.lbl_ate_emissao.setEnabled(False)

        self.dt_emissao_fim = QDateEdit()
        self.dt_emissao_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao_fim.setCalendarPopup(True)
        self.dt_emissao_fim.setDate(QDate.currentDate())
        self.dt_emissao_fim.setMinimumWidth(96)
        self.dt_emissao_fim.setEnabled(False)

        self.chk_filtrar_emissao.toggled.connect(self._toggle_emissao_filter)

        self.cmb_artigo = QComboBox()
        self.cmb_artigo.addItem("(todos)")
        self.cmb_artigo.setMinimumWidth(112)
        self.cmb_artigo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        filtros_layout.addWidget(self.chk_filtrar_emissao, row, 0)
        filtros_layout.addWidget(self.dt_emissao_ini, row, 1)
        filtros_layout.addWidget(self.lbl_ate_emissao, row, 2)
        filtros_layout.addWidget(self.dt_emissao_fim, row, 3)
        filtros_layout.addWidget(QLabel(f"{Icons.FILTER} Artigo:"), row, 4)
        filtros_layout.addWidget(self.cmb_artigo, row, 5, 1, 2)

        # LINHA 1: Recebimento
        row = 1

        self.chk_filtrar_recebimento = QCheckBox(f"{Icons.CALENDAR} Filtrar por recebimento:")
        self.chk_filtrar_recebimento.setChecked(True)

        hoje = QDate.currentDate()
        primeiro_dia_mes = QDate(hoje.year(), hoje.month(), 1)
        ontem = hoje.addDays(-1)

        self.dt_recebimento_ini = QDateEdit()
        self.dt_recebimento_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_recebimento_ini.setCalendarPopup(True)
        self.dt_recebimento_ini.setDate(primeiro_dia_mes)
        self.dt_recebimento_ini.setMinimumWidth(96)
        self.dt_recebimento_ini.setEnabled(True)

        self.lbl_ate_recebimento = QLabel("até")
        self.lbl_ate_recebimento.setEnabled(True)

        self.dt_recebimento_fim = QDateEdit()
        self.dt_recebimento_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_recebimento_fim.setCalendarPopup(True)
        self.dt_recebimento_fim.setDate(ontem)
        self.dt_recebimento_fim.setMinimumWidth(96)
        self.dt_recebimento_fim.setEnabled(True)

        self.chk_filtrar_recebimento.toggled.connect(self._toggle_recebimento_filter)

        filtros_layout.addWidget(self.chk_filtrar_recebimento, row, 0)
        filtros_layout.addWidget(self.dt_recebimento_ini, row, 1)
        filtros_layout.addWidget(self.lbl_ate_recebimento, row, 2)
        filtros_layout.addWidget(self.dt_recebimento_fim, row, 3)

        # LINHA 2: Competência / Vendedor / UF / % padrão
        row = 2

        self.cmb_comp = QComboBox()
        self.cmb_comp.addItem("(todas)")
        self.cmb_comp.setMinimumWidth(88)
        self.cmb_comp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cmb_vend = QComboBox()
        self.cmb_vend.addItem("(todos)")
        self.cmb_vend.setMinimumWidth(104)
        self.cmb_vend.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cmb_uf = QComboBox()
        self.cmb_uf.addItem("(todas)")
        self.cmb_uf.setMinimumWidth(72)

        self.spn_pct = QSpinBox()
        self.spn_pct.setRange(0, 100)
        self.spn_pct.setValue(5)
        self.spn_pct.setFixedWidth(58)

        filtros_layout.addWidget(QLabel(f"{Icons.CALENDAR} Competência:"), row, 0)
        filtros_layout.addWidget(self.cmb_comp, row, 1)
        filtros_layout.addWidget(QLabel(f"{Icons.USER} Vendedor:"), row, 2)
        filtros_layout.addWidget(self.cmb_vend, row, 3)
        filtros_layout.addWidget(QLabel(f"{Icons.FLAG} UF:"), row, 4)
        filtros_layout.addWidget(self.cmb_uf, row, 5)
        filtros_layout.addWidget(QLabel(f"{Icons.CHART} % padrão:"), row, 6)
        filtros_layout.addWidget(self.spn_pct, row, 7)

        filtros_layout.setColumnStretch(1, 1)
        filtros_layout.setColumnStretch(3, 1)
        filtros_layout.setColumnMinimumWidth(4, 64)
        filtros_layout.setColumnMinimumWidth(6, 74)

        layout.addWidget(filtros_container)

    def _create_action_buttons(self, layout):
        """Cria os botões de ação em 2 linhas (principais + utilidades) + Criar Regras."""
        from PySide6.QtWidgets import QFrame, QSizePolicy, QHBoxLayout, QVBoxLayout, QPushButton

        card = QFrame()
        card.setObjectName("actionsCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(6, 6, 6, 6)
        card_lay.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.setContentsMargins(0, 0, 0, 0)

        def mk_btn(text: str, obj: str, min_w: int = 102) -> QPushButton:
            b = QPushButton(text)
            b.setObjectName(obj)
            b.setMinimumWidth(min_w)
            b.setMinimumHeight(32)
            b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            return b

        # ===== Principais =====
        self.btn_refresh = mk_btn("Atualizar", "btnPrimary", 104)
        self.btn_salvar = mk_btn("Salvar", "btnSuccess", 94)
        self.btn_validar = mk_btn("Validar", "btnSuccess", 94)
        self.btn_consol = mk_btn("Consolidar", "btnPrimary", 112)
        self.btn_enviar = mk_btn("Enviar E-mail", "btnSecondary", 118)

        # ===== Utilidades =====
        self.btn_voltar = mk_btn("Voltar p/ Consulta", "btnGhost", 128)
        self.btn_aplicar_todos = mk_btn("Aplicar % em todos", "btnSecondary", 128)
        self.btn_sincronizar = mk_btn("Sincronizar", "btnWarning", 106)
        self.btn_aplicar_regras = mk_btn("Aplicar Regras", "btnPrimary", 114)

        # ✅ NOVO: Criar Regras
        self.btn_gerenciar_regras = mk_btn("Criar Regras", "btnSecondary", 112)

        row1.addWidget(self.btn_refresh)
        row1.addWidget(self.btn_salvar)
        row1.addWidget(self.btn_validar)
        row1.addWidget(self.btn_consol)
        row1.addWidget(self.btn_enviar)

        self.btn_more = QToolButton()
        self.btn_more.setObjectName("btnGhost")
        self.btn_more.setText("Mais acoes")
        self.btn_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_more.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_more.setMinimumWidth(108)
        self.btn_more.setMinimumHeight(32)

        self.more_menu = QMenu(self)
        self.act_voltar = self.more_menu.addAction("Voltar p/ Consulta")
        self.act_aplicar_todos = self.more_menu.addAction("Aplicar % em todos")
        self.act_sincronizar = self.more_menu.addAction("Sincronizar")
        self.more_menu.addSeparator()
        self.act_aplicar_regras = self.more_menu.addAction("Aplicar Regras")
        self.act_gerenciar_regras = self.more_menu.addAction("Criar Regras")
        self.btn_more.setMenu(self.more_menu)

        row1.addStretch()
        row1.addWidget(self.btn_more)

        card_lay.addLayout(row1)

        # Conectar eventos
        self.btn_refresh.clicked.connect(self.refresh_extrato)
        self.btn_salvar.clicked.connect(self.on_salvar_alteracoes)
        self.btn_validar.clicked.connect(self.on_validar)
        self.btn_enviar.clicked.connect(self.on_enviar_emails)
        self.btn_voltar.clicked.connect(self.voltar_para_consulta)
        self.btn_aplicar_todos.clicked.connect(self._aplicar_pct_todos)
        self.btn_sincronizar.clicked.connect(self.abrir_sincronizacao)
        self.btn_aplicar_regras.clicked.connect(self._aplicar_regras_teste)
        self.btn_gerenciar_regras.clicked.connect(self._abrir_gerenciador_regras)
        self.act_voltar.triggered.connect(self.voltar_para_consulta)
        self.act_aplicar_todos.triggered.connect(self._aplicar_pct_todos)
        self.act_sincronizar.triggered.connect(self.abrir_sincronizacao)
        self.act_aplicar_regras.triggered.connect(self._aplicar_regras_teste)
        self.act_gerenciar_regras.triggered.connect(self._abrir_gerenciador_regras)

        # Permissões
        self._configure_button_permissions()

        layout.addWidget(card)

    def _configure_button_permissions(self):
        """Configura permissões dos botões baseado no perfil."""
        if self.role in ("gestora", "admin"):
            self.btn_enviar.hide()
        elif self.role == "controladoria":
            self.btn_salvar.show()
            self.btn_validar.show()
            self.btn_consol.show()
            self.btn_enviar.show()
            self.act_voltar.setVisible(False)
            self.act_sincronizar.setVisible(False)
        else:
            self.btn_salvar.hide()
            self.btn_validar.hide()
            self.btn_consol.hide()
            self.btn_enviar.hide()

        self.btn_more.setVisible(any([
            self.act_voltar.isVisible(),
            self.act_aplicar_todos.isVisible(),
            self.act_sincronizar.isVisible(),
            self.act_aplicar_regras.isVisible(),
            self.act_gerenciar_regras.isVisible(),
        ]))

    def _create_table(self, layout):
        self.tbl_extrato = ExcelLikeTableView()
        self.tbl_extrato.horizontalHeader().setStretchLastSection(True)
        self.tbl_extrato.horizontalHeader().setHighlightSections(False)
        self.tbl_extrato.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_extrato.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl_extrato.verticalHeader().setVisible(False)
        self.tbl_extrato.setSortingEnabled(True)
        self.tbl_extrato.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tbl_extrato)

    def _create_footer(self, layout):
        linha_inferior = QHBoxLayout()
        linha_inferior.addStretch()

        self.lbl_count_extrato = QLabel("0 registro(s)")
        self.lbl_count_extrato.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 13px;")
        linha_inferior.addWidget(self.lbl_count_extrato)

        self.lbl_total_recebido = QLabel("Total selecionado: R$ 0,00")
        self.lbl_total_recebido.setStyleSheet("font-weight: 600; color: #9ca3af; margin-left: 20px; font-size: 13px;")
        linha_inferior.addWidget(self.lbl_total_recebido)

        layout.addLayout(linha_inferior)

    def _setup_sync_monitor(self):
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(10 * 60 * 1000)
        self._sync_timer.timeout.connect(self.check_sync_status)
        self._sync_timer.start()

        self._sync_debounce_timer = QTimer(self)
        self._sync_debounce_timer.setSingleShot(True)
        self._sync_debounce_timer.setInterval(1200)
        self._sync_debounce_timer.timeout.connect(self.check_sync_status)

    def _schedule_sync_check(self, delay_ms: int = 1200):
        if hasattr(self, "_sync_debounce_timer") and self.isVisible():
            self._sync_debounce_timer.start(delay_ms)

    def _set_sync_banner(self, message: str, state: str = "info", allow_apply: bool = False, visible: bool = True):
        self.lbl_sync_banner.setText(message)
        self.sync_banner.setProperty("state", state)
        self.btn_sync_apply_now.setVisible(allow_apply)
        self.sync_banner.setVisible(visible)
        self.sync_banner.style().unpolish(self.sync_banner)
        self.sync_banner.style().polish(self.sync_banner)

    def _count_sync_operations(self, resultado: dict[str, Any]) -> int:
        return (
            int(resultado.get("faltando", 0))
            + int(resultado.get("sobrando", 0))
            + int(resultado.get("alterados", 0))
            + int(resultado.get("divergentes", 0))
        )

    def _analyze_current_sync_scope(self):
        scope = self._get_sync_scope_from_visible_data()
        if scope is None:
            return None, None

        data_ini, data_fim, vendedor = scope
        service = SyncService(self.cfg)
        return scope, service.analyze(data_ini, data_fim, vendedor)

    def check_sync_status(self, force: bool = False):
        if self._sync_check_running:
            return

        scope = self._get_sync_scope_from_visible_data()
        if scope is None:
            self._pending_sync_result = None
            self.sync_banner.setVisible(False)
            return

        self._start_async_sync_check(scope, force)

    def _start_async_sync_check(self, scope, force: bool):
        if self._sync_check_running:
            return

        data_ini, data_fim, vendedor = scope
        self._sync_check_running = True
        self._sync_check_force_feedback = force
        self.btn_sync_check_now.setEnabled(False)
        self.btn_sync_check_now.setText("Verificando...")
        self.btn_sync_apply_now.setEnabled(False)

        worker = SyncWorker(data_ini, data_fim, vendedor, self.cfg)
        self._sync_check_worker = worker
        worker.finished.connect(self._on_async_sync_check_finished)
        worker.start()

    def _on_async_sync_check_finished(self, resultado):
        force = self._sync_check_force_feedback
        self._sync_check_running = False
        self._sync_check_force_feedback = False
        self.btn_sync_check_now.setEnabled(True)
        self.btn_sync_check_now.setText("Verificar agora")
        self.btn_sync_apply_now.setEnabled(True)

        worker = self._sync_check_worker
        self._sync_check_worker = None
        if worker is not None:
            try:
                worker.finished.disconnect(self._on_async_sync_check_finished)
            except Exception:
                pass
            worker.deleteLater()

        if not isinstance(resultado, dict):
            self._pending_sync_result = None
            if force:
                self._set_sync_banner(
                    "Nao foi possivel verificar a sincronizacao automaticamente.",
                    state="danger",
                    allow_apply=False,
                    visible=True,
                )
            return

        if "erro" in resultado:
            self._pending_sync_result = None
            if force:
                self._set_sync_banner(
                    f"Nao foi possivel verificar a sincronizacao automaticamente: {resultado['erro']}",
                    state="danger",
                    allow_apply=False,
                    visible=True,
                )
            return

        total_ops = self._count_sync_operations(resultado)
        self._pending_sync_result = resultado if total_ops > 0 else None

        if total_ops > 0:
            self._set_sync_banner(
                f"Extrato desatualizado: {total_ops} divergencia(s) encontrada(s) em {resultado.get('periodo', '')}.",
                state="warning",
                allow_apply=True,
                visible=True,
            )
        elif force:
            self._set_sync_banner(
                "Extrato conferido. Nenhuma divergencia encontrada no escopo atual.",
                state="success",
                allow_apply=False,
                visible=True,
            )
        else:
            self.sync_banner.setVisible(False)

    def sync_from_banner(self):
        if self._sync_check_running:
            self._set_sync_banner(
                "A verificacao ainda esta em andamento. Aguarde alguns instantes.",
                state="info",
                allow_apply=False,
                visible=True,
            )
            return

        if self._sync_apply_worker is not None:
            self._set_sync_banner(
                "A sincronizacao ja esta em andamento. Aguarde a conclusao.",
                state="info",
                allow_apply=False,
                visible=True,
            )
            return

        resultado = self._pending_sync_result
        if not resultado:
            self.check_sync_status(force=True)
            return

        total_ops = self._count_sync_operations(resultado)
        if total_ops == 0:
            self._set_sync_banner(
                "Extrato conferido. Nenhuma divergencia encontrada no escopo atual.",
                state="success",
                allow_apply=False,
                visible=True,
            )
            return

        reply = QMessageBox.question(
            self,
            "Sincronizar Extrato",
            (
                f"Foram encontradas {total_ops} divergencia(s) no extrato visivel.\n\n"
                f"Periodo: {resultado.get('periodo', '')}\n"
                f"Vendedor: {resultado.get('vendedor', 'TODOS')}\n\n"
                f"Deseja sincronizar agora?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_sync_apply_now.setEnabled(False)
        self.btn_sync_check_now.setEnabled(False)
        self._sync_apply_overlay = LoadingOverlay(self.window(), f"{Icons.LOADING} Sincronizando extrato")
        self._sync_apply_overlay.show_overlay()

        worker = SyncApplyWorker(self.cfg, resultado)
        self._sync_apply_worker = worker
        worker.finished.connect(self._on_sync_apply_finished)
        worker.start()

    def _on_sync_apply_finished(self, payload):
        worker = self._sync_apply_worker
        self._sync_apply_worker = None
        if worker is not None:
            try:
                worker.finished.disconnect(self._on_sync_apply_finished)
            except Exception:
                pass
            worker.deleteLater()

        if self._sync_apply_overlay is not None:
            try:
                self._sync_apply_overlay.close_overlay()
            except Exception:
                pass
            self._sync_apply_overlay = None

        self.btn_sync_apply_now.setEnabled(True)
        self.btn_sync_check_now.setEnabled(True)

        if not isinstance(payload, dict) or not payload.get("ok"):
            erro = "Erro desconhecido na sincronizacao."
            if isinstance(payload, dict):
                erro = payload.get("erro", erro)
            self._set_sync_banner(
                f"Erro ao sincronizar automaticamente: {erro}",
                state="danger",
                allow_apply=False,
                visible=True,
            )
            QMessageBox.critical(self, "Sincronizacao", f"Erro ao sincronizar automaticamente:\n{erro}")
            return

        resumo = payload.get("resumo", {})
        self._pending_sync_result = None
        self.refresh_extrato()
        self._set_sync_banner(
            f"Sincronizacao concluida com sucesso: {resumo.get('total', 0)} operacao(oes).",
            state="success",
            allow_apply=False,
            visible=True,
        )
        QuickFeedback.show(self, f"Sincronizacao aplicada: {resumo.get('total', 0)} operacao(oes)", success=True)

    # ============================================================
    # Toggles
    # ============================================================

    def _toggle_emissao_filter(self, checked):
        self.dt_emissao_ini.setEnabled(checked)
        self.dt_emissao_fim.setEnabled(checked)
        self.lbl_ate_emissao.setEnabled(checked)
        self.refresh_extrato()

    def _toggle_recebimento_filter(self, checked):
        self.dt_recebimento_ini.setEnabled(checked)
        self.dt_recebimento_fim.setEnabled(checked)
        self.lbl_ate_recebimento.setEnabled(checked)
        self.refresh_extrato()

    # ============================================================
    # Fluxos extras
    # ============================================================

    def abrir_sincronizacao(self):
        from tabs.sincronizacao import DialogSincronizacao
        dialog = DialogSincronizacao(self, self.cfg)
        dialog.exec()
        self.refresh_extrato()
        self.check_sync_status(force=True)

    def get_filtered_data(self) -> pd.DataFrame:
        return self.df_extrato.copy()

    def ensure_current_data_synced(self, action_label: str = "continuar") -> bool:
        loading = LoadingOverlay(self.window(), f"{Icons.LOADING} Verificando sincronizacao")
        loading.show_overlay()

        try:
            scope, resultado = self._analyze_current_sync_scope()
            if scope is None or resultado is None:
                return True
        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(
                self,
                "Sincronizacao",
                f"Erro ao verificar sincronizacao antes de {action_label}:\n{e}"
            )
            return False
        finally:
            try:
                loading.close_overlay()
            except Exception:
                pass

        total_ops = self._count_sync_operations(resultado)
        if total_ops == 0:
            self._pending_sync_result = None
            return True

        self._pending_sync_result = resultado
        self._set_sync_banner(
            f"Extrato desatualizado: {total_ops} divergencia(s) encontrada(s) em {resultado.get('periodo', '')}.",
            state="warning",
            allow_apply=True,
            visible=True,
        )

        reply = QMessageBox.question(
            self,
            "Sincronizacao Necessaria",
            f"Foram encontradas {total_ops} divergencia(s) no extrato visivel antes de {action_label}.\n\n"
            f"Periodo analisado: {resultado.get('periodo', '')}\n"
            f"Vendedor: {resultado.get('vendedor', 'TODOS')}\n\n"
            f"Deseja sincronizar agora e continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return False

        loading = LoadingOverlay(self.window(), f"{Icons.LOADING} Sincronizando extrato")
        loading.show_overlay()
        try:
            service = SyncService(self.cfg)
            resumo = service.sync_result(resultado)
            self._pending_sync_result = None
            self.refresh_extrato()
            self._set_sync_banner(
                f"Sincronizacao concluida com sucesso: {resumo['total']} operacao(oes).",
                state="success",
                allow_apply=False,
                visible=True,
            )
            QuickFeedback.show(
                self,
                f"Sincronizacao aplicada: {resumo['total']} operacao(oes)",
                success=True,
            )
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Sincronizacao",
                f"Erro ao sincronizar automaticamente:\n{e}"
            )
            return False
        finally:
            loading.close_overlay()

    def _get_sync_scope_from_visible_data(self):
        data_ini = None
        data_fim = None

        chosen_comp = self.cmb_comp.currentText().strip() if self.cmb_comp.currentText() else ""
        if chosen_comp and chosen_comp != "(todas)":
            partes = chosen_comp.split("-")
            if len(partes) == 2:
                mes_txt, ano_txt = partes[0].strip().title(), partes[1].strip()
                mapa_meses = {nome: numero for numero, nome in PT_BR_MONTHS.items()}
                mes = mapa_meses.get(mes_txt)
                if mes and ano_txt.isdigit():
                    ano = int(ano_txt)
                    ultimo_dia = monthrange(ano, mes)[1]
                    data_ini = pd.Timestamp(year=ano, month=mes, day=1).date()
                    data_fim = pd.Timestamp(year=ano, month=mes, day=ultimo_dia).date()

        if data_ini is None or data_fim is None:
            if self.chk_filtrar_recebimento.isChecked():
                data_ini = self.dt_recebimento_ini.date().toPython()
                data_fim = self.dt_recebimento_fim.date().toPython()

        if data_ini is None or data_fim is None:
            if self.df_extrato.empty or "Recebimento" not in self.df_extrato.columns:
                return None

            recebimentos = pd.to_datetime(
                self.df_extrato["Recebimento"], dayfirst=True, errors="coerce"
            ).dropna()
            if recebimentos.empty:
                return None

            data_ini = recebimentos.min().date()
            data_fim = recebimentos.max().date()

        vendedor = None
        chosen_v = self.cmb_vend.currentText()
        if chosen_v and chosen_v != "(todos)":
            vendedor = chosen_v
        else:
            vendedores = self.df_extrato.get("Vendedor")
            if vendedores is not None:
                unicos = sorted(set(v for v in vendedores.dropna().astype(str).unique() if v))
                if len(unicos) == 1:
                    vendedor = unicos[0]

        return data_ini, data_fim, vendedor

    def _abrir_gerenciador_regras(self):
        # Campos disponíveis: use as colunas atuais do df se tiver
        if not self.df_extrato.empty:
            fields = list(self.df_extrato.columns)
        else:
            fields = [
                "Vendedor", "Cliente", "UF", "Artigo", "Prazo Médio", "Preço Venda",
                "% Percentual Padrão", "% Comissão", "Recebido", "Rec Liquido", "Competência"
            ]

        dlg = RuleEditorDialog(rules_path=self.rules_path, available_fields=fields, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.rules_memoria = self._load_rules_from_json()
            QuickFeedback.show(self, "Regras atualizadas.", success=True)

    # ============================================================
    # Refresh / Data
    # ============================================================

    def refresh_extrato(self):
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Carregando extrato")
        loading.show_overlay()

        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT Id as DBId, Competencia, Doc as ID, VendedorID, Vendedor, Titulo, Cliente, UF,
                        Artigo, Linha, Recebido, ICMSST, Frete, RecebimentoLiq as [Rec Liquido],
                        PrazoMedio as [Prazo Médio], PrecoMedio as [Preço Médio], PrecoVenda as [Preço Venda],
                        MeioPagamento as [M Pagamento], Emissao as [Emissão], Vencimento as [Vencimento],
                        DataRecebimento as [Recebimento], PercComissao as [% Comissão], ValorComissao as [Valor Comissão],
                        Observacao as [Observação], Validado, ValidadoPor, ValidadoEm, Consolidado,
                        Percentual_Comissao as [% Percentual Padrão]
                    FROM dbo.Stik_Extrato_Comissoes
                    ORDER BY DataRecebimento DESC, Id DESC
                """)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]

            df = pd.DataFrame.from_records(rows, columns=cols)

            for col in ["% Comissão", "% Percentual Padrão", "Recebido", "Valor Comissão"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            df["% Comissão"] = df["% Comissão"].round(4)
            df["% Percentual Padrão"] = df["% Percentual Padrão"].round(4)

            df["% Diferença"] = (df["% Comissão"] - df["% Percentual Padrão"]).round(4)

            df["Valor Comissão Padrão"] = (
                df["Recebido"] * (df["% Percentual Padrão"] / 100)
            ).round(2)

            df["Diferença R$"] = (
                df["Valor Comissão"] - df["Valor Comissão Padrão"]
            ).round(2)

        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Extrato", f"Erro ao carregar extrato: {e}")
            return

        loading.update_message(f"{Icons.LOADING} Processando dados...")

        if "Recebimento" in df.columns:
            df["Competência"] = df["Recebimento"].apply(comp_br)

        for c in ("Emissão", "Vencimento", "Recebimento", "ValidadoEm"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y")

        self._update_combos(df)
        df = self._apply_filters(df)

        self.df_extrato = df.copy()
        self._display_extrato(df)

        total = len(df)
        self.lbl_count_extrato.setText(f"{total} registro(s)")

        try:
            self.tbl_extrato.selectionModel().selectionChanged.disconnect()
        except Exception:
            pass

        self.tbl_extrato.selectionModel().selectionChanged.connect(self._atualizar_total_recebido)
        self._atualizar_total_recebido()

        loading.close_overlay()
        QuickFeedback.show(self, f"{total} registro(s) no extrato", success=True)
        self._schedule_sync_check(4000)

    def _update_combos(self, df):
        comps_novos = set(c for c in df.get("Competência", pd.Series([])).dropna().unique() if c)
        if comps_novos != self._cache_competencias:
            self._cache_competencias = comps_novos
            comps = sorted(comps_novos, reverse=True)

            from datetime import datetime
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            meses_br = {
                1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
            }
            competencia_atual = f"{meses_br[mes_atual]}-{ano_atual}"

            cur_c = self.cmb_comp.currentText()
            self.cmb_comp.blockSignals(True)
            self.cmb_comp.clear()
            self.cmb_comp.addItem("(todas)")
            self.cmb_comp.addItems(comps)

            if competencia_atual in comps and cur_c == "(todas)":
                self.cmb_comp.setCurrentText(competencia_atual)
            elif cur_c and cur_c in ["(todas)", *comps]:
                self.cmb_comp.setCurrentText(cur_c)

            self.cmb_comp.blockSignals(False)

        vends_novos = set(v for v in df.get("Vendedor", pd.Series([])).dropna().astype(str).unique() if v)
        if vends_novos != self._cache_vendedores:
            self._cache_vendedores = vends_novos
            vends = sorted(vends_novos)
            cur_v = self.cmb_vend.currentText()
            self.cmb_vend.blockSignals(True)
            self.cmb_vend.clear()
            self.cmb_vend.addItem("(todos)")
            self.cmb_vend.addItems(vends)
            if cur_v and cur_v in ["(todos)", *vends]:
                self.cmb_vend.setCurrentText(cur_v)
            self.cmb_vend.blockSignals(False)

        if "Artigo" in df.columns:
            artigos_novos = set(df["Artigo"].dropna().unique())
            if artigos_novos != self._cache_artigos:
                self._cache_artigos = artigos_novos
                artigos = sorted(artigos_novos)
                cur_a = self.cmb_artigo.currentText()
                self.cmb_artigo.blockSignals(True)
                self.cmb_artigo.clear()
                self.cmb_artigo.addItem("(todos)")
                self.cmb_artigo.addItems(artigos)
                if cur_a and cur_a in ["(todos)", *artigos]:
                    self.cmb_artigo.setCurrentText(cur_a)
                self.cmb_artigo.blockSignals(False)

        if "UF" in df.columns:
            ufs_novos = set(df["UF"].dropna().unique())
            if ufs_novos != self._cache_ufs:
                self._cache_ufs = ufs_novos
                ufs = sorted(ufs_novos)
                cur_u = self.cmb_uf.currentText()
                self.cmb_uf.blockSignals(True)
                self.cmb_uf.clear()
                self.cmb_uf.addItem("(todas)")
                self.cmb_uf.addItems(ufs)
                if cur_u and cur_u in ["(todas)", *ufs]:
                    self.cmb_uf.setCurrentText(cur_u)
                self.cmb_uf.blockSignals(False)

    def _apply_filters(self, df):
        chosen_c = self.cmb_comp.currentText()
        if chosen_c and chosen_c != "(todas)":
            df = df[df["Competência"] == chosen_c]

        chosen_v = self.cmb_vend.currentText()
        if chosen_v and chosen_v != "(todos)":
            df = df[df["Vendedor"].astype(str) == chosen_v]

        artigo = self.cmb_artigo.currentText()
        if artigo != "(todos)" and "Artigo" in df.columns:
            df = df[df["Artigo"] == artigo]

        uf = self.cmb_uf.currentText()
        if uf != "(todas)" and "UF" in df.columns:
            df = df[df["UF"] == uf]

        if self.chk_filtrar_emissao.isChecked():
            try:
                data_ini = self.dt_emissao_ini.date().toPython()
                data_fim = self.dt_emissao_fim.date().toPython()
                if "Emissão" in df.columns:
                    df_temp = df.copy()
                    df_temp["_Emissao_dt"] = pd.to_datetime(df_temp["Emissão"], dayfirst=True, errors="coerce").dt.date
                    mask = (df_temp["_Emissao_dt"] >= data_ini) & (df_temp["_Emissao_dt"] <= data_fim)
                    df = df[mask]
            except Exception as e:
                print(f"Erro ao filtrar por emissão: {e}")

        if self.chk_filtrar_recebimento.isChecked():
            try:
                data_ini = self.dt_recebimento_ini.date().toPython()
                data_fim = self.dt_recebimento_fim.date().toPython()
                if "Recebimento" in df.columns:
                    df_temp = df.copy()
                    df_temp["_Recebimento_dt"] = pd.to_datetime(df_temp["Recebimento"], dayfirst=True, errors="coerce").dt.date
                    mask = (df_temp["_Recebimento_dt"] >= data_ini) & (df_temp["_Recebimento_dt"] <= data_fim)
                    df = df[mask]
            except Exception as e:
                print(f"Erro ao filtrar por recebimento: {e}")

        return df

    # ============================================================
    # Table / Display
    # ============================================================

    def _display_extrato(self, df):
        df_show = apply_display_formats(df.copy())
        cols_show = self._get_display_columns(df_show.columns)

        # limpar delegates
        if self.tbl_extrato.model() is not None:
            for col in range(self.tbl_extrato.model().columnCount()):
                self.tbl_extrato.setItemDelegateForColumn(col, None)

        model = EditableTableModel(cols_show, df_show[cols_show].values.tolist())

        model.dataChanged.connect(
            lambda top_left, bottom_right, roles=[]: self._recalcular_comissao_ao_editar(
                top_left, bottom_right, model, cols_show
            )
        )

        if self.role in ("gestora", "admin", "controladoria"):
            model.set_columns_readonly(["% Comissão", "Valor Comissão"])
        else:
            model.set_all_readonly(True)

        self.tbl_extrato.setModel(None)
        self.tbl_extrato.setModel(model)
        self.tbl_extrato.setSortingEnabled(False)

        if self.role in ("gestora", "admin", "controladoria"):
            if "% Comissão" in cols_show:
                col_idx = cols_show.index("% Comissão")
                delegate_percent = DecimalDelegate(decimal_places=2, parent=self.tbl_extrato)
                self.tbl_extrato.setItemDelegateForColumn(col_idx, delegate_percent)

            if "Valor Comissão" in cols_show:
                col_idx = cols_show.index("Valor Comissão")
                delegate_valor = DecimalDelegate(decimal_places=2, parent=self.tbl_extrato)
                self.tbl_extrato.setItemDelegateForColumn(col_idx, delegate_valor)

        header = self.tbl_extrato.horizontalHeader()
        self.tbl_extrato.resizeColumnsToContents()

        min_widths = {
            "ID": 60,
            "Vendedor": 120,
            "Titulo": 180,
            "Cliente": 150,
            "Artigo": 150,
            "UF": 40,
            "Recebido": 110,
            "Rec Liquido": 110,
            "Preço Venda": 110,
            "Valor Comissão": 120,
            "% Comissão": 80,
            "Emissão": 95,
            "Vencimento": 95,
            "Recebimento": 95,
            "Competência": 90,
            "ValidadoEm": 95,
        }

        for col in range(model.columnCount()):
            col_name = cols_show[col] if col < len(cols_show) else ""
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            if col_name in min_widths:
                if self.tbl_extrato.columnWidth(col) < min_widths[col_name]:
                    self.tbl_extrato.setColumnWidth(col, min_widths[col_name])

        header.setStretchLastSection(True)

        # seleção -> total
        try:
            self.tbl_extrato.selectionModel().selectionChanged.disconnect()
        except Exception:
            pass
        self.tbl_extrato.selectionModel().selectionChanged.connect(self._atualizar_total_recebido)

        # header click sort
        def on_header_clicked(section):
            m = self.tbl_extrato.model()
            if hasattr(m, "sort"):
                try:
                    current_col = getattr(m, "_sort_column", -1)
                    current_order = getattr(m, "_sort_order", Qt.SortOrder.AscendingOrder)
                except Exception:
                    current_col = -1
                    current_order = Qt.SortOrder.AscendingOrder

                if current_col != section:
                    order = Qt.SortOrder.AscendingOrder
                else:
                    order = (
                        Qt.SortOrder.DescendingOrder
                        if current_order == Qt.SortOrder.AscendingOrder
                        else Qt.SortOrder.AscendingOrder
                    )
                m.sort(section, order)
            self._atualizar_total_recebido()

        try:
            header.sectionClicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        header.sectionClicked.connect(on_header_clicked)

    def _recalcular_comissao_ao_editar(self, top_left, bottom_right, model, cols_show):
        try:
            if "% Comissão" not in cols_show or "Valor Comissão" not in cols_show or "Rec Liquido" not in cols_show:
                return

            col_pct_idx = cols_show.index("% Comissão")
            col_val_idx = cols_show.index("Valor Comissão")
            col_rec_idx = cols_show.index("Rec Liquido")

            if top_left.column() != col_pct_idx:
                return

            row = top_left.row()

            pct_before = None
            val_before = None
            dbid = None
            ctx: Dict[str, Any] = {}

            if not self.df_extrato.empty and row < len(self.df_extrato):
                pct_before = self.df_extrato.iloc[row].get("% Comissão", None)
                val_before = self.df_extrato.iloc[row].get("Valor Comissão", None)
                dbid = self.df_extrato.iloc[row].get("DBId", None)

                for k in ["Vendedor", "Cliente", "UF", "Artigo", "Prazo Médio", "Preço Venda", "Recebido", "Rec Liquido", "% Percentual Padrão"]:
                    if k in self.df_extrato.columns:
                        ctx[k] = self.df_extrato.iloc[row].get(k, None)

            pct_str = str(model.data(model.index(row, col_pct_idx)) or "0")
            rec_str = str(model.data(model.index(row, col_rec_idx)) or "0")

            pct = br_to_decimal(pct_str, 4) or Decimal("0.0000")
            rec_liq = br_to_decimal(rec_str, 2) or Decimal("0.00")

            valor_comissao = (rec_liq * pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            valor_formatado = f"{float(valor_comissao):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            model.blockSignals(True)
            model.setData(model.index(row, col_val_idx), valor_formatado, Qt.EditRole)
            model.blockSignals(False)

            if not self.df_extrato.empty and row < len(self.df_extrato):
                self.df_extrato.iloc[row, self.df_extrato.columns.get_loc("% Comissão")] = float(pct)
                self.df_extrato.iloc[row, self.df_extrato.columns.get_loc("Valor Comissão")] = float(valor_comissao)

            # Auditoria
            try:
                event = build_edit_event(
                    username=self.username,
                    dbid=int(dbid) if dbid is not None and str(dbid).isdigit() else None,
                    row_context=ctx,
                    pct_before=pct_before,
                    pct_after=float(pct),
                    valor_before=val_before,
                    valor_after=float(valor_comissao),
                    action="manual_edit",
                    note="edição em % Comissão",
                )
                append_jsonl(self.audit_log_path, event)
            except Exception as log_err:
                print(f"⚠️ Falha ao logar auditoria JSONL: {log_err}")

        except Exception as e:
            print(f"❌ Erro ao recalcular comissão: {e}")
            import traceback
            traceback.print_exc()

    def _get_display_columns(self, cols_all):
        hide = {"VendedorID", "Linha", "ICMSST", "Frete", "Competencia", "Consolidado"}
        order = [
            "DBId", "Competência", "Validado", "ID", "Vendedor", "Titulo", "Cliente", "UF", "Artigo",
            "Recebido", "Rec Liquido", "Prazo Médio", "Preço Médio", "Preço Venda",
            "M Pagamento", "Emissão", "Vencimento", "Recebimento",
            "% Percentual Padrão", "% Comissão", "Valor Comissão", "Valor Comissão Padrão",
            "% Diferença", "Diferença R$", "Observação", "ValidadoPor", "ValidadoEm"
        ]
        cols = [c for c in order if c in cols_all]
        cols += [c for c in cols_all if c not in set(cols) | hide]
        return cols

    def _atualizar_total_recebido(self):
        total = 0.0
        model = self.tbl_extrato.model()
        if not model:
            return

        for index in self.tbl_extrato.selectedIndexes():
            header = model.headerData(index.column(), Qt.Horizontal)
            if str(header).strip().lower() in ["rec liquido", "recebido"]:
                try:
                    valor_str = str(index.data()).replace(".", "").replace(",", ".")
                    total += float(valor_str)
                except (ValueError, TypeError):
                    pass

        self.lbl_total_recebido.setText(
            f"Total selecionado: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    # ============================================================
    # Ações
    # ============================================================

    def _aplicar_pct_todos(self):
        pct = self.spn_pct.value()
        if self.df_extrato.empty:
            return

        df = self.df_extrato.copy()
        if "% Comissão" in df.columns:
            df["% Comissão"] = pct

        self.df_extrato = df.copy()
        self._display_extrato(df)
        QuickFeedback.show(self, f"% Comissão atualizado para {pct:.2f} em todas as linhas exibidas", success=True)

    def _aplicar_regras_teste(self):
        """Aplica regras do rules.json no dataframe em tela + auditoria JSONL."""
        if self.df_extrato.empty:
            QuickFeedback.show(self, "Sem dados no extrato.", success=False)
            return

        # Recarrega regras sempre que aplicar (pra refletir edição do JSON)
        self.rules_memoria = self._load_rules_from_json()

        session_id = generate_session_id(self.username)

        df = self.df_extrato.copy()

        if "% Percentual Padrão" not in df.columns:
            QMessageBox.warning(self, "Regras", "Coluna '% Percentual Padrão' não encontrada.")
            return

        if "% Comissão" not in df.columns:
            df["% Comissão"] = df["% Percentual Padrão"]

        if "Observação" not in df.columns:
            df["Observação"] = ""

        if "Valor Comissão" not in df.columns:
            df["Valor Comissão"] = 0.0

        new_pct: List[float] = []
        new_obs: List[str] = []
        new_val: List[float] = []

        for _, r in df.iterrows():
            row = r.to_dict()

            pct_before = row.get("% Comissão")
            valor_before = row.get("Valor Comissão")

            pct_aplicado, motivo = apply_rules_to_row(row, self.rules_memoria)
            new_pct.append(pct_aplicado)

            obs_atual = str(row.get("Observação") or "").strip()
            obs_nova = obs_atual + " | " + motivo if (motivo and obs_atual) else (motivo or obs_atual)
            new_obs.append(obs_nova)

            val_calc = None
            if "Rec Liquido" in df.columns:
                rec = row.get("Rec Liquido", 0)
                try:
                    rec_d = br_to_decimal(rec, 2) if isinstance(rec, str) else Decimal(str(float(rec))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                except Exception:
                    rec_d = Decimal("0.00")

                try:
                    pct_d = br_to_decimal(pct_aplicado, 4) if isinstance(pct_aplicado, str) else Decimal(str(float(pct_aplicado))).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    )
                except Exception:
                    pct_d = Decimal("0.0000")

                val_calc = (rec_d * pct_d / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                new_val.append(float(val_calc))
            else:
                new_val.append(float(valor_before or 0))

            pct_after = pct_aplicado
            valor_after = float(val_calc) if val_calc is not None else float(valor_before or 0)

            mudou_pct = str(pct_before) != str(pct_after)
            mudou_val = str(valor_before) != str(valor_after)

            if mudou_pct or mudou_val:
                # contexto reduzido
                ctx = {
                    "session_id": session_id,
                    "rule_result": motivo,
                    "Vendedor": row.get("Vendedor"),
                    "Cliente": row.get("Cliente"),
                    "UF": row.get("UF"),
                    "Artigo": row.get("Artigo"),
                    "Prazo Médio": row.get("Prazo Médio"),
                    "Competência": row.get("Competência"),
                }

                try:
                    event = build_edit_event(
                        username=self.username,
                        dbid=row.get("DBId") if "DBId" in df.columns else None,
                        row_context=ctx,
                        pct_before=pct_before,
                        pct_after=pct_after,
                        valor_before=valor_before,
                        valor_after=valor_after,
                        action="apply_rules",
                        note=motivo or "regra aplicada",
                    )
                    append_jsonl(self.audit_log_path, event)
                except Exception as log_err:
                    print(f"⚠️ Falha ao logar auditoria de regra: {log_err}")

        df["% Comissão"] = (
            pd.to_numeric(pd.Series(new_pct, index=df.index), errors="coerce")
            .fillna(0)
            .round(4)
        )
        df["Observação"] = new_obs
        df["Valor Comissão"] = pd.to_numeric(pd.Series(new_val, index=df.index), errors="coerce").fillna(0).round(2)

        if "Recebido" not in df.columns:
            df["Recebido"] = 0

        df["Valor Comissão Padrão"] = (
            pd.to_numeric(df["Recebido"], errors="coerce").fillna(0)
            * (pd.to_numeric(df["% Percentual Padrão"], errors="coerce").fillna(0) / 100)
        ).round(2)

        df["% Diferença"] = (
            pd.to_numeric(df["% Comissão"], errors="coerce").fillna(0)
            - pd.to_numeric(df["% Percentual Padrão"], errors="coerce").fillna(0)
        ).round(4)

        df["Diferença R$"] = (
            pd.to_numeric(df["Valor Comissão"], errors="coerce").fillna(0)
            - pd.to_numeric(df["Valor Comissão Padrão"], errors="coerce").fillna(0)
        ).round(2)

        self.df_extrato = df.copy()
        self._display_extrato(df)
        QuickFeedback.show(self, "Regras aplicadas.", success=True)

    # ============================================================
    # Persistência / Validação / E-mail / Remoção
    # (mantive igual ao seu código para não quebrar fluxo)
    # ============================================================

    def on_salvar_alteracoes(self):
        if self.role not in ("gestora", "admin", "controladoria"):
            QMessageBox.warning(self, "Permissão", "Apenas a gestora (Karen) ou admin podem salvar alterações.")
            return

        editor = self.tbl_extrato.focusWidget()
        if editor is not None:
            self.tbl_extrato.closeEditor(editor, QAbstractItemDelegate.EndEditHint.SubmitModelCache)
        self.tbl_extrato.clearFocus()
        QApplication.processEvents()

        model: EditableTableModel = self.tbl_extrato.model()
        if model is None:
            return

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.SAVE} Salvando alterações")
        loading.show_overlay()

        try:
            hdr = model.headers

            def idx(h):
                try:
                    return hdr.index(h)
                except ValueError:
                    return None

            i_db = idx("DBId")
            i_pct = idx("% Comissão")
            i_obs = idx("Observação")
            i_cons = idx("Consolidado")
            i_rec = idx("Rec Liquido")

            if i_db is None:
                loading.close_overlay()
                QMessageBox.warning(self, "Erro", "Coluna DBId não encontrada!")
                return

            updated = 0
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                total = len(model.rows)

                for i, r in enumerate(model.rows, 1):
                    loading.update_message(f"{Icons.SAVE} Salvando {i}/{total}")
                    dbid = r[i_db]

                    if i_cons is not None and str(r[i_cons]).strip() in ("1", "True", "true"):
                        continue

                    pct = br_to_decimal(r[i_pct], 4) if i_pct is not None else Decimal("0.0000")

                    val = Decimal("0.00")
                    if pct is not None and i_rec is not None:
                        rec_liq = br_to_decimal(r[i_rec], 2) or Decimal("0.00")
                        val = (rec_liq * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                    obs = str(r[i_obs])[:500] if i_obs is not None else None

                    cur.execute("""
                        UPDATE dbo.Stik_Extrato_Comissoes
                        SET PercComissao = ?,
                            ValorComissao = ?,
                            Observacao = COALESCE(?, Observacao)
                        WHERE Id = ?
                    """, float(pct), float(val), obs, int(dbid))

                    updated += cur.rowcount

                conn.commit()

            loading.close_overlay()
            QuickFeedback.show(self, f"{updated} linha(s) atualizadas", success=True)
            self.refresh_extrato()

        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Salvar", f"Erro ao salvar: {e}")
            import traceback
            traceback.print_exc()

    def on_validar(self):
        if self.role not in ("gestora", "admin", "controladoria"):
            QMessageBox.warning(self, "Permissão", "Apenas a gestora (Karen) ou admin podem validar.")
            return

        if not self.ensure_current_data_synced("validar"):
            return

        model: EditableTableModel = self.tbl_extrato.model()
        if model is None:
            return

        sel = self.tbl_extrato.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Validação", "Selecione uma ou mais linhas.")
            return

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.EMAIL} Enviando e-mails de validação")
        loading.show_overlay()

        try:
            idxs_visuais = [s.row() for s in sel]
            df_vendedor = self.df_extrato.iloc[idxs_visuais].copy()

            if not df_vendedor.empty:
                vendedores = df_vendedor["Vendedor"].unique()
                for i, vendedor in enumerate(vendedores, 1):
                    loading.update_message(f"{Icons.EMAIL} Enviando para {vendedor} ({i}/{len(vendedores)})")
                    df_vend = df_vendedor[df_vendedor["Vendedor"] == vendedor]
                    try:
                        enviar_email_comissao(df_vend)
                    except Exception as e:
                        print(f"Erro ao enviar e-mail para {vendedor}: {e}")

            loading.update_message(f"{Icons.CHECK} Validando registros no banco")

            hdr = model.headers
            try:
                i_db = hdr.index("DBId")
            except ValueError:
                loading.close_overlay()
                return

            try:
                i_cons = hdr.index("Consolidado")
            except ValueError:
                i_cons = None

            count = 0
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                for s in sel:
                    row = model.rows[s.row()]
                    if i_cons is not None and str(row[i_cons]).strip() in ("1", "True", "true"):
                        continue

                    dbid = int(row[i_db])
                    cur.execute("""
                        UPDATE dbo.Stik_Extrato_Comissoes
                           SET Validado = 1, ValidadoPor = ?, ValidadoEm = GETDATE()
                         WHERE Id = ?
                    """, self.username, dbid)
                    count += cur.rowcount
                conn.commit()

            loading.close_overlay()
            QuickFeedback.show(self, f"{count} linha(s) validadas e e-mails enviados", success=True)
            self.refresh_extrato()

        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Validar", f"Erro ao validar: {e}")

    def on_enviar_emails(self):
        if not self.ensure_current_data_synced("enviar e-mail"):
            return

        model: EditableTableModel = self.tbl_extrato.model()
        if model is None:
            return

        sel = self.tbl_extrato.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Enviar E-mail", "Selecione uma ou mais linhas para enviar.")
            return

        headers = model.headers
        selected_rows_data = [model.rows[s.row()] for s in sel]
        df_selecionado = pd.DataFrame(selected_rows_data, columns=headers)

        if df_selecionado.empty:
            QMessageBox.information(self, "Extrato", "Nenhum dado disponível para envio.")
            return

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.EMAIL} Preparando e-mails")
        loading.show_overlay()

        try:
            vendedores_enviados = []
            vendedores_sem_email = []

            vendedores_unicos = df_selecionado.groupby("Vendedor")
            total_vendedores = len(vendedores_unicos)

            for i, (vendedor, df_vend) in enumerate(vendedores_unicos, 1):
                loading.update_message(f"{Icons.EMAIL} Enviando para {vendedor} ({i}/{total_vendedores})")

                vendedor_norm = str(vendedor).strip().upper()
                email = VENDEDOR_EMAIL_NORMALIZADO.get(vendedor_norm)

                if not email:
                    vendedores_sem_email.append(vendedor)
                    continue

                try:
                    enviar_email_comissao(df_vend)
                    vendedores_enviados.append(vendedor)
                except Exception as e:
                    print(f"Erro ao enviar e-mail para {vendedor}: {e}")

            loading.close_overlay()

            msg_partes = []
            if vendedores_enviados:
                msg_partes.append("✅ E-mails enviados com sucesso para:\n" + "\n".join(f"  • {v}" for v in vendedores_enviados))

            if vendedores_sem_email:
                msg_partes.append("\n⚠️ Vendedores sem e-mail cadastrado:\n" + "\n".join(f"  • {v}" for v in vendedores_sem_email))

            if vendedores_enviados:
                QuickFeedback.show(self, f"{len(vendedores_enviados)} e-mail(s) enviado(s)", success=True)
                QMessageBox.information(self, "E-mails", "\n".join(msg_partes))
            else:
                QMessageBox.warning(self, "E-mails", "Nenhum e-mail foi enviado.\n\n" + "\n".join(msg_partes))

        except Exception as e:
            loading.close_overlay()
            QMessageBox.warning(self, "Aviso", f"Erro ao enviar e-mails:\n{e}")

    def voltar_para_consulta(self):
        sel = self.tbl_extrato.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Extrato", "Nenhum item selecionado.")
            return

        reply = QMessageBox.question(
            self,
            "Remover do Extrato",
            f"⚠️ Deseja remover {len(sel)} registro(s) do extrato?\n\n"
            f"Os registros serão DELETADOS do banco de dados.\n\n"
            f"Você poderá adicioná-los novamente pela janela de Consulta,\n"
            f"buscando pelo período de RECEBIMENTO correto.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Removendo do extrato")
        loading.show_overlay()

        try:
            model: EditableTableModel = self.tbl_extrato.model()
            if model is None:
                loading.close_overlay()
                return

            hdr = model.headers
            try:
                i_db = hdr.index("DBId")
            except ValueError:
                loading.close_overlay()
                QMessageBox.critical(self, "Erro", "Coluna DBId não encontrada!")
                return

            ids_deletar = []
            for s in sel:
                row = model.rows[s.row()]
                db_id = int(row[i_db])
                ids_deletar.append(db_id)

            deletados = 0
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                total = len(ids_deletar)

                for i, db_id in enumerate(ids_deletar, 1):
                    loading.update_message(f"{Icons.LOADING} Removendo {i}/{total}")

                    cur.execute("""
                        SELECT Consolidado
                        FROM dbo.Stik_Extrato_Comissoes
                        WHERE Id = ?
                    """, db_id)

                    result = cur.fetchone()
                    if result and result[0] == 1:
                        continue

                    cur.execute("""
                        DELETE FROM dbo.Stik_Extrato_Comissoes
                        WHERE Id = ? AND Consolidado = 0
                    """, db_id)

                    deletados += cur.rowcount

                conn.commit()

            loading.close_overlay()

            if deletados > 0:
                QuickFeedback.show(self, f"{deletados} registro(s) removido(s) do extrato", success=True)
                self.refresh_extrato()
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"✅ {deletados} registro(s) removido(s) do extrato.\n\n"
                    f"Agora você pode:\n"
                    f"1. Ir na aba CONSULTA\n"
                    f"2. Filtrar pelo período de RECEBIMENTO correto\n"
                    f"3. Adicionar os títulos novamente"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "Nenhum registro foi removido.\n\n"
                    "Possíveis motivos:\n"
                    "- Os registros já estão consolidados\n"
                    "- Já foram deletados anteriormente"
                )

        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Erro", f"Erro ao remover do extrato:\n{e}")

    # ============================================================
    # Regras JSON -> objetos do engine
    # ============================================================

    def _load_rules_from_json(self) -> List[Rule]:
        """
        Carrega rules.json e converte para objetos Rule/Condition usados pelo engine.
        """
        rules_raw = load_rules(self.rules_path)
        rules_objs: List[Rule] = []

        for r in rules_raw:
            try:
                conditions = []
                for c in (r.get("conditions") or []):
                    conditions.append(Condition(c.get("field"), c.get("op"), c.get("value")))

                rules_objs.append(
                    Rule(
                        name=r.get("name", "Sem nome"),
                        priority=int(r.get("priority") or 0),
                        conditions=conditions,
                        set_percentual=r.get("set_percentual"),
                        note=r.get("note", ""),
                        stop_on_match=bool(r.get("stop_on_match", True)),
                    )
                )
            except Exception as e:
                print(f"⚠️ Regra inválida no JSON: {r} | erro={e}")

        return rules_objs
