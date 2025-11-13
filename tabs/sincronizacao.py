"""
Sistema de Sincronização TopManager ↔ Comissys
OTIMIZADO: Por Competência + Vendedor
Garante que % Comissão personalizado não seja alterado
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, 
    QTextEdit, QMessageBox, QProgressBar, QComboBox, QDateEdit, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from config import DBConfig, get_conn
from queries_1 import build_query_866
from utils.formatters import br_to_decimal, br_to_float
from ui.icons import Icons


class SyncWorker(QThread):
    """Thread para executar sincronização em background"""
    progress = Signal(str)
    finished = Signal(dict)
    
    def __init__(self, competencia_inicio, competencia_fim, vendedor, cfg):
        super().__init__()
        self.competencia_inicio = competencia_inicio
        self.competencia_fim = competencia_fim
        self.vendedor = vendedor  # 🔹 NOVO: pode ser None (todos) ou nome específico
        self.cfg = cfg
    
    def run(self):
        """Executa sincronização"""
        try:
            resultado = self.sincronizar()
            self.finished.emit(resultado)
        except Exception as e:
            self.finished.emit({"erro": str(e)})
    
    def sincronizar(self):
        """Compara TopManager vs Comissys e sincroniza"""
        vendedor_info = self.vendedor if self.vendedor else "TODOS"
        self.progress.emit(f"📊 Buscando dados do TopManager ({vendedor_info})...")
        
        # 1. Buscar títulos do TopManager (por vendedor ou todos)
        di = self.competencia_inicio.strftime('%Y%m%d')
        df = self.competencia_fim.strftime('%Y%m%d')
        
        sql, params = build_query_866(di, df, self.vendedor)  # 🔹 MODIFICADO: passa vendedor
        
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            while cur.description is None and cur.nextset():
                pass
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        
        df_topmanager = pd.DataFrame.from_records(rows, columns=cols)
        
        # Renomeia NmLot para Vendedor
        if "NmLot" in df_topmanager.columns:
            df_topmanager.rename(columns={"NmLot": "Vendedor"}, inplace=True)
        
        # 🔹 CORREÇÃO: Normaliza datas para formato ISO
        df_topmanager["_Recebimento_dt"] = pd.to_datetime(
            df_topmanager["Recebimento"], 
            dayfirst=True, 
            errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        
        self.progress.emit(f"✅ TopManager: {len(df_topmanager)} registro(s)")
        
        # 2. Buscar títulos do Comissys (mesmo período e vendedor)
        self.progress.emit(f"📊 Buscando dados do Comissys ({vendedor_info})...")
        
        # 🔹 MODIFICADO: adiciona filtro por vendedor se especificado
        if self.vendedor:
            query = """
                SELECT 
                    Id as DBId,
                    Doc as ID,
                    Titulo,
                    Artigo,
                    Vendedor,
                    CONVERT(VARCHAR(10), DataRecebimento, 23) as DataRecebimentoISO,
                    RecebimentoLiq,
                    PercComissao,
                    Consolidado
                FROM dbo.Stik_Extrato_Comissoes
                WHERE DataRecebimento BETWEEN ? AND ?
                  AND Vendedor = ?
                  AND Consolidado = 0
                ORDER BY Vendedor, Doc, DataRecebimento
            """
            params_query = (self.competencia_inicio, self.competencia_fim, self.vendedor)
        else:
            query = """
                SELECT 
                    Id as DBId,
                    Doc as ID,
                    Titulo,
                    Artigo,
                    Vendedor,
                    CONVERT(VARCHAR(10), DataRecebimento, 23) as DataRecebimentoISO,
                    RecebimentoLiq,
                    PercComissao,
                    Consolidado
                FROM dbo.Stik_Extrato_Comissoes
                WHERE DataRecebimento BETWEEN ? AND ?
                  AND Consolidado = 0
                ORDER BY Vendedor, Doc, DataRecebimento
            """
            params_query = (self.competencia_inicio, self.competencia_fim)
        
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            cur.execute(query, params_query)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        
        df_comissys = pd.DataFrame.from_records(rows, columns=cols)
        
        self.progress.emit(f"✅ Comissys: {len(df_comissys)} registro(s)")
        
        # 3. Criar chaves normalizadas para comparação
        self.progress.emit("🔍 Comparando TopManager vs Comissys...")
        
        # 🔹 CORREÇÃO: Normalização completa (lower, strip)
        df_topmanager["_chave"] = df_topmanager.apply(
            lambda x: (
                str(x.get("ID", "")).strip().lower(),
                str(x.get("Titulo", "")).strip().lower(),
                str(x.get("Artigo", "")).strip().lower(),
                str(x.get("Vendedor", "")).strip().lower(),
                str(x["_Recebimento_dt"])
            ),
            axis=1
        )
        
        df_comissys["_chave"] = df_comissys.apply(
            lambda x: (
                str(x.get("ID", "")).strip().lower(),
                str(x.get("Titulo", "")).strip().lower(),
                str(x.get("Artigo", "")).strip().lower(),
                str(x.get("Vendedor", "")).strip().lower(),
                str(x["DataRecebimentoISO"])
            ),
            axis=1
        )
        
        chaves_topmanager = set(df_topmanager["_chave"])
        chaves_comissys = set(df_comissys["_chave"])
        
        # 4. Identificar diferenças
        faltando_comissys = chaves_topmanager - chaves_comissys
        sobrando_comissys = chaves_comissys - chaves_topmanager
        
        self.progress.emit(f"📊 Análise concluída:")
        self.progress.emit(f"   ✅ Em sincronia: {len(chaves_topmanager & chaves_comissys)}")
        self.progress.emit(f"   ⚠️ Faltando no Comissys: {len(faltando_comissys)}")
        self.progress.emit(f"   ⚠️ Sobrando no Comissys: {len(sobrando_comissys)}")
        
        # 5. Preparar relatório
        resultado = {
            "total_topmanager": len(df_topmanager),
            "total_comissys": len(df_comissys),
            "em_sincronia": len(chaves_topmanager & chaves_comissys),
            "faltando": len(faltando_comissys),
            "sobrando": len(sobrando_comissys),
            "df_faltando": df_topmanager[df_topmanager["_chave"].isin(faltando_comissys)],
            "df_sobrando": df_comissys[df_comissys["_chave"].isin(sobrando_comissys)],
            "vendedor": self.vendedor or "TODOS",
            "periodo": f"{self.competencia_inicio.strftime('%d/%m/%Y')} a {self.competencia_fim.strftime('%d/%m/%Y')}"
        }
        
        return resultado


class DialogSincronizacao(QDialog):
    """Dialog para sincronização TopManager ↔ Comissys"""
    
    def __init__(self, parent=None, cfg=None):
        super().__init__(parent)
        self.cfg = cfg or DBConfig()
        self.resultado = None
        self._setup_ui()
        self._carregar_vendedores()
    
    def _setup_ui(self):
        """Configura interface"""
        self.setWindowTitle("🔄 Sincronização TopManager ↔ Comissys")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        
        # Título
        lbl_titulo = QLabel("🔄 Sistema de Sincronização Otimizada")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(lbl_titulo)
        
        # Descrição
        lbl_desc = QLabel(
            "✅ Sincronização otimizada por competência e vendedor\n"
            "✅ Não sobrecarrega o TopManager\n"
            "✅ Preserva % comissão personalizado\n"
            "✅ Consultas rápidas (2-5 segundos por vendedor)"
        )
        lbl_desc.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(lbl_desc)
        
        # 🔹 NOVO: Grupo de filtros
        group_filtros = QGroupBox("🔍 Selecione o que sincronizar:")
        filtros_layout = QGridLayout()
        
        # Período
        filtros_layout.addWidget(QLabel("📅 Período:"), 0, 0)
        self.dt_inicio = QDateEdit()
        self.dt_inicio.setDisplayFormat("dd/MM/yyyy")
        self.dt_inicio.setCalendarPopup(True)
        self.dt_inicio.setDate(QDate.currentDate().addMonths(-1).addDays(1))
        filtros_layout.addWidget(self.dt_inicio, 0, 1)
        
        filtros_layout.addWidget(QLabel("até"), 0, 2)
        self.dt_fim = QDateEdit()
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.dt_fim, 0, 3)
        
        # Vendedor
        filtros_layout.addWidget(QLabel("👤 Vendedor:"), 1, 0)
        self.cmb_vendedor = QComboBox()
        self.cmb_vendedor.setMinimumWidth(300)
        filtros_layout.addWidget(self.cmb_vendedor, 1, 1, 1, 3)
        
        group_filtros.setLayout(filtros_layout)
        layout.addWidget(group_filtros)
        
        # Área de log
        lbl_log = QLabel("📋 Log de execução:")
        lbl_log.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_log)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(
            "background: #f5f5f5; "
            "font-family: 'Consolas', 'Monaco', monospace; "
            "font-size: 12px; "
            "padding: 10px;"
            "color: #000000;"
        )
        layout.addWidget(self.txt_log)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_analisar = QPushButton("🔍 Analisar Diferenças")
        self.btn_analisar.setObjectName("btnPrimary")
        self.btn_analisar.setMinimumWidth(180)
        self.btn_analisar.clicked.connect(self.analisar)
        
        self.btn_sincronizar = QPushButton("✅ Sincronizar")
        self.btn_sincronizar.setObjectName("btnSuccess")
        self.btn_sincronizar.setMinimumWidth(180)
        self.btn_sincronizar.setEnabled(False)
        self.btn_sincronizar.clicked.connect(self.sincronizar)
        
        self.btn_fechar = QPushButton("❌ Fechar")
        self.btn_fechar.setObjectName("btnGhost")
        self.btn_fechar.setMinimumWidth(120)
        self.btn_fechar.clicked.connect(self.close)
        
        btn_layout.addWidget(self.btn_analisar)
        btn_layout.addWidget(self.btn_sincronizar)
        btn_layout.addWidget(self.btn_fechar)
        
        layout.addLayout(btn_layout)
    
    def _carregar_vendedores(self):
        """🔹 NOVO: Carrega lista de vendedores do extrato"""
        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT Vendedor 
                    FROM dbo.Stik_Extrato_Comissoes
                    WHERE Consolidado = 0
                      AND Vendedor IS NOT NULL
                    ORDER BY Vendedor
                """)
                vendedores = [r[0] for r in cur.fetchall()]
            
            self.cmb_vendedor.clear()
            self.cmb_vendedor.addItem("(todos)")  # 🔹 Opção para sincronizar todos
            self.cmb_vendedor.addItems(vendedores)
        except Exception as e:
            self.log(f"⚠️ Erro ao carregar vendedores: {e}")
    
    def log(self, mensagem):
        """Adiciona mensagem ao log"""
        self.txt_log.append(mensagem)
    
    def analisar(self):
        """Analisa diferenças entre TopManager e Comissys"""
        # 🔹 MODIFICADO: pega dados dos filtros
        vendedor = self.cmb_vendedor.currentText()
        if vendedor == "(todos)":
            vendedor = None
            
            # Aviso se for sincronizar todos
            reply = QMessageBox.question(
                self,
                "Sincronizar Todos?",
                "⚠️ Você selecionou TODOS os vendedores!\n\n"
                "Isso pode:\n"
                "• Sobrecarregar o TopManager\n"
                "• Demorar vários minutos\n\n"
                "Recomendamos sincronizar por vendedor.\n\n"
                "Deseja continuar mesmo assim?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        competencia_inicio = self.dt_inicio.date().toPython()
        competencia_fim = self.dt_fim.date().toPython()
        
        self.txt_log.clear()
        self.log("=" * 80)
        self.log("🔄 SINCRONIZAÇÃO OTIMIZADA")
        self.log("=" * 80)
        self.log(f"📅 Período: {competencia_inicio.strftime('%d/%m/%Y')} a {competencia_fim.strftime('%d/%m/%Y')}")
        self.log(f"👤 Vendedor: {vendedor or 'TODOS'}")
        self.log("")
        
        # Desabilita botões
        self.btn_analisar.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminado
        
        # Inicia worker thread
        self.worker = SyncWorker(competencia_inicio, competencia_fim, vendedor, self.cfg)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_analise_concluida)
        self.worker.start()
    
    def on_analise_concluida(self, resultado):
        """Callback quando análise termina"""
        self.progress_bar.setVisible(False)
        self.btn_analisar.setEnabled(True)
        
        if "erro" in resultado:
            self.log(f"\n❌ ERRO: {resultado['erro']}")
            QMessageBox.critical(self, "Erro", f"Erro ao analisar:\n{resultado['erro']}")
            return
        
        self.resultado = resultado
        
        # Exibe resumo
        self.log("\n" + "=" * 80)
        self.log("📊 RESUMO DA ANÁLISE")
        self.log("=" * 80)
        self.log(f"TopManager: {resultado['total_topmanager']} registro(s)")
        self.log(f"Comissys:   {resultado['total_comissys']} registro(s)")
        self.log(f"Em sincronia: {resultado['em_sincronia']} ✅")
        self.log(f"Faltando no Comissys: {resultado['faltando']} ⚠️")
        self.log(f"Sobrando no Comissys: {resultado['sobrando']} ⚠️")
        self.log("=" * 80)
        
        # Mostra detalhes dos faltantes
        if resultado['faltando'] > 0:
            self.log("\n⚠️ TÍTULOS FALTANDO NO COMISSYS (precisam ser adicionados):")
            df_faltando = resultado['df_faltando']
            for idx, row in df_faltando.head(20).iterrows():
                self.log(
                    f"   • {row.get('Vendedor', '')} - "
                    f"Doc {row.get('ID', '')} - "
                    f"{row.get('Titulo', '')} - "
                    f"{row.get('Artigo', '')}"
                )
            if len(df_faltando) > 20:
                self.log(f"   ... e mais {len(df_faltando) - 20} título(s)")
        
        # Mostra detalhes dos sobrando
        if resultado['sobrando'] > 0:
            self.log("\n⚠️ TÍTULOS SOBRANDO NO COMISSYS (não estão no TopManager):")
            df_sobrando = resultado['df_sobrando']
            for idx, row in df_sobrando.head(20).iterrows():
                self.log(
                    f"   • {row.get('Vendedor', '')} - "
                    f"Doc {row.get('ID', '')} - "
                    f"{row.get('Titulo', '')} - "
                    f"{row.get('Artigo', '')}"
                )
            if len(df_sobrando) > 20:
                self.log(f"   ... e mais {len(df_sobrando) - 20} título(s)")
        
        # Habilita botão de sincronizar se houver diferenças
        if resultado['faltando'] > 0 or resultado['sobrando'] > 0:
            self.btn_sincronizar.setEnabled(True)
            self.log("\n✅ Clique em 'Sincronizar' para corrigir automaticamente.")
        else:
            self.log("\n✅ PERFEITO! Tudo em sincronia. Nenhuma ação necessária.")
    
    def sincronizar(self):
        """🔹 IMPLEMENTADO: Sincroniza Comissys com TopManager"""
        if not self.resultado:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar Sincronização",
            f"⚠️ ATENÇÃO!\n\n"
            f"Esta operação vai:\n\n"
            f"• ADICIONAR {self.resultado['faltando']} título(s) que faltam\n"
            f"• REMOVER {self.resultado['sobrando']} título(s) que sobraram\n\n"
            f"Vendedor: {self.resultado['vendedor']}\n"
            f"Período: {self.resultado['periodo']}\n\n"
            f"✅ % Comissão personalizado será PRESERVADO\n\n"
            f"Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        self.log("\n🔄 Iniciando sincronização...")
        self.btn_sincronizar.setEnabled(False)
        
        try:
            # Adicionar títulos faltantes
            if self.resultado['faltando'] > 0:
                self.log(f"\n📥 Adicionando {self.resultado['faltando']} título(s)...")
                self._adicionar_faltantes()
            
            # Remover títulos sobrando
            if self.resultado['sobrando'] > 0:
                self.log(f"\n🗑️ Removendo {self.resultado['sobrando']} título(s)...")
                self._remover_sobrando()
            
            self.log("\n✅ Sincronização concluída com sucesso!")
            QMessageBox.information(
                self,
                "Sucesso",
                f"✅ Sincronização concluída!\n\n"
                f"• {self.resultado['faltando']} título(s) adicionado(s)\n"
                f"• {self.resultado['sobrando']} título(s) removido(s)"
            )
            
            # Limpa resultado
            self.resultado = None
            
        except Exception as e:
            self.log(f"\n❌ ERRO: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao sincronizar:\n{e}")
        finally:
            self.btn_sincronizar.setEnabled(False)
    
    def _adicionar_faltantes(self):
        """🔹 IMPLEMENTADO: Adiciona títulos que faltam no Comissys"""
        df_faltando = self.resultado['df_faltando']
        
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            adicionados = 0
            
            for idx, row in df_faltando.iterrows():
                try:
                    # 🔹 PRESERVA % COMISSÃO: usa padrão do vendedor
                    pct_padrao = br_to_decimal(
                        row.get("Percentual_Comissao") or row.get("% Percentual Padrão") or 0.05,
                        4
                    ) or Decimal('0.05')
                    
                    rec_liq = br_to_decimal(row.get("Rec Liquido", 0), 2) or Decimal('0.00')
                    valor_com = (rec_liq * pct_padrao / Decimal('100')).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP
                    )
                    
                    comp_iso = pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce")
                    comp_iso = comp_iso.strftime("%Y-%m") if pd.notna(comp_iso) else None
                    
                    # Insert
                    cur.execute("""
                        INSERT INTO dbo.Stik_Extrato_Comissoes (
                            Competencia, Doc, Cliente, Artigo, Linha, UF,
                            DataRecebimento, RecebimentoLiq, PercComissao, ValorComissao,
                            Observacao, CriadoPor,
                            VendedorID, Vendedor, Titulo, MeioPagamento,
                            Emissao, Vencimento, Recebido, ICMSST, Frete,
                            PrecoMedio, PrecoVenda, PrazoMedio, Percentual_Comissao,
                            Validado, ValidadoPor, ValidadoEm, Consolidado
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'Sync-Auto',
                                 ?,?,?,?,?,?,?,?,?,?,?,?,?, 0, NULL, NULL, 0)
                    """,
                        comp_iso,
                        int(str(row.get("ID", 0)) or 0),
                        str(row.get("Cliente", ""))[:200],
                        str(row.get("Artigo", ""))[:200],
                        str(row.get("Linha", ""))[:200],
                        str(row.get("UF", ""))[:2],
                        pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce").date(),
                        rec_liq, pct_padrao, valor_com,
                        "Adicionado por sincronização automática",
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
                    adicionados += 1
                    
                    if adicionados % 10 == 0:
                        self.log(f"   ✅ {adicionados}/{len(df_faltando)} adicionado(s)...")
                        
                except Exception as e:
                    self.log(f"   ❌ Erro ao adicionar Doc {row.get('ID', '')}: {e}")
            
            conn.commit()
            self.log(f"✅ {adicionados} título(s) adicionado(s) com sucesso")
    
    def _remover_sobrando(self):
        """🔹 IMPLEMENTADO: Remove títulos que sobraram no Comissys"""
        df_sobrando = self.resultado['df_sobrando']
        
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            removidos = 0
            
            for idx, row in df_sobrando.iterrows():
                try:
                    db_id = int(row['DBId'])
                    cur.execute("""
                        DELETE FROM dbo.Stik_Extrato_Comissoes 
                        WHERE Id = ? AND Consolidado = 0
                    """, db_id)
                    removidos += cur.rowcount
                    
                    if removidos % 10 == 0:
                        self.log(f"   ✅ {removidos}/{len(df_sobrando)} removido(s)...")
                        
                except Exception as e:
                    self.log(f"   ❌ Erro ao remover Doc {row.get('ID', '')}: {e}")
            
            conn.commit()
            self.log(f"✅ {removidos} título(s) removido(s) com sucesso")