from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd

from utils.formatters import br_to_decimal, br_to_float


EXTRATO_INSERT_SQL = """
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
"""


def insert_extrato_row(
    cur,
    row: dict[str, Any] | pd.Series,
    *,
    pct_comissao: Any = None,
    criado_por: str = "PySide6-App",
    observacao: str | None = None,
    preserve: dict[str, Any] | None = None,
) -> None:
    cur.execute(EXTRATO_INSERT_SQL, build_extrato_insert_params(
        row,
        pct_comissao=pct_comissao,
        criado_por=criado_por,
        observacao=observacao,
        preserve=preserve,
    ))


def build_extrato_insert_params(
    row: dict[str, Any] | pd.Series,
    *,
    pct_comissao: Any = None,
    criado_por: str = "PySide6-App",
    observacao: str | None = None,
    preserve: dict[str, Any] | None = None,
):
    data = row.to_dict() if isinstance(row, pd.Series) else dict(row)
    preserve = preserve or {}

    pct = br_to_decimal(_pick_pct(data, pct_comissao, preserve), 4) or Decimal("0.0000")
    pct_padrao = br_to_decimal(
        data.get("Percentual_Comissao")
        if data.get("Percentual_Comissao") not in (None, "")
        else data.get("% Percentual Padrão")
        if data.get("% Percentual Padrão") not in (None, "")
        else data.get("% Percentual PadrÃ£o")
        if data.get("% Percentual PadrÃ£o") not in (None, "")
        else pct,
        4,
    ) or Decimal("0.0000")

    recebido = br_to_decimal(data.get("Recebido", 0), 2) or Decimal("0.00")
    icmsst = br_to_decimal(data.get("ICMSST", 0), 2) or Decimal("0.00")
    frete = br_to_decimal(data.get("Frete", 0), 2) or Decimal("0.00")

    rec_liq = (recebido - icmsst - frete).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    valor_com = (rec_liq * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    dt_receb = pd.to_datetime(data.get("Recebimento"), dayfirst=True, errors="coerce")
    if pd.isna(dt_receb):
        dt_receb = pd.to_datetime(data.get("DataRecebimentoISO"), errors="coerce")
    competencia = dt_receb.strftime("%Y-%m") if pd.notna(dt_receb) else None

    obs_final = preserve.get("Observacao")
    if obs_final in (None, ""):
        obs_final = observacao
    if obs_final in (None, ""):
        obs_final = data.get("Observação")
    if obs_final in (None, ""):
        obs_final = data.get("Observacao")

    validado_raw = preserve.get("Validado")
    validado = 1 if str(validado_raw).strip().lower() in {"1", "true", "sim"} else 0

    return (
        competencia,
        int(str(data.get("ID", 0)) or 0),
        str(data.get("Cliente", ""))[:200],
        str(data.get("Artigo", ""))[:200],
        str(data.get("Linha", ""))[:200],
        str(data.get("UF", ""))[:2],
        dt_receb.date() if pd.notna(dt_receb) else None,
        rec_liq,
        pct,
        valor_com,
        str(obs_final or "")[:500],
        criado_por,
        int(br_to_float(data.get("VendedorID", 0))) or None,
        str(data.get("Vendedor", ""))[:200] or None,
        str(data.get("Titulo", ""))[:120] or None,
        str(data.get("M Pagamento") or data.get("MeioPagamento") or "")[:100] or None,
        _to_date(data.get("Emissão") or data.get("Emissao") or data.get("EmissÃ£o")),
        _to_date(data.get("Vencimento")),
        recebido,
        icmsst,
        frete,
        br_to_decimal(data.get("Preço Médio") or data.get("PrecoMedio") or data.get("PreÃ§o MÃ©dio"), 4),
        br_to_decimal(data.get("Preço Venda") or data.get("PrecoVenda") or data.get("PreÃ§o Venda"), 4),
        br_to_decimal(data.get("Prazo Médio") or data.get("PrazoMedio") or data.get("Prazo MÃ©dio"), 2),
        pct_padrao,
        validado,
        preserve.get("ValidadoPor"),
        preserve.get("ValidadoEm"),
    )


def _pick_pct(data: dict[str, Any], pct_comissao: Any, preserve: dict[str, Any]) -> Any:
    for value in (
        preserve.get("PercComissao"),
        pct_comissao,
        data.get("% Comissão"),
        data.get("Percentual_Comissao"),
        data.get("% Percentual Padrão"),
        data.get("% Percentual PadrÃ£o"),
        Decimal("0.0000"),
    ):
        if value not in (None, ""):
            return value
    return Decimal("0.0000")


def _to_date(value):
    dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
    return None if pd.isna(dt) else dt.date()
