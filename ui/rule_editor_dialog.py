# ui/rule_editor_dialog.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton, QWidget,
    QAbstractItemView, QHeaderView, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox, QComboBox, QFrame, QSizePolicy, QScrollArea
)

from rules.rules_store import load_rules, save_rules, normalize_rules
from models import ExcelLikeTableView


OPS = ["==", "!=", ">", ">=", "<", "<=", "in", "contains"]


def _try_number(s: str) -> Any:
    """
    tenta converter string para int/float, senão retorna string original.
    """
    if s is None:
        return ""
    txt = str(s).strip()
    if txt == "":
        return ""
    # vírgula -> ponto
    txt_num = txt.replace(".", "").replace(",", ".") if ("," in txt and txt.count(",") == 1) else txt
    try:
        if "." in txt_num:
            return float(txt_num)
        return int(txt_num)
    except Exception:
        return txt


def _card(title: str) -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    f.setFrameShape(QFrame.NoFrame)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(10)

    lbl = QLabel(title)
    lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff;")
    lay.addWidget(lbl)
    return f


class ConditionRow(QWidget):
    def __init__(self, fields: List[str], parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.cmb_field = QComboBox()
        self.cmb_field.addItems(fields)
        self.cmb_field.setMinimumWidth(200)

        self.cmb_op = QComboBox()
        self.cmb_op.addItems(OPS)
        self.cmb_op.setFixedWidth(90)

        self.ed_value = QLineEdit()
        self.ed_value.setPlaceholderText("Valor (ex: 30, CE, Carlos Pereira, 0.02, A;B;C)")
        self.ed_value.setMinimumWidth(220)

        self.btn_remove = QPushButton("Remover")
        self.btn_remove.setObjectName("btnDanger")
        self.btn_remove.setFixedWidth(110)

        lay.addWidget(self.cmb_field, 2)
        lay.addWidget(self.cmb_op, 0)
        lay.addWidget(self.ed_value, 3)
        lay.addWidget(self.btn_remove, 0)

    def to_dict(self) -> Dict[str, Any]:
        field = self.cmb_field.currentText().strip()
        op = self.cmb_op.currentText().strip()
        raw = self.ed_value.text().strip()

        if op == "in":
            # separa por vírgula ou ponto e vírgula
            parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
            value: Any = [_try_number(p) for p in parts]
        else:
            value = _try_number(raw)

        return {"field": field, "op": op, "value": value}

    def load_from(self, d: Dict[str, Any]) -> None:
        self.cmb_field.setCurrentText(str(d.get("field") or ""))
        self.cmb_op.setCurrentText(str(d.get("op") or "=="))
        v = d.get("value")
        if isinstance(v, list):
            self.ed_value.setText(", ".join(str(x) for x in v))
        else:
            self.ed_value.setText("" if v is None else str(v))


class RuleEditorDialog(QDialog):
    """
    Gerenciador de regras (Opção B):
      - Lista de regras à esquerda
      - Editor completo à direita
      - Condições dinâmicas
      - Salva no rules.json
    """

    def __init__(self, *, rules_path: str, available_fields: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Regras")
        self.resize(1100, 650)

        self.rules_path = rules_path
        self.available_fields = available_fields or [
            "Vendedor", "Cliente", "UF", "Artigo", "Prazo Médio", "Preço Venda",
            "% Percentual Padrão", "% Comissão", "Recebido", "Rec Liquido", "Competência"
        ]

        self._rules: List[Dict[str, Any]] = []
        self._selected_index: Optional[int] = None
        self._condition_rows: List[ConditionRow] = []

        self._build_ui()
        self._reload_rules()

    # ---------------- UI ----------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # LEFT: lista
        left = _card("Regras cadastradas")
        left_lay = left.layout()

        self.tbl_rules = ExcelLikeTableView()
        self.tbl_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_rules.verticalHeader().setVisible(False)
        self.tbl_rules.horizontalHeader().setStretchLastSection(True)
        self.tbl_rules.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.model_rules = QStandardItemModel(0, 5)
        self.model_rules.setHorizontalHeaderLabels(["Nome", "Prioridade", "Set %", "Stop", "Condições"])
        self.tbl_rules.setModel(self.model_rules)

        header = self.tbl_rules.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        left_lay.addWidget(self.tbl_rules)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_reload = QPushButton("Recarregar")
        self.btn_reload.setObjectName("btnSecondary")

        self.btn_new = QPushButton("Nova Regra")
        self.btn_new.setObjectName("btnPrimary")

        self.btn_delete = QPushButton("Excluir")
        self.btn_delete.setObjectName("btnDanger")

        btn_row.addWidget(self.btn_reload)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_delete)

        left_lay.addLayout(btn_row)

        # RIGHT: editor
        right = _card("Editor da regra")
        right_lay = right.layout()

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Nome da regra (ex: Prazo 0-30 sobe 1 ponto)")

        self.spn_priority = QSpinBox()
        self.spn_priority.setRange(-9999, 9999)
        self.spn_priority.setValue(10)

        self.dbl_set_pct = QDoubleSpinBox()
        self.dbl_set_pct.setDecimals(4)
        self.dbl_set_pct.setRange(0.0, 100.0)  # você trabalha em decimal (0.02) ou porcentagem? aqui é livre.
        self.dbl_set_pct.setSingleStep(0.01)

        self.chk_stop = QCheckBox("Parar na primeira regra que bater (stop_on_match)")
        self.chk_stop.setChecked(True)

        self.ed_note = QLineEdit()
        self.ed_note.setPlaceholderText("Observação interna (opcional)")

        form.addWidget(QLabel("Nome:"), 0, 0)
        form.addWidget(self.ed_name, 0, 1, 1, 3)

        form.addWidget(QLabel("Prioridade:"), 1, 0)
        form.addWidget(self.spn_priority, 1, 1)

        form.addWidget(QLabel("Aplicar %:"), 1, 2)
        form.addWidget(self.dbl_set_pct, 1, 3)

        form.addWidget(self.chk_stop, 2, 0, 1, 4)

        form.addWidget(QLabel("Nota:"), 3, 0)
        form.addWidget(self.ed_note, 3, 1, 1, 3)

        right_lay.addLayout(form)

        # Condições (scroll)
        cond_title = QHBoxLayout()
        cond_title.addWidget(QLabel("Condições"))
        cond_title.addStretch()

        self.btn_add_condition = QPushButton("Adicionar condição")
        self.btn_add_condition.setObjectName("btnPrimary")
        self.btn_add_condition.setFixedWidth(170)
        cond_title.addWidget(self.btn_add_condition)

        right_lay.addLayout(cond_title)

        self.cond_scroll = QScrollArea()
        self.cond_scroll.setWidgetResizable(True)
        self.cond_scroll.setFrameShape(QFrame.NoFrame)

        self.cond_container = QWidget()
        self.cond_container_lay = QVBoxLayout(self.cond_container)
        self.cond_container_lay.setContentsMargins(0, 0, 0, 0)
        self.cond_container_lay.setSpacing(8)
        self.cond_container_lay.addStretch()

        self.cond_scroll.setWidget(self.cond_container)
        right_lay.addWidget(self.cond_scroll, 1)

        # botões editor
        editor_btns = QHBoxLayout()
        editor_btns.setSpacing(8)
        editor_btns.addStretch()

        self.btn_save = QPushButton("Salvar")
        self.btn_save.setObjectName("btnSuccess")
        self.btn_save.setFixedWidth(140)

        self.btn_apply_close = QPushButton("Salvar e Fechar")
        self.btn_apply_close.setObjectName("btnPrimary")
        self.btn_apply_close.setFixedWidth(170)

        editor_btns.addWidget(self.btn_save)
        editor_btns.addWidget(self.btn_apply_close)
        right_lay.addLayout(editor_btns)

        # add to root
        left.setMinimumWidth(440)
        root.addWidget(left, 4)
        root.addWidget(right, 6)

        # signals
        self.btn_reload.clicked.connect(self._reload_rules)
        self.btn_new.clicked.connect(self._new_rule)
        self.btn_delete.clicked.connect(self._delete_selected_rule)
        self.btn_add_condition.clicked.connect(lambda: self._add_condition_row())
        self.btn_save.clicked.connect(lambda: self._save_rule(close_after=False))
        self.btn_apply_close.clicked.connect(lambda: self._save_rule(close_after=True))

        self.tbl_rules.selectionModel().selectionChanged.connect(self._on_select_rule)

    # ---------------- Data ----------------

    def _reload_rules(self):
        self._rules = normalize_rules(load_rules(self.rules_path))
        self._selected_index = None
        self._refresh_table()
        self._new_rule(clear_only=True)

    def _refresh_table(self):
        self.model_rules.setRowCount(0)
        for r in self._rules:
            name = str(r.get("name") or "")
            pr = int(r.get("priority") or 0)
            sp = r.get("set_percentual")
            stop = bool(r.get("stop_on_match", True))
            conds = r.get("conditions") or []

            row = [
                QStandardItem(name),
                QStandardItem(str(pr)),
                QStandardItem("" if sp is None else str(sp)),
                QStandardItem("Sim" if stop else "Não"),
                QStandardItem(str(len(conds))),
            ]
            for it in row:
                it.setEditable(False)
            self.model_rules.appendRow(row)

        if self.model_rules.rowCount() == 0:
            # placeholder “vazio”
            pass

    def _on_select_rule(self):
        sel = self.tbl_rules.selectionModel().selectedRows()
        if not sel:
            return
        idx = sel[0].row()
        if 0 <= idx < len(self._rules):
            self._selected_index = idx
            self._load_rule_to_editor(self._rules[idx])

    # ---------------- Editor helpers ----------------

    def _clear_conditions(self):
        # remove widgets
        for w in self._condition_rows:
            w.setParent(None)
            w.deleteLater()
        self._condition_rows.clear()

    def _add_condition_row(self, d: Optional[Dict[str, Any]] = None):
        w = ConditionRow(self.available_fields, parent=self.cond_container)
        w.btn_remove.clicked.connect(lambda: self._remove_condition_row(w))

        # insere antes do stretch final
        self.cond_container_lay.insertWidget(self.cond_container_lay.count() - 1, w)
        self._condition_rows.append(w)

        if d:
            w.load_from(d)

    def _remove_condition_row(self, w: ConditionRow):
        if w in self._condition_rows:
            self._condition_rows.remove(w)
        w.setParent(None)
        w.deleteLater()

    def _new_rule(self, clear_only: bool = False):
        self._selected_index = None
        self.ed_name.setText("")
        self.spn_priority.setValue(10)
        self.dbl_set_pct.setValue(0.0)
        self.chk_stop.setChecked(True)
        self.ed_note.setText("")
        self._clear_conditions()
        self._add_condition_row()
        if not clear_only:
            self.tbl_rules.clearSelection()

    def _load_rule_to_editor(self, r: Dict[str, Any]):
        self.ed_name.setText(str(r.get("name") or ""))
        self.spn_priority.setValue(int(r.get("priority") or 0))

        sp = r.get("set_percentual")
        try:
            self.dbl_set_pct.setValue(float(sp) if sp is not None else 0.0)
        except Exception:
            self.dbl_set_pct.setValue(0.0)

        self.chk_stop.setChecked(bool(r.get("stop_on_match", True)))
        self.ed_note.setText(str(r.get("note") or ""))

        self._clear_conditions()
        conds = r.get("conditions") or []
        if not conds:
            self._add_condition_row()
        else:
            for c in conds:
                if isinstance(c, dict):
                    self._add_condition_row(c)

    def _collect_rule_from_editor(self) -> Tuple[Optional[Dict[str, Any]], str]:
        name = self.ed_name.text().strip()
        if not name:
            return None, "Informe um nome para a regra."

        priority = int(self.spn_priority.value())
        set_pct = float(self.dbl_set_pct.value())
        stop = bool(self.chk_stop.isChecked())
        note = self.ed_note.text().strip()

        conditions = []
        for w in self._condition_rows:
            c = w.to_dict()
            # valida campo e operador
            if not c.get("field") or not c.get("op"):
                continue
            # valor obrigatório
            if c.get("value") in ("", None, []):
                continue
            conditions.append(c)

        if not conditions:
            return None, "Adicione pelo menos 1 condição válida (campo, operador e valor)."

        rule = {
            "name": name,
            "priority": priority,
            "conditions": conditions,
            "set_percentual": set_pct,
            "note": note,
            "stop_on_match": stop,
        }
        return rule, ""

    def _save_rule(self, close_after: bool = False):
        rule, err = self._collect_rule_from_editor()
        if not rule:
            QMessageBox.warning(self, "Regra", err)
            return

        # carrega atual, atualiza, salva
        rules = normalize_rules(load_rules(self.rules_path))

        if self._selected_index is None:
            rules.append(rule)
        else:
            if 0 <= self._selected_index < len(rules):
                rules[self._selected_index] = rule
            else:
                rules.append(rule)

        rules = normalize_rules(rules)
        save_rules(self.rules_path, rules)

        # reload UI
        self._rules = rules
        self._refresh_table()

        # tenta re-selecionar regra pelo nome
        sel_idx = None
        for i, r in enumerate(self._rules):
            if r.get("name") == rule.get("name"):
                sel_idx = i
                break
        if sel_idx is not None:
            self._selected_index = sel_idx
            self.tbl_rules.selectRow(sel_idx)

        if close_after:
            self.accept()
        else:
            QMessageBox.information(self, "Regras", "Regra salva com sucesso.")

    def _delete_selected_rule(self):
        sel = self.tbl_rules.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Regras", "Selecione uma regra para excluir.")
            return

        idx = sel[0].row()
        if not (0 <= idx < len(self._rules)):
            return

        name = str(self._rules[idx].get("name") or "")
        resp = QMessageBox.question(
            self,
            "Excluir regra",
            f"Deseja excluir a regra:\n\n{name}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        rules = normalize_rules(load_rules(self.rules_path))
        if 0 <= idx < len(rules):
            rules.pop(idx)

        save_rules(self.rules_path, normalize_rules(rules))
        self._reload_rules()
