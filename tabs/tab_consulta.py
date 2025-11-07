
"""
Aba de Consulta - Busca e adição de lançamentos ao extrato
RESPONSIVA | OTIMIZADA | COM FEEDBACKS | CORRIGIDA
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QSpinBox, QPushButton, QTableView, QMessageBox,
    QHeaderView, QAbstractItemView, QSizePolicy
)
from PySide6.QtCore import QDate, Qt, QTimer
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

from config import DBConfig, get_conn
from queries_1 import build_query_866
from models import EditableTableModel
from utils.formatters import br_to_decimal, br_to_float, apply_display_formats
from ui.loading_overlay import LoadingOverlay, QuickFeedback
from ui.icons import Icons, icon_button_text


class TabConsulta(QWidget):
    """
    Aba de Consulta de Comissões
    Permite buscar lançamentos e adicioná-los ao extrato
    """
    
    def __init__(self, parent=None, role: str = "admin"):
        super().__init__(parent)
        self.role = role
        self.cfg = DBConfig()
        self.df_result = pd.DataFrame()
        
        # Cache para otimização
        self._cache_vendedores = set()
        self._cache_artigos = set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface da aba"""
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)
        
        # Container de filtros (RESPONSIVO)
        self._create_filters(lay)
        
        # Botões de ação
        self._create_action_buttons(lay)
        
        # Tabela de resultados
        self._create_table(lay)
        
        # Label de contador
        self.lbl_total = QLabel("Total de linhas: 0")
        self.lbl_total.setAlignment(Qt.AlignRight)
        self.lbl_total.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 13px;")
        lay.addWidget(self.lbl_total)
    
    def _create_filters(self, layout):
        """Cria o container de filtros RESPONSIVO"""
        filtros_container = QWidget()
        filtros_container.setObjectName("filtrosContainer")
        filtros_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # Grid layout para responsividade
        from PySide6.QtWidgets import QGridLayout
        filtros_layout = QGridLayout(filtros_container)
        filtros_layout.setSpacing(10)
        filtros_layout.setContentsMargins(16, 12, 16, 12)

        # LINHA 0
        row = 0
        
        # Filtrar por
        filtros_layout.addWidget(QLabel("Filtrar por:"), row, 0)
        self.cmb_tipo_data = QComboBox()
        self.cmb_tipo_data.addItems(["Recebimento", "Emissão"])
        self.cmb_tipo_data.setFixedWidth(120)
        filtros_layout.addWidget(self.cmb_tipo_data, row, 1)

        # Período
        filtros_layout.addWidget(QLabel(f"{Icons.CALENDAR} Período:"), row, 2)
        self.dt_ini = QDateEdit()
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setCalendarPopup(True)
        self.dt_ini.setDate(QDate.currentDate().addMonths(-1).addDays(1))
        self.dt_ini.setMinimumWidth(110)
        filtros_layout.addWidget(self.dt_ini, row, 3)

        filtros_layout.addWidget(QLabel("até"), row, 4)
        self.dt_fim = QDateEdit()
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDate(QDate.currentDate())
        self.dt_fim.setMinimumWidth(110)
        filtros_layout.addWidget(self.dt_fim, row, 5)

        # LINHA 1
        row = 1
        
        # Vendedor
        filtros_layout.addWidget(QLabel(f"{Icons.USER} Vendedor:"), row, 0)
        self.cmb_vendedor = QComboBox()
        self.cmb_vendedor.addItem("(todos)")
        self.cmb_vendedor.setMinimumWidth(150)
        self.cmb_vendedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout.addWidget(self.cmb_vendedor, row, 1, 1, 2)

        # Artigo
        filtros_layout.addWidget(QLabel(f"{Icons.FILTER} Artigo:"), row, 3)
        self.cmb_artigo = QComboBox()
        self.cmb_artigo.addItem("(todos)")
        self.cmb_artigo.setMinimumWidth(180)
        self.cmb_artigo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout.addWidget(self.cmb_artigo, row, 4, 1, 2)

        # % padrão
        filtros_layout.addWidget(QLabel(f"{Icons.CHART} % padrão:"), row, 6)
        self.spn_pct = QSpinBox()
        self.spn_pct.setRange(0, 100)
        self.spn_pct.setValue(5)
        self.spn_pct.setFixedWidth(70)
        filtros_layout.addWidget(self.spn_pct, row, 7)
        
        # Permite que as colunas se expandam
        filtros_layout.setColumnStretch(1, 1)
        filtros_layout.setColumnStretch(4, 1)
        
        layout.addWidget(filtros_container)
    
    def _create_action_buttons(self, layout):
        """Cria os botões de ação"""
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setObjectName("btnPrimary")
        self.btn_buscar.setMinimumWidth(120)
        self.btn_buscar.clicked.connect(self.on_buscar)

        self.btn_add = QPushButton("Adicionar ao Extrato")
        self.btn_add.setObjectName("btnSuccess")
        self.btn_add.setMinimumWidth(160)
        self.btn_add.clicked.connect(self.add_to_extrato)
        
        btn_layout.addWidget(self.btn_buscar)
        btn_layout.addWidget(self.btn_add)
        
        layout.addLayout(btn_layout)

    def _create_table(self, layout):
        """Cria a tabela de resultados"""
        self.tbl = QTableView()
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.horizontalHeader().setHighlightSections(False)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSortingEnabled(True)
        self.tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tbl)
    
    def on_buscar(self):
        """Executa a busca de dados COM FEEDBACK"""
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Buscando dados")
        loading.show_overlay()

        try:
            # Captura as datas do período
            di = self.dt_ini.date().toString('yyyyMMdd')
            df_ = self.dt_fim.date().toString('yyyyMMdd')
            tipo_filtro = self.cmb_tipo_data.currentText()
            
            vendedor = self.cmb_vendedor.currentText()
            if vendedor == "(todos)":
                vendedor = None

            loading.update_message(f"{Icons.LOADING} Consultando banco de dados")
            
            # Executa a query (OTIMIZADO - apenas uma chamada)
            sql, params = build_query_866(di, df_, vendedor)
            num_markers = sql.count("?")
            if len(params) > num_markers:
                params = params[:num_markers]

            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                while cur.description is None and cur.nextset():
                    pass
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
            
            df_res = pd.DataFrame.from_records(rows, columns=cols)
            
            if df_res.empty:
                loading.close_overlay()
                QuickFeedback.show(self, "Nenhum resultado encontrado", success=False)
                self._display_empty_results()
                return
            
            loading.update_message(f"{Icons.LOADING} Processando dados")
            
            # Filtro por tipo de data (Emissão)
            if tipo_filtro == "Emissão" and "Emissão" in df_res.columns:
                dt_inicio = pd.to_datetime(di, format='%Y%m%d')
                dt_fim_periodo = pd.to_datetime(df_, format='%Y%m%d')
                
                df_res["_Emissao_dt"] = pd.to_datetime(
                    df_res["Emissão"], 
                    format='%d/%m/%Y',
                    errors='coerce'
                )
                mask = (df_res["_Emissao_dt"] >= dt_inicio) & (df_res["_Emissao_dt"] <= dt_fim_periodo)
                df_res = df_res[mask].copy()
                df_res.drop(columns=["_Emissao_dt"], inplace=True)
            
            # Adiciona % Percentual Padrão
            if "Percentual_Comissao" in df_res.columns:
                df_res["% Percentual Padrão"] = df_res["Percentual_Comissao"].astype(float).round(4)

            # Renomeia NmLot para Vendedor
            if "NmLot" in df_res.columns:
                df_res.rename(columns={"NmLot": "Vendedor"}, inplace=True)

            # Atualiza combo de vendedores (OTIMIZADO - apenas se mudou)
            self._update_vendedor_combo(df_res)

            # 🔹 CORREÇÃO: Remove itens já no extrato verificando ID + Artigo + Titulo
            ids_artigos_titulos_rasc = self._fetch_extrato_docs_artigos_titulos_set()
            
            if "ID" in df_res.columns and "Artigo" in df_res.columns and "Titulo" in df_res.columns and ids_artigos_titulos_rasc:
                len_antes = len(df_res)
                
                # Cria chave composta (ID, Artigo, Titulo)
                df_res["_chave"] = df_res.apply(
                    lambda x: (str(x["ID"]).strip(), str(x["Artigo"]).strip(), str(x.get("Titulo", "")).strip()), 
                    axis=1
                )
                
                # Remove registros que já estão no extrato
                df_res = df_res[~df_res["_chave"].isin(ids_artigos_titulos_rasc)].copy()
                df_res.drop(columns=["_chave"], inplace=True)
                
                removidos = len_antes - len(df_res)
                if removidos > 0:
                    print(f"{removidos} registro(s) já estão no extrato (removidos da consulta)")

            # Aplica filtro por artigo
            chosen_artigo = self.cmb_artigo.currentText()
            if chosen_artigo and chosen_artigo != "(todos)":
                df_res = df_res[df_res["Artigo"] == chosen_artigo]

            # Atualiza combo de artigos (OTIMIZADO)
            self._update_artigo_combo(df_res)

            # Adiciona colunas esperadas
            df_res = self._add_expected_columns(df_res)

            # Guarda o resultado
            self.df_result = df_res

            # Exibe na tabela
            self._display_results(df_res)

            # Atualiza contador
            self._update_counter(df_res)
            
            loading.close_overlay()
            QuickFeedback.show(self, f"{len(df_res)} registro(s) encontrado(s)", success=True)

        except Exception as e:
            loading.close_overlay()
            import traceback
            QMessageBox.critical(
                self, 
                "Erro na consulta", 
                f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=1)}"
            )
    
    def _display_empty_results(self):
        """Exibe tabela vazia quando não há resultados"""
        self.df_result = pd.DataFrame()
        self.tbl.setModel(None)
        self.lbl_total.setText("Total de linhas: 0")
    
    def _update_vendedor_combo(self, df):
        """Atualiza o combo de vendedores (OTIMIZADO)"""
        vendedores_novos = set(df["Vendedor"].dropna().astype(str).unique())
        
        # Apenas atualiza se mudou
        if vendedores_novos != self._cache_vendedores:
            self._cache_vendedores = vendedores_novos
            vendedores = sorted(vendedores_novos)
            cur_v = self.cmb_vendedor.currentText()
            
            self.cmb_vendedor.blockSignals(True)  # Evita triggers desnecessários
            self.cmb_vendedor.clear()
            self.cmb_vendedor.addItem("(todos)")
            self.cmb_vendedor.addItems(vendedores)
            if cur_v and cur_v in ["(todos)", *vendedores]:
                self.cmb_vendedor.setCurrentText(cur_v)
            self.cmb_vendedor.blockSignals(False)
    
    def _update_artigo_combo(self, df):
        """Atualiza o combo de artigos (OTIMIZADO)"""
        artigos_novos = set(df["Artigo"].dropna().unique())
        
        # Apenas atualiza se mudou
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
    
    def _fetch_extrato_docs_artigos_titulos_set(self) -> set:
        """
        🔹 CORREÇÃO: Busca tuplas (ID, Artigo, Titulo) já presentes no extrato
        Isso evita duplicatas exatas mas permite mesmo ID com artigos/titulos diferentes
        """
        out = set()
        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT Doc, Artigo, Titulo 
                    FROM dbo.Stik_Extrato_Comissoes 
                    WHERE Consolidado = 0
                """)
                out = {(str(r[0]).strip(), str(r[1]).strip(), str(r[2] or "").strip()) for r in cur.fetchall()}
        except Exception as e:
            print(f"Erro ao buscar IDs+Artigos+Titulos do extrato: {e}")
        return out
    
    def _add_expected_columns(self, df):
        """Adiciona colunas esperadas ao DataFrame (OTIMIZADO)"""
        expected = [
            "ID", "VendedorID", "Vendedor", "Titulo", "Cliente", "UF", "Artigo", "Linha",
            "Recebido", "ICMSST", "Frete", "Rec Liquido", "Prazo Médio",
            "Preço Médio", "Preço Venda", "M Pagamento", "Emissão", "Vencimento", 
            "Recebimento", "% Percentual Padrão"
        ]
        
        # Adiciona colunas faltantes de uma vez
        missing_cols = [c for c in expected if c not in df.columns]
        for c in missing_cols:
            df[c] = ""

        # Normaliza colunas numéricas (vetorizado - mais rápido)
        num_cols = ["Recebido", "ICMSST", "Frete", "Rec Liquido", "Prazo Médio", 
                    "Preço Médio", "Preço Venda"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        
        # Normaliza datas (vetorizado)
        for c in ("Emissão", "Vencimento", "Recebimento"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

        # Adiciona % Comissão e Observação
        if "% Comissão" not in df.columns:
            df["% Comissão"] = float(self.spn_pct.value())
        if "Observação" not in df.columns:
            df["Observação"] = ""

        return df[expected + ["% Comissão", "Observação"]].reset_index(drop=True)
    
    def _display_results(self, df):
        """Exibe os resultados na tabela"""
        df_show = apply_display_formats(df.copy())
        cols_show = self._get_display_columns(df_show.columns)

        model = EditableTableModel(cols_show, df_show[cols_show].values.tolist())
        self.tbl.setModel(model)
        self.tbl.resizeColumnsToContents()
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    
    def _get_display_columns(self, cols_all):
        """Retorna as colunas a serem exibidas"""
        hide = {"VendedorID", "Linha", "ICMSST", "Frete"}
        return [c for c in cols_all if c not in hide]
    
    def _update_counter(self, df):
        """Atualiza o contador de linhas"""
        total_linhas = len(df)
        duplicadas = len(df[df.duplicated()])
        docs_unicos = df["ID"].nunique() if "ID" in df.columns else 0
        
        self.lbl_total.setText(
            f"Total: {total_linhas:,} linha(s) | Documentos únicos: {docs_unicos:,} | Duplicadas: {duplicadas}"
            .replace(",", ".")
        )
    
    def add_to_extrato(self, selected_rows=None) -> tuple:
        """
        Adiciona linhas selecionadas ao extrato COM FEEDBACK
        
        Args:
            selected_rows: Lista de índices das linhas selecionadas (None/bool = usar seleção da tabela)
        
        Returns:
            tuple: (inserted, errors)
        """
        model: EditableTableModel = self.tbl.model()
        if model is None:
            return 0, 0
        
        # 🔹 CORREÇÃO: Ignora se vier bool (evento do botão)
        if selected_rows is None or isinstance(selected_rows, bool):
            sel = self.tbl.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Adicionar", "Selecione uma ou mais linhas para adicionar ao extrato.")
                return 0, 0
            selected_rows = [s.row() for s in sel]

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Adicionando ao extrato")
        loading.show_overlay()

        try:
            hdr = model.headers
            def idx(h):
                try:
                    return hdr.index(h)
                except ValueError:
                    return None

            ix = {h: idx(h) for h in ["ID", "Titulo", "Cliente", "% Comissão"]}
            inserted = 0
            errors = 0

            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                total = len(selected_rows)
                
                for i, s in enumerate(sorted(selected_rows, reverse=True), 1):
                    loading.update_message(f"{Icons.LOADING} Processando {i}/{total}")
                    
                    view_row = model.rows[s]
                    id_val = str(view_row[ix["ID"]]).strip()
                    tit_val = str(view_row[ix["Titulo"]]).strip() if ix["Titulo"] is not None else None
                    cli_val = str(view_row[ix["Cliente"]]).strip() if ix["Cliente"] is not None else None

                    df = self.df_result
                    mask = df["ID"].astype(str).str.strip().eq(id_val)
                    if tit_val is not None:
                        mask &= df["Titulo"].astype(str).str.strip().eq(tit_val)
                    if cli_val is not None:
                        mask &= df["Cliente"].astype(str).str.strip().eq(cli_val)
                    
                    mt = df[mask]
                    if mt.empty:
                        errors += 1
                        continue

                    row = mt.iloc[0].to_dict()

                    # Cálculos
                    pct = br_to_decimal(
                        view_row[ix["% Comissão"]] if ix["% Comissão"] is not None else row.get("% Comissão", 0), 
                        4
                    ) or Decimal('0.0000')
                    
                    rec_liq = br_to_decimal(row.get("Rec Liquido", 0), 2) or Decimal('0.00')
                    valor_com = (rec_liq * pct / Decimal('100')).quantize(
                        Decimal('0.01'), 
                        rounding=ROUND_HALF_UP
                    )
                    pct_padrao = br_to_decimal(
                        row.get("Percentual_Comissao") or row.get("% Percentual Padrão") or 0.01, 
                        4
                    )

                    comp_iso = pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce")
                    comp_iso = comp_iso.strftime("%Y-%m") if pd.notna(comp_iso) else None

                    # Insert no banco
                    cur.execute("""
                        INSERT INTO dbo.Stik_Extrato_Comissoes (
                            Competencia, Doc, Cliente, Artigo, Linha, UF,
                            DataRecebimento, RecebimentoLiq, PercComissao, ValorComissao,
                            Observacao, CriadoPor,
                            VendedorID, Vendedor, Titulo, MeioPagamento,
                            Emissao, Vencimento, Recebido, ICMSST, Frete,
                            PrecoMedio, PrecoVenda, PrazoMedio, Percentual_Comissao,
                            Validado, ValidadoPor, ValidadoEm, Consolidado
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'PySide6-App',
                                 ?,?,?,?,?,?,?,?,?,?,?,?,?, 0, NULL, NULL, 0)
                    """,
                        comp_iso,
                        int(str(row.get("ID", 0)) or 0),
                        str(row.get("Cliente", ""))[:200],
                        str(row.get("Artigo", ""))[:200],
                        str(row.get("Linha", ""))[:200],
                        str(row.get("UF", ""))[:2],
                        pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce").date(),
                        rec_liq, pct, valor_com,
                        str(row.get("Observação", ""))[:500],
                        int(br_to_float(row.get("VendedorID", 0))) or None,
                        str(row.get("Vendedor", ""))[:200] or None,
                        str(row.get("Titulo", ""))[:120] or None,
                        str(row.get("M Pagamento", ""))[:100] or None,
                        pd.to_datetime(row.get("Emissão"), dayfirst=True, errors="coerce").date() if row.get("Emissão") else None,
                        pd.to_datetime(row.get("Vencimento"), dayfirst=True, errors="coerce").date() if row.get("Vencimento") else None,
                        br_to_decimal(row.get("Recebido", 0), 2),
                        br_to_decimal(row.get("ICMSST", 0), 2),
                        br_to_decimal(row.get("Frete", 0), 2),
                        br_to_decimal(row.get("Preço Médio", 0), 4),
                        br_to_decimal(row.get("Preço Venda", 0), 4),
                        br_to_decimal(row.get("Prazo Médio", 0), 2),
                        pct_padrao
                    )
                    
                    inserted += 1
                    model.remove_rows([s])
                    self.df_result.drop(mt.index[0], inplace=True)

                conn.commit()
            
            loading.close_overlay()
            QuickFeedback.show(self, f"{inserted} registro(s) adicionado(s) ao extrato", success=True)
            
            # Atualiza contador após remoção
            self._update_counter(self.df_result)
            
        except Exception as e:
            loading.close_overlay()
            raise Exception(f"Erro ao gravar no extrato: {str(e)}")

        return inserted, errors