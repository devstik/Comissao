# rules_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Condition:
    field: str
    op: str
    value: Any

    def match(self, row: Dict[str, Any]) -> bool:
        v = row.get(self.field)

        # normaliza strings
        if isinstance(v, str):
            v_cmp = v.strip().upper()
        else:
            v_cmp = v

        val = self.value
        if isinstance(val, str):
            val_cmp = val.strip().upper()
        else:
            val_cmp = val

        try:
            if self.op == "==":
                return v_cmp == val_cmp
            if self.op == "!=":
                return v_cmp != val_cmp
            if self.op == ">":
                return v_cmp > val_cmp
            if self.op == ">=":
                return v_cmp >= val_cmp
            if self.op == "<":
                return v_cmp < val_cmp
            if self.op == "<=":
                return v_cmp <= val_cmp
            if self.op == "in":
                return v_cmp in val_cmp
        except Exception:
            return False

        return False

@dataclass
class Rule:
    name: str
    priority: int = 0
    enabled: bool = True
    stop_on_match: bool = True
    conditions: List[Condition] = None

    # ações (percentual inteiro: 2.0 = 2%)
    set_percentual: Optional[float] = None   # define o % comissão
    add_percentual: Optional[float] = None   # soma ao % comissão (ex: +1.0)
    note: str = ""

def apply_rules_to_row(row: Dict[str, Any], rules: List[Rule]) -> Tuple[float, str]:
    """
    Retorna: (pct_aplicado, motivo)
    Convenção: percentuais são INTEIROS (5.0 = 5%)
    """
    pct_padrao = float(row.get("% Percentual Padrão") or 0.0)
    pct_atual = float(row.get("% Comissão") or pct_padrao or 0.0)

    motivos: List[str] = []
    rules_sorted = sorted([r for r in rules if r.enabled], key=lambda r: r.priority, reverse=True)

    for rule in rules_sorted:
        conds = rule.conditions or []
        if all(c.match(row) for c in conds):
            before = pct_atual
            if rule.set_percentual is not None:
                pct_atual = float(rule.set_percentual)
            if rule.add_percentual is not None:
                pct_atual = float(pct_atual) + float(rule.add_percentual)

            msg = f"{rule.name} ({before:.4f}→{pct_atual:.4f})"
            if rule.note:
                msg += f" {rule.note}"
            motivos.append(msg)

            if rule.stop_on_match:
                break

    return pct_atual, " | ".join(motivos) if motivos else ""
