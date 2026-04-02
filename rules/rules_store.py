# rules/rules_store.py
import json
import os
import tempfile
from typing import Any, Dict, List


def ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def normalize_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Garante campos mínimos e ordena por prioridade (desc) e nome (asc).
    """
    out: List[Dict[str, Any]] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        rr = dict(r)
        rr.setdefault("name", "Regra sem nome")
        rr.setdefault("priority", 0)
        rr.setdefault("conditions", [])
        rr.setdefault("set_percentual", None)
        rr.setdefault("note", "")
        rr.setdefault("stop_on_match", True)

        # garante types básicos
        try:
            rr["priority"] = int(rr.get("priority") or 0)
        except Exception:
            rr["priority"] = 0

        if not isinstance(rr.get("conditions"), list):
            rr["conditions"] = []

        out.append(rr)

    # priority desc, name asc
    out.sort(key=lambda x: (-int(x.get("priority") or 0), str(x.get("name") or "")))
    return out


def save_rules(path: str, rules: List[Dict[str, Any]]) -> None:
    """
    Salva rules.json de forma atômica.
    """
    ensure_parent_dir(path)

    folder = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="rules_", suffix=".tmp", dir=folder)
    os.close(fd)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _backup_corrupted_file(path: str) -> None:
    """
    Se o rules.json estiver corrompido, salva uma cópia .bak antes de resetar.
    """
    try:
        if os.path.exists(path):
            bak = path + ".bak"
            # não sobrescreve bak existente
            if not os.path.exists(bak):
                with open(path, "rb") as src, open(bak, "wb") as dst:
                    dst.write(src.read())
    except Exception:
        # backup é best-effort
        pass


def load_rules(path: str) -> List[Dict[str, Any]]:
    """
    Lê rules.json e retorna lista de regras (dicts).
    Se não existir, cria com [].
    Se corromper, faz backup e volta [] (sem derrubar o app).
    """
    ensure_parent_dir(path)

    if not os.path.exists(path):
        save_rules(path, [])
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = []

        return normalize_rules(data)

    except Exception:
        _backup_corrupted_file(path)
        # reseta pra não travar o app
        try:
            save_rules(path, [])
        except Exception:
            pass
        return []


def add_rule(path: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules = load_rules(path)
    rules.append(rule)
    rules = normalize_rules(rules)
    save_rules(path, rules)
    return rules


def update_rule(path: str, index: int, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules = load_rules(path)
    if 0 <= index < len(rules):
        rules[index] = rule
    rules = normalize_rules(rules)
    save_rules(path, rules)
    return rules


def delete_rule(path: str, index: int) -> List[Dict[str, Any]]:
    rules = load_rules(path)
    if 0 <= index < len(rules):
        rules.pop(index)
    rules = normalize_rules(rules)
    save_rules(path, rules)
    return rules
