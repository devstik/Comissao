# models.py
from __future__ import annotations
from typing import List, Any, Set
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit
from PySide6.QtGui import QFont, QColor

_NUMERIC_HINTS = {
    "Recebido","ICMSST","Frete","Rec Liquido",
    "Prazo Médio","Preço Médio","Preço Venda",
    "% Comissão","Valor Comissão"
}
def _is_num(header: str) -> bool:
    h = (header or "").strip()
    return h in _NUMERIC_HINTS or any(x in h.lower() for x in ["preço","receb","prazo","valor","%"])
def _s(v: Any) -> str:
    return "" if v is None else str(v)

class EditableTableModel(QAbstractTableModel):
    def __init__(self, headers: List[str], rows: List[List[Any]]):
        super().__init__()
        self.headers = list(headers)
        self.rows = [list(r) for r in rows]
        self._all_readonly = False
        self._editable_cols: Set[int] = set()
        
        # Estado de ordenação
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder

    # ---- API usada no main.py ----
    def set_all_readonly(self, value: bool):
        self._all_readonly = bool(value)
        tl = self.index(0,0)
        br = self.index(max(0,self.rowCount()-1), max(0,self.columnCount()-1))
        self.dataChanged.emit(tl, br, [Qt.ItemDataRole.EditRole])

    def set_columns_readonly(self, editable_headers: List[str]):
        self._editable_cols.clear()
        allow = set(editable_headers or [])
        for i,h in enumerate(self.headers):
            if h in allow:
                self._editable_cols.add(i)
        tl = self.index(0,0)
        br = self.index(max(0,self.rowCount()-1), max(0,self.columnCount()-1))
        self.dataChanged.emit(tl, br, [Qt.ItemDataRole.EditRole])

    def remove_rows(self, indices: List[int]):
        for r in sorted(indices, reverse=True):
            if 0 <= r < len(self.rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                del self.rows[r]
                self.endRemoveRows()

    # ---- QAbstractTableModel ----
    def rowCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.rows)
    def columnCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        r,c = index.row(), index.column()
        if r<0 or r>=len(self.rows) or c<0 or c>=len(self.headers): return None
        val = self.rows[r][c]; head = self.headers[c]
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return _s(val)
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if _is_num(head):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Destaca a coluna ordenada
        if role == Qt.ItemDataRole.BackgroundRole:
            if c == self._sort_column:
                return QColor(30, 35, 50)
        
        # Coluna ordenada em negrito
        if role == Qt.ItemDataRole.FontRole:
            if c == self._sort_column:
                font = QFont()
                font.setBold(True)
                return font
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                header = self.headers[section] if 0 <= section < len(self.headers) else ""
                # Adiciona seta indicadora de ordenação
                if section == self._sort_column:
                    arrow = " ▲" if self._sort_order == Qt.SortOrder.AscendingOrder else " ▼"
                    return header + arrow
                return header
            
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                if section == self._sort_column:
                    font.setPointSize(font.pointSize() + 1)
                return font
        
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return section + 1
        
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid(): return Qt.ItemFlag.NoItemFlags
        f = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if not self._all_readonly:
            if (not self._editable_cols) or (index.column() in self._editable_cols):
                f |= Qt.ItemFlag.ItemIsEditable
        return f

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid(): return False
        r,c = index.row(), index.column()
        if r<0 or r>=len(self.rows) or c<0 or c>=len(self.headers): return False
        if self._all_readonly: return False
        if self._editable_cols and c not in self._editable_cols: return False
        self.rows[r][c] = (value)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Implementa ordenação inteligente da tabela"""
        if column < 0 or column >= len(self.headers):
            return

        self.layoutAboutToBeChanged.emit()

        self._sort_column = column
        self._sort_order = order

        def convert_value(val):
            if val is None or val == "":
                return ("empty", "")

            val_str = str(val).strip()

            try:
                num_str = val_str.replace(".", "").replace(",", ".")
                num_str = num_str.replace("%", "").strip()
                num_val = float(num_str)
                return ("num", num_val)
            except:
                pass

            if "/" in val_str and len(val_str) == 10:
                try:
                    d, m, y = val_str.split("/")
                    return ("date", f"{y}{m}{d}")
                except:
                    pass

            if "-" in val_str and len(val_str) <= 9:
                month_map = {
                    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
                    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
                    "set": "09", "out": "10", "nov": "11", "dez": "12"
                }
                parts = val_str.lower().split("-")
                if len(parts) == 2 and parts[0] in month_map:
                    return ("comp", f"{parts[1]}{month_map[parts[0]]}")

            return ("str", val_str.lower())

        reverse = (order == Qt.SortOrder.DescendingOrder)
        self.rows.sort(key=lambda row: convert_value(row[column]), reverse=reverse)

        self.layoutChanged.emit()
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(self.headers) - 1)

class DecimalDelegate(QStyledItemDelegate):
    """
    Delegate para formatação automática de decimais
    Usuario digita: 3 → Formata para: 3,0000
    """
    
    def __init__(self, decimal_places=2, parent=None):
        super().__init__(parent)
        self.decimal_places = decimal_places
    
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return editor
    
    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value:
            value_str = str(value).replace(".", "").replace(",", ".")
            try:
                value_float = float(value_str)
                editor.setText(str(value_float))
            except:
                editor.setText(str(value))
        else:
            editor.setText("")
    
    def setModelData(self, editor, model, index):
        from utils.formatters import fmt_num
        
        text = editor.text().strip()
        
        if not text:
            formatted = fmt_num(0, self.decimal_places)
            model.setData(index, formatted, Qt.EditRole)
            return
        
        try:
            value_str = text.replace(",", ".")
            value_float = float(value_str)
            formatted = fmt_num(value_float, self.decimal_places)
            model.setData(index, formatted, Qt.EditRole)
        except ValueError:
            model.setData(index, text, Qt.EditRole)