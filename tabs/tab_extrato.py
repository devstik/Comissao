"""
Aba de Extrato - Validação e gerenciamento de comissões
RESPONSIVA | OTIMIZADA | COM FEEDBACKS | LAYOUT PADRONIZADO
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QComboBox, QDateEdit, QSpinBox, QPushButton, QTableView,
    QMessageBox, QHeaderView, QAbstractItemView, QCheckBox, 
    QApplication, QSizePolicy, QAbstractItemDelegate
)
from PySide6.QtCore import QDate, Qt
import pandas as pd

from config import DBConfig, get_conn
from models import EditableTableModel, DecimalDelegate
from utils.formatters import br_to_decimal, apply_display_formats, comp_br
from utils.email_sender import enviar_email_comissao
from constants import VENDEDOR_EMAIL_NORMALIZADO
from ui.loading_overlay import LoadingOverlay, QuickFeedback
from ui.icons import Icons, icon_button_text


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
        
        # Cache para otimização
        self._cache_competencias = set()
        self._cache_vendedores = set()
        self._cache_artigos = set()
        self._cache_ufs = set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface da aba"""
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # Container de filtros (RESPONSIVO - igual consulta)
        self._create_filters(lay)

        # Botões de ação
        self._create_action_buttons(lay)

        # Tabela
        self._create_table(lay)

        # Rodapé com contadores
        self._create_footer(lay)
    
    def _create_filters(self, layout):
        """Cria o container de filtros RESPONSIVO"""
        filtros_container = QWidget()
        filtros_container.setObjectName("filtrosContainer")
        filtros_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        filtros_layout = QGridLayout(filtros_container)
        filtros_layout.setSpacing(10)
        filtros_layout.setContentsMargins(16, 12, 16, 12)

        # LINHA 0: Filtro de Emissão
        row = 0
        
        self.chk_filtrar_emissao = QCheckBox(f"{Icons.CALENDAR} Filtrar por emissão:")
        self.chk_filtrar_emissao.setChecked(False)

        self.dt_emissao_ini = QDateEdit()
        self.dt_emissao_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao_ini.setCalendarPopup(True)
        self.dt_emissao_ini.setDate(QDate.currentDate().addMonths(-1))
        self.dt_emissao_ini.setMinimumWidth(110)
        self.dt_emissao_ini.setEnabled(False)

        self.lbl_ate_emissao = QLabel("até")
        self.lbl_ate_emissao.setEnabled(False)

        self.dt_emissao_fim = QDateEdit()
        self.dt_emissao_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao_fim.setCalendarPopup(True)
        self.dt_emissao_fim.setDate(QDate.currentDate())
        self.dt_emissao_fim.setMinimumWidth(110)
        self.dt_emissao_fim.setEnabled(False)

        self.chk_filtrar_emissao.toggled.connect(self._toggle_emissao_filter)

        # Artigo
        self.cmb_artigo = QComboBox()
        self.cmb_artigo.addItem("(todos)")
        self.cmb_artigo.setMinimumWidth(150)
        self.cmb_artigo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        filtros_layout.addWidget(self.chk_filtrar_emissao, row, 0)
        filtros_layout.addWidget(self.dt_emissao_ini, row, 1)
        filtros_layout.addWidget(self.lbl_ate_emissao, row, 2)
        filtros_layout.addWidget(self.dt_emissao_fim, row, 3)
        filtros_layout.addWidget(QLabel(f"{Icons.FILTER} Artigo:"), row, 4)
        filtros_layout.addWidget(self.cmb_artigo, row, 5, 1, 2)

        row = 1
    
        self.chk_filtrar_recebimento = QCheckBox(f"{Icons.CALENDAR} Filtrar por recebimento:")
        self.chk_filtrar_recebimento.setChecked(True)  

        # 🔹 Define datas: INÍCIO DO MÊS até ONTEM
        hoje = QDate.currentDate()
        primeiro_dia_mes = QDate(hoje.year(), hoje.month(), 1)  
        ontem = hoje.addDays(-1)  
        
        self.dt_recebimento_ini = QDateEdit()
        self.dt_recebimento_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_recebimento_ini.setCalendarPopup(True)
        self.dt_recebimento_ini.setDate(primeiro_dia_mes)  
        self.dt_recebimento_ini.setMinimumWidth(110)
        self.dt_recebimento_ini.setEnabled(True)

        self.lbl_ate_recebimento = QLabel("até")
        self.lbl_ate_recebimento.setEnabled(True)

        self.dt_recebimento_fim = QDateEdit()
        self.dt_recebimento_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_recebimento_fim.setCalendarPopup(True)
        self.dt_recebimento_fim.setDate(ontem) 
        self.dt_recebimento_fim.setMinimumWidth(110)
        self.dt_recebimento_fim.setEnabled(True)

        self.chk_filtrar_recebimento.toggled.connect(self._toggle_recebimento_filter)

        filtros_layout.addWidget(self.chk_filtrar_recebimento, row, 0)
        filtros_layout.addWidget(self.dt_recebimento_ini, row, 1)
        filtros_layout.addWidget(self.lbl_ate_recebimento, row, 2)
        filtros_layout.addWidget(self.dt_recebimento_fim, row, 3)
        
        # LINHA 2: Outros filtros
        row = 2
        
        self.cmb_comp = QComboBox()
        self.cmb_comp.addItem("(todas)")
        self.cmb_comp.setMinimumWidth(120)
        self.cmb_comp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cmb_vend = QComboBox()
        self.cmb_vend.addItem("(todos)")
        self.cmb_vend.setMinimumWidth(150)
        self.cmb_vend.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cmb_uf = QComboBox()
        self.cmb_uf.addItem("(todas)")
        self.cmb_uf.setMinimumWidth(100)

        self.spn_pct = QSpinBox()
        self.spn_pct.setRange(0, 100)
        self.spn_pct.setValue(5)
        self.spn_pct.setFixedWidth(80)

        filtros_layout.addWidget(QLabel(f"{Icons.CALENDAR} Competência:"), row, 0)
        filtros_layout.addWidget(self.cmb_comp, row, 1)
        filtros_layout.addWidget(QLabel(f"{Icons.USER} Vendedor:"), row, 2)
        filtros_layout.addWidget(self.cmb_vend, row, 3)
        filtros_layout.addWidget(QLabel(f"{Icons.FLAG} UF:"), row, 4)
        filtros_layout.addWidget(self.cmb_uf, row, 5)
        filtros_layout.addWidget(QLabel(f"{Icons.CHART} % padrão:"), row, 6)
        filtros_layout.addWidget(self.spn_pct, row, 7)

        # Permite expansão
        filtros_layout.setColumnStretch(1, 1)
        filtros_layout.setColumnStretch(3, 1)
        
        layout.addWidget(filtros_container)
    
    def _create_action_buttons(self, layout):
        """Cria os botões de ação (LAYOUT HORIZONTAL IGUAL CONSULTA)"""

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.btn_refresh = QPushButton("Atualizar")
        self.btn_refresh.setObjectName("btnPrimary")
        self.btn_refresh.setMinimumWidth(120)

        self.btn_salvar = QPushButton("Salvar")
        self.btn_salvar.setObjectName("btnSuccess")
        self.btn_salvar.setMinimumWidth(120)

        self.btn_validar = QPushButton("Validar")
        self.btn_validar.setObjectName("btnSuccess")
        self.btn_validar.setMinimumWidth(120)

        self.btn_consol = QPushButton("Consolidar")
        self.btn_consol.setObjectName("btnPrimary")
        self.btn_consol.setMinimumWidth(120)

        self.btn_enviar = QPushButton("Enviar E-mail")
        self.btn_enviar.setObjectName("btnSecondary")
        self.btn_enviar.setMinimumWidth(120)

        self.btn_enviar_manual = QPushButton("Enviar E-mail Manual")
        self.btn_enviar_manual.setObjectName("btnSecondary")
        self.btn_enviar_manual.setMinimumWidth(140)

        btn_aplicar_todos = QPushButton("Aplicar % em todos")

        self.btn_voltar = QPushButton("Voltar p/ Consulta")
        self.btn_voltar.setObjectName("btnGhost")
        self.btn_voltar.setMinimumWidth(140)

        self.btn_sincronizar = QPushButton("Sincronizar")
        self.btn_sincronizar.setObjectName("btnWarning")
        self.btn_sincronizar.setMinimumWidth(120)



        # Adiciona todos na linha
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_salvar)
        btn_layout.addWidget(self.btn_validar)
        btn_layout.addWidget(self.btn_consol)
        btn_layout.addWidget(self.btn_enviar)
        btn_layout.addWidget(self.btn_voltar)
        btn_layout.addWidget(btn_aplicar_todos)
        btn_layout.addWidget(self.btn_sincronizar)

        # Conectar eventos
        self.btn_refresh.clicked.connect(self.refresh_extrato)
        self.btn_salvar.clicked.connect(self.on_salvar_alteracoes)
        self.btn_validar.clicked.connect(self.on_validar)
        self.btn_enviar.clicked.connect(self.on_enviar_emails)
        self.btn_voltar.clicked.connect(self.voltar_para_consulta)
        btn_aplicar_todos.clicked.connect(self._aplicar_pct_todos)
        self.btn_sincronizar.clicked.connect(self.abrir_sincronizacao)

        # Permissões de botões
        self._configure_button_permissions()

        layout.addLayout(btn_layout)
    
    def _configure_button_permissions(self):
        """Configura permissões dos botões baseado no perfil"""
        if self.role in ("gestora", "admin"):
            self.btn_enviar.hide()
        elif self.role == "controladoria":
            self.btn_salvar.show()
            self.btn_validar.show()
            self.btn_consol.show()
            self.btn_enviar.show()
            self.btn_voltar.hide()
            self.btn_sincronizar.hide()
        else:
            self.btn_salvar.hide()
            self.btn_validar.hide()
            self.btn_consol.hide()
            self.btn_enviar.hide()

    def _create_table(self, layout):
        """Cria a tabela de extrato"""
        self.tbl_extrato = QTableView()
        self.tbl_extrato.horizontalHeader().setStretchLastSection(True)
        self.tbl_extrato.horizontalHeader().setHighlightSections(False)
        self.tbl_extrato.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_extrato.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl_extrato.verticalHeader().setVisible(False)
        self.tbl_extrato.setSortingEnabled(True)
        self.tbl_extrato.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tbl_extrato)
    
    def _create_footer(self, layout):
        """Cria o rodapé com contador de registros"""
        linha_inferior = QHBoxLayout()
        linha_inferior.addStretch()
        
        self.lbl_count_extrato = QLabel("0 registro(s)")
        self.lbl_count_extrato.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 13px;")
        linha_inferior.addWidget(self.lbl_count_extrato)

        self.lbl_total_recebido = QLabel("Total selecionado: R$ 0,00")
        self.lbl_total_recebido.setStyleSheet("font-weight: 600; color: #9ca3af; margin-left: 20px; font-size: 13px;")
        linha_inferior.addWidget(self.lbl_total_recebido)

        layout.addLayout(linha_inferior)
    
    def _toggle_emissao_filter(self, checked):
        """Habilita/desabilita filtro de emissão"""
        self.dt_emissao_ini.setEnabled(checked)
        self.dt_emissao_fim.setEnabled(checked)
        self.lbl_ate_emissao.setEnabled(checked)
        self.refresh_extrato()

    def _toggle_recebimento_filter(self, checked):
        """Habilita/desabilita filtro de recebimento"""
        self.dt_recebimento_ini.setEnabled(checked)
        self.dt_recebimento_fim.setEnabled(checked)
        self.lbl_ate_recebimento.setEnabled(checked)
        self.refresh_extrato()  
    
    def abrir_sincronizacao(self):
        """Abre dialog de sincronização"""
        from tabs.sincronizacao import DialogSincronizacao
        dialog = DialogSincronizacao(self, self.cfg)
        dialog.exec()

        self.refresh_extrato()

    def refresh_extrato(self):
        """Carrega dados do extrato do banco COM FEEDBACK"""
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Carregando extrato")
        loading.show_overlay()
        
        try:
            # 🔹 Consulta ao banco
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
            
            # # 🔹 🔸 FILTRO AUTOMÁTICO PARA CONTROLADORIA 🔸 🔹
            # if self.role.lower() == "controladoria" and not df.empty:
            #     from datetime import datetime, timedelta
            #     ontem = (datetime.now() - timedelta(days=1)).date()
            #     df["Recebimento"] = pd.to_datetime(df["Recebimento"], errors="coerce").dt.date
            #     df = df[df["Recebimento"] == ontem]
            
            # 🔹 Garantir que % Comissão use o valor salvo no banco
            if "% Comissão" in df.columns and "PercComissao" in df.columns:
                df["% Comissão"] = df["PercComissao"].astype(float).round(4)
            
            # 🔹 Ajuste se não existir coluna
            if "Percentual_Comissao" not in df.columns and "% Percentual Padrão" in df.columns:
                df["% Percentual Padrão"] = df["% Percentual Padrão"].astype(float).round(4)

        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Extrato", f"Erro ao carregar extrato: {e}")
            return

        loading.update_message(f"{Icons.LOADING} Processando dados")

        # 🔹 Converte datas
        if "Recebimento" in df.columns:
            df["Competência"] = df["Recebimento"].apply(comp_br)
        
        for c in ("Emissão", "Vencimento", "Recebimento", "ValidadoEm"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y")

        # 🔹 Atualiza combos (OTIMIZADO)
        self._update_combos(df)

        # 🔹 Aplica filtros
        df = self._apply_filters(df)

        # 🔹 Guarda o DataFrame
        self.df_extrato = df.copy()

        # 🔹 Exibe na tabela
        self._display_extrato(df)

        # 🔹 Atualiza contador
        total = len(df)
        self.lbl_count_extrato.setText(f"{total:,} registro(s)".replace(",", "."))

        # 🔹 Conecta seleção para atualizar totais
        try:
            self.tbl_extrato.selectionModel().selectionChanged.disconnect()
        except:
            pass
        self.tbl_extrato.selectionModel().selectionChanged.connect(self._atualizar_total_recebido)
        
        # 🔹 Força atualização inicial do total
        self._atualizar_total_recebido()
        
        loading.close_overlay()
        QuickFeedback.show(self, f"{total} registro(s) no extrato", success=True)
        
    def _update_combos(self, df):
        """Atualiza os combos de filtros (OTIMIZADO - apenas se mudou)"""
        # Competências
        comps_novos = set(c for c in df.get("Competência", pd.Series([])).dropna().unique() if c)
        if comps_novos != self._cache_competencias:
            self._cache_competencias = comps_novos
            comps = sorted(comps_novos, reverse=True)  # 🔹 Ordem decrescente (mais recente primeiro)
            
            # 🔹 Determina competência atual (mês vigente)
            from datetime import datetime
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            
            # Mapeia mês para formato brasileiro
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
            
            # 🔹 Define competência atual como padrão (se existir nos dados)
            if competencia_atual in comps and cur_c == "(todas)":
                self.cmb_comp.setCurrentText(competencia_atual)
            elif cur_c and cur_c in ["(todas)", *comps]:
                self.cmb_comp.setCurrentText(cur_c)
            
            self.cmb_comp.blockSignals(False)

        # Vendedores
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

        # Artigos
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

        # UFs
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
        """Aplica os filtros selecionados"""
        # Competência
        chosen_c = self.cmb_comp.currentText()
        if chosen_c and chosen_c != "(todas)":
            df = df[df["Competência"] == chosen_c]

        # Vendedor
        chosen_v = self.cmb_vend.currentText()
        if chosen_v and chosen_v != "(todos)":
            df = df[df["Vendedor"].astype(str) == chosen_v]

        # Artigo
        artigo = self.cmb_artigo.currentText()
        if artigo != "(todos)" and "Artigo" in df.columns:
            df = df[df["Artigo"] == artigo]

        # UF
        uf = self.cmb_uf.currentText()
        if uf != "(todas)" and "UF" in df.columns:
            df = df[df["UF"] == uf]

        # Filtro por período de emissão
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

        # Aplica % padrão SOMENTE onde não há valor definido
        pct_padrao = self.spn_pct.value()
        if pct_padrao > 0 and "% Comissão" in df.columns:
            df.loc[df["% Comissão"].isna() | (df["% Comissão"] == 0), "% Comissão"] = pct_padrao


        return df
    
    def _display_extrato(self, df):
        """Exibe os dados na tabela"""
        df_show = apply_display_formats(df.copy())
        cols_show = self._get_display_columns(df_show.columns)
        
        # 🔹 Limpar delegates antes de trocar o model
        if self.tbl_extrato.model() is not None:
            for col in range(self.tbl_extrato.model().columnCount()):
                self.tbl_extrato.setItemDelegateForColumn(col, None)
        
        # 🔹 Criar model
        model = EditableTableModel(cols_show, df_show[cols_show].values.tolist())
        
        # 🔥 NOVO: Conectar sinal ANTES de definir readonly
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
        
        # 🔹 Associar model à tabela
        self.tbl_extrato.setModel(model)
        self.tbl_extrato.setSortingEnabled(False)

        if self.role in ("gestora", "admin", "controladoria"):
            # Delegate para coluna "% Comissão" (2 casas decimais: 5,00)
            if "% Comissão" in cols_show:
                col_idx = cols_show.index("% Comissão")
                delegate_percent = DecimalDelegate(decimal_places=2, parent=self.tbl_extrato)
                self.tbl_extrato.setItemDelegateForColumn(col_idx, delegate_percent)
            
            # Delegate para coluna "Valor Comissão" (2 casas decimais: 150,00)
            if "Valor Comissão" in cols_show:
                col_idx = cols_show.index("Valor Comissão")
                delegate_valor = DecimalDelegate(decimal_places=2, parent=self.tbl_extrato)
                self.tbl_extrato.setItemDelegateForColumn(col_idx, delegate_valor)
                    
        # 🔹 Configurar redimensionamento das colunas
        header = self.tbl_extrato.horizontalHeader()
        
        # Primeiro ajustar todas ao conteúdo
        self.tbl_extrato.resizeColumnsToContents()
        
        # Larguras mínimas sugeridas para cada tipo de coluna
        min_widths = {
            "ID": 60,
            "Vendedor": 120,
            "Titulo": 180,
            "Cliente": 150,
            "Artigo": 150,
            "Linha": 100,
            "UF": 40,
            "Recebido": 110,
            "Rec Liquido": 110,
            "Preço Venda": 110,
            "Valor Comissão": 120,
            "% Comissão": 80,
            "ICMSST": 90,
            "Frete": 90,
            "Emissão": 95,
            "Vencimento": 95,
            "Recebimento": 95,
            "Competência": 90,
            "ValidadoEm": 95
        }
        
        # Configurar modo Interactive para permitir ajuste manual
        # e aplicar larguras mínimas
        for col in range(model.columnCount()):
            col_name = cols_show[col] if col < len(cols_show) else ""
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            
            # Aplicar largura mínima se definida
            if col_name in min_widths:
                current_width = self.tbl_extrato.columnWidth(col)
                if current_width < min_widths[col_name]:
                    self.tbl_extrato.setColumnWidth(col, min_widths[col_name])
        
        # Última coluna se expande para preencher espaço disponível
        header.setStretchLastSection(True)
        # 🔹 Reconectar signal de seleção (atualiza total)
        try:
            self.tbl_extrato.selectionModel().selectionChanged.disconnect()
        except:
            pass
        self.tbl_extrato.selectionModel().selectionChanged.connect(self._atualizar_total_recebido)
        
        # 🔹 Adicionar evento de clique no cabeçalho para ordenar e recalcular total
        header = self.tbl_extrato.horizontalHeader()

        def on_header_clicked(section):
            model = self.tbl_extrato.model()
            if hasattr(model, "sort"):
                order = (
                    Qt.SortOrder.DescendingOrder
                    if getattr(model, "_sort_order", Qt.SortOrder.AscendingOrder)
                    == Qt.SortOrder.AscendingOrder
                    else Qt.SortOrder.AscendingOrder
                )
                model.sort(section, order)
            self._atualizar_total_recebido()

        try:
            header.sectionClicked.disconnect()
        except (TypeError, RuntimeError):
            pass  # Ignora se não há conexão
        header.sectionClicked.connect(on_header_clicked)

    def _recalcular_comissao_ao_editar(self, top_left, bottom_right, model, cols_show):
        """
        🔥 Recalcula automaticamente o Valor Comissão quando % Comissão é editado
        Usa a mesma lógica da tab_consulta: (Rec Liquido * % / 100) com ROUND_HALF_UP
        """
        try:
            # Verifica se tem as colunas necessárias
            if "% Comissão" not in cols_show or "Valor Comissão" not in cols_show or "Rec Liquido" not in cols_show:
                return
            
            col_pct_idx = cols_show.index("% Comissão")
            col_val_idx = cols_show.index("Valor Comissão")
            col_rec_idx = cols_show.index("Rec Liquido")
            
            # Se a coluna alterada NÃO foi "% Comissão", não faz nada
            if top_left.column() != col_pct_idx:
                return
            
            from decimal import Decimal, ROUND_HALF_UP
            
            row = top_left.row()
            
            # 🔹 Pega os valores do modelo (já estão formatados em pt-BR)
            pct_str = str(model.data(model.index(row, col_pct_idx)) or "0")
            rec_str = str(model.data(model.index(row, col_rec_idx)) or "0")
            
            # 🔹 Converte para Decimal usando br_to_decimal
            pct = br_to_decimal(pct_str, 4) or Decimal('0.0000')
            rec_liq = br_to_decimal(rec_str, 2) or Decimal('0.00')
            
            # 🔹 Calcula: Valor Comissão = (Rec Liquido * % Comissão / 100)
            # Usa ROUND_HALF_UP igual TopManager
            valor_comissao = (rec_liq * pct / Decimal('100')).quantize(
                Decimal('0.01'), 
                rounding=ROUND_HALF_UP
            )
            
            # 🔹 Formata para exibição (padrão brasileiro: 1.234,56)
            valor_formatado = f"{float(valor_comissao):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # 🔹 Atualiza o modelo (visual) - IMPORTANTE: Bloqueia recursão
            model.blockSignals(True)
            model.setData(model.index(row, col_val_idx), valor_formatado, Qt.EditRole)
            model.blockSignals(False)
            
            # 🔹 Atualiza também o DataFrame interno (para salvar depois)
            if not self.df_extrato.empty and row < len(self.df_extrato):
                self.df_extrato.iloc[row, self.df_extrato.columns.get_loc("Valor Comissão")] = float(valor_comissao)
            
            print(f"✅ Recalculado: Linha {row+1} | % = {pct} | Rec Liq = {rec_liq} | Valor = {valor_comissao}")
                    
        except Exception as e:
            print(f"❌ Erro ao recalcular comissão: {e}")
            import traceback
            traceback.print_exc()

    def _get_display_columns(self, cols_all):
        """Retorna as colunas a serem exibidas"""
        hide = {"VendedorID", "Linha", "ICMSST", "Frete", "Competencia", "Consolidado"}
        order = ["DBId", "Competência", "Validado", "ID", "Vendedor", "Titulo", "Cliente", "UF", "Artigo",
                 "Recebido", "Rec Liquido", "Prazo Médio", "Preço Médio", "Preço Venda",
                 "M Pagamento", "Emissão", "Vencimento", "Recebimento", "% Percentual Padrão",
                 "% Comissão", "Valor Comissão", "Observação", "ValidadoPor", "ValidadoEm"]
        cols = [c for c in order if c in cols_all]
        cols += [c for c in cols_all if c not in set(cols) | hide]
        return cols
    
    def _atualizar_total_recebido(self):
        """Atualiza o total de valores selecionados"""
        total = 0.0
        model = self.tbl_extrato.model()

        if not model:
            return

        for index in self.tbl_extrato.selectedIndexes():
            header = model.headerData(index.column(), Qt.Horizontal)
            if str(header).strip().lower() in ["rec liquido", "recebido"]:
                try:
                    valor_str = str(index.data()).replace('.', '').replace(',', '.')
                    total += float(valor_str)
                except (ValueError, TypeError):
                    pass

        self.lbl_total_recebido.setText(
            f"Total selecionado: R$ {total:,.2f}"
            .replace(',', 'X').replace('.', ',').replace('X', '.')
        )
    
    def on_salvar_alteracoes(self):
        """Salva alterações no extrato (gestora/admin) COM FEEDBACK"""
        if self.role not in ("gestora", "admin", "controladoria"):
            QMessageBox.warning(self, "Permissão", "Apenas a gestora (Karen) ou admin podem salvar alterações.")
            return
        
        # 🔹 Força fechar qualquer editor ativo
        editor = self.tbl_extrato.focusWidget()
        if editor is not None:
            self.tbl_extrato.closeEditor(
                editor, 
                QAbstractItemDelegate.EndEditHint.SubmitModelCache
            )
        self.tbl_extrato.clearFocus()
        
        # 🔹 IMPORTANTE: Aguarda processamento de eventos pendentes
        QApplication.processEvents()

        model: EditableTableModel = self.tbl_extrato.model()
        if model is None:
            return

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.SAVE} Salvando alterações")
        loading.show_overlay()

        try:
            from decimal import Decimal, ROUND_HALF_UP
            
            hdr = model.headers
            def idx(h):
                try:
                    return hdr.index(h)
                except ValueError:
                    return None

            i_db = idx("DBId")
            i_pct = idx("% Comissão")
            i_val = idx("Valor Comissão")
            i_obs = idx("Observação")
            i_cons = idx("Consolidado")
            i_rec = idx("Rec Liquido")  # 🔹 Necessário para recalcular

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
                    
                    # Pula se consolidado
                    if i_cons is not None and str(r[i_cons]).strip() in ("1", "True", "true"):
                        continue
                    
                    # 🔹 Converte % Comissão
                    pct = br_to_decimal(r[i_pct], 4) if i_pct is not None else Decimal('0.0000')
                    
                    # 🔹 RECALCULA Valor Comissão baseado no % e Rec Liquido
                    # Garante que mesmo se o usuário não editou, o valor está correto
                    val = Decimal('0.00')
                    if pct is not None and i_rec is not None:
                        rec_liq = br_to_decimal(r[i_rec], 2) or Decimal('0.00')
                        
                        # Calcula com ROUND_HALF_UP (igual TopManager)
                        val = (rec_liq * pct / Decimal('100')).quantize(
                            Decimal('0.01'), 
                            rounding=ROUND_HALF_UP
                        )
                        
                        print(f"📊 Salvando linha {i}: DBId={dbid} | % = {pct} | Rec Liq = {rec_liq} | Valor = {val}")
                    
                    obs = str(r[i_obs])[:500] if i_obs is not None else None
                    
                    # 🔹 Atualiza no banco
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
        """Valida registros selecionados (gestora/admin) COM FEEDBACK"""
        if self.role not in ("gestora", "admin", "controladoria"):
            QMessageBox.warning(self, "Permissão", "Apenas a gestora (Karen) ou admin podem validar.")
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
            # Pega índices visuais
            idxs_visuais = [s.row() for s in sel]
            df_vendedor = self.df_extrato.iloc[idxs_visuais].copy()

            # Envia e-mail por vendedor
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
        """Envia e-mail para vendedores selecionados COM FEEDBACK"""
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
        # idxs_visuais = [s.row() for s in sel]
        # df_selecionado = self.df_extrato.iloc[idxs_visuais].copy()
        
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

                vendedor_norm = vendedor.strip().upper()
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
            
            # Mensagem de resumo
            msg_partes = []
            if vendedores_enviados:
                msg_partes.append(f"✅ E-mails enviados com sucesso para:\n" + "\n".join(f"  • {v}" for v in vendedores_enviados))
            
            if vendedores_sem_email:
                msg_partes.append(f"\n⚠️ Vendedores sem e-mail cadastrado:\n" + "\n".join(f"  • {v}" for v in vendedores_sem_email))
            
            if vendedores_enviados:
                QuickFeedback.show(self, f"{len(vendedores_enviados)} e-mail(s) enviado(s)", success=True)
                QMessageBox.information(self, "E-mails", "\n".join(msg_partes))
            else:
                QMessageBox.warning(self, "E-mails", "Nenhum e-mail foi enviado.\n\n" + "\n".join(msg_partes))
                
        except Exception as e:
            loading.close_overlay()
            QMessageBox.warning(self, "Aviso", f"Erro ao enviar e-mails:\n{e}")
    
    def voltar_para_consulta(self):
        """
        Remove registros do EXTRATO (deleta do banco)
        Após deletar, os títulos poderão ser buscados novamente na janela de Consulta
        """
        sel = self.tbl_extrato.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Extrato", "Nenhum item selecionado.")
            return

        # 🔹 CONFIRMAÇÃO com aviso claro
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
            
            # 🔹 Coleta os IDs do banco (DBId) dos registros selecionados
            ids_deletar = []
            for s in sel:
                row = model.rows[s.row()]
                db_id = int(row[i_db])
                ids_deletar.append(db_id)
            
            # 🔹 DELETA do banco de dados
            deletados = 0
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                total = len(ids_deletar)
                
                for i, db_id in enumerate(ids_deletar, 1):
                    loading.update_message(f"{Icons.LOADING} Removendo {i}/{total}")
                    
                    # Verifica se não está consolidado (segurança)
                    cur.execute("""
                        SELECT Consolidado 
                        FROM dbo.Stik_Extrato_Comissoes 
                        WHERE Id = ?
                    """, db_id)
                    
                    result = cur.fetchone()
                    if result and result[0] == 1:
                        # Está consolidado, não pode deletar
                        continue
                    
                    # Deleta do banco
                    cur.execute("""
                        DELETE FROM dbo.Stik_Extrato_Comissoes 
                        WHERE Id = ? AND Consolidado = 0
                    """, db_id)
                    
                    deletados += cur.rowcount
                
                conn.commit()
            
            loading.close_overlay()
            
            if deletados > 0:
                QuickFeedback.show(self, f"{deletados} registro(s) removido(s) do extrato", success=True)
                self.refresh_extrato()  # Atualiza a tela
                
                # 🔹 Mensagem informativa
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
    
    def get_filtered_data(self) -> pd.DataFrame:
        """Retorna os dados filtrados atualmente"""
        df = self.df_extrato.copy()
        chosen_c = self.cmb_comp.currentText()
        chosen_v = self.cmb_vend.currentText()
        if chosen_c and chosen_c != "(todas)":
            df = df[df["Competência"] == chosen_c]
        if chosen_v and chosen_v != "(todos)":
            df = df[df["Vendedor"].astype(str) == chosen_v]
        return df
    
    def _aplicar_pct_todos(self):
        """Aplica o valor do QSpinBox (% padrão) em todas as linhas atualmente exibidas"""
        pct = self.spn_pct.value()
        model = self.tbl_extrato.model()
        if model is None:
            return

        df = self.df_extrato.copy()
        if "% Comissão" in df.columns:
            df["% Comissão"] = pct

        self._display_extrato(df)
        QuickFeedback.show(self, f"% Comissão atualizado para {pct:.2f} em todas as linhas exibidas", success=True)