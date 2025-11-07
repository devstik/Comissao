"""
Aba de Consolidados - Visualização e gestão de comissões consolidadas
RESPONSIVA | OTIMIZADA | COM FEEDBACKS | LAYOUT PADRONIZADO
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPushButton, QTableView, QMessageBox, QFileDialog,
    QHeaderView, QAbstractItemView, QInputDialog, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt
import pandas as pd
import os

from config import DBConfig, get_conn
from models import EditableTableModel
from utils.formatters import apply_display_formats, comp_br, br_to_decimal, br_to_float
from utils.pdf_generator import gerar_pdf_extrato
from constants import USERS, SMTP_CONFIG
from email.message import EmailMessage
import smtplib
from ui.loading_overlay import LoadingOverlay, QuickFeedback
from ui.icons import Icons, icon_button_text


class TabConsolidados(QWidget):
    """
    Aba de Consolidados
    Exibe e gerencia registros já consolidados
    """
    
    def __init__(self, parent=None, role: str = "admin", username: str = "admin"):
        super().__init__(parent)
        self.role = role
        self.username = username
        self.cfg = DBConfig()
        self.df_consolidados = pd.DataFrame()
        
        # Cache para otimização
        self._cache_competencias = set()
        self._cache_vendedores = set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface da aba"""
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)
        
        # Filtros e botões (LAYOUT PADRONIZADO)
        self._create_filters_and_buttons(lay)
        
        # Tabela
        self._create_table(lay)
        
        # Rodapé com contador
        self._create_footer(lay)
    
    def _create_filters_and_buttons(self, layout):
        """Cria filtros e botões (LAYOUT RESPONSIVO)"""
        # Container de filtros
        filtros_container = QWidget()
        filtros_container.setObjectName("filtrosContainer")
        filtros_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        filtros_layout = QGridLayout(filtros_container)
        filtros_layout.setSpacing(10)
        filtros_layout.setContentsMargins(16, 12, 16, 12)
        
        # Competência
        filtros_layout.addWidget(QLabel(f"{Icons.CALENDAR} Competência:"), 0, 0)
        self.cmb_comp_consol = QComboBox()
        self.cmb_comp_consol.addItem("(todas)")
        self.cmb_comp_consol.setMinimumWidth(120)
        self.cmb_comp_consol.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout.addWidget(self.cmb_comp_consol, 0, 1)
        
        # Vendedor
        filtros_layout.addWidget(QLabel(f"{Icons.USER} Vendedor:"), 0, 2)
        self.cmb_vend_consol = QComboBox()
        self.cmb_vend_consol.addItem("(todos)")
        self.cmb_vend_consol.setMinimumWidth(150)
        self.cmb_vend_consol.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout.addWidget(self.cmb_vend_consol, 0, 3, 1, 2)
        
        filtros_layout.setColumnStretch(1, 1)
        filtros_layout.setColumnStretch(3, 1)
        
        layout.addWidget(filtros_container)
        
        # Botões de ação (HORIZONTAL)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.btn_refresh = QPushButton("Atualizar")
        self.btn_refresh.setObjectName("btnPrimary")
        self.btn_refresh.setMinimumWidth(120)

        self.btn_pdf = QPushButton("Gerar PDF")
        self.btn_pdf.setObjectName("btnSuccess")
        self.btn_pdf.setMinimumWidth(120)

        self.btn_email = QPushButton("Enviar E-mail")
        self.btn_email.setObjectName("btnSecondary")
        self.btn_email.setMinimumWidth(120)

        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("btnDanger")
        self.btn_excluir.setMinimumWidth(120)

        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_email)
        btn_layout.addWidget(self.btn_excluir)
        
        layout.addLayout(btn_layout)
        
        # Conectar eventos
        self.btn_refresh.clicked.connect(self.refresh_consolidados)
        self.btn_pdf.clicked.connect(self.on_gerar_pdf_consolidados)
        self.btn_email.clicked.connect(self.on_enviar_email_consolidados)
        self.btn_excluir.clicked.connect(self.on_excluir_consolidados)
    
    def _create_table(self, layout):
        """Cria a tabela de consolidados"""
        self.tbl_consolidados = QTableView()
        self.tbl_consolidados.horizontalHeader().setStretchLastSection(True)
        self.tbl_consolidados.horizontalHeader().setHighlightSections(False)
        self.tbl_consolidados.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_consolidados.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl_consolidados.verticalHeader().setVisible(False)
        self.tbl_consolidados.setSortingEnabled(True)
        self.tbl_consolidados.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tbl_consolidados)
    
    def _create_footer(self, layout):
        """Cria rodapé com contador"""
        linha_inferior = QHBoxLayout()
        linha_inferior.addStretch()
        
        self.lbl_count_consolidados = QLabel("0 registro(s)")
        self.lbl_count_consolidados.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 13px;")
        linha_inferior.addWidget(self.lbl_count_consolidados)
        
        layout.addLayout(linha_inferior)
    
    def refresh_consolidados(self):
        """Carrega dados consolidados do banco COM FEEDBACK"""
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOADING} Carregando consolidados")
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
                           Observacao as [Observação]
                    FROM dbo.Stik_Consolidacao_Comissoes
                    ORDER BY DataRecebimento DESC, Id DESC
                """)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
            df = pd.DataFrame.from_records(rows, columns=cols)
        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Consolidados", f"Erro ao carregar consolidados: {e}")
            return

        loading.update_message(f"{Icons.LOADING} Processando dados")

        # Converte datas
        if "Recebimento" in df.columns:
            df["Competência"] = df["Recebimento"].apply(comp_br)
        
        for c in ("Emissão", "Vencimento", "Recebimento"):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y")

        # Atualizar combos (OTIMIZADO)
        self._update_combos(df)

        # Aplicar filtros
        df = self._apply_filters(df)

        # Guardar base
        self.df_consolidados = df.copy()

        # Exibir
        self._display_consolidados(df)
        
        # Atualizar contador
        total = len(df)
        self.lbl_count_consolidados.setText(f"{total:,} registro(s)".replace(",", "."))
        
        loading.close_overlay()
        QuickFeedback.show(self, f"{total} registro(s) consolidado(s)", success=True)
    
    def _update_combos(self, df):
        """Atualiza os combos de filtros (OTIMIZADO)"""
        # Competências
        comps_novos = set(c for c in df.get("Competência", pd.Series([])).dropna().unique() if c)
        if comps_novos != self._cache_competencias:
            self._cache_competencias = comps_novos
            comps = sorted(comps_novos)
            cur_c = self.cmb_comp_consol.currentText()
            self.cmb_comp_consol.blockSignals(True)
            self.cmb_comp_consol.clear()
            self.cmb_comp_consol.addItem("(todas)")
            self.cmb_comp_consol.addItems(comps)
            if cur_c and cur_c in ["(todas)", *comps]:
                self.cmb_comp_consol.setCurrentText(cur_c)
            self.cmb_comp_consol.blockSignals(False)

        # Vendedores
        vends_novos = set(v for v in df.get("Vendedor", pd.Series([])).dropna().astype(str).unique() if v)
        if vends_novos != self._cache_vendedores:
            self._cache_vendedores = vends_novos
            vends = sorted(vends_novos)
            cur_v = self.cmb_vend_consol.currentText()
            self.cmb_vend_consol.blockSignals(True)
            self.cmb_vend_consol.clear()
            self.cmb_vend_consol.addItem("(todos)")
            self.cmb_vend_consol.addItems(vends)
            if cur_v and cur_v in ["(todos)", *vends]:
                self.cmb_vend_consol.setCurrentText(cur_v)
            self.cmb_vend_consol.blockSignals(False)
    
    def _apply_filters(self, df):
        """Aplica os filtros selecionados"""
        chosen_c = self.cmb_comp_consol.currentText()
        chosen_v = self.cmb_vend_consol.currentText()
        
        if chosen_c and chosen_c != "(todas)":
            df = df[df["Competência"] == chosen_c]
        if chosen_v and chosen_v != "(todos)":
            df = df[df["Vendedor"].astype(str) == chosen_v]
        
        return df
    
    def _display_consolidados(self, df):
        """Exibe os consolidados na tabela"""
        df_show = apply_display_formats(df.copy())
        cols_show = self._get_display_columns(df_show.columns)

        model = EditableTableModel(cols_show, df_show[cols_show].values.tolist())
        model.set_all_readonly(True)  # Consolidados são readonly

        self.tbl_consolidados.setModel(model)
        self.tbl_consolidados.resizeColumnsToContents()
    
    def _get_display_columns(self, cols_all):
        """Retorna as colunas a serem exibidas"""
        hide = {"VendedorID", "Linha", "ICMSST", "Frete", "Competencia", "Consolidado"}
        order = ["DBId", "Competência", "ID", "Vendedor", "Titulo", "Cliente", "UF", "Artigo",
                 "Recebido", "Rec Liquido", "Prazo Médio", "Preço Médio", "Preço Venda",
                 "M Pagamento", "Emissão", "Vencimento", "Recebimento",
                 "% Comissão", "Valor Comissão", "Observação"]
        cols = [c for c in order if c in cols_all]
        cols += [c for c in cols_all if c not in set(cols) | hide]
        return cols
    
    def get_filtered_data(self) -> pd.DataFrame:
        """Retorna consolidados filtrados"""
        return self._apply_filters(self.df_consolidados.copy())
    
    def on_gerar_pdf_consolidados(self):
        """Gerar PDF dos consolidados COM FEEDBACK"""
        df = self.get_filtered_data()
        if df.empty:
            QMessageBox.information(self, "PDF", "Nenhum dado consolidado no filtro atual.")
            return
        
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            QMessageBox.critical(self, "PDF", "Instale: pip install reportlab")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar PDF", "consolidados_comissoes.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.PDF} Gerando PDF")
        loading.show_overlay()
        
        try:
            gerar_pdf_extrato(path, df)
            loading.close_overlay()
            QuickFeedback.show(self, "PDF gerado com sucesso", success=True)
            QMessageBox.information(self, "PDF", f"PDF gerado com sucesso:\n{path}")
        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF:\n{str(e)}")
    
    def on_enviar_email_consolidados(self):
        """Enviar por email os consolidados COM FEEDBACK"""
        df = self.get_filtered_data()
        if df.empty:
            QMessageBox.information(self, "E-mail", "Nenhum dado consolidado no filtro atual.")
            return

        to, ok = QInputDialog.getText(self, "Enviar por E-mail", "E-mail do destinatário:")
        if not ok or not to.strip():
            return
        to = to.strip()

        tmp_pdf = "consolidados_tmp.pdf"
        
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.EMAIL} Enviando e-mail")
        loading.show_overlay()
        
        try:
            # Gera PDF
            loading.update_message(f"{Icons.PDF} Gerando PDF")
            gerar_pdf_extrato(tmp_pdf, df)

            loading.update_message(f"{Icons.EMAIL} Enviando para {to}")

            # Composição do e-mail
            msg = EmailMessage()
            msg["Subject"] = "Extrato de Comissão - Registros CONSOLIDADOS"
            msg["From"] = SMTP_CONFIG["user"]
            msg["To"] = to
            msg.set_content("Segue extrato de comissão com registros já consolidados no sistema.")

            # Anexa PDF
            with open(tmp_pdf, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="pdf",
                    filename="consolidados_comissoes.pdf"
                )

            # Envia
            srv = smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=30)
            if SMTP_CONFIG["use_tls"]:
                srv.starttls()
            srv.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            srv.send_message(msg)
            srv.quit()

            loading.close_overlay()
            QuickFeedback.show(self, f"E-mail enviado para {to}", success=True)
            QMessageBox.information(self, "E-mail", f"E-mail enviado para: {to}")
        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Erro", f"Erro ao enviar e-mail:\n{str(e)}")
        finally:
            try:
                os.remove(tmp_pdf)
            except:
                pass
    
    def on_excluir_consolidados(self):
        """Excluir registros consolidados - requer senha do admin COM FEEDBACK"""
        model: EditableTableModel = self.tbl_consolidados.model()
        if model is None:
            return
        
        sel = self.tbl_consolidados.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Exclusão", "Selecione uma ou mais linhas para excluir.")
            return
        
        # Confirma a ação
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Você está prestes a excluir {len(sel)} registro(s) consolidado(s).\n\n"
            "Esta ação é IRREVERSÍVEL e removerá os dados permanentemente.\n\n"
            f"{'Esta operação requer autorização do administrador.' if self.username != 'admin' else ''}\n\n"
            "Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Se NÃO for admin, verifica senha
        if self.username != "admin":
            if not self._verificar_senha_admin():
                QMessageBox.information(
                    self,
                    "Operação Cancelada",
                    "Exclusão cancelada. Entre em contato com o administrador para autorizar esta operação."
                )
                return
        
        hdr = model.headers
        try:
            i_db = hdr.index("DBId")
        except ValueError:
            QMessageBox.warning(self, "Erro", "Coluna DBId não encontrada.")
            return
        
        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.DELETE} Excluindo registros")
        loading.show_overlay()
        
        deleted = 0
        docs_affected = []
        
        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                
                # Coleta os IDs para excluir
                ids_to_delete = []
                rows_to_remove = []
                
                for s in sel:
                    row_idx = s.row()
                    row = model.rows[row_idx]
                    dbid = int(row[i_db])
                    ids_to_delete.append(dbid)
                    rows_to_remove.append(row_idx)
                
                total = len(ids_to_delete)
                
                # Executa a exclusão no banco
                for i, dbid in enumerate(ids_to_delete, 1):
                    loading.update_message(f"{Icons.DELETE} Excluindo {i}/{total}")
                    
                    # Busca o Doc antes de excluir
                    cur.execute("SELECT Doc FROM dbo.Stik_Consolidacao_Comissoes WHERE Id = ?", dbid)
                    result = cur.fetchone()
                    if result:
                        doc = result[0]
                        docs_affected.append(doc)
                    
                    # Remove da tabela de consolidação
                    cur.execute("DELETE FROM dbo.Stik_Consolidacao_Comissoes WHERE Id = ?", dbid)
                    deleted += cur.rowcount
                
                loading.update_message(f"{Icons.UNLOCK} Desmarcando registros no extrato")
                
                # Desmarca como consolidado na tabela de extrato
                for doc in docs_affected:
                    cur.execute("""
                        UPDATE dbo.Stik_Extrato_Comissoes 
                        SET Consolidado = 0 
                        WHERE Doc = ?
                    """, doc)
                
                conn.commit()
                
                # Remove da view
                model.remove_rows(rows_to_remove)
                
            loading.close_overlay()
            QuickFeedback.show(self, f"{deleted} registro(s) excluído(s)", success=True)
            
            QMessageBox.information(
                self,
                "Exclusão Concluída",
                f"{deleted} registro(s) excluído(s) com sucesso.\n\n"
                f"Os registros foram desmarcados como consolidados no extrato."
                + (f"\nOperação autorizada pelo administrador." if self.username != "admin" else "")
            )
            
            # Atualiza a aba
            self.refresh_consolidados()
            
        except Exception as e:
            loading.close_overlay()
            QMessageBox.critical(self, "Erro ao excluir", f"Erro: {str(e)}")
    
    def _verificar_senha_admin(self) -> bool:
        """Solicita senha do admin para operações críticas"""
        senha, ok = QInputDialog.getText(
            self, 
            "Autenticação do Administrador", 
            "Esta operação requer autorização do administrador.\n\n"
            "Digite a senha do usuário 'admin':",
            QLineEdit.Password
        )
        if not ok:
            return False
        
        if senha == USERS["admin"]["pwd"]:
            return True
        else:
            QMessageBox.warning(self, "Autenticação", "Senha do administrador incorreta!")
            return False
    
    def consolidar_registros(self, df_to_consolidate: pd.DataFrame) -> tuple:
        """
        Consolida registros validados no banco COM FEEDBACK
        
        Args:
            df_to_consolidate: DataFrame com os dados a consolidar
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if df_to_consolidate.empty:
            return False, "Nenhum dado para consolidar."

        # Verificar se todas as linhas estão validadas
        nao_validadas = df_to_consolidate[
            df_to_consolidate["Validado"].astype(str).isin(["0", "False", "false", "nan", "None", ""])
        ]
        
        if not nao_validadas.empty:
            vendedores_nao_validados = nao_validadas["Vendedor"].dropna().unique()
            return False, (
                f"{len(nao_validadas)} linha(s) não estão validadas.\n"
                "A consolidação só é permitida quando todas as linhas estão validadas.\n\n"
                "Vendedores com registros não validados:\n" + 
                "\n".join(map(str, vendedores_nao_validados))
            )

        # Verificar se há linhas já consolidadas
        if "Consolidado" in df_to_consolidate.columns:
            if (df_to_consolidate["Consolidado"].astype(str).isin(["1", "True", "true"])).any():
                return False, "Existem linhas já consolidadas. Remova-as para prosseguir."

        parent_window = self.window()
        loading = LoadingOverlay(parent_window, f"{Icons.LOCK} Consolidando registros")
        loading.show_overlay()

        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                total = len(df_to_consolidate)
                
                for i, (_, row) in enumerate(df_to_consolidate.iterrows(), 1):
                    loading.update_message(f"{Icons.LOCK} Consolidando {i}/{total}")
                    
                    comp_iso = None
                    try:
                        comp_iso = pd.to_datetime(
                            row.get("Recebimento"), 
                            dayfirst=True, 
                            errors="coerce"
                        ).strftime("%Y-%m")
                    except:
                        pass

                    # Insere na consolidação
                    cur.execute("""
                        INSERT INTO dbo.Stik_Consolidacao_Comissoes (
                            Competencia, Doc, Cliente, Artigo, Linha, UF,
                            DataRecebimento, RecebimentoLiq, PercComissao, ValorComissao,
                            Observacao, CriadoPor,
                            VendedorID, Vendedor, Titulo, MeioPagamento,
                            Emissao, Vencimento, Recebido, ICMSST, Frete,
                            PrecoMedio, PrecoVenda, PrazoMedio
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'PySide6-App',
                                ?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                        comp_iso,
                        int(str(row.get("ID", 0)) or 0),
                        str(row.get("Cliente", ""))[:200],
                        str(row.get("Artigo", ""))[:200],
                        str(row.get("Linha", ""))[:200],
                        str(row.get("UF", ""))[:2],
                        pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce").date(),
                        br_to_decimal(row.get("Rec Liquido", 0), 2),
                        br_to_decimal(row.get("% Comissão", 0), 4),
                        br_to_decimal(row.get("Valor Comissão", 0), 2),
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
                        br_to_decimal(row.get("Prazo Médio", 0), 2)
                    )
                    
                    # Marca como consolidado
                    cur.execute(
                        "UPDATE dbo.Stik_Extrato_Comissoes SET Consolidado = 1 WHERE Id = ?", 
                        int(row["DBId"])
                    )
                
                conn.commit()
            
            loading.close_overlay()
            QuickFeedback.show(self, f"{total} registro(s) consolidado(s)", success=True)
            
            return True, f"Consolidado com sucesso! {total} linhas travadas no extrato."
            
        except Exception as e:
            loading.close_overlay()
            return False, f"Erro ao consolidar: {str(e)}"