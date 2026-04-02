# rules/rules_audit.py
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


def _safe_json(v: Any):
    """Converte tipos não-serializáveis para algo seguro."""
    try:
        json.dumps(v)
        return v
    except Exception:
        return str(v)


def append_jsonl(path: str, event: Dict[str, Any]) -> None:
    """
    Anexa 1 evento em JSONL (1 linha por evento).
    Cria a pasta se não existir.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    clean = {k: _safe_json(v) for k, v in event.items()}

    # Timestamp ISO UTC
    clean.setdefault("ts_utc", datetime.now(timezone.utc).isoformat())

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(clean, ensure_ascii=False) + "\n")


def generate_session_id(username: str) -> str:
    """
    Gera um id de sessão (útil para agrupar eventos de uma mesma ação,
    ex.: "Aplicar Regras" em lote).
    """
    user = (username or "user").strip().lower()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = uuid.uuid4().hex[:8]
    return f"{user}-{stamp}-{short}"


def _to_int_or_none(v: Any) -> Optional[int]:
    """Converte dbid para int quando possível."""
    if v is None:
        return None
    try:
        s = str(v).strip()
        if not s:
            return None
        return int(float(s))  # aceita "123" e "123.0"
    except Exception:
        return None


def build_edit_event(
    *,
    username: str,
    dbid: Optional[int],
    row_context: Dict[str, Any],
    pct_before: Any,
    pct_after: Any,
    valor_before: Any,
    valor_after: Any,
    action: str = "manual_edit",  # manual_edit | apply_rules | etc
    note: str = "",
) -> Dict[str, Any]:
    """
    Monta o evento padrão de auditoria.
    row_context: pode conter Vendedor, Cliente, UF, Artigo, Prazo Médio, etc.
    """
    return {
        "action": action,
        "username": (username or "").strip(),
        "dbid": _to_int_or_none(dbid),
        "note": note,
        "pct_before": pct_before,
        "pct_after": pct_after,
        "valor_before": valor_before,
        "valor_after": valor_after,
        "context": row_context or {},
    }
