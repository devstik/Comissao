from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd
from PySide6.QtCore import QDate, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from config import DBConfig, get_conn
from queries import build_query_866
from utils.extrato_writer import EXTRATO_INSERT_SQL, build_extrato_insert_params, insert_extrato_row
from utils.formatters import br_to_decimal


def fmt_currency(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return f"R$ {v}"


def _txt(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip().lower()


def _dec(v, places=2):
    try:
        out = br_to_decimal(v, places)
        return out if out is not None else Decimal("0").quantize(Decimal("1").scaleb(-places))
    except Exception:
        return Decimal("0").quantize(Decimal("1").scaleb(-places))


def _date_iso(v):
    dt = pd.to_datetime(v, dayfirst=True, errors="coerce")
    return "" if pd.isna(dt) else dt.strftime("%Y-%m-%d")


def _base_key(row):
    return (
        _txt(row.get("ID")),
        _txt(row.get("Titulo")),
        _txt(row.get("Artigo")),
        _txt(row.get("Vendedor")),
        _txt(row.get("_Recebimento_iso") or row.get("DataRecebimentoISO")),
    )


def _prepare(df, from_query):
    out = df.copy()
    if from_query and "NmLot" in out.columns and "Vendedor" not in out.columns:
        out.rename(columns={"NmLot": "Vendedor"}, inplace=True)
    if from_query:
        out["_Recebimento_iso"] = pd.to_datetime(out.get("Recebimento"), dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        out["_Recebimento_iso"] = out.get("DataRecebimentoISO", "")
    out["_chave_base"] = out.apply(_base_key, axis=1)
    if out.empty:
        out["_dup_idx"] = []
        out["_chave"] = []
        return out
    sort_cols = [c for c in ["ID", "Titulo", "Artigo", "Cliente", "Vendedor", "_Recebimento_iso", "Recebido"] if c in out.columns]
    if sort_cols:
        out = out.sort_values(by=sort_cols).reset_index(drop=True)
    out["_dup_idx"] = out.groupby("_chave_base").cumcount()
    out["_chave"] = out.apply(lambda r: r["_chave_base"] + (int(r["_dup_idx"]),), axis=1)
    return out


def _group_diff(df_tm, df_cs, tm_cols, cs_cols, tol=Decimal("0.05")):
    col_tm = next((c for c in tm_cols if c in df_tm.columns), None)
    col_cs = next((c for c in cs_cols if c in df_cs.columns), None)
    if not col_tm or not col_cs:
        return []
    grp_tm = pd.to_numeric(df_tm[col_tm], errors="coerce").fillna(0).groupby(df_tm["_chave_base"]).sum()
    grp_cs = pd.to_numeric(df_cs[col_cs], errors="coerce").fillna(0).groupby(df_cs["_chave_base"]).sum()
    out = []
    for key in grp_tm.index.union(grp_cs.index):
        tm = Decimal(str(float(grp_tm.get(key, 0.0)))).quantize(Decimal("0.01"))
        cs = Decimal(str(float(grp_cs.get(key, 0.0)))).quantize(Decimal("0.01"))
        if abs(tm - cs) > tol:
            out.append({"chave_base": key, "valor_tm": float(tm), "valor_cs": float(cs), "delta": float(tm - cs)})
    return out


def _row_diff(df_tm, df_cs, shared):
    if not shared:
        return []
    tm_idx = df_tm.set_index("_chave")
    cs_idx = df_cs.set_index("_chave")
    out = []
    fields = [
        ("Titulo", ["Titulo"], ["Titulo"], "text"),
        ("Artigo", ["Artigo"], ["Artigo"], "text"),
        ("DataRecebimento", ["_Recebimento_iso"], ["DataRecebimentoISO"], "text"),
        ("Recebido", ["Recebido"], ["Recebido"], "num"),
        ("RecebimentoLiq", ["Rec Liquido", "RecebimentoLiq"], ["RecebimentoLiq", "Rec Liquido"], "num"),
        ("PrecoVenda", ["PrecoVenda", "Preço Venda"], ["PrecoVenda", "Preço Venda"], "num"),
    ]
    for key in shared:
        try:
            tm_row = tm_idx.loc[key]
            cs_row = cs_idx.loc[key]
        except Exception:
            continue
        diffs = {}
        for name, tm_cands, cs_cands, kind in fields:
            tm_col = next((c for c in tm_cands if c in tm_row.index), None)
            cs_col = next((c for c in cs_cands if c in cs_row.index), None)
            tm_val = tm_row.get(tm_col) if tm_col else None
            cs_val = cs_row.get(cs_col) if cs_col else None
            same = abs(_dec(tm_val) - _dec(cs_val)) <= Decimal("0.01") if kind == "num" else _txt(tm_val) == _txt(cs_val)
            if not same:
                diffs[name] = {"tm": tm_val, "cs": cs_val}
        if diffs:
            out.append({"chave": key, "chave_base": key[:5], "ID": tm_row.get("ID") or cs_row.get("ID"), "DBId": cs_row.get("DBId"), "diffs": diffs, "tm_row": tm_row.to_dict(), "cs_row": cs_row.to_dict()})
    return out


class SyncWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)

    def __init__(self, competencia_inicio, competencia_fim, vendedor, cfg):
        super().__init__()
        self.competencia_inicio = competencia_inicio
        self.competencia_fim = competencia_fim
        self.vendedor = vendedor
        self.cfg = cfg

    def run(self):
        try:
            self.finished.emit(self.analisar())
        except Exception as e:
            self.finished.emit({"erro": str(e), "traceback": str(e)})

    def analisar(self):
        di = self.competencia_inicio.strftime("%Y%m%d")
        df = self.competencia_fim.strftime("%Y%m%d")
        sql, params = build_query_866(di, df, self.vendedor)
        num_markers = sql.count("?")
        if len(params) > num_markers:
            params = params[:num_markers]
        self.progress.emit("Buscando origem pela build_query_866")
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            while cur.description is None and cur.nextset():
                pass
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        df_tm = _prepare(pd.DataFrame.from_records(rows, columns=cols), True)

        self.progress.emit("Buscando extrato local")
        if self.vendedor:
            query = "SELECT Id as DBId, Doc as ID, Titulo, Artigo, Cliente, Vendedor, CONVERT(VARCHAR(10), DataRecebimento, 23) as DataRecebimentoISO, RecebimentoLiq, Recebido, PercComissao, PrecoVenda FROM dbo.Stik_Extrato_Comissoes WHERE DataRecebimento BETWEEN ? AND ? AND Vendedor = ? AND Consolidado = 0"
            params_cs = (self.competencia_inicio, self.competencia_fim, self.vendedor)
        else:
            query = "SELECT Id as DBId, Doc as ID, Titulo, Artigo, Cliente, Vendedor, CONVERT(VARCHAR(10), DataRecebimento, 23) as DataRecebimentoISO, RecebimentoLiq, Recebido, PercComissao, PrecoVenda FROM dbo.Stik_Extrato_Comissoes WHERE DataRecebimento BETWEEN ? AND ? AND Consolidado = 0"
            params_cs = (self.competencia_inicio, self.competencia_fim)
        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            cur.execute(query, params_cs)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        df_cs = _prepare(pd.DataFrame.from_records(rows, columns=cols), False)

        missing = set(df_tm["_chave"]) - set(df_cs["_chave"])
        extra = set(df_cs["_chave"]) - set(df_tm["_chave"])
        shared = set(df_tm["_chave"]) & set(df_cs["_chave"])
        altered = _row_diff(df_tm, df_cs, shared)
        altered_bases = {a["chave_base"] for a in altered}
        diff_receb = _group_diff(df_tm, df_cs, ["Recebido"], ["Recebido"])
        diff_recliq = _group_diff(df_tm, df_cs, ["Rec Liquido", "RecebimentoLiq"], ["RecebimentoLiq", "Rec Liquido"])
        divergent_bases = ({d["chave_base"] for d in diff_receb} | {d["chave_base"] for d in diff_recliq}) - altered_bases
        divergent_payloads = []
        for key in sorted(divergent_bases):
            divergent_payloads.append({"chave_base": key, "ID": key[0], "tm_rows": df_tm[df_tm["_chave_base"] == key].to_dict("records"), "cs_rows": df_cs[df_cs["_chave_base"] == key].to_dict("records")})

        tm_total = float(pd.to_numeric(df_tm.get("Recebido"), errors="coerce").fillna(0).sum()) if "Recebido" in df_tm else 0.0
        cs_total = float(pd.to_numeric(df_cs.get("Recebido"), errors="coerce").fillna(0).sum()) if "Recebido" in df_cs else 0.0
        tm_liq = float(pd.to_numeric(df_tm.get("Rec Liquido"), errors="coerce").fillna(0).sum()) if "Rec Liquido" in df_tm else 0.0
        cs_liq = float(pd.to_numeric(df_cs.get("RecebimentoLiq"), errors="coerce").fillna(0).sum()) if "RecebimentoLiq" in df_cs else 0.0

        return {
            "total_topmanager": len(df_tm),
            "total_comissys": len(df_cs),
            "em_sincronia": max(0, len(shared) - len(altered) - len(divergent_payloads)),
            "faltando": len(missing),
            "sobrando": len(extra),
            "alterados": len(altered),
            "divergentes": len(divergent_payloads),
            "df_faltando": df_tm[df_tm["_chave"].isin(missing)].copy(),
            "df_sobrando": df_cs[df_cs["_chave"].isin(extra)].copy(),
            "df_alterados": pd.DataFrame(altered),
            "df_divergentes": pd.DataFrame(divergent_payloads),
            "divergencias_totais": {"recebido": diff_receb, "recliq": diff_recliq},
            "totais": {"tm_recebido": tm_total, "cs_recebido": cs_total, "delta_recebido": tm_total - cs_total, "tm_recliq": tm_liq, "cs_recliq": cs_liq, "delta_recliq": tm_liq - cs_liq},
            "vendedor": self.vendedor or "TODOS",
            "periodo": f"{self.competencia_inicio.strftime('%d/%m/%Y')} a {self.competencia_fim.strftime('%d/%m/%Y')}",
            "source_info": {"topmanager": "SQL build_query_866 via DBConfig", "comissys": "dbo.Stik_Extrato_Comissoes"},
            "df_topmanager_full": df_tm.copy(),
            "df_comissys_full": df_cs.copy(),
        }


class SyncService:
    def __init__(self, cfg=None, atualizar_alterados=True, recalcular_comissao=True):
        self.cfg = cfg or DBConfig()
        self.atualizar_alterados = atualizar_alterados
        self.recalcular_comissao = recalcular_comissao

    def analyze(self, competencia_inicio, competencia_fim, vendedor=None):
        return SyncWorker(competencia_inicio, competencia_fim, vendedor, self.cfg).analisar()

    def sync_result(self, resultado):
        tm_full = resultado.get("df_topmanager_full")
        cs_full = resultado.get("df_comissys_full")
        if not isinstance(tm_full, pd.DataFrame):
            tm_full = pd.DataFrame()
        if not isinstance(cs_full, pd.DataFrame):
            cs_full = pd.DataFrame()

        preserve_map = {}
        if not cs_full.empty and "_chave" in cs_full.columns:
            for _, row in cs_full.iterrows():
                preserve_map[row["_chave"]] = {
                    "PercComissao": row.get("PercComissao"),
                    "Observacao": row.get("Observacao"),
                    "Validado": row.get("Validado"),
                    "ValidadoPor": row.get("ValidadoPor"),
                    "ValidadoEm": row.get("ValidadoEm"),
                }

        with get_conn(self.cfg) as conn:
            cur = conn.cursor()
            try:
                removidos = self._delete_scope(cur, resultado)
                inseridos = 0
                params_batch = []
                for _, row in tm_full.iterrows():
                    preserve = preserve_map.get(row.get("_chave"))
                    params_batch.append(
                        build_extrato_insert_params(
                            row,
                            criado_por="Sync-Replace",
                            observacao="Reconstruido por sincronizacao",
                            preserve=preserve,
                        )
                    )
                    inseridos += 1

                if params_batch:
                    try:
                        cur.fast_executemany = True
                    except Exception:
                        pass
                    cur.executemany(EXTRATO_INSERT_SQL, params_batch)

                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return {
            "adicionados": inseridos,
            "atualizados": 0,
            "divergentes": 0,
            "removidos": removidos,
            "total": inseridos + removidos,
        }

    def _insert_row(self, cur, row: pd.Series, criado_por: str, obs: str, preserve: dict[str, Any] | None = None):
        insert_extrato_row(
            cur,
            row,
            criado_por=criado_por,
            observacao=obs,
            preserve=preserve,
        )
        return
        doc_id = int(float(str(row.get("ID")).strip()))
        dt_rec = pd.to_datetime(row.get("Recebimento"), dayfirst=True, errors="coerce")
        dt_rec = None if pd.isna(dt_rec) else dt_rec.date()
        comp = dt_rec.strftime("%Y-%m") if dt_rec else None
        rec_liq = _dec(row.get("Rec Liquido") or row.get("RecebimentoLiq"), 2)
        pct = _dec(
            (preserve or {}).get("PercComissao")
            or row.get("Percentual_Comissao")
            or row.get("% Percentual Padrão")
            or Decimal("5.00"),
            4,
        )
        valor = (rec_liq * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        obs_final = (preserve or {}).get("Observacao") or obs
        validado = 1 if str((preserve or {}).get("Validado")).strip() in ("1", "True", "true") else 0
        validado_por = (preserve or {}).get("ValidadoPor")
        validado_em = (preserve or {}).get("ValidadoEm")
        cur.execute(
            """
            INSERT INTO dbo.Stik_Extrato_Comissoes (
                Competencia, Doc, Cliente, Artigo, Linha, UF,
                DataRecebimento, RecebimentoLiq, PercComissao, ValorComissao,
                Observacao, CriadoPor,
                VendedorID, Vendedor, Titulo, MeioPagamento,
                Emissao, Vencimento, Recebido, ICMSST, Frete,
                PrecoMedio, PrecoVenda, PrazoMedio, Percentual_Comissao,
                Validado, ValidadoPor, ValidadoEm, Consolidado
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,
                     ?,?,?,?,?,?,?,?,?,?,?,?,?, ?, ?, ?, 0)
            """,
            comp,
            doc_id,
            str(row.get("Cliente") or "")[:200] or None,
            str(row.get("Artigo") or "")[:200] or None,
            str(row.get("Linha") or "")[:200] or None,
            str(row.get("UF") or "")[:2] or None,
            dt_rec,
            rec_liq,
            pct,
            valor,
            obs_final,
            criado_por,
            int(float(str(row.get("VendedorID")).strip())) if row.get("VendedorID") not in (None, "") else None,
            str(row.get("Vendedor") or "")[:200] or None,
            str(row.get("Titulo") or "")[:120] or None,
            str(row.get("M Pagamento") or row.get("MeioPagamento") or "")[:100] or None,
            self._to_date(row.get("Emissão") or row.get("Emissao")),
            self._to_date(row.get("Vencimento")),
            _dec(row.get("Recebido"), 2),
            _dec(row.get("ICMSST"), 2),
            _dec(row.get("Frete"), 2),
            _dec(row.get("Preço Médio") or row.get("PrecoMedio"), 4),
            _dec(row.get("Preço Venda") or row.get("PrecoVenda"), 4),
            _dec(row.get("Prazo Médio") or row.get("PrazoMedio"), 2),
            pct,
            validado,
            validado_por,
            validado_em,
        )

    def _to_date(self, value):
        dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
        return None if pd.isna(dt) else dt.date()

    def _add_missing(self, cur, df):
        if df is None or df.empty:
            return 0
        count = 0
        for _, row in df.iterrows():
            self._insert_row(cur, row, "Sync-Auto", "Inserido por sincronizacao")
            count += 1
        return count

    def _update_changed(self, cur, df):
        if df is None or df.empty:
            return 0
        count = 0
        for _, item in df.iterrows():
            dbid = item.get("DBId") or item.get("cs_row", {}).get("DBId")
            if not dbid:
                continue
            tm_row = item.get("tm_row", {})
            diffs = item.get("diffs", {})
            fields, values = [], []
            if "Recebido" in diffs:
                fields.append("Recebido = ?")
                values.append(_dec(tm_row.get("Recebido"), 2))
            if "RecebimentoLiq" in diffs:
                rec_liq = _dec(tm_row.get("Rec Liquido") or tm_row.get("RecebimentoLiq"), 2)
                fields.append("RecebimentoLiq = ?")
                values.append(rec_liq)
                if self.recalcular_comissao:
                    perc = _dec(item.get("cs_row", {}).get("PercComissao"), 4)
                    fields.append("ValorComissao = ?")
                    values.append((rec_liq * perc / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            if "PrecoVenda" in diffs:
                fields.append("PrecoVenda = ?")
                values.append(_dec(tm_row.get("PrecoVenda") or tm_row.get("Preço Venda"), 4))
            if "Titulo" in diffs:
                fields.append("Titulo = ?")
                values.append(str(tm_row.get("Titulo") or "")[:120] or None)
            if "Artigo" in diffs:
                fields.append("Artigo = ?")
                values.append(str(tm_row.get("Artigo") or "")[:200] or None)
            if "DataRecebimento" in diffs:
                fields.append("DataRecebimento = ?")
                values.append(pd.to_datetime(tm_row.get("_Recebimento_iso"), errors="coerce").date())
            if not fields:
                continue
            fields.append("Observacao = ?")
            values.append(f"Atualizado por Sync-Auto em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            values.append(int(dbid))
            cur.execute(f"UPDATE dbo.Stik_Extrato_Comissoes SET {', '.join(fields)} WHERE Id = ? AND Consolidado = 0", values)
            if cur.rowcount > 0:
                count += 1
        return count

    def _rebuild_divergent(self, cur, df):
        if df is None or df.empty:
            return 0
        count = 0
        for _, item in df.iterrows():
            for cs_row in item.get("cs_rows") or []:
                if cs_row.get("DBId"):
                    cur.execute("DELETE FROM dbo.Stik_Extrato_Comissoes WHERE Id = ? AND Consolidado = 0", int(cs_row["DBId"]))
            for tm_row in item.get("tm_rows") or []:
                self._insert_row(cur, pd.Series(tm_row), "Sync-Rebuild", "Reconciliado por sincronizacao")
            count += 1
        return count

    def _remove_extra(self, cur, df):
        if df is None or df.empty:
            return 0
        count = 0
        for _, row in df.iterrows():
            if row.get("DBId"):
                cur.execute("DELETE FROM dbo.Stik_Extrato_Comissoes WHERE Id = ? AND Consolidado = 0", int(row["DBId"]))
                if cur.rowcount > 0:
                    count += 1
        return count

    def _delete_scope(self, cur, resultado):
        vendedor = resultado.get("vendedor")
        periodo = resultado.get("periodo", "")
        try:
            inicio_txt, fim_txt = periodo.split(" a ")
            inicio = pd.to_datetime(inicio_txt, dayfirst=True, errors="coerce").date()
            fim = pd.to_datetime(fim_txt, dayfirst=True, errors="coerce").date()
        except Exception:
            raise ValueError("Período inválido para reconstrução do extrato.")

        if vendedor and vendedor != "TODOS":
            cur.execute(
                """
                DELETE FROM dbo.Stik_Extrato_Comissoes
                WHERE DataRecebimento BETWEEN ? AND ?
                  AND Vendedor = ?
                  AND Consolidado = 0
                """,
                inicio,
                fim,
                vendedor,
            )
        else:
            cur.execute(
                """
                DELETE FROM dbo.Stik_Extrato_Comissoes
                WHERE DataRecebimento BETWEEN ? AND ?
                  AND Consolidado = 0
                """,
                inicio,
                fim,
            )
        return cur.rowcount


class DialogSincronizacao(QDialog):
    def __init__(self, parent=None, cfg=None):
        super().__init__(parent)
        self.cfg = cfg or DBConfig()
        self.resultado = None
        self._setup_ui()
        self._load_vendedores()

    def _setup_ui(self):
        self.setWindowTitle("Sincronizacao TopManager x Comissys")
        self.setMinimumSize(900, 700)
        layout = QVBoxLayout(self)

        filtros = QGroupBox("Escopo")
        filtros_layout = QGridLayout(filtros)
        filtros_layout.addWidget(QLabel("Periodo:"), 0, 0)
        self.dt_inicio = QDateEdit()
        self.dt_inicio.setDisplayFormat("dd/MM/yyyy")
        self.dt_inicio.setCalendarPopup(True)
        self.dt_inicio.setDate(QDate.currentDate().addMonths(-1).addDays(1))
        filtros_layout.addWidget(self.dt_inicio, 0, 1)
        filtros_layout.addWidget(QLabel("ate"), 0, 2)
        self.dt_fim = QDateEdit()
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.dt_fim, 0, 3)
        filtros_layout.addWidget(QLabel("Vendedor:"), 1, 0)
        self.cmb_vendedor = QComboBox()
        self.cmb_vendedor.setMinimumWidth(320)
        filtros_layout.addWidget(self.cmb_vendedor, 1, 1, 1, 3)
        layout.addWidget(filtros)

        opcoes = QGroupBox("Opcoes")
        opcoes_layout = QVBoxLayout(opcoes)
        self.chk_atualizar_alterados = QCheckBox("Atualizar alterados")
        self.chk_atualizar_alterados.setChecked(True)
        self.chk_recalcular_comissao = QCheckBox("Recalcular ValorComissao")
        self.chk_recalcular_comissao.setChecked(True)
        self.chk_gerar_relatorio = QCheckBox("Gerar relatorio e snapshots CSV")
        self.chk_gerar_relatorio.setChecked(True)
        opcoes_layout.addWidget(self.chk_atualizar_alterados)
        opcoes_layout.addWidget(self.chk_recalcular_comissao)
        opcoes_layout.addWidget(self.chk_gerar_relatorio)
        layout.addWidget(opcoes)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_analisar = QPushButton("Analisar Diferencas")
        self.btn_analisar.setObjectName("btnPrimary")
        self.btn_analisar.clicked.connect(self.analisar)
        btn_layout.addWidget(self.btn_analisar)
        self.btn_sincronizar = QPushButton("Sincronizar")
        self.btn_sincronizar.setObjectName("btnSuccess")
        self.btn_sincronizar.setEnabled(False)
        self.btn_sincronizar.clicked.connect(self.sincronizar)
        btn_layout.addWidget(self.btn_sincronizar)
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setObjectName("btnGhost")
        self.btn_fechar.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_fechar)
        layout.addLayout(btn_layout)

    def _load_vendedores(self):
        try:
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT Vendedor FROM dbo.Stik_Extrato_Comissoes WHERE Consolidado = 0 AND Vendedor IS NOT NULL ORDER BY Vendedor")
                vendedores = [r[0] for r in cur.fetchall()]
        except Exception:
            vendedores = []
        self.cmb_vendedor.clear()
        self.cmb_vendedor.addItem("(todos)")
        self.cmb_vendedor.addItems(vendedores)

    def log(self, msg):
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def analisar(self):
        vendedor = self.cmb_vendedor.currentText()
        vendedor = None if vendedor == "(todos)" else vendedor
        inicio = self.dt_inicio.date().toPython()
        fim = self.dt_fim.date().toPython()
        if inicio > fim:
            QMessageBox.warning(self, "Periodo", "Data inicial maior que data final.")
            return
        self.txt_log.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.btn_analisar.setEnabled(False)
        self.btn_sincronizar.setEnabled(False)
        self.worker = SyncWorker(inicio, fim, vendedor, self.cfg)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_analise_concluida)
        self.worker.start()

    def on_analise_concluida(self, resultado):
        self.progress_bar.setVisible(False)
        self.btn_analisar.setEnabled(True)
        if "erro" in resultado:
            self.log(f"ERRO: {resultado['erro']}")
            QMessageBox.critical(self, "Erro", resultado["erro"])
            return
        self.resultado = resultado
        self.log(f"Resumo: TM={resultado['total_topmanager']} | CS={resultado['total_comissys']} | sync={resultado['em_sincronia']} | faltando={resultado['faltando']} | sobrando={resultado['sobrando']} | alterados={resultado['alterados']} | divergentes={resultado['divergentes']}")
        totais = resultado["totais"]
        self.log(f"Recebido origem={fmt_currency(totais['tm_recebido'])} | comissys={fmt_currency(totais['cs_recebido'])}")
        self.log(f"Rec.Liq origem={fmt_currency(totais['tm_recliq'])} | comissys={fmt_currency(totais['cs_recliq'])}")
        if self.chk_gerar_relatorio.isChecked():
            path = self._gerar_relatorio(resultado, "analise")
            self.log(f"Relatorio salvo em {path}")
        total_ops = resultado["faltando"] + resultado["sobrando"] + resultado["alterados"] + resultado["divergentes"]
        self.btn_sincronizar.setEnabled(total_ops > 0)

    def sincronizar(self):
        if not self.resultado:
            return
        total_ops = self.resultado["faltando"] + self.resultado["sobrando"] + self.resultado["alterados"] + self.resultado["divergentes"]
        if total_ops == 0:
            QMessageBox.information(self, "Sincronizacao", "Nada a sincronizar.")
            return
        if QMessageBox.question(self, "Confirmar", f"Serao aplicadas {total_ops} operacao(oes). Continuar?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        try:
            service = SyncService(self.cfg, self.chk_atualizar_alterados.isChecked(), self.chk_recalcular_comissao.isChecked())
            resumo = service.sync_result(self.resultado)
            self.log(f"Sincronizacao concluida: {resumo}")
            if self.chk_gerar_relatorio.isChecked():
                path = self._gerar_relatorio(self.resultado, "concluido")
                self.log(f"Relatorio final salvo em {path}")
            QMessageBox.information(self, "Sucesso", f"Sincronizacao concluida: {resumo['total']} operacao(oes).")
            self.btn_sincronizar.setEnabled(False)
        except Exception as e:
            self.log(f"ERRO: {e}")
            QMessageBox.critical(self, "Erro", str(e))
        finally:
            self.progress_bar.setVisible(False)

    def _gerar_relatorio(self, resultado, stage):
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        vendedor = (resultado.get("vendedor") or "TODOS").replace(" ", "_")
        path = logs_dir / f"sync_{vendedor}_{ts}_{stage}.txt"
        lines = [
            "=" * 80,
            f"RELATORIO DE SINCRONIZACAO - {stage.upper()}",
            "=" * 80,
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Periodo: {resultado.get('periodo', 'N/A')}",
            f"Vendedor: {resultado.get('vendedor', 'N/A')}",
            "",
            "FONTE USADA PELA SINCRONIZACAO:",
            f"  Origem:   {resultado.get('source_info', {}).get('topmanager', 'N/A')}",
            f"  Comissys: {resultado.get('source_info', {}).get('comissys', 'N/A')}",
            "",
            "RESUMO:",
            f"  Total TopManager: {resultado.get('total_topmanager', 0)}",
            f"  Total Comissys: {resultado.get('total_comissys', 0)}",
            f"  Em sincronia: {resultado.get('em_sincronia', 0)}",
            f"  Faltando: {resultado.get('faltando', 0)}",
            f"  Sobrando: {resultado.get('sobrando', 0)}",
            f"  Alterados: {resultado.get('alterados', 0)}",
            f"  Divergentes: {resultado.get('divergentes', 0)}",
            "",
        ]
        totais = resultado.get("totais", {})
        lines += [
            "TOTAIS (Recebido / Rec.Liq):",
            f"  TopManager: {fmt_currency(totais.get('tm_recebido', 0))} / {fmt_currency(totais.get('tm_recliq', 0))}",
            f"  Comissys:   {fmt_currency(totais.get('cs_recebido', 0))} / {fmt_currency(totais.get('cs_recliq', 0))}",
            f"  Diferenca:  {fmt_currency(totais.get('delta_recebido', 0))} / {fmt_currency(totais.get('delta_recliq', 0))}",
            "",
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        tm_full = resultado.get("df_topmanager_full")
        cs_full = resultado.get("df_comissys_full")
        if isinstance(tm_full, pd.DataFrame):
            tm_full.to_csv(logs_dir / f"sync_{vendedor}_{ts}_{stage}_topmanager.csv", index=False, encoding="utf-8-sig")
        if isinstance(cs_full, pd.DataFrame):
            cs_full.to_csv(logs_dir / f"sync_{vendedor}_{ts}_{stage}_comissys.csv", index=False, encoding="utf-8-sig")
        return str(path)
